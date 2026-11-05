"""Patient-robust EEG features for the second feature-engineering experiment.

Unlike the legacy extractor, this representation emphasizes relative spectral
composition and scale-normalized temporal shape. It is deterministic and does
not learn from labels or fit statistics across recordings.
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import trapezoid
from scipy.signal import welch

ROBUST_FEATURE_VERSION = "relative_spectral_shape_v1"
ROBUST_FREQUENCY_BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 40.0),
}
ROBUST_FEATURE_NAMES = (
    "log_std",
    "normalized_line_length",
    "skewness",
    "excess_kurtosis",
    "relative_delta_power",
    "relative_theta_power",
    "relative_alpha_power",
    "relative_beta_power",
    "relative_gamma_power",
    "spectral_entropy",
)


def _band_power(frequencies: np.ndarray, psd: np.ndarray, low: float, high: float) -> float:
    inside = (frequencies > low) & (frequencies < high)
    x = np.concatenate(([low], frequencies[inside], [high]))
    y = np.interp(x, frequencies, psd)
    return max(float(trapezoid(y, x)), 0.0)


def _one_channel(signal: np.ndarray, sfreq: float) -> list[float]:
    signal = np.asarray(signal, dtype=np.float64)
    if signal.ndim != 1 or signal.size < 2 or not np.isfinite(signal).all():
        raise ValueError("Each EEG channel must be a finite, non-empty 1D signal.")
    if not np.isfinite(sfreq) or sfreq < 80:
        raise ValueError("Sampling frequency must be finite and at least 80 Hz.")

    mean = float(np.mean(signal))
    centered = signal - mean
    std = float(np.std(centered))
    eps = np.finfo(np.float64).eps
    safe_std = max(std, eps)
    log_std = float(np.log(max(std, 1e-12)))
    normalized_line_length = float(np.mean(np.abs(np.diff(signal))) / safe_std)

    if std <= eps * max(1.0, float(np.max(np.abs(signal)))):
        skewness = 0.0
        excess_kurtosis = 0.0
    else:
        skewness = float(np.mean(centered ** 3) / (std ** 3))
        excess_kurtosis = float(np.mean(centered ** 4) / (std ** 4) - 3.0)

    nperseg = min(signal.size, max(1, int(round(2.0 * sfreq))))
    frequencies, psd = welch(
        signal, fs=float(sfreq), nperseg=nperseg,
        detrend="constant", scaling="density",
    )
    powers = np.asarray([
        _band_power(frequencies, psd, low, high)
        for low, high in ROBUST_FREQUENCY_BANDS.values()
    ], dtype=np.float64)
    total = float(np.sum(powers))
    if total <= eps:
        relative = np.zeros_like(powers)
    else:
        relative = powers / total

    retained = (frequencies >= 0.5) & (frequencies <= 40.0)
    spectral = np.maximum(psd[retained], 0.0)
    spectral_total = float(np.sum(spectral))
    if spectral_total <= eps or spectral.size <= 1:
        entropy = 0.0
    else:
        probabilities = spectral / spectral_total
        probabilities = probabilities[probabilities > 0.0]
        entropy = float(-np.sum(probabilities * np.log(probabilities)) / np.log(spectral.size))

    return [
        log_std, normalized_line_length, skewness, excess_kurtosis,
        *relative.tolist(), entropy,
    ]


def extract_robust_features(windows: np.ndarray, sfreq: float) -> np.ndarray:
    """Return float32 features shaped (windows, channels * 10).

    Relative band powers reduce sensitivity to absolute channel amplitude.
    Normalized line length and standardized moments retain temporal-shape
    information. No cross-recording or label-dependent operation is performed.
    """
    values = np.asarray(windows, dtype=np.float64)
    if values.ndim != 3 or any(size == 0 for size in values.shape):
        raise ValueError("Expected windows shaped (n_windows, n_channels, n_samples).")
    if not np.isfinite(values).all():
        raise ValueError("EEG windows contain NaN or infinite values.")
    if not np.isscalar(sfreq) or not np.isfinite(sfreq) or sfreq < 80:
        raise ValueError("Sampling frequency must be finite and at least 80 Hz.")

    n_windows, n_channels, _ = values.shape
    output = np.empty((n_windows, n_channels, len(ROBUST_FEATURE_NAMES)), dtype=np.float32)
    for window_index in range(n_windows):
        for channel_index in range(n_channels):
            output[window_index, channel_index] = _one_channel(
                values[window_index, channel_index], float(sfreq)
            )
    if not np.isfinite(output).all():
        raise ValueError("Robust feature extraction generated non-finite values.")
    return output.reshape(n_windows, -1)
