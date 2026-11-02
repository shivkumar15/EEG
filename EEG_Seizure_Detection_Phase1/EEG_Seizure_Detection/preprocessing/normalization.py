import numpy as np


class FoldChannelStandardizer:
    """Standardize EEG channels using statistics fitted on training windows.

    Input shape: (windows, channels, samples). Fit only on the current
    outer-fold training patients, then reuse unchanged for validation and test.
    The caller is responsible for enforcing patient-disjoint fold inputs.
    """

    def __init__(self, epsilon=1e-6):
        if not np.isfinite(epsilon) or epsilon <= 0:
            raise ValueError("epsilon must be a finite positive number.")
        self.epsilon = float(epsilon)
        self.mean_ = None
        self.scale_ = None
        self.n_channels_ = None

    @staticmethod
    def _validate_windows(windows):
        values = np.asarray(windows, dtype=np.float64)
        if values.ndim != 3:
            raise ValueError(
                "EEG windows must have shape (windows, channels, samples)."
            )
        if any(size == 0 for size in values.shape):
            raise ValueError("EEG windows must be non-empty on every axis.")
        if not np.all(np.isfinite(values)):
            raise ValueError("EEG windows contain NaN or infinite values.")
        return values

    def fit(self, training_windows):
        """Fit channel statistics on training-fold windows only."""
        values = self._validate_windows(training_windows)
        self.n_channels_ = values.shape[1]
        self.mean_ = np.mean(values, axis=(0, 2))
        std = np.std(values, axis=(0, 2))
        self.scale_ = np.maximum(std, self.epsilon)
        return self

    def transform(self, windows):
        """Apply fitted training statistics without refitting."""
        if self.mean_ is None or self.scale_ is None:
            raise RuntimeError("Standardizer must be fitted before transform().")
        values = self._validate_windows(windows)
        if values.shape[1] != self.n_channels_:
            raise ValueError(
                f"Expected {self.n_channels_} channels, received {values.shape[1]}."
            )
        transformed = (
            values - self.mean_[None, :, None]
        ) / self.scale_[None, :, None]
        return transformed.astype(np.float32)

    def fit_transform(self, training_windows):
        """Fit on training windows and return their standardized values."""
        return self.fit(training_windows).transform(training_windows)
