# Inner OOF scaler statistics cache

## Purpose

The first outer fold holds out `patient_01`. Its remaining 22 patients are
used for inner model development. This cache stores per-recording raw EEG
channel sufficient statistics so each patient-held-out inner fold can construct
its own training-only channel scaler without repeatedly flattening all samples.

## Contents

- `evaluation/oof_scaler_cache.py`: population count/mean/M2 calculation,
  parallel-Welford merge, scaler finalization, and fold-specific `log_std`
  reconstruction.
- `scripts/build_oof_recording_stats_cache.py`: resumable per-recording
  statistics artifacts and a manifest under `cache/oof_recording_stats_v1`.

The builder processes only the first outer fold's 22 training patients. It
excludes the outer held-out patient before opening processed recordings.
Existing per-recording artifacts are reused only when their source signature
and array structure validate. A changed processed source invalidates its
corresponding artifact.

## Run

From the EEG Python project root:

```powershell
python -m pytest tests/test_oof_scaler_cache.py -q
python -m scripts.build_oof_recording_stats_cache --audit ..\\..\\docs\\full_annotation_audit.csv
```

The builder reads existing processed NPZ windows; it does not require original
EDF files, run Welch spectral extraction, train a model, or read outer-test
recordings. It can be safely rerun after interruption. Do not commit generated
cache files.

## OOF fold requirements

For each of the 22 inner held-out patients:
1. Merge statistics from the other 21 patients only.
2. Finalize the channel scaler using population variance and epsilon
   `1e-6`, matching `FoldChannelStandardizer`.
3. Recompute the 17 `log_std` columns from the raw processed windows using
   that fold's scaler. This is necessary because the existing validation cache
   contains 422 windows clipped at the `log(1e-12)` floor in every channel.
4. Reuse the other nine cached features only after checking recording identity,
   row alignment, feature version, and numerical invariance.
5. Train on the 21 patients and score only the held-out inner patient.

The OOF score collection and threshold-selection protocol must be completed
and frozen before the outer `patient_01` test labels are accessed. The cache
builder is not itself an OOF evaluation and does not claim model performance.
