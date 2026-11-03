import unittest

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from modeling.baseline import (
    FeatureBatch, calculate_metrics, choose_f1_threshold,
    fit_validate_model, positive_scores, build_baseline_estimators,
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


if __name__ == "__main__":
    unittest.main()
