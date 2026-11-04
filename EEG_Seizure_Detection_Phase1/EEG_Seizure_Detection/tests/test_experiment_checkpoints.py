import tempfile
import unittest
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from modeling.experiment_checkpoints import ModelStageCheckpointStore


class ModelStageCheckpointTests(unittest.TestCase):
    def test_json_checkpoint_reused_only_for_matching_signature(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = ModelStageCheckpointStore(Path(temporary), {"fold": 1, "seed": 42})
            first.save_json("validation", {"threshold": 0.4})
            self.assertEqual(first.load_json("validation"), {"threshold": 0.4})
            changed = ModelStageCheckpointStore(Path(temporary), {"fold": 2, "seed": 42})
            self.assertIsNone(changed.load_json("validation"))

    def test_estimator_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ModelStageCheckpointStore(Path(temporary), {"model": "lr", "fold": 1})
            X = np.array([[-2.0], [-1.0], [1.0], [2.0]])
            y = np.array([0, 0, 1, 1])
            estimator = LogisticRegression(random_state=42).fit(X, y)
            store.save_estimator("inner_model", estimator)
            restored = store.load_estimator("inner_model")
            self.assertIsNotNone(restored)
            np.testing.assert_allclose(
                estimator.predict_proba(X), restored.predict_proba(X)
            )

    def test_corrupt_estimator_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ModelStageCheckpointStore(Path(temporary), {"fold": 1})
            store.save_estimator("model", LogisticRegression())
            (Path(temporary) / "model.joblib").write_bytes(b"corrupt")
            self.assertIsNone(store.load_estimator("model"))

    def test_score_arrays_round_trip_and_reject_invalid_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ModelStageCheckpointStore(Path(temporary), {"fold": 1})
            y = np.array([0, 1, 0], dtype=np.int8)
            scores = np.array([-0.5, 1.2, 0.1])
            store.save_scores("validation_scores", y, scores)
            restored = store.load_scores("validation_scores")
            np.testing.assert_array_equal(restored[0], y)
            np.testing.assert_array_equal(restored[1], scores)
            with self.assertRaises(ValueError):
                store.save_scores("bad", y, np.array([0.1, np.nan, 0.2]))

    def test_corrupt_score_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = ModelStageCheckpointStore(Path(temporary), {"fold": 1})
            store.save_scores("test_scores", np.array([0, 1]), np.array([0.2, 0.8]))
            (Path(temporary) / "test_scores.npz").write_bytes(b"broken")
            self.assertIsNone(store.load_scores("test_scores"))


if __name__ == "__main__":
    unittest.main()
