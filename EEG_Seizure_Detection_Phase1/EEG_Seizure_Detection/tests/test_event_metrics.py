import unittest

import numpy as np

from evaluation.event_metrics import (
    aggregate_event_metrics,
    evaluate_recording_events,
    parse_seizure_intervals,
    windows_to_alarms,
)


class EventMetricTests(unittest.TestCase):
    def test_positive_overlapping_windows_merge_into_one_alarm(self):
        alarms = windows_to_alarms(
            [0, 5, 10, 15], [0, 1, 1, 0],
            recording_duration_seconds=25, window_seconds=10,
        )
        self.assertEqual([(a.start, a.end) for a in alarms], [(5.0, 20.0)])

    def test_short_gap_can_be_merged_when_explicitly_configured(self):
        alarms = windows_to_alarms(
            [0, 15], [1, 1], recording_duration_seconds=30,
            window_seconds=10, merge_gap_seconds=5,
        )
        self.assertEqual([(a.start, a.end) for a in alarms], [(0.0, 25.0)])

    def test_gap_is_not_merged_when_it_exceeds_policy(self):
        alarms = windows_to_alarms(
            [0, 20], [1, 1], recording_duration_seconds=30,
            window_seconds=10, merge_gap_seconds=5,
        )
        self.assertEqual(len(alarms), 2)

    def test_detects_event_and_reports_onset_delay(self):
        result = evaluate_recording_events(
            [0, 5, 10, 15], [0, 1, 1, 0], [(12, 16)],
            recording_duration_seconds=20, window_seconds=5,
        )
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["detected_events"], 1)
        self.assertEqual(result["event_sensitivity"], 1.0)
        self.assertEqual(result["mean_detection_delay_seconds"], 0.0)

    def test_missed_event_has_zero_event_sensitivity(self):
        result = evaluate_recording_events(
            [0, 5, 10], [0, 0, 0], [(12, 16)],
            recording_duration_seconds=15, window_seconds=5,
        )
        self.assertEqual(result["missed_events"], 1)
        self.assertEqual(result["event_sensitivity"], 0.0)
        self.assertIsNone(result["mean_detection_delay_seconds"])

    def test_false_alarm_rate_uses_non_seizure_exposure(self):
        result = evaluate_recording_events(
            [0, 10, 20, 30], [1, 0, 0, 1], [(20, 25)],
            recording_duration_seconds=40, window_seconds=5,
        )
        self.assertEqual(result["false_alarm_count"], 1)
        self.assertAlmostEqual(result["non_seizure_duration_seconds"], 35.0)
        self.assertAlmostEqual(
            result["false_alarms_per_hour"], 3600.0 / 35.0
        )

    def test_alarm_touching_event_boundary_without_overlap_is_false(self):
        result = evaluate_recording_events(
            [0, 10], [1, 0], [(10, 15)],
            recording_duration_seconds=20, window_seconds=5,
        )
        self.assertEqual(result["detected_events"], 0)
        self.assertEqual(result["false_alarm_count"], 1)

    def test_no_seizure_recording_reports_false_alarm_rate_and_no_event_sensitivity(self):
        result = evaluate_recording_events(
            [0, 5, 10], [0, 1, 0], [],
            recording_duration_seconds=15, window_seconds=5,
        )
        self.assertIsNone(result["event_sensitivity"])
        self.assertEqual(result["false_alarm_count"], 1)
        self.assertAlmostEqual(result["false_alarms_per_hour"], 3600.0 / 15.0)

    def test_multiple_seizures_are_evaluated_independently(self):
        result = evaluate_recording_events(
            [0, 5, 10, 15, 20, 25], [0, 1, 0, 0, 1, 0],
            [(6, 9), (21, 24)], recording_duration_seconds=30,
            window_seconds=5,
        )
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(result["detected_events"], 2)
        self.assertEqual(result["event_sensitivity"], 1.0)

    def test_manifest_interval_strings_are_parsed(self):
        intervals = parse_seizure_intervals(["2996-3036", "10.5-12.25"])
        self.assertEqual(
            [(item.start, item.end) for item in intervals],
            [(10.5, 12.25), (2996.0, 3036.0)],
        )

    def test_aggregate_metrics_pool_counts_and_exposure(self):
        first = evaluate_recording_events(
            [0, 5], [1, 0], [(1, 3)], recording_duration_seconds=10,
            window_seconds=5,
        )
        second = evaluate_recording_events(
            [0, 5], [0, 1], [], recording_duration_seconds=10,
            window_seconds=5,
        )
        combined = aggregate_event_metrics([first, second])
        self.assertEqual(combined["recording_count"], 2)
        self.assertEqual(combined["event_count"], 1)
        self.assertEqual(combined["detected_events"], 1)
        self.assertEqual(combined["false_alarm_count"], 1)
        self.assertAlmostEqual(combined["non_seizure_duration_seconds"], 18.0)


if __name__ == "__main__":
    unittest.main()
