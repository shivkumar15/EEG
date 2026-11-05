"""Reusable per-recording channel statistics for patient-grouped OOF scaling.

Statistics are computed from the existing processed EEG windows. They contain
no labels and can be merged to fit a scaler without rereading all samples.
"""
from __future__ import annotations

import numpy as np


def channel_sufficient_statistics(windows: np.ndarray) -> dict[str, object]:
    """Return population count, mean and M2 per channel for one recording."""
    values = np.asarray(windows, dtype=np.float64)
    if values.ndim != 3 or any(size == 0 for size in values.shape):
        raise ValueError("windows must have non-empty (windows, channels, samples) shape")
    if not np.isfinite(values).all():
        raise ValueError("windows contain non-finite values")
    flattened = values.transpose(1, 0, 2).reshape(values.shape[1], -1)
    mean = np.mean(flattened, axis=1)
    centered = flattened - mean[:, None]
    m2 = np.sum(centered * centered, axis=1)
    return {"count": int(flattened.shape[1]), "mean": mean, "m2": m2}


def merge_channel_statistics(
    left: dict[str, object], right: dict[str, object]
) -> dict[str, object]:
    """Merge two population-statistic states using parallel Welford."""
    n_a, n_b = int(left["count"]), int(right["count"])
    mean_a = np.asarray(left["mean"], dtype=np.float64)
    mean_b = np.asarray(right["mean"], dtype=np.float64)
    m2_a = np.asarray(left["m2"], dtype=np.float64)
    m2_b = np.asarray(right["m2"], dtype=np.float64)
    if n_a <= 0 or n_b <= 0:
        raise ValueError("statistics counts must be positive")
    if mean_a.ndim != 1 or mean_b.shape != mean_a.shape:
        raise ValueError("statistics channel dimensions do not match")
    if m2_a.shape != mean_a.shape or m2_b.shape != mean_a.shape:
        raise ValueError("statistics M2 dimensions do not match")
    if not all(np.isfinite(v).all() for v in (mean_a, mean_b, m2_a, m2_b)):
        raise ValueError("statistics contain non-finite values")
    if np.any(m2_a < 0) or np.any(m2_b < 0):
        raise ValueError("statistics M2 must be non-negative")
    total = n_a + n_b
    delta = mean_b - mean_a
    mean = mean_a + delta * (n_b / total)
    m2 = m2_a + m2_b + delta * delta * (n_a * n_b / total)
    return {"count": total, "mean": mean, "m2": m2}


def finalize_channel_statistics(
    state: dict[str, object], epsilon: float = 1e-6
) -> tuple[np.ndarray, np.ndarray]:
    """Return mean and population-standard-deviation scale."""
    count = int(state["count"])
    mean = np.asarray(state["mean"], dtype=np.float64)
    m2 = np.asarray(state["m2"], dtype=np.float64)
    if count <= 0 or mean.ndim != 1 or m2.shape != mean.shape:
        raise ValueError("invalid channel statistics state")
    if not np.isfinite(mean).all() or not np.isfinite(m2).all() or np.any(m2 < 0):
        raise ValueError("invalid channel statistics values")
    if not np.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("epsilon must be finite and positive")
    return mean.copy(), np.maximum(np.sqrt(np.maximum(m2 / count, 0.0)), epsilon)


def recompute_log_std_features(
    windows: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
    chunk_size: int = 256,
) -> np.ndarray:
    """Recompute channel log_std exactly under a supplied fold scaler.

    Mirrors FoldChannelStandardizer.transform followed by the log_std portion
    of extract_robust_features, including float32 transform precision and the
    1e-12 log floor. Output shape is (n_windows, n_channels), float32.
    """
    values = np.asarray(windows)
    mean = np.asarray(mean, dtype=np.float64)
    scale = np.asarray(scale, dtype=np.float64)
    if values.ndim != 3 or any(size == 0 for size in values.shape):
        raise ValueError("windows must have non-empty (windows, channels, samples) shape")
    if mean.shape != (values.shape[1],) or scale.shape != mean.shape:
        raise ValueError("mean/scale must match the window channel count")
    if not np.isfinite(values).all() or not np.isfinite(mean).all():
        raise ValueError("windows and mean must be finite")
    if not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError("scale must be finite and positive")
    if not isinstance(chunk_size, (int, np.integer)) or isinstance(chunk_size, bool) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    result = np.empty((len(values), values.shape[1]), dtype=np.float32)
    for start in range(0, len(values), int(chunk_size)):
        stop = min(start + int(chunk_size), len(values))
        standardized = ((np.asarray(values[start:stop], dtype=np.float64)
                         - mean[None, :, None]) / scale[None, :, None]).astype(np.float32)
        centered = standardized.astype(np.float64)
        centered -= np.mean(centered, axis=-1, keepdims=True)
        std = np.std(centered, axis=-1)
        result[start:stop] = np.log(np.maximum(std, 1e-12)).astype(np.float32)
    if not np.isfinite(result).all():
        raise RuntimeError("recomputed log_std contains non-finite values")
    return result
