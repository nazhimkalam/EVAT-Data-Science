"""Baseline forecasting models for comparison with XGBoost"""

import warnings
warnings.filterwarnings('ignore')

import os
import numpy as np
from itertools import product

# SARIMAX imports
from pmdarima.arima import auto_arima
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Exponential Smoothing imports
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# LSTM imports
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dropout, Dense
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping

    # Enable Metal GPU acceleration
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    os.environ['METAL_DEVICE_ONLY_FALLBACK'] = '0'
except ImportError:
    print("Warning: TensorFlow not available for LSTM")

# ============================================================================
# SARIMAX - Statistical Time Series Model
# ============================================================================

def train_sarimax_tuned(endog, exog, max_p=2, max_d=1, max_q=2):
    """
    Train SARIMAX with auto-tuned hyperparameters.

    Args:
        endog: Target time series (1D array)
        exog: Exogenous features (2D array)
        max_p, max_d, max_q: Max search range for (p,d,q)

    Returns:
        fitted_model with best parameters
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
        print(f"   Auto-tune failed, using default (1,0,1)")
        best_order = (1, 0, 1)

    # Test seasonal orders for 24-hour seasonality
    print("   🔍 Testing seasonal orders...")
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

    print(f"   Best seasonal order: {best_seasonal_order}")

    # Train final model
    try:
        model = SARIMAX(
            endog, exog=exog,
            order=best_order,
            seasonal_order=best_seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        fitted = model.fit(disp=False)
    except Exception:
        model = SARIMAX(endog, exog=exog, order=(1, 0, 1))
        fitted = model.fit(disp=False)

    return fitted


def predict_sarimax(model, exog):
    """Make predictions with SARIMAX model."""
    try:
        forecast = model.get_forecast(steps=len(exog), exog=exog)
        predictions = forecast.predicted_mean.values
    except Exception:
        predictions = np.full(len(exog), np.mean(model.fittedvalues))

    return np.maximum(predictions, 0)


# ============================================================================
# LSTM - Deep Learning Sequence Model
# ============================================================================

def create_sequences(X, y, sequence_length=24):
    """Create sliding window sequences for LSTM."""
    X_seq, y_seq = [], []

    for i in range(len(X) - sequence_length + 1):
        X_seq.append(X[i:i+sequence_length])
        y_seq.append(y[i+sequence_length-1])

    return np.array(X_seq), np.array(y_seq)


def train_lstm(X_train, y_train, sequence_length=24, epochs=20):
    """
    Train LSTM model.

    Args:
        X_train: Training features (2D array)
        y_train: Training targets (1D array)
        sequence_length: Lookback window (hours)
        epochs: Training epochs

    Returns:
        Trained LSTM model
    """
    print(f"   🔄 Creating sequences (window={sequence_length}h)...")

    X_seq, y_seq = create_sequences(X_train, y_train, sequence_length)

    if len(X_seq) < 100:
        print(f"   ⚠️ Not enough sequences, reducing window...")
        sequence_length = 12
        X_seq, y_seq = create_sequences(X_train, y_train, sequence_length)

    print(f"   ⚙️ Training LSTM (sequences: {len(X_seq)})...")

    # Simplified architecture for faster training
    model = Sequential([
        LSTM(32, activation='relu', input_shape=(sequence_length, X_train.shape[1])),
        Dropout(0.1),
        Dense(16, activation='relu'),
        Dense(1)
    ])

    model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])

    early_stop = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)

    model.fit(X_seq, y_seq, epochs=epochs, batch_size=32, callbacks=[early_stop], verbose=0)

    model.sequence_length = sequence_length
    return model


def predict_lstm(model, X_test, sequence_length=24):
    """Make predictions with LSTM model."""
    if hasattr(model, 'sequence_length'):
        sequence_length = model.sequence_length

    predictions = []
    init_window = np.tile(X_test.mean(axis=0), (sequence_length, 1))

    for i in range(len(X_test)):
        if i < sequence_length:
            window = np.vstack([init_window[i:], X_test[:i+1]])
        else:
            window = X_test[i-sequence_length+1:i+1]

        if len(window) == sequence_length:
            window_reshaped = window.reshape(1, sequence_length, -1)
            pred = model.predict(window_reshaped, verbose=0)[0, 0]
            predictions.append(pred)
        else:
            predictions.append(X_test[i].mean())

    return np.maximum(np.array(predictions), 0)


# ============================================================================
# EXPONENTIAL SMOOTHING - Holt-Winters Model
# ============================================================================

def train_exponential_smoothing(endog, exog=None, seasonal_periods=24):
    """
    Train Exponential Smoothing (Holt-Winters) model.

    Args:
        endog: Target time series (1D array)
        exog: Exogenous features (ignored, for API consistency)
        seasonal_periods: Seasonality period (24 hours)

    Returns:
        Fitted Exponential Smoothing model
    """
    print("   ⚙️ Training Exponential Smoothing...")

    try:
        model = ExponentialSmoothing(
            endog,
            seasonal_periods=seasonal_periods,
            trend='add',
            seasonal='add',
            initialization_method='estimated'
        )
        fitted = model.fit(optimized=True)
    except Exception:
        try:
            model = ExponentialSmoothing(
                endog,
                seasonal_periods=seasonal_periods,
                trend='add',
                seasonal='mul',
                initialization_method='estimated'
            )
            fitted = model.fit(optimized=True)
        except Exception:
            model = ExponentialSmoothing(endog, trend='add', seasonal=None)
            fitted = model.fit(optimized=True)

    return fitted


def predict_exponential_smoothing(model, steps):
    """Make predictions with Exponential Smoothing model."""
    try:
        forecast = model.forecast(steps=steps)
        predictions = forecast.values if hasattr(forecast, 'values') else np.array(forecast)
    except Exception:
        predictions = np.full(steps, model.fittedvalues.mean())

    return np.maximum(predictions, 0)
