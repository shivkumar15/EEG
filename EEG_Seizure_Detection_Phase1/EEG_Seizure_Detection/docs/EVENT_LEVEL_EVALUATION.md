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

Newly processed NPZ files now persist `recording_duration_seconds` from the
actual loaded signal sample count divided by sampling frequency, and the
metadata CSV repeats this value for integrity checks. The event evaluator
requires `recording_duration_seconds` explicitly. The 683 existing processed
NPZ files predate this field, so they must be backfilled from EDF headers or
reprocessed before event-level false-alarm rates are computed. The last
complete window end is only a lower bound because a trailing partial window
may exist. Do **not** use that lower bound as the false-alarm-rate denominator.

## Matching and aggregation

Each annotated seizure event is evaluated independently: any overlapping
alarm detects that event. Thus one long alarm can overlap two annotations and
detect both; alarm-merging parameters must be frozen and reported. A false
alarm is an alarm with no overlap with any seizure event.

`aggregate_event_metrics` pools event counts and non-seizure exposure across
recordings. Compute patient-macro metrics separately by first aggregating
recordings within each canonical patient; do not treat recording-level values
as independent patients.

## Limitations

The overlap-based match is intentionally transparent and has no extra onset
tolerance. It does not model clinical seizure alarm requirements, intervention
latency, or alarm refractory policies. Any alternative matching rule must be
predeclared, validated on inner patients, and versioned before outer-test use.
