import numpy as np
import pytest

from config import PREFERRED_CHANNELS
from scripts.audit_patient14_model_contributions import (
    FEATURE_NAMES,
    contribution_summary,
)


def test_contribution_summary_groups_all_channels_and_preserves_recording_offsets():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(4, len(PREFERRED_CHANNELS) * len(FEATURE_NAMES)))
    coef = rng.normal(size=X.shape[1])
    labels = np.array([1, 0, 1, 0], dtype=np.int8)
    offsets = [
        {"relative_path": "chb14/chb14_03.edf", "start": 0, "end": 2},
        {"relative_path": "chb14/chb14_04.edf", "start": 2, "end": 4},
    ]

    result = contribution_summary(X, coef, 0.25, labels, offsets, PREFERRED_CHANNELS)

    assert len(result["feature_group_contributions"]) == len(FEATURE_NAMES)
    assert len(result["per_recording_contributions"]) == 2
    assert len(result["largest_absolute_coefficients"]) == 40
    assert result["per_recording_contributions"][0]["positive_windows"] == 1
    assert result["per_recording_contributions"][1]["positive_windows"] == 1
    assert result["logit_reconstruction_max_abs_error"] < 1e-10


def test_contribution_summary_rejects_noncontiguous_recording_offsets():
    X = np.zeros((2, len(PREFERRED_CHANNELS) * len(FEATURE_NAMES)))
    coef = np.zeros(X.shape[1])
    labels = np.array([0, 1], dtype=np.int8)
    offsets = [{"relative_path": "bad.edf", "start": 1, "end": 2}]

    with pytest.raises(RuntimeError, match="contiguous"):
        contribution_summary(X, coef, 0.0, labels, offsets, PREFERRED_CHANNELS)
