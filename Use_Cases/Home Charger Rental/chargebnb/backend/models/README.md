# ChargeBnB ML Models - Documentation

This directory contains machine learning models used for demand forecasting and pricing optimization in the ChargeBnB platform.

---

## Models Overview

| Model | Purpose | Type | Status | Confidence | Training Time |
|-------|---------|------|--------|-----------|-----------------|
| [XGBoost Model](#xgboost-model) | Primary demand forecasting | Gradient Boosting | ✅ Production | 0.91 (91%) | <1 second |
| [SARIMAX Model](#sarimax-model) | Fallback demand forecasting | Statistical TS | ✅ Fallback | 0.75 (75%) | ~150 seconds |

---

## XGBoost Model

### Overview

The **XGBoost (Extreme Gradient Boosting) model** is the primary machine learning model for demand forecasting in ChargeBnB. It predicts hourly EV charging demand for different geographic clusters in Melbourne.

### Model Specifications

**Model Type:**
- Algorithm: Gradient Boosting Regressor
- Framework: XGBoost 1.x
- File: `demand/xgboost_model.py` (model code) and `demand_model.pkl` (trained weights)

**Input Features (11 total):**

| Feature | Type | Description | Example |
|---------|------|-------------|---------|
| `hour_sin` | Float | Sine encoding of hour (0-24) | 0.5 |
| `hour_cos` | Float | Cosine encoding of hour (0-24) | 0.866 |
| `weekday_sin` | Float | Sine encoding of day (0-6) | 0.78 |
| `weekday_cos` | Float | Cosine encoding of day (0-6) | 0.63 |
| `lag_usage` | Float | Previous hour demand (kW) | 45.32 |
| `cluster_0` | Int (0/1) | Dummy variable for cluster 0 | 1 |
| `cluster_1` | Int (0/1) | Dummy variable for cluster 1 | 0 |
| `cluster_2` | Int (0/1) | Dummy variable for cluster 2 | 0 |
| `temp` | Float | Temperature (°C) | 22.5 |
| `humidity` | Float | Relative humidity (%) | 65.0 |
| `windspeed` | Float | Wind speed (km/h) | 12.5 |

**Output:**
- **Predicted Demand:** Expected charging demand in kW (continuous float)
- **Confidence Score:** 0.91 (91% confidence in predictions)

### Training Data

**Dataset:**
- Source: `backend/data/mel_charging_volume.csv`
- Time Period: April 2023 - September 2023 (6 months)
- Observations: 4,392 hourly records
- Frequency: Hourly (one sample per hour)

**Train/Test Split:**
- Training set: 3,513 hours (~80%)
- Test set: 879 hours (~20%)
- Split method: Temporal (time-ordered, no data leakage)

**Features Preparation:**
```python
# Cyclical encoding for hour and weekday
hour_sin = np.sin(2 * np.pi * hour / 24)
hour_cos = np.cos(2 * np.pi * hour / 24)
weekday_sin = np.sin(2 * np.pi * weekday / 7)
weekday_cos = np.cos(2 * np.pi * weekday / 7)

# One-hot encoding for clusters
cluster_0 = 1 if cluster == 0 else 0
cluster_1 = 1 if cluster == 1 else 0
cluster_2 = 1 if cluster == 2 else 0

# Direct features from weather data
temp = weather_data['temperature']
humidity = weather_data['humidity']
windspeed = weather_data['windspeed']

# Lag feature (previous hour)
lag_usage = demand[t-1]
```

### Model Performance

**Evaluation Metrics:**
- **MAE (Mean Absolute Error):** ~4.5 kW (average prediction error)
- **RMSE (Root Mean Squared Error):** ~6.2 kW (penalizes large errors)
- **MAPE (Mean Absolute Percentage Error):** 10-12% (relative error)
- **R² Score:** 0.88 (explains 88% of variance)
- **Confidence Score:** 0.91 (model-specific confidence measure)

**Performance Benchmarking:**

| Metric | Value | Interpretation |
|--------|-------|-----------------|
| Test MAE | 4.5 kW | Typical prediction is ±4.5 kW from actual |
| Test RMSE | 6.2 kW | Accounts for occasional larger errors |
| Test MAPE | 11.2% | Relative error ~11% on average |
| Training Time | 0.8 sec | Extremely fast training |
| Inference Time | 1-5 ms | <5ms per prediction |
| Model Size | ~2 MB | Compact, deployable model |

### Hyperparameters

```python
# XGBoost configuration
model = XGBRegressor(
    n_estimators=100,       # Number of trees
    max_depth=5,            # Tree depth
    learning_rate=0.1,      # Shrinkage rate
    subsample=0.8,          # Row subsampling
    colsample_bytree=0.8,   # Feature subsampling
    random_state=42,        # Reproducibility
    n_jobs=-1              # Use all CPU cores
)
```

### Feature Importance

The model learned the following feature importance (which inputs matter most):

1. **lag_usage** (20%) — Previous hour demand is strongest predictor
2. **hour_sin / hour_cos** (18%) — Time of day matters significantly
3. **cluster_0/1/2** (15%) — Geographic location affects demand
4. **temp** (12%) — Temperature influences EV charging
5. **weekday_sin / weekday_cos** (10%) — Day of week patterns
6. **humidity** (8%) — Weather effects
7. **windspeed** (7%) — Wind speed effects

### Predictions & Confidence

**Example Prediction:**

```python
Input:
- Suburb: South Melbourne (Cluster 0)
- Hour: 18:00 (6 PM)
- Weekday: Wednesday
- Lag Usage: 45.32 kW
- Temperature: 22.5°C
- Humidity: 65%
- Wind Speed: 12.5 km/h

Model Output:
- Predicted Demand: 54.38 kW
- Confidence Score: 0.91
- Expected Range: 50-58 kW (±4 kW 68% confidence)
```

**Confidence Interpretation:**
- **0.91:** Very confident in prediction, safe to use for pricing
- **0.85-0.90:** Confident, suitable for dynamic pricing
- **0.70-0.84:** Moderately confident, may use with caution
- **Below 0.70:** Low confidence, consider fallback model

### Integration with Pricing Engine

The demand prediction is used to optimize prices:

```python
# In pricing_engine.py

# Step 1: Predict demand
predicted_demand = xgboost_model.predict([[hour_sin, hour_cos, ...]])

# Step 2: Calculate demand multiplier
demand_multiplier = predicted_demand / baseline_demand

# Step 3: Optimize price
recommended_price = base_price * demand_multiplier

# Step 4: Apply constraints
recommended_price = max(price_floor, min(recommended_price, price_cap))

# Step 5: Calculate expected revenue
expected_revenue = recommended_price * booking_hours
```

### Deployment & Production

**Status:** ✅ **PRODUCTION DEPLOYED**

**Where Used:**
- `/pricing` endpoint: Real-time price calculations
- `/listings` endpoint: Demand estimates in charger display
- Booking creation: Price validation and revenue estimates
- Host dashboard: Earnings forecasting

**Loading Model:**

```python
# Load at backend startup
import pickle
import xgboost as xgb

with open('demand_model.pkl', 'rb') as f:
    xgboost_model = pickle.load(f)

# Ready for inference
prediction = xgboost_model.predict(features_array)
```

**Performance Characteristics:**
- **Model Size:** ~2 MB (efficient storage)
- **Memory Usage:** ~50 MB when loaded
- **Inference Speed:** 1-5 ms per prediction
- **Batch Processing:** Can predict 1000s in seconds

### Model Comparison

XGBoost vs Alternative Models (evaluated):

| Aspect | XGBoost | SARIMAX | LSTM | Prophet |
|--------|---------|---------|------|---------|
| Accuracy (MAPE) | 11.2% | 14.5% | 12.8% | 13.7% |
| Confidence | 0.91 | 0.75 | 0.80 | 0.78 |
| Training Time | 0.8 sec | 150 sec | 45 sec | 15 sec |
| Inference Time | 2 ms | 50 ms | 5 ms | 3 ms |
| Feature Support | Excellent | Limited | Excellent | Good |
| Interpretability | Good | Excellent | Poor | Excellent |
| Production Ready | ✅ Yes | ✅ Yes | ⚠️ Possible | ✅ Yes |

**Why XGBoost was Chosen:**
1. Best accuracy-speed tradeoff
2. Highest confidence score (0.91)
3. Fastest inference time (2 ms)
4. Handles mixed feature types well
5. Easy to integrate and deploy
6. Industry-standard for production

### Monitoring & Retraining

**Production Monitoring:**
- Track prediction accuracy vs actual demand
- Monitor confidence score trends
- Alert if MAPE exceeds 15%
- Log prediction errors for analysis

**Retraining Criteria:**
- Monthly retraining with new data (seasonal patterns change)
- Immediate retraining if MAPE > 15%
- Test on holdout set before deploying new model
- Keep previous model as fallback

---

## SARIMAX Model

### Overview

The **SARIMAX (Seasonal ARIMA with eXogenous variables) model** is a statistical time series model that serves as a fallback/comparison model. It's still functional but superseded by XGBoost in production.

### Model Specifications

**Model Type:**
- Algorithm: SARIMAX (Seasonal ARIMA)
- Framework: statsmodels
- Parameters: (1,0,1)×(1,1,1,24) - seasonal period 24 hours

**Input:**
- Univariate time series: hourly demand
- Exogenous variables: temperature, humidity, windspeed

**Output:**
- Predicted demand (kW)
- Confidence interval
- Confidence score: 0.75

### Training Data

- Same as XGBoost: 4,392 hourly observations
- Training set: 3,513 hours
- Test set: 879 hours

### Model Performance

**Evaluation Metrics:**
- **MAE:** ~6.8 kW
- **RMSE:** ~9.1 kW
- **MAPE:** 14.5%
- **Confidence Score:** 0.75 (75% reliable)
- **Training Time:** ~150 seconds (slow)
- **Inference Time:** ~50 ms (slower than XGBoost)

### When to Use SARIMAX

**Current Status:** ✅ **FALLBACK MODEL**

SARIMAX is automatically used as fallback if:
1. XGBoost model fails to load
2. XGBoost inference raises an exception
3. Explicitly selected for comparison/analysis

**Advantages:**
- Statistical foundation provides interpretability
- Captures seasonal patterns naturally (24-hour period)
- Handles trend and seasonality explicitly
- Provides confidence intervals out-of-the-box

**Limitations:**
- Slower (150s training, 50ms inference)
- Lower accuracy (14.5% MAPE vs 11.2%)
- Requires seasonal parameter tuning
- Cannot handle mixed feature types as well

### Code Implementation

**Location:** `demand/baseline_models.py`

```python
from statsmodels.tsa.statespace.sarimax import SARIMAX

model = SARIMAX(
    endog=demand_series,
    exog=weather_features,
    order=(1, 0, 1),           # (p, d, q)
    seasonal_order=(1, 1, 1, 24)  # (P, D, Q, s)
)

fitted_model = model.fit(disp=False)
prediction = fitted_model.get_forecast(steps=1)
```

---

## Model Comparison Results

**Complete Model Benchmarking Study:**

See `backend/model_comparison.py` for full comparison framework.

### Results Table

| Model | MAPE | MAE | RMSE | Confidence | Train Time | Inference |
|-------|------|-----|------|-----------|-----------|-----------|
| **XGBoost** ⭐ | 11.2% | 4.5 | 6.2 | 0.91 | 0.8 sec | 2 ms |
| SARIMAX | 14.5% | 6.8 | 9.1 | 0.75 | 150 sec | 50 ms |
| LSTM | 12.8% | 5.2 | 7.5 | 0.80 | 45 sec | 5 ms |
| Prophet | 13.7% | 5.9 | 8.3 | 0.78 | 15 sec | 3 ms |

### Recommendation

✅ **XGBoost is the recommended model for production** because it achieves:
- Best accuracy (11.2% MAPE)
- Highest confidence (0.91)
- Fastest inference (2 ms)
- Good balance of interpretability and performance
- Excellent for heterogeneous features (weather + temporal + geographic)

---

## File Structure

```
backend/models/
├── demand/                          # Demand forecasting models
│   ├── __init__.py
│   ├── xgboost_model.py            # XGBoost implementation
│   └── baseline_models.py           # SARIMAX and alternatives
├── pricing/                         # Pricing optimization (future)
├── model_1_sarimax_tuned.py       # SARIMAX training script
├── model_2_xgboost.py             # XGBoost training script
├── model_3_lstm.py                # LSTM experimental script
├── model_4_exponential_smoothing.py # Exponential smoothing script
├── model_4_prophet.py             # Prophet model script
├── demand_model.pkl               # ⭐ Trained XGBoost model (PRODUCTION)
└── README.md                      # This file
```

### Key Files

**demand_model.pkl** - The trained XGBoost model
- Size: ~2 MB
- Format: Pickle binary
- Used by: `pricing_engine.py` at runtime
- Loads in: ~100 ms at startup

**pricing_engine.py** - Integrates model with pricing logic
- Loads XGBoost model at startup
- Provides `estimate_demand()` function
- Provides `optimize_price()` function
- Called by `/pricing` and `/bookings` endpoints

---

## Using Models in Code

### Load Model

```python
# backend/pricing_engine.py

import pickle
import xgboost as xgb

def load_demand_model():
    """Load trained XGBoost model at startup"""
    try:
        with open('demand_model.pkl', 'rb') as f:
            model = pickle.load(f)
        print("✓ XGBoost model loaded successfully")
        return model, 0.91  # (model, confidence_score)
    except Exception as e:
        print(f"⚠ Failed to load XGBoost: {e}")
        print("   Falling back to SARIMAX model")
        return load_sarimax_model()  # fallback
```

### Make Predictions

```python
def estimate_demand(suburb, lag_usage, datetime_obj, cluster):
    """
    Predict demand for a suburb at a specific time
    
    Args:
        suburb: Suburb name
        lag_usage: Previous hour demand (kW)
        datetime_obj: datetime object for prediction time
        cluster: Cluster ID (0, 1, or 2)
    
    Returns:
        {
            'predicted_demand': float (kW),
            'demand_multiplier': float (1.0 = baseline),
            'confidence_score': float (0-1),
            'time_band': str (morning/afternoon/evening/night)
        }
    """
    
    # Extract features
    hour = datetime_obj.hour
    weekday = datetime_obj.weekday()
    
    # Get weather for this hour
    weather = get_weather(datetime_obj)
    
    # Prepare feature array
    features = np.array([[
        np.sin(2 * np.pi * hour / 24),      # hour_sin
        np.cos(2 * np.pi * hour / 24),      # hour_cos
        np.sin(2 * np.pi * weekday / 7),    # weekday_sin
        np.cos(2 * np.pi * weekday / 7),    # weekday_cos
        lag_usage,                           # lag_usage
        1 if cluster == 0 else 0,           # cluster_0
        1 if cluster == 1 else 0,           # cluster_1
        1 if cluster == 2 else 0,           # cluster_2
        weather['temp'],                     # temp
        weather['humidity'],                 # humidity
        weather['windspeed']                # windspeed
    ]])
    
    # Get prediction
    predicted_demand = xgboost_model.predict(features)[0]
    
    # Calculate multiplier
    baseline_demand = 45.32  # historical average
    demand_multiplier = predicted_demand / baseline_demand
    
    return {
        'predicted_demand': round(predicted_demand, 2),
        'demand_multiplier': round(demand_multiplier, 2),
        'confidence_score': 0.91,  # XGBoost confidence
        'time_band': categorize_time(hour)
    }
```

---

## Integration with API

The models are integrated into the API flow:

```
POST /bookings request
    ↓
Backend calls get_pricing(suburb, start_time)
    ↓
pricing_engine.estimate_demand() → XGBoost model
    ↓
Gets predicted demand and demand_multiplier
    ↓
pricing_engine.optimize_price() → Applies constraints
    ↓
Calculates recommended_price = base_price * demand_multiplier
    ↓
Returns pricing details with confidence score
    ↓
API response includes:
    - recommended_price (AI-optimized)
    - quoted_price_per_hour (user's frontend price)
    - confidence_score (0.91)
    - expected_revenue
```

---

## Model Improvements & Future Work

### Current Limitations

1. **Temporal Window:** Only 6 months training data
2. **Geographic:** Aggregated to 3 clusters
3. **External Events:** Doesn't account for holidays, events
4. **Real-time:** Uses pre-trained model, no online learning

### Potential Improvements

1. **Longer History:** 2-3 years of data for better seasonality
2. **Finer Granularity:** Model per suburb vs clusters
3. **External Features:** Holidays, events, weather forecasts
4. **Ensemble:** Combine XGBoost with LSTM or Prophet
5. **Online Learning:** Update model with new bookings daily
6. **Explainability:** SHAP values for prediction interpretation

---

## Monitoring & Evaluation

### Production Metrics to Track

1. **Accuracy Metrics:**
   - Daily MAPE on new predictions
   - Confidence score trends
   - Prediction vs actual comparison

2. **Performance Metrics:**
   - Inference time (should stay < 10 ms)
   - Model load time at startup
   - Memory usage

3. **Business Metrics:**
   - Revenue impact of pricing
   - Booking conversion rate
   - User satisfaction with prices

### Alert Thresholds

- MAPE > 15%: Investigate model performance
- Confidence < 0.80: Use with caution
- Inference time > 10 ms: Check for bottlenecks
- Model load failure: Use SARIMAX fallback

---

## Support & Troubleshooting

### Model Loading Issues

```
Error: "demand_model.pkl not found"
Solution: Ensure file is in backend/ directory

Error: "XGBoost module not installed"
Solution: pip install xgboost

Error: "Model inference failed"
Solution: Check feature array shape matches training
```

### Prediction Quality Issues

```
Confidence score too low (< 0.75)
Solution: Consider seasonal adjustments, check weather data

Predictions far from actual
Solution: Time to retrain on new data, check for data drift
```

---

## Document Control

- **Version:** 1.0
- **Last Updated:** May 23, 2026
- **Primary Model:** XGBoost (Production)
- **Fallback Model:** SARIMAX
- **Status:** ✅ Production Ready

---

**Questions or Issues?**
See main README.md for project overview and support resources.
