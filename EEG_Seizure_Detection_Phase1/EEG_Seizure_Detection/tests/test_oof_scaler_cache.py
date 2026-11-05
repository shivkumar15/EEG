import numpy as np
import pytest

from evaluation.oof_scaler_cache import (
    channel_sufficient_statistics,
    finalize_channel_statistics,
    merge_channel_statistics,
    recompute_log_std_features,
)


def test_merged_recording_statistics_match_concatenated_population_stats():
    rng = np.random.default_rng(12)
    a = rng.normal(size=(3, 2, 128))
    b = rng.normal(loc=2.0, scale=3.0, size=(5, 2, 128))
    merged = merge_channel_statistics(
        channel_sufficient_statistics(a), channel_sufficient_statistics(b)
    )
    mean, scale = finalize_channel_statistics(merged)
    direct = np.concatenate([a, b], axis=0).transpose(1, 0, 2).reshape(2, -1)
    np.testing.assert_allclose(mean, direct.mean(axis=1), rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(scale, direct.std(axis=1), rtol=1e-12, atol=1e-12)



def test_chunked_recording_statistics_match_one_batch():
    rng = np.random.default_rng(44)
    values = rng.normal(size=(9, 3, 128))
    chunked = channel_sufficient_statistics(values, chunk_size=2)
    direct = channel_sufficient_statistics(values, chunk_size=9)
    np.testing.assert_allclose(chunked["mean"], direct["mean"], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(chunked["m2"], direct["m2"], rtol=1e-12, atol=1e-10)

def test_statistics_merge_is_order_independent_within_tolerance():
    rng = np.random.default_rng(3)
    batches = [rng.normal(size=(n, 2, 64)) for n in (2, 4, 3)]
    states = [channel_sufficient_statistics(batch) for batch in batches]
    left = merge_channel_statistics(merge_channel_statistics(states[0], states[1]), states[2])
    right = merge_channel_statistics(states[0], merge_channel_statistics(states[1], states[2]))
    np.testing.assert_allclose(left["mean"], right["mean"], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(left["m2"], right["m2"], rtol=1e-12, atol=1e-10)


def test_recomputed_log_std_matches_robust_extractor_and_preserves_clipped_windows():
    from feature_selection.robust_feature_extraction import extract_robust_features
    rng = np.random.default_rng(4)
    windows = rng.normal(size=(4, 2, 512)).astype(np.float32)
    windows[0] = 0.0
    mean = np.array([0.1, -0.2])
    scale = np.array([2.0, 0.5])
    standardized = ((windows.astype(np.float64) - mean[None, :, None])
                    / scale[None, :, None]).astype(np.float32)
    expected = extract_robust_features(standardized, 256)[:, 0::10]
    actual = recompute_log_std_features(windows, mean, scale, chunk_size=2)
    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-6)
    assert np.isfinite(actual).all()
    assert np.all(actual[0] <= np.log(1e-12))


@pytest.mark.parametrize("bad", [np.zeros((2, 3)), np.ones((0, 2, 8))])
def test_statistics_reject_invalid_shapes(bad):
    with pytest.raises(ValueError):
        channel_sufficient_statistics(bad)


def test_statistics_reject_non_finite_values():
    values = np.ones((2, 1, 8))
    values[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        channel_sufficient_statistics(values)


def test_recompute_rejects_invalid_scaler():
    with pytest.raises(ValueError, match="positive"):
        recompute_log_std_features(np.ones((1, 2, 8)), np.zeros(2), np.zeros(2))
