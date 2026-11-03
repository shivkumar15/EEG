"""Leakage-aware classical baseline utilities.

This module deliberately separates inner validation from outer evaluation.
It materializes feature rows for one split at a time; it never combines
recordings from the outer test patient with training data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from data_management.fold_data import load_recording_windows
from data_management.patient_mapping import Recording
from feature_selection.feature_extraction import extract_features
from preprocessing.normalization import FoldChannelStandardizer


@dataclass(frozen=True, slots=True)
class FeatureBatch:
    X: np.ndarray
    y: np.ndarray
    recording_paths: tuple[str, ...]


def fit_channel_standardizer(
    recordings: Sequence[Recording], processed_dir,
) -> FoldChannelStandardizer:
    """Fit channel statistics on exactly the supplied recordings, streamed."""
    scaler = FoldChannelStandardizer()

    def batches():
        for recording in recordings:
            yield load_recording_windows(processed_dir, recording).X

    return scaler.fit_batches(batches())


def collect_features(
    recordings: Sequence[Recording], processed_dir,
    channel_scaler: FoldChannelStandardizer,
) -> FeatureBatch:
    """Extract one recording at a time, retaining only its feature rows.

    This is intended for one LOPO fold/split, not the entire 683-recording
    cohort. Feature matrices are float32 until concatenation.
    """
    if not recordings:
        raise ValueError("Cannot collect features from an empty recording list")
    matrices: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    paths: list[str] = []
    expected_columns = None
    for recording in recordings:
        item = load_recording_windows(processed_dir, recording)
        standardized = channel_scaler.transform(item.X)
        features = extract_features(standardized, item.sfreq)
        if expected_columns is None:
            expected_columns = features.shape[1]
        if features.ndim != 2 or features.shape != (len(item.y), expected_columns):
            raise RuntimeError(f"Invalid feature matrix for {recording.relative_path}")
        if not np.isfinite(features).all():
            raise RuntimeError(f"Non-finite features for {recording.relative_path}")
        matrices.append(features)
        labels.append(item.y)
        paths.extend([recording.relative_path] * len(item.y))
    X = np.concatenate(matrices, axis=0).astype(np.float32, copy=False)
    y = np.concatenate(labels).astype(np.int8, copy=False)
    if len(X) != len(y) or not np.isin(y, (0, 1)).all():
        raise RuntimeError("Collected features and binary labels are inconsistent")
    return FeatureBatch(X, y, tuple(paths))


def build_baseline_estimators(random_state: int = 42) -> dict[str, Pipeline]:
    """Return fixed, documented baseline estimators (no outer-test tuning)."""
    return {
        "logistic_regression": Pipeline([
            ("feature_scaler", StandardScaler()),
            ("classifier", LogisticRegression(
                solver="liblinear", class_weight="balanced",
                max_iter=1000, random_state=random_state,
            )),
        ]),
        "random_forest": Pipeline([
            ("feature_scaler", StandardScaler()),
            ("classifier", RandomForestClassifier(
                n_estimators=100, max_depth=18, min_samples_leaf=5,
                class_weight="balanced_subsample", max_samples=0.5,
                n_jobs=-1, random_state=random_state,
            )),
        ]),
    }


def positive_scores(estimator, X: np.ndarray) -> np.ndarray:
    """Return a continuous positive-class score for threshold selection."""
    if hasattr(estimator, "predict_proba"):
        scores = estimator.predict_proba(X)[:, 1]
    elif hasattr(estimator, "decision_function"):
        scores = estimator.decision_function(X)
    else:
        raise TypeError("Estimator must expose predict_proba or decision_function")
    scores = np.asarray(scores, dtype=np.float64)
    if scores.ndim != 1 or not np.isfinite(scores).all():
        raise ValueError("Estimator returned invalid positive-class scores")
    return scores


def choose_f1_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Choose an F1-maximizing threshold using validation labels only."""
    y = np.asarray(y_true, dtype=np.int8)
    values = np.asarray(scores, dtype=np.float64)
    if y.ndim != 1 or values.shape != y.shape or not np.isin(y, (0, 1)).all():
        raise ValueError("Expected aligned one-dimensional binary labels and scores")
    if not np.isfinite(values).all() or not np.any(y == 1):
        raise ValueError("Threshold selection requires finite scores and positive labels")
    candidates = np.unique(values)
    # Include a threshold above the maximum to represent the all-negative case.
    candidates = np.concatenate((candidates, [np.nextafter(values.max(), np.inf)]))
    best_threshold, best_f1 = float(candidates[0]), -1.0
    for threshold in candidates:
        predicted = values >= threshold
        score = f1_score(y, predicted, zero_division=0)
        if score > best_f1:
            best_threshold, best_f1 = float(threshold), float(score)
    return best_threshold


def calculate_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    """Calculate window metrics; AUROC is null for a single-class target."""
    y = np.asarray(y_true, dtype=np.int8)
    values = np.asarray(scores, dtype=np.float64)
    if y.ndim != 1 or values.shape != y.shape or len(y) == 0:
        raise ValueError("Expected non-empty aligned one-dimensional arrays")
    if not np.isin(y, (0, 1)).all() or not np.isfinite(values).all():
        raise ValueError("Labels must be binary and scores finite")
    predicted = values >= threshold
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    sensitivity = float(tp / (tp + fn)) if tp + fn else 0.0
    specificity = float(tn / (tn + fp)) if tn + fp else 0.0
    return {
        "threshold": float(threshold),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "auroc": float(roc_auc_score(y, values)) if len(np.unique(y)) == 2 else None,
        "auprc": float(average_precision_score(y, values)) if np.any(y == 1) else None,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "window_count": int(len(y)),
        "positive_windows": int(np.sum(y == 1)),
    }


def fit_validate_model(
    estimator, fit_batch: FeatureBatch, validation_batch: FeatureBatch,
) -> tuple[object, float, dict]:
    """Fit on inner-fit patients and choose threshold on validation patients."""
    if len(np.unique(fit_batch.y)) != 2:
        raise ValueError("Inner-fit data must contain both classes")
    if len(np.unique(validation_batch.y)) != 2:
        raise ValueError("Validation data must contain both classes for this baseline")
    estimator.fit(fit_batch.X, fit_batch.y)
    scores = positive_scores(estimator, validation_batch.X)
    threshold = choose_f1_threshold(validation_batch.y, scores)
    return estimator, threshold, calculate_metrics(validation_batch.y, scores, threshold)


def refit_and_evaluate(
    estimator, outer_train_batch: FeatureBatch, outer_test_batch: FeatureBatch,
    validation_threshold: float,
) -> tuple[object, dict]:
    """Refit a fresh estimator on all outer-training patients, then test once.

    Callers must build both batches using a channel standardizer fitted on
    all outer-training patients. The threshold is frozen from inner validation;
    outer-test labels are used only by calculate_metrics after predictions.
    """
    if len(np.unique(outer_train_batch.y)) != 2:
        raise ValueError("Outer-training data must contain both classes")
    if not np.isfinite(validation_threshold):
        raise ValueError("Validation threshold must be finite")
    estimator.fit(outer_train_batch.X, outer_train_batch.y)
    test_scores = positive_scores(estimator, outer_test_batch.X)
    return estimator, calculate_metrics(
        outer_test_batch.y, test_scores, float(validation_threshold)
    )
