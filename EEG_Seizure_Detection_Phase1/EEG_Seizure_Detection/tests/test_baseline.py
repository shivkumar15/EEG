import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from modeling.baseline import (
    FeatureBatch, calculate_metrics, choose_f1_threshold,
    fit_validate_model, positive_scores, build_baseline_estimators,
    collect_features,
)


class BaselineUtilityTests(unittest.TestCase):
    def test_builds_two_documented_baselines(self):
        models = build_baseline_estimators()
        self.assertEqual(set(models), {"logistic_regression", "random_forest"})
        self.assertIn("feature_scaler", models["logistic_regression"].named_steps)

    def test_threshold_is_selected_from_validation_scores(self):
        y = np.array([0, 0, 1, 1])
        scores = np.array([-2.0, -1.0, 1.0, 2.0])
        threshold = choose_f1_threshold(y, scores)
        self.assertEqual(calculate_metrics(y, scores, threshold)["f1"], 1.0)

    def test_metrics_report_confusion_counts_and_imbalance_metrics(self):
        y = np.array([0, 0, 0, 1, 1])
        scores = np.array([0.1, 0.2, 0.8, 0.7, 0.9])
        result = calculate_metrics(y, scores, 0.5)
        self.assertEqual((result["tn"], result["fp"], result["fn"], result["tp"]), (2, 1, 0, 2))
        self.assertEqual(result["sensitivity"], 1.0)
        self.assertEqual(result["specificity"], 2 / 3)
        self.assertIsNotNone(result["auprc"])
        self.assertIsNotNone(result["auroc"])

    def test_auroc_is_none_for_single_class_test_patient(self):
        result = calculate_metrics(np.zeros(3), np.array([0.1, 0.2, 0.3]), 0.2)
        self.assertIsNone(result["auroc"])
        self.assertIsNone(result["auprc"])

    def test_fit_validation_keeps_validation_out_of_estimator_fit(self):
        X_fit = np.array([[-2.0], [-1.0], [1.0], [2.0]])
        y_fit = np.array([0, 0, 1, 1])
        X_val = np.array([[-3.0], [3.0]])
        y_val = np.array([0, 1])
        model = Pipeline([
            ("scale", StandardScaler()),
            ("classifier", LogisticRegression(random_state=1)),
        ])
        fitted, threshold, metrics = fit_validate_model(
            model, FeatureBatch(X_fit, y_fit, ()),
            FeatureBatch(X_val, y_val, ()),
        )
        self.assertEqual(fitted.named_steps["scale"].mean_[0], 0.0)
        self.assertTrue(np.isfinite(positive_scores(fitted, X_val)).all())
        self.assertGreaterEqual(threshold, float(np.min(positive_scores(fitted, X_val))))
        self.assertIn("f1", metrics)

    def test_collect_features_preallocates_aligned_float32_matrix(self):
        from data_management.patient_mapping import Recording

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            recordings = [
                Recording("chb01", "patient_01", "chb01_01.edf", "chb01/chb01_01.edf",
                          0, (), "test", "SUCCESS"),
                Recording("chb02", "patient_02", "chb02_01.edf", "chb02/chb02_01.edf",
                          1, ("10-20",), "test", "SUCCESS"),
            ]
            labels = [np.array([0, 0], dtype=np.int8), np.array([0, 1], dtype=np.int8)]
            for recording, target in zip(recordings, labels):
                filename = f"{recording.subject}_{Path(recording.edf_file).stem}.npz"
                np.savez_compressed(directory / filename, y=target)

            loaded = [
                SimpleNamespace(X=np.zeros((2, 17, 4), dtype=np.float32), y=target, sfreq=256.0)
                for target in labels
            ]
            scaler = SimpleNamespace(transform=lambda values: values)
            feature_matrices = [
                np.full((2, 221), 1.0, dtype=np.float32),
                np.full((2, 221), 2.0, dtype=np.float32),
            ]
            with patch("modeling.baseline.load_recording_windows", side_effect=loaded), 
                 patch("modeling.baseline.extract_features", side_effect=feature_matrices):
                batch = collect_features(recordings, directory, scaler)

            self.assertEqual(batch.X.shape, (4, 221))
            self.assertEqual(batch.X.dtype, np.float32)
            self.assertTrue(np.array_equal(batch.y, np.array([0, 0, 0, 1], dtype=np.int8)))
            self.assertTrue(np.all(batch.X[:2] == 1.0))
            self.assertTrue(np.all(batch.X[2:] == 2.0))
            self.assertEqual(batch.recording_paths, ())

    def test_collect_features_rejects_manifest_label_disagreement(self):
        from data_management.patient_mapping import Recording

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            recording = Recording(
                "chb01", "patient_01", "chb01_01.edf", "chb01/chb01_01.edf",
                1, ("10-20",), "test", "SUCCESS",
            )
            filename = f"{recording.subject}_{Path(recording.edf_file).stem}.npz"
            np.savez_compressed(directory / filename, y=np.array([0, 0], dtype=np.int8))
            with self.assertRaisesRegex(ValueError, "disagree"):
                collect_features([recording], directory, SimpleNamespace(transform=lambda x: x))


if __name__ == "__main__":
    unittest.main()
