import numpy as np


class FoldChannelStandardizer:
    """Standardize channels using statistics fitted on training-fold windows.

    Input shape: (windows, channels, samples). The caller must enforce that
    only inner-fit patients are passed to fit/fit_batches.
    """
    def __init__(self, epsilon=1e-6):
        if not np.isfinite(epsilon) or epsilon <= 0:
            raise ValueError("epsilon must be a finite positive number.")
        self.epsilon = float(epsilon)
        self.mean_ = None
        self.scale_ = None
        self.n_channels_ = None
        self.n_values_per_channel_ = None

    @staticmethod
    def _validate_windows(windows):
        values = np.asarray(windows, dtype=np.float64)
        if values.ndim != 3:
            raise ValueError("EEG windows must have shape (windows, channels, samples).")
        if any(size == 0 for size in values.shape):
            raise ValueError("EEG windows must be non-empty on every axis.")
        if not np.all(np.isfinite(values)):
            raise ValueError("EEG windows contain NaN or infinite values.")
        return values

    def fit(self, training_windows):
        return self.fit_batches([training_windows])

    def fit_batches(self, training_batches):
        """Incrementally fit exact population statistics over recording batches."""
        count, mean, m2, n_channels = 0, None, None, None
        for batch in training_batches:
            values = self._validate_windows(batch)
            if n_channels is None:
                n_channels = values.shape[1]
            elif values.shape[1] != n_channels:
                raise ValueError("Training batches have inconsistent channel counts.")
            flattened = values.transpose(1, 0, 2).reshape(values.shape[1], -1)
            batch_count = flattened.shape[1]
            batch_mean = np.mean(flattened, axis=1)
            centered = flattened - batch_mean[:, None]
            batch_m2 = np.sum(centered * centered, axis=1)
            if count == 0:
                count, mean, m2 = batch_count, batch_mean, batch_m2
            else:
                total = count + batch_count
                delta = batch_mean - mean
                mean = mean + delta * (batch_count / total)
                m2 = m2 + batch_m2 + delta * delta * (count * batch_count / total)
                count = total
        if count == 0:
            raise ValueError("Cannot fit standardizer on no training windows.")
        variance = np.maximum(m2 / count, 0.0)
        self.n_channels_ = n_channels
        self.n_values_per_channel_ = count
        self.mean_ = mean
        self.scale_ = np.maximum(np.sqrt(variance), self.epsilon)
        return self

    def transform(self, windows):
        if self.mean_ is None or self.scale_ is None:
            raise RuntimeError("Standardizer must be fitted before transform().")
        values = self._validate_windows(windows)
        if values.shape[1] != self.n_channels_:
            raise ValueError(
                f"Expected {self.n_channels_} channels, received {values.shape[1]}."
            )
        return ((values - self.mean_[None, :, None]) /
                self.scale_[None, :, None]).astype(np.float32)

    def fit_transform(self, training_windows):
        return self.fit(training_windows).transform(training_windows)
