#!/usr/bin/env python3
"""
Model 2: XGBoost Regressor with Hyperparameter Tuning
Uses gradient boosting with grid search optimization
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import GridSearchCV
import time

def train_xgboost(X_train, y_train):
    """
    Train XGBoost with hyperparameter tuning via grid search

    Args:
        X_train: Training features (2D array)
        y_train: Training targets (1D array)

    Returns:
        Trained XGBoost model
    """

    print("   🔍 Grid searching hyperparameters...")

    # Define parameter grid
    param_grid = {
        'max_depth': [5, 7],
        'learning_rate': [0.01, 0.05],
        'n_estimators': [100, 150],
        'subsample': [0.8],
    }

    # Base model (single-threaded to avoid macOS threading issues)
    base_model = XGBRegressor(
        random_state=42,
        n_jobs=1,
        verbosity=0,
        tree_method='hist'
    )

    # Grid search (use smaller CV for speed, single-threaded)
    grid_search = GridSearchCV(
        base_model, param_grid,
        cv=2,  # Reduced from 3 for speed
        scoring='neg_mean_absolute_error',
        n_jobs=1,  # Single-threaded
        verbose=0
    )

    print("   ⚙️ Training XGBoost...")
    grid_search.fit(X_train, y_train)

    best_params = grid_search.best_params_
    print(f"   Best params: {best_params}")
    print(f"   Best CV score (neg MAE): {grid_search.best_score_:.2f}")

    # Return best estimator
    return grid_search.best_estimator_

def predict_xgboost(model, X_test):
    """
    Make predictions with XGBoost model

    Args:
        model: Trained XGBoost model
        X_test: Test features (2D array)

    Returns:
        Predictions (1D array)
    """
    predictions = model.predict(X_test)
    # Ensure predictions are positive
    predictions = np.maximum(predictions, 0)
    return predictions
