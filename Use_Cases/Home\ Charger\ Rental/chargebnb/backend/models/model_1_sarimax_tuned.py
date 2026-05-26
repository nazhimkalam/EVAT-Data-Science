#!/usr/bin/env python3
"""
Model 1: SARIMAX with Hyperparameter Tuning
Auto-tunes SARIMAX parameters to find the best configuration
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
from statsmodels.tsa.arima.auto_arima import auto_arima
from statsmodels.tsa.statespace.sarimax import SARIMAX
from itertools import product

def train_sarimax_tuned(endog, exog, max_p=2, max_d=1, max_q=2):
    """
    Train SARIMAX with auto-tuned hyperparameters

    Args:
        endog: Target time series (1D array)
        exog: Exogenous features (2D array)
        max_p, max_d, max_q: Max search range for (p,d,q)

    Returns:
        fitted_model, best_order tuple
    """

    print("   🔍 Auto-tuning SARIMAX parameters...")

    # Auto-tune (p,d,q) order
    try:
        auto_model = auto_arima(
            endog, exog=exog,
            max_p=max_p, max_d=max_d, max_q=max_q,
            seasonal=False,
            stepwise=True, trace=False,
            error_action='ignore',
            suppress_warnings=True
        )
        best_order = auto_model.order
        print(f"   Auto-tuned order: {best_order}")
    except Exception as e:
        print(f"   Auto-tune failed: {e}, using default (1,0,1)")
        best_order = (1, 0, 1)

    # Test seasonal orders for 24-hour seasonality
    print("   🔍 Testing seasonal orders (24-hour cycle)...")
    best_aic = np.inf
    best_seasonal_order = (0, 0, 0, 24)

    for P, D, Q in [(0,0,0), (1,0,0), (0,1,0), (0,0,1), (1,1,1)]:
        try:
            model = SARIMAX(
                endog, exog=exog,
                order=best_order,
                seasonal_order=(P, D, Q, 24),
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            fitted = model.fit(disp=False)

            if fitted.aic < best_aic:
                best_aic = fitted.aic
                best_seasonal_order = (P, D, Q, 24)
        except:
            pass

    print(f"   Best seasonal order: {best_seasonal_order} (AIC: {best_aic:.1f})")

    # Train final model with best orders
    print("   ⚙️ Training final SARIMAX model...")
    try:
        model = SARIMAX(
            endog, exog=exog,
            order=best_order,
            seasonal_order=best_seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        fitted = model.fit(disp=False)
    except Exception as e:
        print(f"   Fallback to (1,0,1) without seasonality: {e}")
        model = SARIMAX(
            endog, exog=exog,
            order=(1, 0, 1),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        fitted = model.fit(disp=False)

    return fitted, best_order

def predict_sarimax(model, exog):
    """
    Make predictions with SARIMAX model

    Args:
        model: Fitted SARIMAX model
        exog: Exogenous features for prediction (2D array)

    Returns:
        Predictions (1D array)
    """
    try:
        forecast = model.get_forecast(steps=len(exog), exog=exog)
        predictions = forecast.predicted_mean.values
    except Exception as e:
        # Fallback: return mean value
        print(f"   Prediction error: {e}, returning mean")
        predictions = np.full(len(exog), np.mean(model.fittedvalues))

    # Ensure predictions are positive
    predictions = np.maximum(predictions, 0)
    return predictions
