# Current Project Status — 5 November 2026

**Active repository:** https://github.com/shivkumar15/EEG  
**Active branch:** `feature/threshold-strategy-score-artifacts`  
**Current milestone:** Phase 4 baseline engineering — accuracy roadmap Gate 0 regression checks passed; event-level evaluation is the next implementation milestone.

## Project objective

Academic binary seizure detection from EEG windows using the CHB-MIT dataset. The task is seizure detection, not prediction of future seizures. This is not a medical device and must not be used for diagnosis or treatment decisions.

## Verified research dataset

- Full audit: 686 EDF recordings, 198 seizure events, 24 subject folders; zero annotation parse failures.
- Primary cohort: 683 recordings, 185 seizure events, 23 independent patients.
- CHB01 and CHB21 are grouped as the same individual (`patient_01`).
- Three CHB12 recordings are excluded from the primary cohort because of incompatible montage.
- All 686 headers were inspected; all use 256 Hz.
- Preferred 17-channel montage is present in 683/686 recordings.

## Verified preprocessing and split design

- Full primary-cohort integrity audit: 683/683 recordings valid.
- 704,836 windows: 702,280 normal and 2,556 seizure.
- Window length 10 seconds; stride 5 seconds.
- 23 outer LOPO folds; every eligible recording tested exactly once; no patient leakage in split inspection.
- Nested split: 17 fit patients, 5 validation patients, 1 outer-test patient.
- Fold-wise standardization is fitted on inner-fit patients only and applied to validation/test.
- These audits verify data and split integrity, not model performance.

## Verified feature pipeline

- 13 features per channel and 17 channels = 221 features per window.
- Features include time-domain statistics, five frequency-band powers and spectral entropy.
- Welch uses up to 2-second segments; band power integrates between configured edges using interpolated PSD values.
- Synthetic validation covers five pure tones, ten boundary-near frequencies, a mixed 2 Hz + 10 Hz signal and a noisy 10 Hz signal.
- `PreparedFold.iter_features("fit"|"validation"|"test")` streams one recording at a time and returns features with labels, timestamps, sampling frequency and recording identity.
- Synthetic validation and software tests do not establish real-EEG model performance.
- Fold-standardized band powers are not calibrated physical microvolt-squared power.

## Phase 4 — baseline model development

### Implemented
- Feature extraction and fold-wise feature integration.
- Logistic Regression and Random Forest baseline pipelines/utilities.
- Validation-only F1 threshold selection and metric calculation.
- First-fold preflight and first-fold runner.
- Per-recording feature cache and fold-specific scaler checkpoints.
- Model-stage checkpoint store and integration on the current branch.

### Current checkpoint implementation (4.5.2)
The current branch contains model-stage persistence for:
1. Completed inner Logistic Regression fit.
2. Inner validation scores.
3. Validation-selected threshold and metrics.
4. Completed final outer-training model fit.
5. Outer-test scores.
6. Completed first-fold JSON result.

Reuse is guarded by experiment signatures and artifact SHA-256 integrity. Cached labels are compared with current split labels.

**Known limitation:** an interrupted `LogisticRegression(solver="liblinear")` fit must restart from the beginning; the solver does not provide a supported mid-fit continuation mechanism. Checkpoints preserve completed stages, not an in-progress solver state.

**Verification state (5 November 2026):** the active branch `feature/threshold-strategy-score-artifacts` is 19 commits ahead of `feature/model-stage-checkpoints` and includes the model-stage checkpoint implementation. The user reports the complete repository test suite passing after the event-evaluation changes: **147 passed, 4 subtests passed, 4 skipped, 0 failures, in 3.43 seconds**. The focused event and saved-window tests passed **12/12 in 2.14 seconds**. These are local software-test results; they do not validate model accuracy or prove an actual long-running process can resume from a real interruption. The robust feature extraction tests also pass: 6/6 in 1.20 seconds. These are local software-test results; they do not validate model accuracy or prove an actual long-running process can resume from a real interruption. A controlled runner interruption/restart test remains pending. Do not start an expensive full-data experiment until runtime and recovery gates are reviewed.

## Event-level evaluation foundation — implementation started

- Added `evaluation/event_metrics.py` for positive-window alarm merging, annotation overlap matching, event sensitivity, detection delay, false-alarm count and false alarms per non-seizure hour.
- Added deterministic synthetic tests in `tests/test_event_metrics.py`.
- Added `docs/EVENT_LEVEL_EVALUATION.md` to freeze version-1 semantics.
- Newly processed NPZ and metadata files now store exact EDF recording duration. Existing 683 NPZ artifacts predate this field; do not calculate false alarms/hour from their last complete window end.
- **Local verification complete (5 November 2026):** focused event + saved-window tests 12/12 passed in 2.14 seconds; full suite 147 passed, 4 subtests passed, 4 skipped, 0 failures, in 3.43 seconds.

## Immediate next actions

1. Implement a safe, restartable exact-duration backfill for existing processed recordings using EDF header-only reads; preserve existing NPZ contents and record duration in aligned metadata/manifest artifacts.
2. Add focused tests for interrupted/resumed backfill, existing-duration validation, metadata alignment and missing/corrupt EDF handling.
3. Integrate event evaluation into the first-fold runner, retaining recording identity, timestamps and exact duration in each score artifact.
4. Add patient-level event summaries and per-event error tables.
5. Profile representative feature/scaler stages and validate recovery before authorizing any model training.

## Not yet completed

- Complete 23-fold baseline runner and aggregated results.
- Real-EEG baseline metrics across all outer patients.
- 1D CNN, CNN-BiLSTM and CNN-BiLSTM-attention experiments.
- Event-level evaluation integration into the model runner and full 23-patient results.
- Explainability.
- FastAPI inference integration.
- React dashboard integration with validated model output.
- Final reproducibility and submission package.

## React dashboard status

Separate branch: `feature/react-dashboard-foundation`. Open PR #1: https://github.com/shivkumar15/EEG/pull/1. It contains illustrative mock data only. It is not merged, the local build has not been confirmed here, and it is not connected to a trained model or inference API.

## Research safeguards

- Never randomly split overlapping windows across train/test.
- Never fit scalers, feature selectors, thresholds or hyperparameters on outer-test patients.
- Keep all model comparisons on identical patient-wise splits.
- Report window-level and event-level results separately.
- Define event matching and alarm rules before reporting false alarms per hour.
- Preserve dataset provenance and do not commit raw EDFs or runtime caches.

## Relevant documentation

- [Project Master Plan](PROJECT_MASTER_PLAN.md)
- [AI / Teammate Handoff](AI_HANDOFF.md)
- [Development Log](DEVELOPMENT_LOG.md)
- [Training Checkpoint Policy](ML_TRAINING_CHECKPOINT_POLICY.md)
- [Scaler Checkpoints](SCALER_CHECKPOINTS.md)
- [Model-Stage Checkpoints](MODEL_STAGE_CHECKPOINTS.md)
- [Upstream Change Log](CHANGELOG_FOR_UPSTREAM.md)
