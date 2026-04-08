from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path

from pydantic import BaseModel
from typing import Any, Dict, Optional

from datetime import datetime
import math

import sqlite3

try:
    from backend.pricing_engine import estimate_demand, optimize_price
except ImportError:
    from pricing_engine import estimate_demand, optimize_price

app = FastAPI(title="ChargeBnB Backend")

# Allow frontend HTML/JS to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DB_PATH = BASE_DIR / "chargebnb.db"

clustered_df = pd.read_csv(DATA_DIR / "clustered_suburbs.csv")
prices_df = pd.read_csv(DATA_DIR / "optimal_prices_all_suburbs.csv")
chargers_df = pd.read_csv(DATA_DIR / "charger_info_mel.csv")
coords_df = pd.read_csv(DATA_DIR / "Co-oridnates.csv")

PRICE_LOOKUP: Dict[str, Any] = {}
CLUSTER_LABEL_LOOKUP: Dict[str, str] = {}
COORD_LOOKUP: Dict[str, tuple] = {}
CHARGER_SAMPLE_LOOKUP: Dict[str, pd.Series] = {}

class BookingRequest(BaseModel):
    listing_id: str
    suburb: str
    title: str
    start: str
    end: str
    user_id: int
    vehicle: Optional[str] = None
    promo: Optional[str] = None
    quoted_price_per_hour: float
    total_amount: float

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id TEXT NOT NULL,
            suburb TEXT NOT NULL,
            title TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            vehicle TEXT,
            promo TEXT,
            hours REAL NOT NULL,
            quoted_price_per_hour REAL NOT NULL,
            backend_price_per_hour REAL NOT NULL,
            frontend_total_amount REAL NOT NULL,
            backend_expected_total REAL NOT NULL,
            status TEXT NOT NULL,
            time_band TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def clean_suburb_name(value: str) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()

def calculate_booking_hours(start: str, end: str) -> float:
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    hours = (end_dt - start_dt).total_seconds() / 3600
    return round(max(0.0, hours), 2)

def compute_expected_total(price_per_hour: float, hours: float) -> float:
    return round(float(price_per_hour) * float(hours), 2)

def build_lookup_maps() -> None:
    global PRICE_LOOKUP, CLUSTER_LABEL_LOOKUP, COORD_LOOKUP, CHARGER_SAMPLE_LOOKUP

    PRICE_LOOKUP = {
        clean_suburb_name(row["Suburb"]): row
        for _, row in prices_df.iterrows()
    }

    CLUSTER_LABEL_LOOKUP = {
        clean_suburb_name(row["Suburb"]): row.get("Cluster_Label", "Unknown")
        for _, row in clustered_df.iterrows()
    }

    COORD_LOOKUP = {}
    for _, row in coords_df.iterrows():
        suburb_clean = clean_suburb_name(row.get("suburb", row.get("Suburb", "")))
        if not suburb_clean:
            continue

        latitude = float(row["latitude"]) if "latitude" in row.index and pd.notna(row["latitude"]) else None
        longitude = float(row["longitude"]) if "longitude" in row.index and pd.notna(row["longitude"]) else None
        COORD_LOOKUP[suburb_clean] = (latitude, longitude)

    CHARGER_SAMPLE_LOOKUP = {}
    for _, row in chargers_df.iterrows():
        suburb_clean = clean_suburb_name(row.get("suburb", row.get("Suburb", "")))
        if suburb_clean:
            CHARGER_SAMPLE_LOOKUP.setdefault(suburb_clean, row)

def has_overlapping_booking(listing_id: str, start: str, end: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM bookings
        WHERE listing_id = ?
          AND status = 'confirmed'
          AND start < ?
          AND end > ?
        LIMIT 1
    """, (listing_id, end, start))

    row = cursor.fetchone()
    conn.close()

    return row is not None

def is_listing_available(listing_id: str, start: str | None = None, end: str | None = None) -> tuple[bool, str]:
    if not start or not end:
        return True, "No time window provided"

    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return False, "Invalid datetime format"

    if end_dt <= start_dt:
        return False, "End time must be after start time"

    if has_overlapping_booking(listing_id, start, end):
        return False, "Already booked for selected time"

    return True, "Available"


def get_suburb_coordinates(suburb_clean: str):
    return COORD_LOOKUP.get(suburb_clean, (None, None))


def get_suburb_charger_sample(suburb_clean: str):
    row = CHARGER_SAMPLE_LOOKUP.get(suburb_clean)
    if row is None:
        return {
            "connector": "Type 2",
            "kw": 7
        }

    possible_connector_cols = ["Connector", "Connector Type", "connector_type", "Charger Type", "Type"]
    possible_kw_cols = ["kW", "KW", "Power", "Power (kW)", "Charger Power"]

    connector = next(
        (str(row[col]).strip() for col in possible_connector_cols if col in row.index and pd.notna(row[col])),
        "Type 2"
    )

    kw = None
    for col in possible_kw_cols:
        if col in row.index and pd.notna(row[col]):
            try:
                kw = float(row[col])
            except Exception:
                kw = None
            break

    return {
        "connector": connector,
        "kw": float(kw) if kw is not None else 7
    }

clustered_df["suburb_clean"] = clustered_df["Suburb"].apply(clean_suburb_name)
prices_df["suburb_clean"] = prices_df["Suburb"].apply(clean_suburb_name)

if "Suburb" in chargers_df.columns:
    chargers_df["suburb_clean"] = chargers_df["Suburb"].apply(clean_suburb_name)
elif "suburb" in chargers_df.columns:
    chargers_df["suburb_clean"] = chargers_df["suburb"].apply(clean_suburb_name)

if "suburb" in coords_df.columns:
    coords_df["suburb_clean"] = coords_df["suburb"].apply(clean_suburb_name)
elif "Suburb" in coords_df.columns:
    coords_df["suburb_clean"] = coords_df["Suburb"].apply(clean_suburb_name)

@app.on_event("startup")
def startup():
    init_db()
    build_lookup_maps()

@app.get("/")
def home():
    return {"message": "ChargeBnB backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/listings")
def get_listings(start: str | None = None, end: str | None = None):
    listings = []

    for _, row in prices_df.iterrows():
        suburb = row["Suburb"]
        suburb_clean = row["suburb_clean"]
        cluster = int(row["Cluster"])
        optimal_price = float(row["Optimal_Price"])

        cluster_label = CLUSTER_LABEL_LOOKUP.get(suburb_clean, "Unknown")
        lat, lng = get_suburb_coordinates(suburb_clean)
        charger_info = get_suburb_charger_sample(suburb_clean)

        listing_id = suburb_clean.replace(" ", "_")
        available, availability_reason = is_listing_available(listing_id, start, end)

        listings.append({
            "id": listing_id,
            "title": f"Charger in {suburb}",
            "suburb": suburb,
            "cluster": cluster,
            "cluster_label": cluster_label,
            "price_per_hour": round(optimal_price, 2),
            "available": available,
            "availability_reason": availability_reason,
            "connector": charger_info["connector"],
            "kw": charger_info["kw"],
            "lat": lat,
            "lng": lng
        })

    return {
        "count": len(listings),
        "start": start,
        "end": end,
        "listings": listings
    }

@app.get("/pricing")
def get_pricing(suburb: str, start: str | None = None):
    suburb_clean = clean_suburb_name(suburb)
    row = PRICE_LOOKUP.get(suburb_clean)

    if row is None:
        return {
            "found": False,
            "message": f"No pricing data found for suburb: {suburb}"
        }

    base_price = float(row["Optimal_Price"])
    lag_usage = float(row["Lag_Usage"])

    if start:
        try:
            dt = datetime.fromisoformat(start)
        except ValueError:
            return {
                "found": False,
                "message": "Invalid datetime format for 'start'. Use ISO format like 2026-04-05T18:00"
            }
    else:
        dt = datetime.now()

    pricing = estimate_demand(row["Suburb"], lag_usage, dt, int(row["Cluster"]))
    optimization = optimize_price(base_price, pricing["expected_demand"], pricing["time_band"])

    time_band = pricing["time_band"]
    demand_multiplier = pricing["demand_multiplier"]
    expected_demand = pricing["expected_demand"]
    confidence_score = pricing.get("confidence_score", 0.0)
    dynamic_price = optimization["recommended_price"]
    expected_revenue = optimization["expected_revenue"]

    return {
        "found": True,
        "suburb": row["Suburb"],
        "cluster": int(row["Cluster"]),
        "lag_usage": round(lag_usage, 2),
        "base_price": round(base_price, 2),
        "recommended_price": dynamic_price,
        "demand_multiplier": demand_multiplier,
        "expected_demand": expected_demand,
        "expected_revenue": expected_revenue,
        "confidence_score": confidence_score,
        "price_floor": optimization["price_floor"],
        "price_cap": optimization["price_cap"],
        "price_band": optimization["price_band"],
        "time_band": time_band,
        "start_time_used": dt.isoformat(timespec="minutes")
    }

@app.post("/bookings")
def create_booking(payload: BookingRequest):
    try:
        start_dt = datetime.fromisoformat(payload.start)
        end_dt = datetime.fromisoformat(payload.end)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format for start or end")

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    booking_hours = calculate_booking_hours(payload.start, payload.end)

    if booking_hours <= 0:
        raise HTTPException(status_code=400, detail="Booking duration must be greater than zero")

    if has_overlapping_booking(payload.listing_id, payload.start, payload.end):
        raise HTTPException(
            status_code=409,
            detail="This listing is already booked for the selected time range"
        )

    pricing_data = get_pricing(payload.suburb, payload.start)

    if not pricing_data.get("found"):
        raise HTTPException(status_code=404, detail=f"No pricing found for suburb: {payload.suburb}")

    recommended_price = float(pricing_data["recommended_price"])
    expected_total = compute_expected_total(recommended_price, booking_hours)
    frontend_total_amount = compute_expected_total(payload.quoted_price_per_hour, booking_hours)

    if abs(payload.total_amount - frontend_total_amount) > 0.01:
        frontend_total_amount = compute_expected_total(payload.quoted_price_per_hour, booking_hours)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bookings (
            listing_id, suburb, title, start, end, user_id, vehicle, promo,
            hours, quoted_price_per_hour, backend_price_per_hour,
            frontend_total_amount, backend_expected_total, status, time_band
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload.listing_id,
        payload.suburb,
        payload.title,
        payload.start,
        payload.end,
        payload.user_id,
        payload.vehicle,
        payload.promo,
        booking_hours,
        payload.quoted_price_per_hour,
        recommended_price,
        frontend_total_amount,
        expected_total,
        "confirmed",
        pricing_data["time_band"]
    ))

    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()

    return {
        "success": True,
        "message": "Booking created successfully",
        "booking": {
            "booking_id": booking_id,
            "listing_id": payload.listing_id,
            "suburb": payload.suburb,
            "title": payload.title,
            "start": payload.start,
            "end": payload.end,
            "user_id": payload.user_id,
            "vehicle": payload.vehicle,
            "promo": payload.promo,
            "hours": booking_hours,
            "quoted_price_per_hour": payload.quoted_price_per_hour,
            "backend_price_per_hour": recommended_price,
            "frontend_total_amount": payload.total_amount,
            "backend_expected_total": expected_total,
            "status": "confirmed",
            "time_band": pricing_data["time_band"]
        }
    }

@app.get("/bookings")
def get_bookings():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings ORDER BY booking_id DESC")
    rows = cursor.fetchall()
    conn.close()

    bookings = [dict(row) for row in rows]

    return {
        "count": len(bookings),
        "bookings": bookings
    }

@app.get("/bookings/{booking_id}")
def get_booking_by_id(booking_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    return dict(row)

@app.get("/host/bookings")
def get_host_bookings(listing_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM bookings
        WHERE listing_id = ?
        ORDER BY start DESC
    """, (listing_id,))

    rows = cursor.fetchall()
    conn.close()

    bookings = [dict(row) for row in rows]

    return {
        "listing_id": listing_id,
        "count": len(bookings),
        "bookings": bookings
    }

@app.get("/host/summary")
def get_host_summary(listing_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) AS total_bookings,
            COALESCE(SUM(backend_expected_total), 0) AS total_earnings
        FROM bookings
        WHERE listing_id = ?
          AND status = 'confirmed'
    """, (listing_id,))

    row = cursor.fetchone()
    conn.close()

    total_bookings = int(row["total_bookings"]) if row else 0
    total_earnings = float(row["total_earnings"]) if row else 0.0

    return {
        "listing_id": listing_id,
        "total_bookings": total_bookings,
        "total_earnings": round(total_earnings, 2)
    }