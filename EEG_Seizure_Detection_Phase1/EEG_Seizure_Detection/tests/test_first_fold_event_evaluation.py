import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from data_management.patient_mapping import Recording
from scripts.evaluate_first_fold_events import _score_slices, _patient_summaries


class FirstFoldEventEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.recording = Recording(
            subject="chb01", patient_id="patient_01",
            edf_file="chb01_03.edf", relative_path="chb01/chb01_03.edf",
            seizure_count=1, seizure_intervals_seconds=("10-15",),
            annotation_source="subject_summary", status="SUCCESS",
        )

    def test_score_slicing_aligns_saved_window_labels_and_counts_event_without_duration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            np.savez_compressed(
                root / "chb01_chb01_03.npz",
                y=np.asarray([0, 1, 0], dtype=np.int8),
                starts=np.asarray([0.0, 5.0, 10.0]),
            )
            results = _score_slices(
                [self.recording],
                np.asarray([0, 1, 0], dtype=np.int8),
                np.asarray([0.1, 0.9, 0.2]),
                root,
                0.5,
                "test",
            )
            self.assertEqual(results[0]["event_count"], 1)
            self.assertEqual(results[0]["detected_events"], 1)
            self.assertEqual(results[0]["false_alarm_count"], 0)
            self.assertIsNone(results[0]["false_alarms_per_hour"])

    def test_score_label_misalignment_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            np.savez_compressed(
                root / "chb01_chb01_03.npz",
                y=np.asarray([1, 0, 0], dtype=np.int8),
                starts=np.asarray([0.0, 5.0, 10.0]),
            )
            with self.assertRaisesRegex(ValueError, "do not align"):
                _score_slices(
                    [self.recording],
                    np.asarray([0, 1, 0], dtype=np.int8),
                    np.asarray([0.1, 0.9, 0.2]),
                    root,
                    0.5,
                    "test",
                )

    def test_patient_summary_keeps_unknown_exposure_null(self):
        rows = [{
            "patient_id": "patient_01",
            "event_count": 2,
            "detected_events": 1,
            "missed_events": 1,
            "mean_detection_delay_seconds": 3.0,
            "false_alarm_count": 4,
        }]
        summary = _patient_summaries(rows)[0]
        self.assertEqual(summary["event_sensitivity"], 0.5)
        self.assertEqual(summary["false_alarm_count"], 4)
        self.assertIsNone(summary["false_alarms_per_hour"])


if __name__ == "__main__":
    unittest.main()
