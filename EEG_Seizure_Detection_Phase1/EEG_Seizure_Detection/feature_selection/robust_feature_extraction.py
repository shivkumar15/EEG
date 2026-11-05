"""Patient-robust EEG features for the second feature-engineering experiment."""
from __future__ import annotations

import numpy as np
from scipy.signal import welch

ROBUST_FEATURE_VERSION = "relative_spectral_shape_v1"
ROBUST_FREQUENCY_BANDS = (
    (0.5, 4.0), (4.0, 8.0), (8.0, 13.0), (13.0, 30.0), (30.0, 40.0),
)
ROBUST_FEATURE_NAMES = (
    "log_std", "normalized_line_length", "skewness", "excess_kurtosis",
    "relative_delta_power", "relative_theta_power", "relative_alpha_power",
    "relative_beta_power", "relative_gamma_power", "spectral_entropy",
)


def extract_robust_features(windows: np.ndarray, sfreq: float) -> np.ndarray:
    """Extract 10 vectorized features/channel; output is finite float32.

    Relative spectral composition and normalized temporal shape reduce
    sensitivity to absolute EEG amplitude. Welch is vectorized across windows
    and channels to avoid millions of Python-level per-channel calls.
    """
    values = np.asarray(windows, dtype=np.float64)
    if values.ndim != 3 or any(size == 0 for size in values.shape):
        raise ValueError("Expected windows shaped (n_windows, n_channels, n_samples).")
    if not np.isfinite(values).all():
        raise ValueError("EEG windows contain NaN or infinite values.")
    if not np.isscalar(sfreq) or not np.isfinite(sfreq) or sfreq < 80:
        raise ValueError("Sampling frequency must be finite and at least 80 Hz.")
    minimum_samples = int(np.ceil(2.0 * float(sfreq)))
    if values.shape[-1] < minimum_samples:
        raise ValueError(
            f"Each window must contain at least 2 seconds of EEG "
            f"({minimum_samples} samples at {sfreq} Hz)."
        )

    eps = np.finfo(np.float64).eps
    centered = values - np.mean(values, axis=-1, keepdims=True)
    std = np.std(centered, axis=-1)
    safe_std = np.maximum(std, eps)
    log_std = np.log(np.maximum(std, 1e-12))
    normalized_line_length = np.mean(np.abs(np.diff(values, axis=-1)), axis=-1) / safe_std
    skewness = np.mean(centered ** 3, axis=-1) / (safe_std ** 3)
    kurtosis = np.mean(centered ** 4, axis=-1) / (safe_std ** 4) - 3.0
    near_constant = std <= eps * np.maximum(1.0, np.max(np.abs(values), axis=-1))
    skewness = np.where(near_constant, 0.0, skewness)
    kurtosis = np.where(near_constant, 0.0, kurtosis)

    nperseg = min(values.shape[-1], max(1, int(round(2.0 * float(sfreq)))))
    frequencies, psd = welch(
        values, fs=float(sfreq), nperseg=nperseg, axis=-1,
        detrend="constant", scaling="density",
    )
    df = float(frequencies[1] - frequencies[0])
    band_powers = []
    for low, high in ROBUST_FREQUENCY_BANDS:
        mask = (frequencies >= low) & (frequencies < high)
        band_powers.append(np.sum(psd[..., mask], axis=-1) * df)
    powers = np.stack(band_powers, axis=-1)
    total_power = np.sum(powers, axis=-1, keepdims=True)
    relative = np.divide(powers, total_power, out=np.zeros_like(powers), where=total_power > eps)

    retained = (frequencies >= 0.5) & (frequencies <= 40.0)
    spectral = np.maximum(psd[..., retained], 0.0)
    spectral_total = np.sum(spectral, axis=-1, keepdims=True)
    probabilities = np.divide(
        spectral, spectral_total, out=np.zeros_like(spectral), where=spectral_total > eps
    )
    log_probabilities = np.zeros_like(probabilities)
    positive = probabilities > 0
    log_probabilities[positive] = np.log(probabilities[positive])
    entropy = -np.sum(probabilities * log_probabilities, axis=-1) / np.log(max(2, spectral.shape[-1]))

    output = np.concatenate([
        log_std[..., None], normalized_line_length[..., None],
        skewness[..., None], kurtosis[..., None], relative,
        entropy[..., None],
    ], axis=-1).astype(np.float32)
    if not np.isfinite(output).all():
        raise ValueError("Robust feature extraction generated non-finite values.")
    return output.reshape(values.shape[0], -1)
