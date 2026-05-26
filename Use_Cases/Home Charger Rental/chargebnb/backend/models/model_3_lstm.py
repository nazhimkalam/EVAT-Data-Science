#!/usr/bin/env python3
"""
Model 3: LSTM (Long Short-Term Memory) Neural Network
Deep learning RNN for sequence modeling
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import os

# Enable Metal GPU acceleration on Apple Silicon
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['METAL_DEVICE_ONLY_FALLBACK'] = '0'

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dropout, Dense
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping

    # Check if Metal GPU is available
    metal_devices = tf.config.list_physical_devices('GPU')
    if metal_devices:
        print(f"   🎮 Metal GPU detected: {len(metal_devices)} GPU(s) available")
        for gpu in metal_devices:
            print(f"      - {gpu}")
except ImportError:
    print("   ⚠️ TensorFlow not installed, installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tensorflow", "-q"])
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dropout, Dense
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping
    import tensorflow as tf

# Set random seeds
np.random.seed(42)
tf.random.set_seed(42)

def create_sequences(X, y, sequence_length=24):
    """
    Create sliding window sequences for LSTM

    Args:
        X: Features (2D array)
        y: Targets (1D array)
        sequence_length: Window size (hours)

    Returns:
        X_seq, y_seq (3D and 1D arrays)
    """
    X_seq, y_seq = [], []

    for i in range(len(X) - sequence_length + 1):
        X_seq.append(X[i:i+sequence_length])
        y_seq.append(y[i+sequence_length-1])

    return np.array(X_seq), np.array(y_seq)

def train_lstm(X_train, y_train, sequence_length=24, epochs=100):
    """
    Train LSTM model

    Args:
        X_train: Training features (2D array)
        y_train: Training targets (1D array)
        sequence_length: Lookback window (hours)
        epochs: Training epochs

    Returns:
        Trained LSTM model
    """

    print(f"   🔄 Creating sequences (window={sequence_length}h)...")

    # Create sequences
    X_seq, y_seq = create_sequences(X_train, y_train, sequence_length)

    if len(X_seq) < 100:
        print(f"   ⚠️ Not enough sequences ({len(X_seq)}), reducing window...")
        sequence_length = 12
        X_seq, y_seq = create_sequences(X_train, y_train, sequence_length)

    print(f"   ⚙️ Training LSTM... (sequences: {len(X_seq)})")

    # Build LSTM model (simplified for faster training)
    model = Sequential([
        LSTM(32, activation='relu', input_shape=(sequence_length, X_train.shape[1])),
        Dropout(0.1),
        Dense(16, activation='relu'),
        Dense(1)
    ])

    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )

    # Early stopping
    early_stop = EarlyStopping(
        monitor='loss',
        patience=10,
        restore_best_weights=True
    )

    # Train
    model.fit(
        X_seq, y_seq,
        epochs=epochs,
        batch_size=32,
        callbacks=[early_stop],
        verbose=0
    )

    # Store sequence_length as model attribute
    model.sequence_length = sequence_length

    return model

def predict_lstm(model, X_test, sequence_length=24):
    """
    Make predictions with LSTM model

    Args:
        model: Trained LSTM model
        X_test: Test features (2D array)
        sequence_length: Lookback window (hours)

    Returns:
        Predictions (1D array)
    """

    # Use stored sequence_length if available
    if hasattr(model, 'sequence_length'):
        sequence_length = model.sequence_length

    predictions = []

    # For initial predictions, pad with mean values
    if len(predictions) == 0:
        init_window = np.tile(X_test.mean(axis=0), (sequence_length, 1))
    else:
        init_window = None

    for i in range(len(X_test)):
        if i < sequence_length:
            # Pad beginning with mean values
            if init_window is None:
                init_window = np.tile(X_test.mean(axis=0), (sequence_length, 1))
            window = np.vstack([init_window[i:], X_test[:i+1]])
        else:
            window = X_test[i-sequence_length+1:i+1]

        if len(window) == sequence_length:
            window_reshaped = window.reshape(1, sequence_length, -1)
            pred = model.predict(window_reshaped, verbose=0)[0, 0]
            predictions.append(pred)
        else:
            # Fallback for edge cases
            predictions.append(X_test[i].mean())

    predictions = np.array(predictions)
    # Ensure predictions are positive
    predictions = np.maximum(predictions, 0)

    return predictions
