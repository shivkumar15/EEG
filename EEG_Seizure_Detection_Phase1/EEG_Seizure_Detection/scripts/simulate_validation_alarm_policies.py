"""Explore duration filtering and short-gap merging on saved robust inner-validation alarms.

This is an interval-level post-processing simulation, not model retraining.
It does not access outer-test recordings or select a final policy.
Run from the EEG_Seizure_Detection project directory:
    python -m scripts.simulate_validation_alarm_policies
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from collections import defaultdict

DEFAULT_INPUT = Path("results/baselines/robust_feature_first_fold_event_metrics_v1.json")
DEFAULT_OUTPUT = Path("results/baselines/robust_validation_alarm_policy_simulation_v1.json")
MIN_DURATIONS = (0.0, 15.0, 20.0, 30.0)
MERGE_GAPS = (0.0, 5.0, 10.0, 15.0, 20.0, 30.0)


def _interval(start: object, end: object, context: str) -> tuple[float, float]:
    start_value, end_value = float(start), float(end)
    if (
        not math.isfinite(start_value)
        or not math.isfinite(end_value)
        or start_value < 0
        or end_value <= start_value
    ):
        raise ValueError(f"Invalid interval in {context}: {start_value}, {end_value}")
    return start_value, end_value


def merge_intervals(
    intervals: list[tuple[float, float]], gap_seconds: float
) -> list[tuple[float, float]]:
    """Merge overlapping/touching intervals and gaps <= gap_seconds."""
    if not math.isfinite(gap_seconds) or gap_seconds < 0:
        raise ValueError("gap_seconds must be finite and non-negative")
    ordered = sorted(intervals)
    if not ordered:
        return []
    merged: list[list[float]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + gap_seconds + 1e-9:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _overlaps(alarm: tuple[float, float], event: tuple[float, float]) -> bool:
    return alarm[0] < event[1] and alarm[1] > event[0]


def _f2(precision: float, recall: float) -> float:
    denominator = 4 * precision + recall
    return 5 * precision * recall / denominator if denominator else 0.0


def _evaluate_recording(
    record: dict, min_duration: float, merge_gap: float
) -> dict:
    path = record["relative_path"]
    raw_alarms = [
        _interval(a["start"], a["end"], f"alarm {path}")
        for a in record.get("alarms", [])
    ]
    events = [
        _interval(
            e["seizure_start_seconds"], e["seizure_end_seconds"],
            f"seizure event {path}",
        )
        for e in record.get("events", [])
    ]

    merged = merge_intervals(raw_alarms, merge_gap)
    retained = [
        alarm for alarm in merged
        if alarm[1] - alarm[0] + 1e-9 >= min_duration
    ]

    detected = 0
    delays: list[float] = []
    for event in events:
        matching = [alarm for alarm in retained if _overlaps(alarm, event)]
        if matching:
            detected += 1
            first_alarm_start = min(alarm[0] for alarm in matching)
            delays.append(max(0.0, first_alarm_start - event[0]))

    false_alarm_count = sum(
        not any(_overlaps(alarm, event) for event in events)
        for alarm in retained
    )
    exposure = record.get("non_seizure_duration_seconds")
    if exposure is None:
        raise ValueError(f"Missing exact non-seizure exposure for {path}")
    exposure = float(exposure)
    if not math.isfinite(exposure) or exposure <= 0:
        raise ValueError(f"Invalid non-seizure exposure for {path}")

    return {
        "relative_path": path,
        "patient_id": record["patient_id"],
        "event_count": len(events),
        "detected_events": detected,
        "missed_events": len(events) - detected,
        "detection_delays_seconds": delays,
        "alarm_count": len(retained),
        "false_alarm_count": false_alarm_count,
        "non_seizure_duration_seconds": exposure,
    }


def _summarize(records: list[dict]) -> dict:
    event_count = sum(r["event_count"] for r in records)
    detected = sum(r["detected_events"] for r in records)
    false_alarms = sum(r["false_alarm_count"] for r in records)
    exposure = sum(r["non_seizure_duration_seconds"] for r in records)
    delays = [d for r in records for d in r["detection_delays_seconds"]]
    return {
        "recording_count": len(records),
        "event_count": event_count,
        "detected_events": detected,
        "missed_events": event_count - detected,
        "event_sensitivity": detected / event_count if event_count else None,
        "mean_detection_delay_seconds": (
            sum(delays) / len(delays) if delays else None
        ),
        "false_alarm_count": false_alarms,
        "non_seizure_exposure_hours": exposure / 3600.0,
        "false_alarms_per_non_seizure_hour": (
            false_alarms / (exposure / 3600.0)
        ),
    }


def simulate(input_path: Path = DEFAULT_INPUT) -> dict:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    if data.get("status") != "completed":
        raise ValueError("Input robust event evaluation is not completed")
    validation = data.get("validation")
    if not isinstance(validation, dict) or not isinstance(validation.get("recordings"), list):
        raise ValueError("Input does not contain validation recordings")

    source_records = validation["recordings"]
    paths = [r.get("relative_path") for r in source_records]
    if not paths or any(not p for p in paths) or len(paths) != len(set(paths)):
        raise ValueError("Validation recording paths are missing or duplicated")

    expected_count = validation.get("aggregate", {}).get("recording_count")
    if expected_count is not None and expected_count != len(source_records):
        raise ValueError("Validation recording count does not match aggregate")

    simulations = []
    for min_duration in MIN_DURATIONS:
        for merge_gap in MERGE_GAPS:
            per_recording = [
                _evaluate_recording(r, min_duration, merge_gap)
                for r in source_records
            ]
            pooled = _summarize(per_recording)

            by_patient: dict[str, list[dict]] = defaultdict(list)
            for row in per_recording:
                by_patient[row["patient_id"]].append(row)
            patient_summaries = {
                patient: _summarize(rows)
                for patient, rows in sorted(by_patient.items())
            }
            seizure_bearing = [
                item for item in patient_summaries.values()
                if item["event_count"] > 0
            ]
            macro_sensitivity = (
                sum(item["event_sensitivity"] for item in seizure_bearing)
                / len(seizure_bearing)
                if seizure_bearing else None
            )
            macro_f2_proxy_values = []
            for item in seizure_bearing:
                precision_proxy = (
                    item["detected_events"]
                    / (item["detected_events"] + item["false_alarm_count"])
                    if item["detected_events"] + item["false_alarm_count"] else 0.0
                )
                macro_f2_proxy_values.append(
                    _f2(precision_proxy, item["event_sensitivity"])
                )

            simulations.append({
                "min_alarm_duration_seconds": min_duration,
                "merge_gap_seconds": merge_gap,
                "pooled": pooled,
                "seizure_bearing_patient_count": len(seizure_bearing),
                "patient_macro_event_sensitivity": macro_sensitivity,
                "patient_macro_event_f2_proxy": (
                    sum(macro_f2_proxy_values) / len(macro_f2_proxy_values)
                    if macro_f2_proxy_values else None
                ),
                "patients": patient_summaries,
            })

    return {
        "status": "completed",
        "experiment": "robust_validation_alarm_policy_interval_simulation",
        "version": "duration_filter_gap_merge_grid_v1",
        "scope": "inner_validation_only",
        "source_result": str(input_path),
        "model_retrained": False,
        "features_reextracted": False,
        "thresholds_changed": False,
        "outer_test_read": False,
        "policy_grid": {
            "minimum_alarm_duration_seconds": list(MIN_DURATIONS),
            "merge_gap_seconds": list(MERGE_GAPS),
            "combination_count": len(simulations),
            "order": "merge intervals first, then filter by merged duration",
        },
        "metric_notes": [
            "Event detection is evaluated against the retained merged alarm intervals.",
            "Gap merging represents a continuously latched alarm across the merged gap; it can therefore change event overlap and delay.",
            "False alarms are retained alarm episodes overlapping no annotated seizure.",
            "False alarms/hour uses exact saved non-seizure exposure and is pooled by total false alarms divided by total exposure.",
            "Patient macro metrics average only seizure-bearing validation patients.",
            "The event F2 proxy treats detected events as true positives and false-alarm episodes as false positives; it is an exploratory proxy, not clinical utility.",
            "No policy is automatically selected by this script.",
        ],
        "baseline_source_metrics": validation.get("aggregate"),
        "simulations": simulations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = simulate(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(args.output)

    print(json.dumps({
        "status": result["status"],
        "model_retrained": result["model_retrained"],
        "outer_test_read": result["outer_test_read"],
        "combination_count": result["policy_grid"]["combination_count"],
        "output": str(args.output),
    }, indent=2))
    print("\nPolicy results (validation only):")
    for item in result["simulations"]:
        p = item["pooled"]
        print(
            f"min={item['min_alarm_duration_seconds']:>4.0f}s "
            f"gap={item['merge_gap_seconds']:>4.0f}s | "
            f"events={p['detected_events']}/{p['event_count']} "
            f"sens={p['event_sensitivity']:.3f} "
            f"FA={p['false_alarm_count']} "
            f"FA/h={p['false_alarms_per_non_seizure_hour']:.3f} "
            f"delay={p['mean_detection_delay_seconds']}"
        )


if __name__ == "__main__":
    main()
