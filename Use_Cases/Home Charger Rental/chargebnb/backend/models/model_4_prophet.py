#!/usr/bin/env python3
"""
Model 4: Facebook Prophet Time Series Forecasting
Handles seasonality and trend detection automatically
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

try:
    from prophet import Prophet
except ImportError:
    print("   ⚠️ Prophet not installed, installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cmdstanpy", "-q"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pystan", "-q"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fbprophet", "-q"])
    from prophet import Prophet

def train_prophet(train_df, timestamp_col, target_col, feature_cols):
    """
    Train Prophet model

    Args:
        train_df: Training dataframe
        timestamp_col: Column name for timestamp
        target_col: Column name for target
        feature_cols: List of exogenous feature column names

    Returns:
        Trained Prophet model
    """

    print("   🔄 Preparing data for Prophet...")

    # Format for Prophet: ds (datetime) and y (target)
    df_prophet = pd.DataFrame({
        'ds': train_df[timestamp_col],
        'y': train_df[target_col]
    })

    # Add exogenous regressors (weather features)
    weather_cols = ['temp', 'humidity', 'windspeed']
    for col in weather_cols:
        if col in train_df.columns:
            df_prophet[col] = train_df[col].values

    print("   ⚙️ Training Prophet...")

    # Create and configure Prophet model
    model = Prophet(
        growth='linear',
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=True,
        seasonality_mode='additive',
        interval_width=0.8,
        stan_backend='cmdstanpy'  # Use cmdstanpy instead of pystan
    )

    # Add exogenous regressors
    for col in weather_cols:
        if col in df_prophet.columns:
            model.add_regressor(col)

    # Fit model
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(df_prophet)
    except Exception as e:
        print(f"   Prophet fit error: {e}, trying alternative...")
        # Fallback: simple Prophet without stan backend
        model = Prophet(
            growth='linear',
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=True,
            seasonality_mode='additive',
            interval_width=0.8
        )
        for col in weather_cols:
            if col in df_prophet.columns:
                try:
                    model.add_regressor(col)
                except:
                    pass
        model.fit(df_prophet)

    return model

def predict_prophet(model, test_df, timestamp_col, feature_cols):
    """
    Make predictions with Prophet model

    Args:
        model: Trained Prophet model
        test_df: Test dataframe
        timestamp_col: Column name for timestamp
        feature_cols: List of feature column names

    Returns:
        Predictions (1D array)
    """

    # Format for prediction
    df_future = pd.DataFrame({
        'ds': test_df[timestamp_col]
    })

    # Add exogenous regressors if available
    weather_cols = ['temp', 'humidity', 'windspeed']
    for col in weather_cols:
        if col in test_df.columns:
            df_future[col] = test_df[col].values

    # Make forecast
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            forecast = model.predict(df_future)
    except Exception as e:
        print(f"   Prediction error: {e}")
        # Fallback: return mean value
        forecast = pd.DataFrame({
            'yhat': np.full(len(test_df), test_df[test_df.columns[0]].mean())
        })

    predictions = forecast['yhat'].values

    # Ensure predictions are positive
    predictions = np.maximum(predictions, 0)

    return predictions
