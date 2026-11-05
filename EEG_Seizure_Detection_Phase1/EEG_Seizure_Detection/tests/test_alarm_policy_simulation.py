import unittest

from scripts.simulate_validation_alarm_policies import (
    _evaluate_recording,
    merge_intervals,
    MIN_DURATIONS,
    MERGE_GAPS,
)


class AlarmPolicySimulationTests(unittest.TestCase):
    def test_grid_has_24_combinations(self):
        self.assertEqual(len(MIN_DURATIONS) * len(MERGE_GAPS), 24)

    def test_gap_merge_combines_intervals_at_boundary(self):
        self.assertEqual(
            merge_intervals([(0, 10), (15, 20)], 5),
            [(0, 20)],
        )

    def test_gap_larger_than_tolerance_does_not_merge(self):
        self.assertEqual(
            merge_intervals([(0, 10), (15.01, 20)], 5),
            [(0, 10), (15.01, 20)],
        )

    def test_duration_filter_applies_after_gap_merge(self):
        record = {
            "relative_path": "chb01/test.edf",
            "patient_id": "patient_01",
            "alarms": [{"start": 0, "end": 10}, {"start": 15, "end": 20}],
            "events": [],
            "non_seizure_duration_seconds": 3600,
        }
        # Separate 10s and 5s alarms are both removed by a 15s minimum.
        separate = _evaluate_recording(record, 15, 0)
        self.assertEqual(separate["alarm_count"], 0)
        # A 5s gap merge creates one 20s alarm, which is retained.
        merged = _evaluate_recording(record, 15, 5)
        self.assertEqual(merged["alarm_count"], 1)
        self.assertEqual(merged["false_alarm_count"], 1)

    def test_filter_can_remove_short_true_detection(self):
        record = {
            "relative_path": "chb01/test.edf",
            "patient_id": "patient_01",
            "alarms": [{"start": 10, "end": 20}],
            "events": [{"seizure_start_seconds": 15, "seizure_end_seconds": 25}],
            "non_seizure_duration_seconds": 3590,
        }
        baseline = _evaluate_recording(record, 0, 0)
        filtered = _evaluate_recording(record, 15, 0)
        self.assertEqual(baseline["detected_events"], 1)
        self.assertEqual(filtered["detected_events"], 0)

    def test_gap_merge_can_bridge_alarm_across_event_and_is_documented_behavior(self):
        record = {
            "relative_path": "chb01/test.edf",
            "patient_id": "patient_01",
            "alarms": [{"start": 0, "end": 5}, {"start": 15, "end": 20}],
            "events": [{"seizure_start_seconds": 8, "seizure_end_seconds": 12}],
            "non_seizure_duration_seconds": 3596,
        }
        result = _evaluate_recording(record, 0, 10)
        self.assertEqual(result["detected_events"], 1)
        self.assertEqual(result["false_alarm_count"], 0)
        self.assertEqual(result["detection_delays_seconds"], [0.0])


if __name__ == "__main__":
    unittest.main()
