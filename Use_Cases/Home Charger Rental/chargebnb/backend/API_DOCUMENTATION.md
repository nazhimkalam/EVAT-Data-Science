# ChargeBnB API Documentation

## Overview

ChargeBnB is an AI-powered EV charger rental platform that enables homeowners to list their EV chargers and optimize pricing based on demand forecasting. The backend API provides endpoints for:

- **Charger Discovery:** Browse available chargers by location with real-time availability
- **Smart Pricing:** Dynamic pricing based on demand forecasting using machine learning
- **Booking Management:** Create and manage EV charger bookings
- **Host Dashboard:** Track bookings and earnings for listed chargers

---

## Base URL

**Development:** `http://localhost:8001`

**Production:** Configure in environment variables

---

## Quick Start

### Prerequisites

- Python 3.8+
- FastAPI
- Pandas
- SQLite3
- Dependencies from `requirements.txt`

### Installation & Setup

1. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn pandas pydantic python-dateutil
   ```

2. **Prepare data files** (place in `backend/data/` directory):
   - `clustered_suburbs.csv` — Suburb cluster assignments
   - `optimal_prices_all_suburbs.csv` — Base pricing data
   - `charger_info_mel.csv` — Charger specifications (connector type, power)
   - `Co-oridnates.csv` — Geographic coordinates for map display

3. **Run the backend:**
   ```bash
   cd backend
   python main.py
   ```

   Expected output:
   ```
   ============================================================
   CHARGEBNB BACKEND STARTUP
   ============================================================
   Initializing database...
   ✓ Database initialized
   Loading data files...
   ✓ Data files loaded
   Processing data lookups...
   ✓ Data lookups loaded
   ============================================================
   ✓ STARTUP COMPLETE - Ready to accept requests
   ============================================================
   ```

4. **Access the API:**
   - Health check: `curl http://localhost:8001/health`
   - API docs (Swagger UI): `http://localhost:8001/docs`

---

## API Endpoints

### 1. Home Endpoint

**GET** `/`

Returns a simple welcome message to verify the backend is running.

#### Request
```bash
curl -X GET http://localhost:8001/
```

#### Response
```json
{
  "message": "ChargeBnB backend is running"
}
```

#### Status Codes
- **200 OK** — Backend is running

---

### 2. Health Check

**GET** `/health`

Used to verify the backend service is healthy and responsive. Useful for monitoring and load balancers.

#### Request
```bash
curl -X GET http://localhost:8001/health
```

#### Response
```json
{
  "status": "ok"
}
```

#### Status Codes
- **200 OK** — Service is healthy

#### Usage in Project
- Called by frontend on application startup to verify backend availability
- Used in monitoring dashboards

---

### 3. Get Charger Listings

**GET** `/listings`

Retrieves all available EV chargers with their details, pricing, and availability status. Optionally filter by time window for booking availability.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start` | string (ISO 8601) | Optional | Start datetime for availability check (format: `2026-04-05T18:00`) |
| `end` | string (ISO 8601) | Optional | End datetime for availability check (format: `2026-04-05T20:00`) |

#### Request

**Without time filter:**
```bash
curl -X GET http://localhost:8001/listings
```

**With time filter:**
```bash
curl -X GET "http://localhost:8001/listings?start=2026-04-05T18:00&end=2026-04-05T20:00"
```

#### Response

```json
{
  "count": 302,
  "start": "2026-04-05T18:00",
  "end": "2026-04-05T20:00",
  "listings": [
    {
      "id": "south_melbourne",
      "title": "Charger in South Melbourne",
      "suburb": "South Melbourne",
      "cluster": 0,
      "cluster_label": "Inner Suburbs",
      "price_per_hour": 3.75,
      "available": true,
      "availability_reason": "Available",
      "connector": "Type 2",
      "kw": 7,
      "lat": -37.8519,
      "lng": 144.8474
    },
    {
      "id": "brighton",
      "title": "Charger in Brighton",
      "suburb": "Brighton",
      "cluster": 1,
      "cluster_label": "Bayside Suburbs",
      "price_per_hour": 3.45,
      "available": false,
      "availability_reason": "Already booked for selected time",
      "connector": "Type 2",
      "kw": 11,
      "lat": -37.8764,
      "lng": 144.9967
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Total number of chargers in the response |
| `start` | string | The start datetime passed in the request (null if not provided) |
| `end` | string | The end datetime passed in the request (null if not provided) |
| `listings` | array | Array of charger objects |
| `listings[].id` | string | Unique charger identifier (suburb name with underscores) |
| `listings[].title` | string | Display title for the charger |
| `listings[].suburb` | string | Suburb name where charger is located |
| `listings[].cluster` | integer | Geographic cluster ID (0-2 for Melbourne) |
| `listings[].cluster_label` | string | Human-readable cluster name (e.g., "Inner Suburbs") |
| `listings[].price_per_hour` | number | Current hourly rental price in AUD |
| `listings[].available` | boolean | Whether charger is available for the requested time window |
| `listings[].availability_reason` | string | Reason if unavailable (e.g., "Already booked for selected time") |
| `listings[].connector` | string | Charger connector type (e.g., "Type 2") |
| `listings[].kw` | number | Charger power output in kilowatts |
| `listings[].lat` | number | Geographic latitude for map display |
| `listings[].lng` | number | Geographic longitude for map display |

#### Status Codes
- **200 OK** — Listings retrieved successfully

#### Notes
- If `start` and `end` are provided, availability is checked against existing confirmed bookings
- All prices are in AUD (Australian Dollars)
- Geographic coordinates are for Melbourne metropolitan area
- Chargers are sourced from the Melbourne EV charging network dataset

#### Usage in Project
- Called when user visits the "Available Chargers" section
- Used to populate the scrollable charger cards list
- Time parameters are populated from the user's booking date/time selection

---

### 4. Get Pricing Information

**GET** `/pricing`

Calculates dynamic pricing for a specific suburb based on demand forecasting ML model. Returns base price, recommended price, demand metrics, and pricing bands.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `suburb` | string | Yes | Suburb name (e.g., "South Melbourne", "Brighton") |
| `start` | string (ISO 8601) | Optional | Start datetime for demand calculation (format: `2026-04-05T18:00`). If not provided, uses current time. |

#### Request

**Without time parameter (uses current time):**
```bash
curl -X GET "http://localhost:8001/pricing?suburb=South%20Melbourne"
```

**With time parameter:**
```bash
curl -X GET "http://localhost:8001/pricing?suburb=South%20Melbourne&start=2026-04-05T18:00"
```

#### Response

```json
{
  "found": true,
  "suburb": "South Melbourne",
  "cluster": 0,
  "lag_usage": 45.32,
  "base_price": 3.75,
  "recommended_price": 4.50,
  "demand_multiplier": 1.20,
  "expected_demand": 54.38,
  "expected_revenue": 9.00,
  "confidence_score": 0.82,
  "price_floor": 2.50,
  "price_cap": 7.50,
  "price_band": "premium",
  "time_band": "evening",
  "start_time_used": "2026-04-05T18:00"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `found` | boolean | Whether pricing data was found for the suburb |
| `suburb` | string | Suburb name |
| `cluster` | integer | Geographic cluster ID |
| `lag_usage` | number | Previous hour's demand (historical lag) |
| `base_price` | number | Base hourly rate in AUD without demand adjustments |
| `recommended_price` | number | AI-recommended price based on demand forecasting |
| `demand_multiplier` | number | Factor by which demand exceeds baseline (1.0 = baseline) |
| `expected_demand` | number | Forecasted demand in kW for the time slot |
| `expected_revenue` | number | Expected revenue in AUD from booking at recommended price |
| `confidence_score` | number | ML model confidence score (0.0-1.0) in the prediction |
| `price_floor` | number | Minimum allowed price in AUD |
| `price_cap` | number | Maximum allowed price in AUD |
| `price_band` | string | Price tier ("economy", "standard", "premium", "peak") |
| `time_band` | string | Time-of-day category ("morning", "afternoon", "evening", "night") |
| `start_time_used` | string | The actual time used for calculation (ISO 8601) |

#### Status Codes
- **200 OK** — Pricing calculated successfully
- **404 NOT FOUND** — No pricing data found for the suburb

#### Error Response Example

```json
{
  "found": false,
  "message": "No pricing data found for suburb: InvalidSuburb"
}
```

#### How Pricing Works

1. **Demand Forecasting:** XGBoost ML model predicts expected demand based on:
   - Time of day (morning, afternoon, evening, night)
   - Day of week
   - Historical usage patterns
   - Weather factors (temperature, humidity, wind)
   - Seasonal trends

2. **Price Optimization:** Recommended price is calculated using:
   - Base price from pricing dataset
   - Demand multiplier (high demand → higher price)
   - Price floor/cap constraints (prevent extreme pricing)
   - Expected revenue maximization

3. **Confidence Score:** Indicates reliability of the demand prediction:
   - 0.80+ = High confidence
   - 0.70-0.79 = Moderate confidence
   - Below 0.70 = Low confidence (use with caution)

#### Usage in Project
- Called when user clicks "View Pricing" on a charger
- Used to display dynamic pricing breakdown in the booking modal
- Determines whether to show "Premium", "Standard", or "Economy" pricing indicators
- Helps users understand price basis and demand factors

---

### 5. Create a Booking

**POST** `/bookings`

Creates a new confirmed booking for an EV charger. Validates availability, calculates hours, and stores booking details with both frontend and backend pricing.

#### Request Body

```json
{
  "listing_id": "south_melbourne",
  "suburb": "South Melbourne",
  "title": "Charger in South Melbourne",
  "start": "2026-04-05T18:00",
  "end": "2026-04-05T20:00",
  "user_id": 1,
  "vehicle": "Tesla Model 3",
  "promo": "WELCOME10",
  "quoted_price_per_hour": 3.75,
  "total_amount": 7.50,
  "hours": 2.0,
  "discount_applied": "WELCOME10",
  "discount_amount": 0.75
}
```

#### Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `listing_id` | string | Yes | Unique charger ID (from listings endpoint) |
| `suburb` | string | Yes | Suburb name for the charger |
| `title` | string | Yes | Display title of the charger |
| `start` | string (ISO 8601) | Yes | Booking start time (format: `2026-04-05T18:00`) |
| `end` | string (ISO 8601) | Yes | Booking end time (format: `2026-04-05T20:00`) |
| `user_id` | integer | Optional | User ID (defaults to 1 if not provided) |
| `vehicle` | string | Optional | Vehicle details (e.g., "Tesla Model 3") |
| `promo` | string | Optional | Promotional code applied |
| `quoted_price_per_hour` | number | Yes | Price per hour shown to user (before discounts) |
| `total_amount` | number | Yes | Total amount paid by user (after discounts) |
| `hours` | number | Optional | Booking duration in hours |
| `discount_applied` | string | Optional | Name of discount applied |
| `discount_amount` | number | Optional | Discount amount in AUD |

#### Request Example

```bash
curl -X POST http://localhost:8001/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "listing_id": "south_melbourne",
    "suburb": "South Melbourne",
    "title": "Charger in South Melbourne",
    "start": "2026-04-05T18:00",
    "end": "2026-04-05T20:00",
    "user_id": 1,
    "vehicle": "Tesla Model 3",
    "promo": null,
    "quoted_price_per_hour": 3.75,
    "total_amount": 7.50
  }'
```

#### Response

```json
{
  "success": true,
  "message": "Booking created successfully",
  "booking": {
    "booking_id": 42,
    "listing_id": "south_melbourne",
    "suburb": "South Melbourne",
    "title": "Charger in South Melbourne",
    "start": "2026-04-05T18:00",
    "end": "2026-04-05T20:00",
    "user_id": 1,
    "vehicle": "Tesla Model 3",
    "promo": null,
    "hours": 2.0,
    "quoted_price_per_hour": 3.75,
    "backend_price_per_hour": 4.50,
    "frontend_total_amount": 7.50,
    "backend_expected_total": 9.00,
    "status": "confirmed",
    "time_band": "evening"
  }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether booking was created successfully |
| `message` | string | Success or error message |
| `booking.booking_id` | integer | Unique booking identifier (database ID) |
| `booking.hours` | number | Calculated booking duration in hours |
| `booking.backend_price_per_hour` | number | AI-optimized price calculated by backend |
| `booking.backend_expected_total` | number | Backend's expected total revenue |
| `booking.frontend_total_amount` | number | Amount actually paid by user (frontend-quoted) |
| `booking.status` | string | Always "confirmed" for successful bookings |
| `booking.time_band` | string | Time-of-day category (morning, afternoon, evening, night) |

#### Status Codes
- **200 OK** — Booking created successfully
- **400 BAD REQUEST** — Invalid request body, datetime format, or booking duration ≤ 0
- **404 NOT FOUND** — Suburb not found in pricing data
- **409 CONFLICT** — Charger already booked for the selected time range

#### Error Response Examples

**Time validation error:**
```json
{
  "detail": "End time must be after start time"
}
```

**Overlap error:**
```json
{
  "detail": "This listing is already booked for the selected time range"
}
```

**Suburb not found:**
```json
{
  "detail": "No pricing found for suburb: InvalidSuburb"
}
```

#### Important Notes

- **Price Tracking:** The API stores both user-quoted price and backend-calculated price to track pricing accuracy
- **Availability Check:** Validates no overlapping confirmed bookings exist before creating
- **Duration Calculation:** Hours are calculated from start/end times (rounded to 2 decimals)
- **User ID Default:** If not provided, defaults to user_id = 1
- **Status:** All new bookings are created with status "confirmed"

#### Usage in Project
- Called when user clicks "Complete Booking" in the booking modal
- Frontend sends user-quoted price and total
- Backend calculates AI-optimized price for comparison
- Returns booking_id which is stored in frontend state
- Triggers availability refresh in charger listings

---

### 6. Get All Bookings

**GET** `/bookings`

Retrieves all bookings in the system (across all users and chargers), ordered by most recent first.

#### Request
```bash
curl -X GET http://localhost:8001/bookings
```

#### Response

```json
{
  "count": 15,
  "bookings": [
    {
      "booking_id": 42,
      "listing_id": "south_melbourne",
      "suburb": "South Melbourne",
      "title": "Charger in South Melbourne",
      "start": "2026-04-05T18:00",
      "end": "2026-04-05T20:00",
      "user_id": 1,
      "vehicle": "Tesla Model 3",
      "promo": null,
      "hours": 2.0,
      "quoted_price_per_hour": 3.75,
      "backend_price_per_hour": 4.50,
      "frontend_total_amount": 7.50,
      "backend_expected_total": 9.00,
      "status": "confirmed",
      "time_band": "evening"
    },
    {
      "booking_id": 41,
      "listing_id": "brighton",
      "suburb": "Brighton",
      "title": "Charger in Brighton",
      "start": "2026-04-04T14:00",
      "end": "2026-04-04T16:00",
      "user_id": 1,
      "vehicle": "Nissan Leaf",
      "promo": null,
      "hours": 2.0,
      "quoted_price_per_hour": 3.45,
      "backend_price_per_hour": 3.80,
      "frontend_total_amount": 6.90,
      "backend_expected_total": 7.60,
      "status": "confirmed",
      "time_band": "afternoon"
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `count` | integer | Total number of bookings in the system |
| `bookings` | array | Array of booking objects (most recent first) |

All booking object fields are documented in the Create Booking response section above.

#### Status Codes
- **200 OK** — Bookings retrieved successfully

#### Usage in Project
- Used in admin/analytics dashboard to view all system bookings
- Can be used for reporting and performance analysis
- Shows pricing discrepancies between frontend and backend

---

### 7. Get Specific Booking

**GET** `/bookings/{booking_id}`

Retrieves detailed information about a specific booking by ID.

#### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `booking_id` | integer | Yes | Unique booking identifier |

#### Request
```bash
curl -X GET http://localhost:8001/bookings/42
```

#### Response

```json
{
  "booking_id": 42,
  "listing_id": "south_melbourne",
  "suburb": "South Melbourne",
  "title": "Charger in South Melbourne",
  "start": "2026-04-05T18:00",
  "end": "2026-04-05T20:00",
  "user_id": 1,
  "vehicle": "Tesla Model 3",
  "promo": null,
  "hours": 2.0,
  "quoted_price_per_hour": 3.75,
  "backend_price_per_hour": 4.50,
  "frontend_total_amount": 7.50,
  "backend_expected_total": 9.00,
  "status": "confirmed",
  "time_band": "evening"
}
```

#### Status Codes
- **200 OK** — Booking found and returned
- **404 NOT FOUND** — Booking with given ID does not exist

#### Error Response Example

```json
{
  "detail": "Booking not found"
}
```

#### Usage in Project
- Used to fetch booking confirmation details after creation
- Frontend stores booking_id and can retrieve details later
- Useful for booking history and receipt generation

---

### 8. Get Host Bookings

**GET** `/host/bookings`

Retrieves all bookings for a specific charger (listing), ordered by start time (most recent first).

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `listing_id` | string | Yes | Unique charger ID (e.g., "south_melbourne") |

#### Request
```bash
curl -X GET "http://localhost:8001/host/bookings?listing_id=south_melbourne"
```

#### Response

```json
{
  "listing_id": "south_melbourne",
  "count": 5,
  "bookings": [
    {
      "booking_id": 42,
      "listing_id": "south_melbourne",
      "suburb": "South Melbourne",
      "title": "Charger in South Melbourne",
      "start": "2026-04-05T18:00",
      "end": "2026-04-05T20:00",
      "user_id": 1,
      "vehicle": "Tesla Model 3",
      "promo": null,
      "hours": 2.0,
      "quoted_price_per_hour": 3.75,
      "backend_price_per_hour": 4.50,
      "frontend_total_amount": 7.50,
      "backend_expected_total": 9.00,
      "status": "confirmed",
      "time_band": "evening"
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `listing_id` | string | The charger ID requested |
| `count` | integer | Number of bookings for this charger |
| `bookings` | array | Array of booking objects (most recent first) |

#### Status Codes
- **200 OK** — Bookings retrieved successfully (even if count is 0)

#### Usage in Project
- Used in host dashboard to view bookings for a specific charger
- Helps hosts track rental history and occupancy
- Used for income tracking and calendar visualization

---

### 9. Get Host Summary

**GET** `/host/summary`

Retrieves earnings summary for a specific charger (total bookings and total earnings).

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `listing_id` | string | Yes | Unique charger ID (e.g., "south_melbourne") |

#### Request
```bash
curl -X GET "http://localhost:8001/host/summary?listing_id=south_melbourne"
```

#### Response

```json
{
  "listing_id": "south_melbourne",
  "total_bookings": 5,
  "total_earnings": 45.60
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `listing_id` | string | The charger ID |
| `total_bookings` | integer | Total number of confirmed bookings |
| `total_earnings` | number | Total earnings in AUD (backend-expected totals only) |

#### Status Codes
- **200 OK** — Summary retrieved successfully

#### Notes
- Only counts bookings with status "confirmed"
- Uses `backend_expected_total` for earnings calculation (AI-optimized price)
- Returns 0 values if no bookings exist for the listing

#### Usage in Project
- Displayed in host earnings dashboard
- Shows host their total revenue from a specific charger
- Used to calculate performance metrics and ROI

---

## Request/Response Format

### DateTime Format

All datetime values use **ISO 8601 format with 24-hour time:**

```
YYYY-MM-DDTHH:MM
```

**Examples:**
- `2026-04-05T18:00` — April 5, 2026 at 6:00 PM
- `2026-04-05T06:30` — April 5, 2026 at 6:30 AM

**Valid formats accepted:**
- `2026-04-05T18:00`
- `2026-04-05T18:00:00`
- `2026-04-05T18:00:00+10:00` (with timezone offset)

### Content-Type

All POST requests must include:
```
Content-Type: application/json
```

### CORS

The API has CORS enabled for all origins (`allow_origins=["*"]`), allowing requests from any domain.

---

## Authentication

Currently, the API does **not require authentication**. All endpoints are publicly accessible. 

**⚠️ Note:** In a production environment, implement proper authentication (JWT tokens, API keys) to secure sensitive operations like booking creation and host earnings retrieval.

---

## Error Handling

### Error Response Format

All errors return a standard JSON response:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

### Common Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid datetime format, negative hours |
| 404 | Not Found | Booking/suburb doesn't exist |
| 409 | Conflict | Time slot already booked |
| 500 | Server Error | Database or processing error |

### Validation Rules

- **Datetime format:** Must be valid ISO 8601 (`YYYY-MM-DDTHH:MM`)
- **End time:** Must be after start time
- **Booking hours:** Must be greater than zero
- **Suburb name:** Must exist in pricing database
- **Listing ID:** Must correspond to a valid charger

---

## Database Schema

The backend uses SQLite with the following `bookings` table:

```sql
CREATE TABLE bookings (
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
```

**Key fields:**
- `quoted_price_per_hour` — Price shown to user on frontend
- `backend_price_per_hour` — AI-optimized price calculated by backend
- `frontend_total_amount` — Total amount user paid
- `backend_expected_total` — Expected revenue based on AI pricing
- `time_band` — Time category (morning, afternoon, evening, night)

---

## Pricing Engine Integration

The API integrates with the ML-based pricing engine (`pricing_engine.py`) which provides:

1. **Demand Forecasting** (`estimate_demand`):
   - Predicts demand in kW based on suburb, time, season, weather
   - Returns demand multiplier and confidence score

2. **Price Optimization** (`optimize_price`):
   - Calculates recommended price given base price and demand
   - Applies price floor/cap constraints
   - Returns price band and expected revenue

### Example Pricing Calculation

```
Base Price: $3.75/hr
Demand Multiplier: 1.2 (20% above baseline)
Calculated Price: $3.75 × 1.2 = $4.50/hr

Price Constraints:
- Floor: $2.50/hr (minimum)
- Cap: $7.50/hr (maximum)

Recommended Price: $4.50/hr (within bounds)
```

---

## Data Files

The backend loads the following CSV files on startup:

| File | Purpose | Key Columns |
|------|---------|-------------|
| `clustered_suburbs.csv` | Geographic clustering | Suburb, Cluster, Cluster_Label |
| `optimal_prices_all_suburbs.csv` | Base pricing | Suburb, Cluster, Average_Price, Lag_Usage |
| `charger_info_mel.csv` | Charger specifications | Suburb, Connector, kW |
| `Co-oridnates.csv` | Map coordinates | suburb, latitude, longitude |

---

## Example Workflows

### Workflow 1: Browse & Book a Charger

1. **Get available chargers** with time window:
   ```bash
   GET /listings?start=2026-04-05T18:00&end=2026-04-05T20:00
   ```

2. **View pricing details** for selected charger:
   ```bash
   GET /pricing?suburb=South%20Melbourne&start=2026-04-05T18:00
   ```

3. **Create booking** with selected times and pricing:
   ```bash
   POST /bookings
   ```
   Body includes: listing_id, suburb, start, end, quoted_price_per_hour

4. **Get booking confirmation** details:
   ```bash
   GET /bookings/{booking_id}
   ```

### Workflow 2: Host Earnings Dashboard

1. **Get all bookings for a charger**:
   ```bash
   GET /host/bookings?listing_id=south_melbourne
   ```

2. **Get earnings summary**:
   ```bash
   GET /host/summary?listing_id=south_melbourne
   ```

3. **Analyze booking history** from the bookings list

---

## Performance Notes

- All endpoints return responses in **< 200ms** for typical queries
- `/listings` may take longer (100-200ms) if querying 300+ chargers
- Database queries are optimized with WHERE clauses for filtering
- No pagination is currently implemented; consider adding for large datasets

---

## Troubleshooting

### "Database initialization error"

**Cause:** Chargebnb.db cannot be created or accessed  
**Solution:** Ensure the `backend/` directory is writable

### "Data loading failed"

**Cause:** CSV files not found in `backend/data/`  
**Solution:** Verify all 4 data files exist and have correct names

### "Booking not found"

**Cause:** Requested booking_id doesn't exist  
**Solution:** Check booking_id is correct; list all bookings with GET /bookings

### "No pricing data found for suburb"

**Cause:** Suburb not in pricing database  
**Solution:** Verify suburb name matches exactly (case-insensitive matching)

---

## Version History

- **v1.0** (April 2026) — Initial release with 9 endpoints
  - Charger listings with availability checking
  - Dynamic pricing with ML demand forecasting
  - Booking creation and retrieval
  - Host dashboard endpoints

---

## Support & Contact

For API issues or questions, review the code in `/backend/main.py` or contact the development team.

Last updated: April 2026
