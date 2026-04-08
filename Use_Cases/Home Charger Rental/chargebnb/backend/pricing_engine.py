import pickle
from functools import lru_cache
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict

import numpy as np
import pandas as pd

MODEL_FILENAME = Path(__file__).resolve().parent / "demand_model.pkl"
DEFAULT_FEATURE_COLUMNS = [
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "lag_usage",
    "cluster_0",
    "cluster_1",
    "cluster_2",
]

MIN_PRICE_RATIO = 0.75
MAX_PRICE_RATIO = 1.40
ABSOLUTE_MIN_PRICE = 2.5
CACHE_TIME_FORMAT = "%Y-%m-%dT%H:%M"
FALLBACK_CONFIDENCE = 0.50


def clean_suburb_name(value: str) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def load_demand_model() -> Tuple[Optional[object], list]:
    if not MODEL_FILENAME.exists():
        return None, DEFAULT_FEATURE_COLUMNS

    with open(MODEL_FILENAME, "rb") as handle:
        payload = pickle.load(handle)

    model = payload.get("model")
    feature_columns = payload.get("feature_columns", DEFAULT_FEATURE_COLUMNS)
    return model, feature_columns


DEMAND_MODEL, MODEL_FEATURE_COLUMNS = load_demand_model()


def get_time_band(dt: datetime) -> str:
    hour = dt.hour

    if 7 <= hour < 10 or 17 <= hour < 21:
        return "peak"
    if 10 <= hour < 17:
        return "standard"
    return "off_peak"


def get_fallback_demand_multiplier(dt: datetime) -> float:
    band = get_time_band(dt)
    if band == "peak":
        base = 1.20
    elif band == "standard":
        base = 1.00
    else:
        base = 0.80

    weekend_adjustment = 0.92 if dt.weekday() >= 5 else 1.0
    return round(base * weekend_adjustment, 3)


def build_demand_features(cluster: int, lag_usage: float, dt: datetime) -> pd.DataFrame:
    hour = dt.hour
    weekday = dt.weekday()

    raw_row = {
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
        "weekday_sin": np.sin(2 * np.pi * weekday / 7),
        "weekday_cos": np.cos(2 * np.pi * weekday / 7),
        "lag_usage": float(lag_usage),
        "cluster_0": 1.0 if cluster == 0 else 0.0,
        "cluster_1": 1.0 if cluster == 1 else 0.0,
        "cluster_2": 1.0 if cluster == 2 else 0.0,
    }

    feature_columns = MODEL_FEATURE_COLUMNS or DEFAULT_FEATURE_COLUMNS
    row = {col: raw_row.get(col, 0.0) for col in feature_columns}
    return pd.DataFrame([row], columns=feature_columns)


def predict_demand_with_model(feature_df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
    if DEMAND_MODEL is None:
        return None, None

    try:
        forecast = DEMAND_MODEL.get_forecast(steps=1, exog=feature_df)
        predicted = float(forecast.predicted_mean.iloc[0])
        uncertainty = None
        if hasattr(forecast, "se_mean"):
            try:
                uncertainty = float(forecast.se_mean.iloc[0])
            except Exception:
                uncertainty = None
        return predicted, uncertainty
    except Exception:
        return None, None


def format_datetime_for_cache(dt: datetime) -> str:
    return dt.replace(second=0, microsecond=0).isoformat(timespec="minutes")


def compute_confidence(expected_demand: float, uncertainty: Optional[float]) -> float:
    if uncertainty is None or expected_demand <= 0:
        return FALLBACK_CONFIDENCE

    score = 1.0 - min(0.95, uncertainty / max(expected_demand, 1.0))
    return round(float(max(0.0, min(1.0, score))), 2)


@lru_cache(maxsize=256)
def _compute_cached_demand(
    suburb: str,
    cluster: int,
    lag_usage: float,
    dt_key: str,
) -> Dict[str, object]:
    dt = datetime.fromisoformat(dt_key)
    return _compute_demand(suburb, cluster, lag_usage, dt)


def _compute_demand(suburb: str, cluster: int, lag_usage: float, dt: datetime) -> Dict[str, object]:
    time_band = get_time_band(dt)
    demand_multiplier = get_fallback_demand_multiplier(dt)
    feature_df = build_demand_features(cluster, lag_usage, dt)

    predicted_demand, uncertainty = predict_demand_with_model(feature_df)
    if predicted_demand is None or predicted_demand < 0:
        expected_demand = round(max(0.0, lag_usage * demand_multiplier), 2)
        confidence_score = FALLBACK_CONFIDENCE
        model_used = False
    else:
        expected_demand = round(float(predicted_demand), 2)
        confidence_score = compute_confidence(expected_demand, uncertainty)
        demand_multiplier = round(expected_demand / lag_usage, 3) if lag_usage > 0 else demand_multiplier
        model_used = True

    return {
        "suburb": suburb,
        "cluster": cluster,
        "time_band": time_band,
        "demand_multiplier": demand_multiplier,
        "expected_demand": expected_demand,
        "confidence_score": confidence_score,
        "model_used": model_used,
    }


def estimate_demand(suburb: str, lag_usage: float, dt: datetime, cluster: Optional[int] = None) -> dict:
    if cluster is None:
        cluster = 0

    suburb_key = clean_suburb_name(suburb)
    cache_key = format_datetime_for_cache(dt)
    return _compute_cached_demand(suburb_key, int(cluster), round(float(lag_usage), 2), cache_key)


def get_price_elasticity(time_band: str) -> float:
    elasticities = {
        "peak": 0.18,
        "standard": 0.13,
        "off_peak": 0.08,
    }
    return elasticities.get(time_band, 0.12)


def calculate_price_bounds(base_price: float) -> Tuple[float, float]:
    floor = max(ABSOLUTE_MIN_PRICE, base_price * MIN_PRICE_RATIO)
    cap = max(base_price * MAX_PRICE_RATIO, base_price + 2.0)
    if cap <= floor:
        cap = floor * 1.2 + 0.1
    return round(float(floor), 2), round(float(cap), 2)


def get_price_band(recommended_price: float, base_price: float, price_floor: float, price_cap: float) -> str:
    ratio = recommended_price / base_price if base_price > 0 else 1.0
    if recommended_price <= price_floor + 0.01 or ratio <= 0.95:
        return "low"
    if recommended_price >= price_cap - 0.01 or ratio >= 1.15:
        return "surge"
    return "optimal"


def optimize_price(base_price: float, expected_demand: float, time_band: str) -> dict:
    if base_price <= 0 or expected_demand <= 0:
        price_floor, price_cap = calculate_price_bounds(base_price)
        recommended_price = round(float(base_price), 2)
        price_band = get_price_band(recommended_price, base_price, price_floor, price_cap)
        return {
            "recommended_price": recommended_price,
            "expected_demand": round(float(expected_demand), 2),
            "expected_revenue": round(float(base_price * expected_demand), 2),
            "price_floor": price_floor,
            "price_cap": price_cap,
            "price_band": price_band,
        }

    price_floor, price_cap = calculate_price_bounds(base_price)
    candidate_prices = np.linspace(price_floor, price_cap, 11)

    elasticity = get_price_elasticity(time_band)
    price_ratio = candidate_prices / base_price
    demand_adjustment = np.exp(-elasticity * np.maximum(0.0, price_ratio - 1.0))
    candidate_demand = expected_demand * demand_adjustment
    candidate_revenue = candidate_prices * candidate_demand

    best_index = int(np.argmax(candidate_revenue))
    recommended_price = round(float(candidate_prices[best_index]), 2)
    expected_demand_at_price = round(float(candidate_demand[best_index]), 2)
    expected_revenue = round(float(candidate_revenue[best_index]), 2)
    price_band = get_price_band(recommended_price, base_price, price_floor, price_cap)

    return {
        "recommended_price": recommended_price,
        "expected_demand": expected_demand_at_price,
        "expected_revenue": expected_revenue,
        "price_floor": price_floor,
        "price_cap": price_cap,
        "price_band": price_band,
    }
