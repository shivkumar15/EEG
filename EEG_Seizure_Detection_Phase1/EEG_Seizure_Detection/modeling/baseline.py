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
from config import PREFERRED_CHANNELS
from data_management.patient_mapping import Recording
from feature_selection.feature_extraction import FEATURE_NAMES, extract_features
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
        for index, recording in enumerate(recordings, start=1):
            item = load_recording_windows(processed_dir, recording)
            yield item.X
            del item
            if index % 25 == 0 or index == len(recordings):
                print(
                    f"    channel-scaler fit: {index}/{len(recordings)} recordings",
                    flush=True,
                )

    return scaler.fit_batches(batches())


def collect_features(
    recordings: Sequence[Recording], processed_dir,
    channel_scaler: FoldChannelStandardizer,
) -> FeatureBatch:
    """Extract features into one preallocated matrix, one recording at a time.

    A label-only first pass determines the output size without decompressing
    EEG arrays. The second pass loads one recording, extracts its features,
    copies them into the final matrix, and releases the recording before the
    next one. Per-window recording path strings are intentionally not stored.
    """
    from data_management.fold_data import processed_path_for_recording

    if not recordings:
        raise ValueError("Cannot collect features from an empty recording list")

    total_windows = 0
    labels_by_recording = []
    for recording in recordings:
        path = processed_path_for_recording(processed_dir, recording)
        if not path.is_file():
            raise FileNotFoundError(
                f"Processed windows missing for {recording.relative_path}: {path}"
            )
        with np.load(path, allow_pickle=False) as saved:
            if "y" not in saved.files:
                raise ValueError(f"{path.name} is missing the y array")
            raw_labels = np.asarray(saved["y"])
        if raw_labels.ndim != 1 or len(raw_labels) == 0 or not np.isin(raw_labels, (0, 1)).all():
            raise ValueError(f"{path.name} has empty or non-binary labels")
        labels = raw_labels.astype(np.int8, copy=False)
        if bool(np.any(labels == 1)) != (recording.seizure_count > 0):
            raise ValueError(f"{path.name} labels disagree with the audit manifest")
        labels_by_recording.append(labels)
        total_windows += len(labels)

    feature_count = len(PREFERRED_CHANNELS) * len(FEATURE_NAMES)
    X = np.empty((total_windows, feature_count), dtype=np.float32)
    y = np.empty(total_windows, dtype=np.int8)
    cursor = 0

    for index, (recording, expected_y) in enumerate(
        zip(recordings, labels_by_recording), start=1
    ):
        item = load_recording_windows(processed_dir, recording)
        if not np.array_equal(item.y, expected_y):
            raise RuntimeError(
                f"Labels changed between metadata and feature pass: {recording.relative_path}"
            )
        standardized = channel_scaler.transform(item.X)
        features = extract_features(standardized, item.sfreq)
        expected_shape = (len(item.y), feature_count)
        if features.shape != expected_shape or features.dtype != np.float32:
            raise RuntimeError(
                f"Invalid feature matrix for {recording.relative_path}: "
                f"{features.shape}, {features.dtype}"
            )
        if not np.isfinite(features).all():
            raise RuntimeError(f"Non-finite features for {recording.relative_path}")
        next_cursor = cursor + len(item.y)
        X[cursor:next_cursor] = features
        y[cursor:next_cursor] = item.y
        cursor = next_cursor
        if index % 25 == 0 or index == len(recordings):
            print(
                f"    feature extraction: {index}/{len(recordings)} recordings",
                flush=True,
            )
        del item, standardized, features

    if cursor != total_windows or not np.isin(y, (0, 1)).all():
        raise RuntimeError("Collected features and binary labels are inconsistent")
    return FeatureBatch(X, y, ())


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
