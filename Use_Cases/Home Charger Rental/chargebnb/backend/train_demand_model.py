import math
import pickle
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
MODEL_PATH = BASE_DIR / "demand_model.pkl"
PRICE_PATH = BASE_DIR / "data" / "optimal_prices_all_suburbs.csv"
COORDS_PATH = BASE_DIR / "data" / "Co-oridnates.csv"
EVENTS_PATH = ROOT_DIR / "data" / "ml_ev_charging_dataset.csv"

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


def clean_suburb_name(value: str) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371.0 * c


def map_suburb(lat: float, lon: float, coords_df: pd.DataFrame) -> str:
    exact = coords_df[(coords_df["latitude"] == lat) & (coords_df["longitude"] == lon)]
    if not exact.empty:
        return exact.iloc[0]["suburb_clean"]

    distances = coords_df.apply(
        lambda row: haversine_distance(lat, lon, float(row["latitude"]), float(row["longitude"])),
        axis=1
    )
    best_idx = distances.idxmin()
    return coords_df.loc[best_idx, "suburb_clean"]


def prepare_training_data() -> pd.DataFrame:
    prices_df = pd.read_csv(PRICE_PATH)
    prices_df["suburb_clean"] = prices_df["Suburb"].apply(clean_suburb_name)

    coords_df = pd.read_csv(COORDS_PATH)
    coords_df["suburb_clean"] = coords_df["suburb"].apply(clean_suburb_name)

    events_df = pd.read_csv(EVENTS_PATH)
    events_df["Timestamp"] = pd.to_datetime(events_df["Timestamp"])
    events_df["timestamp_hour"] = events_df["Timestamp"].dt.floor("h")

    events_df["suburb_clean"] = events_df.apply(
        lambda row: map_suburb(row["Suburb_Location_Lat"], row["Suburb_Location_Lon"], coords_df),
        axis=1,
    )

    merged = events_df.merge(
        prices_df[["suburb_clean", "Lag_Usage", "Cluster"]],
        on="suburb_clean",
        how="inner",
    )

    grouped = (
        merged
        .groupby(["suburb_clean", "timestamp_hour", "Cluster", "Lag_Usage"], dropna=False)
        .size()
        .reset_index(name="demand")
    )

    grouped["lag_usage"] = grouped["Lag_Usage"].astype(float)
    grouped["hour"] = grouped["timestamp_hour"].dt.hour
    grouped["weekday"] = grouped["timestamp_hour"].dt.weekday
    grouped["hour_sin"] = np.sin(2 * np.pi * grouped["hour"] / 24)
    grouped["hour_cos"] = np.cos(2 * np.pi * grouped["hour"] / 24)
    grouped["weekday_sin"] = np.sin(2 * np.pi * grouped["weekday"] / 7)
    grouped["weekday_cos"] = np.cos(2 * np.pi * grouped["weekday"] / 7)

    for cluster_id in [0, 1, 2]:
        grouped[f"cluster_{cluster_id}"] = (grouped["Cluster"] == cluster_id).astype(float)

    return grouped


def train_model(training_df: pd.DataFrame):
    feature_columns = DEFAULT_FEATURE_COLUMNS
    exog = training_df[feature_columns]
    endog = training_df["demand"]

    print("Training SARIMAX model with", len(training_df), "observations")
    model = SARIMAX(
        endog,
        exog=exog,
        order=(1, 0, 1),
        trend="c",
        enforce_stationarity=False,
        enforce_invertibility=False,
    )

    fitted = model.fit(disp=False)
    print(fitted.summary())

    with open(MODEL_PATH, "wb") as handle:
        pickle.dump(
            {
                "model": fitted,
                "feature_columns": feature_columns,
            },
            handle,
        )

    print("Saved trained demand model to", MODEL_PATH)
    return fitted


def main():
    training_df = prepare_training_data()
    train_model(training_df)


if __name__ == "__main__":
    main()
