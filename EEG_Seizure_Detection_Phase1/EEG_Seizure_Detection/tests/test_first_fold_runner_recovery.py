"""Runner-level tests for durable completed first-fold recovery."""
import json
import tempfile
import unittest

import numpy as np
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from modeling.experiment_checkpoints import ModelStageCheckpointStore
from scripts import run_first_baseline_fold as runner


class FirstFoldRunnerRecoveryTests(unittest.TestCase):
    def test_completed_result_is_recovered_before_expensive_pipeline_starts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            processed_file = root / "recording.npz"
            processed_file.write_bytes(b"processed-recording-fingerprint")

            fit_recording = SimpleNamespace(
                relative_path="chb02/chb02_01.edf",
                patient_id="patient_02",
                seizure_count=0,
            )
            validation_recording = SimpleNamespace(
                relative_path="chb03/chb03_01.edf",
                patient_id="patient_03",
                seizure_count=1,
            )
            test_recording = SimpleNamespace(
                relative_path="chb01/chb01_01.edf",
                patient_id="patient_01",
                seizure_count=1,
            )
            recordings = [fit_recording, validation_recording, test_recording]
            fold = SimpleNamespace(
                fold_id=1,
                test_patient_id="patient_01",
                train_recordings=[fit_recording, validation_recording],
                test_recordings=[test_recording],
            )
            inner_split = SimpleNamespace(
                train_recordings=[fit_recording],
                validation_recordings=[validation_recording],
            )
            expected_result = {
                "experiment": "first_nested_lopo_logistic_regression",
                "status": "completed",
                "fold_id": 1,
                "held_out_patient": "patient_01",
                "outer_test_metrics": {"f1": 0.75},
            }
            output_path = root / "output" / "first_fold.json"

            with (
                patch.object(runner, "PROJECT_ROOT", root),
                patch.object(runner, "PROCESSED_DIR", root / "processed"),
                patch.object(runner, "load_recording_manifest", return_value=recordings),
                patch.object(runner, "filter_primary_cohort", side_effect=lambda value: value),
                patch.object(runner, "build_lopo_folds", return_value=[fold]),
                patch.object(runner, "build_patient_validation_split", return_value=inner_split),
                patch.object(
                    runner, "processed_path_for_recording",
                    return_value=processed_file,
                ),
            ):
                # Seed the durable checkpoint with the exact signature the runner will use.
                context = runner._build_checkpoint_context(fold, inner_split, runner.RANDOM_STATE)
                durable_root = (
                    root / "results" / "baselines" / "checkpoints"
                    / "first_fold_patient_01_logistic_regression"
                )
                durable_store = ModelStageCheckpointStore(durable_root, context)
                durable_store.save_scores(
                    "inner_validation_scores",
                    np.array([0, 1], dtype=np.int8),
                    np.array([0.2, 0.8], dtype=np.float64),
                )
                durable_store.save_scores(
                    "outer_test_scores",
                    np.array([0, 1], dtype=np.int8),
                    np.array([0.3, 0.7], dtype=np.float64),
                )
                durable_store.save_json("fold_result", expected_result)

                with (
                    patch.object(runner, "prepare_lopo_fold", side_effect=AssertionError("fold preparation must be skipped")) as prepare,
                    patch.object(runner, "collect_features", side_effect=AssertionError("feature extraction must be skipped")) as features,
                    patch.object(runner, "fit_channel_standardizer", side_effect=AssertionError("scaler fitting must be skipped")) as scaler,
                    patch.object(runner, "build_baseline_estimators", side_effect=AssertionError("model training must be skipped")) as models,
                    patch.object(runner, "positive_scores", side_effect=AssertionError("model scoring must be skipped")) as scoring,
                ):
                    result = runner.run_first_fold(root / "audit.csv", output_path)

                self.assertEqual(result, expected_result)
                self.assertTrue(output_path.is_file())
                self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), expected_result)
                prepare.assert_not_called()
                features.assert_not_called()
                scaler.assert_not_called()
                models.assert_not_called()
                scoring.assert_not_called()


class ExistingResultSafetyGuardTests(unittest.TestCase):
    def test_completed_legacy_result_without_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "first_fold.json"
            output_path.write_text(
                json.dumps({
                    "experiment": "first_nested_lopo_logistic_regression",
                    "status": "completed",
                    "fold_id": 1,
                    "held_out_patient": "patient_01",
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "no compatible durable checkpoint"):
                runner._check_existing_completed_result(output_path)

            # The safety check must never modify or delete the historical result.
            self.assertTrue(output_path.is_file())
            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8"))["status"],
                "completed",
            )

    def test_missing_output_allows_a_new_experiment(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "not_created_yet.json"
            runner._check_existing_completed_result(output_path)
            self.assertFalse(output_path.exists())

    def test_unreadable_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "corrupt.json"
            output_path.write_text("{not valid json", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "cannot be safely inspected"):
                runner._check_existing_completed_result(output_path)



if __name__ == "__main__":
    unittest.main()
