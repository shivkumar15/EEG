# Event-level evaluation protocol

## Purpose

Window-level classification metrics do not tell us how many annotated seizure
events the system detects or how often it raises alarms during non-seizure
recording time. This module provides deterministic post-processing and
recording-level event metrics. It is an evaluation utility, not a clinical
alarm system.

## Frozen semantics in version 1

- Window predictions are binary and must be generated using a threshold chosen
  on inner validation data. This module never tunes thresholds.
- Each positive window maps to the half-open interval
  `[window_start, window_start + window_seconds)`.
- Overlapping or touching positive windows are merged into one alarm.
- An optional `merge_gap_seconds` can merge alarms separated by a small gap.
  It defaults to zero and must be selected using inner validation only.
- A seizure event is detected if at least one alarm overlaps its annotated
  interval (half-open interval overlap; boundary-only contact is not overlap).
- Detection delay is `max(0, first_overlapping_alarm.start - seizure.start)`.
  An alarm already active at annotated onset therefore has zero delay.
- An alarm is false only if it overlaps no annotated seizure event.
- False alarms/hour = false alarm count / non-seizure recording hours.
  Annotated seizure duration is subtracted from recording duration.
- Event sensitivity is undefined (`null`) for a recording with no annotated
  seizures. False alarms/hour is undefined if there is no non-seizure exposure.

## Exact recording duration is mandatory

Newly processed NPZ files persist `recording_duration_seconds` from the
actual loaded signal sample count divided by sampling frequency, and the
metadata CSV repeats this value. For existing artifacts, first run the read-only
`scripts/audit_recording_durations.py` to inspect duration values already retained
in NPZ files, aligned metadata CSVs and `processed/recording_durations.json`.
The original EDF dataset is currently unavailable in the working copy, so the
EDF-header backfill utility cannot be used unless the source files are restored.
If no exact duration survives, event sensitivity, event counts, detection delay
and false-alarm counts can still be reported from the annotation manifest and
window timestamps. The evaluator accepts a missing duration for these metrics.
In that case non-seizure exposure and false alarms/hour are `null`; pooled
false alarms/hour is also `null` if any included recording lacks exact exposure.
Never substitute the last complete window end as the recording duration.
The last complete window end is only a lower bound because a trailing partial
window may exist. Do **not** use that lower bound as the false-alarm-rate
denominator.

## Matching and aggregation

Each annotated seizure event is evaluated independently: any overlapping
alarm detects that event. Thus one long alarm can overlap two annotations and
detect both; alarm-merging parameters must be frozen and reported. A false
alarm is an alarm with no overlap with any seizure event.

`aggregate_event_metrics` pools event counts and non-seizure exposure across
recordings. If any recording has unknown exposure, pooled exposure and pooled
false alarms/hour are `null`, while event counts, event sensitivity and false-
alarm counts remain available. Compute patient-macro metrics separately by
first aggregating recordings within each canonical patient; do not treat
recording-level values as independent patients.

## Limitations

The overlap-based match is intentionally transparent and has no extra onset
tolerance. It does not model clinical seizure alarm requirements, intervention
latency, or alarm refractory policies. Any alternative matching rule must be
predeclared, validated on inner patients, and versioned before outer-test use.


## First-fold saved-score integration

`scripts/evaluate_first_fold_events.py` evaluates the existing first-fold
inner-validation and outer-test score checkpoints without fitting or loading a
new model. It reconstructs the deterministic patient-grouped split, verifies
the score checkpoint signatures/checksums, and aligns concatenated score
slices to each recording by comparing saved score labels with the NPZ labels.
Any length or label mismatch fails closed.

The script reports event counts, event sensitivity, detection delay and
false-alarm counts for the validation-selected F1 and F2 thresholds. It writes
per-recording and per-patient summaries to
`results/baselines/first_fold_patient_01_event_metrics_v1.json`. Since exact
recording durations are unavailable in the retained cohort, exposure and
false alarms/hour remain null. This is one outer fold only and is not a
full-cohort performance estimate.

Run from the `EEG_Seizure_Detection` directory:

```powershell
python -m scripts.evaluate_first_fold_events --audit ..\\..\\docs\\full_annotation_audit.csv
```

This is a post-processing/evaluation step over saved scores; it does not
retrain Logistic Regression or regenerate EEG features.
