#!/usr/bin/env python3
"""
Model 4: Exponential Smoothing (Holt-Winters)
Built-in statsmodels - no compilation needed, excellent for seasonal data
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

def train_exponential_smoothing(endog, exog=None, seasonal_periods=24):
    """
    Train Exponential Smoothing (Holt-Winters) model

    Args:
        endog: Target time series (1D array)
        exog: Exogenous features (not used, for API consistency)
        seasonal_periods: Seasonality period (hours in a day = 24)

    Returns:
        Fitted Exponential Smoothing model
    """

    print("   🔄 Preparing data for Exponential Smoothing...")

    print("   ⚙️ Training Exponential Smoothing (Holt-Winters)...")

    try:
        # Fit Holt-Winters with additive seasonality
        model = ExponentialSmoothing(
            endog,
            seasonal_periods=seasonal_periods,
            trend='add',
            seasonal='add',
            initialization_method='estimated'
        )
        fitted = model.fit(optimized=True)
        print(f"   ✓ Model converged successfully")
    except Exception as e:
        print(f"   Additive seasonality failed: {e}, trying multiplicative...")
        try:
            model = ExponentialSmoothing(
                endog,
                seasonal_periods=seasonal_periods,
                trend='add',
                seasonal='mul',
                initialization_method='estimated'
            )
            fitted = model.fit(optimized=True)
        except Exception as e2:
            print(f"   Fallback to simple exponential smoothing: {e2}")
            # Simple exponential smoothing
            model = ExponentialSmoothing(
                endog,
                trend='add',
                seasonal=None
            )
            fitted = model.fit(optimized=True)

    return fitted

def predict_exponential_smoothing(model, steps):
    """
    Make predictions with Exponential Smoothing model

    Args:
        model: Fitted Exponential Smoothing model
        steps: Number of steps to forecast

    Returns:
        Predictions (1D array)
    """
    try:
        forecast = model.forecast(steps=steps)
        predictions = forecast.values if hasattr(forecast, 'values') else np.array(forecast)
    except Exception as e:
        print(f"   Prediction error: {e}, returning mean")
        predictions = np.full(steps, model.fittedvalues.mean())

    # Ensure predictions are positive
    predictions = np.maximum(predictions, 0)

    return predictions
