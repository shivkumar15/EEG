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
- Newly processed NPZ and metadata files store exact EDF recording duration. The existing 683-recording processed cohort predates that change. The user confirmed the extracted original EDF dataset was deleted after earlier guidance that it was no longer required. The attempted backfill dry-run consequently found all 683 EDF paths missing; it made no changes. Do not ask the user to download/reprocess the dataset again at this stage.
- Added a read-only `scripts/audit_recording_durations.py` to inspect existing NPZ duration fields, aligned metadata CSVs and any central duration manifest. User ran it successfully: **683 recordings, 0 NPZ durations, 0 metadata durations, 0 manifest durations, 683 missing, 0 conflicts, 0 artifact errors**. It did not read EDFs or modify data.
- Updated `evaluation/event_metrics.py` so exact duration is optional for event matching, event sensitivity, detection delay and false-alarm counts. When duration is unavailable, non-seizure exposure and false alarms/hour are explicitly `null`; pooled false alarms/hour is also null if any recording lacks exact exposure. User verified focused duration/event tests: **18 passed in 0.75 seconds**; full suite: **158 passed, 4 subtests passed, 0 failures in 3.73 seconds**.
- Added `scripts/evaluate_first_fold_events.py` to evaluate the already-saved first-fold inner-validation and outer-test score artifacts without retraining. It reconstructs the deterministic patient split, verifies score artifact signatures/checksums, aligns score slices against per-recording NPZ labels, and writes per-recording/per-patient event metrics. User verified the evaluator's focused tests: **3 passed in 2.10 seconds**; the actual saved-score evaluation completed with no retraining. Validation: 19/29 events detected (65.52%), mean delay 15.74 s, 1,327 false alarms. Held-out patient_01: 1/11 events detected (9.09%), mean delay 58 s, 40 false alarms. F1 and F2 thresholds produced identical event outcomes for this fold. False alarms/hour remains null because exact recording durations are missing.
- Added per-seizure detail to `evaluation/event_metrics.py`: annotation interval, detected/missed status, first overlapping alarm, delay and matching alarm count. Added score diagnostics to the first-fold evaluator: max/median score among windows overlapping each event, highest-scoring window time, margin to selected threshold, and maximum score in a 30-second surrounding context. New focused tests and protocol documentation are committed; user verification is pending.
- **Local verification complete (5 November 2026):** focused event + saved-window tests 12/12 passed in 2.14 seconds; full suite 147 passed, 4 subtests passed, 4 skipped, 0 failures, in 3.43 seconds.

## Immediate next actions

1. Pull the latest branch and run `python -m pytest tests/test_event_metrics.py tests/test_first_fold_event_evaluation.py -q`, then the full suite.
2. Rerun `python -m scripts.evaluate_first_fold_events --audit ..\\..\\docs\\full_annotation_audit.csv` to regenerate the first-fold JSON with per-seizure details; this uses saved scores and does not retrain.
3. Inspect missed/detected seizure annotations and per-recording false-alarm counts to identify patient-specific failure patterns.
4. Extend saved-score event evaluation across all outer folds only where valid score artifacts already exist; do not launch model training just to obtain event metrics.
5. Use the error analysis to choose one controlled accuracy-improvement experiment, with unchanged patient-wise splits and validation-only tuning.

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


### Validation-only event threshold sweep added

- Added `scripts/sweep_event_thresholds.py` and unit tests. It loads the existing checksum-validated first-fold score checkpoints and existing processed timestamps/labels; no model training or feature extraction is performed.
- It evaluates 121 score-quantile candidates from 0.95 to 1.00 plus the existing validation F1/F2 thresholds. Selection uses only inner-validation seizure-bearing patient macro event F2 proxy. The proxy uses detected events divided by detected events plus false-alarm episodes as precision; it is explicitly not false alarms/hour.
- After freezing the validation-selected threshold, the script evaluates the outer-test patient for descriptive comparison only. The outer-test labels do not participate in selection.
- Output: `results/baselines/first_fold_event_threshold_sweep_v1.json`. User pull, tests and execution are pending.


---

## CTO decision update — approved next work (5 November 2026)

The following is the current execution direction and supersedes earlier roadmap/status text that says exact recording durations are unavailable.

### Verified discovery: recording durations are available

A direct GitHub-side audit matched `docs/signal_inventory.csv` against the 683 primary-cohort recordings from `docs/full_annotation_audit.csv`:

- 683/683 primary recordings matched.
- 0 missing, invalid or internally inconsistent duration records.
- Each duration agrees with `n_samples / sampling_frequency_hz` within 0.01 seconds.
- Total raw primary-cohort recording exposure: 979.9286 hours.

The historical NPZ duration audit remains correct (duration is absent from those NPZs), but the separate inventory file supplies the exact duration. **Next code task:** join the inventory by recording identity and use exact durations to calculate non-seizure exposure and false alarms/hour. Do not restore or reprocess EDF files for this purpose. The inventory total is raw recording time; subtract the union of annotated seizure intervals per recording before computing non-seizure FA/hour.

### Decisions adopted from the external checklist

1. Build a reusable, deterministic feature cache with patient ID, recording ID, window start, label, feature version and source signature. Prefer partitioned Parquet or memory-mapped NumPy arrays, not one monolithic CSV. Parallelize per recording only after measuring memory and limiting workers.
2. Create a scale-free feature core: relative five-band powers, spectral entropy, skewness, excess kurtosis and normalized line length. Test `log_std` as a separate amplitude ablation.
3. Compare per-channel features with pooled channel median/IQR and their combination. Test maximum pooling separately due to noisy-channel sensitivity.
4. Use patient-grouped inner out-of-fold predictions for model selection. Verify seizure-bearing patient/event support per fold; do not assume window stratification alone balances patients.
5. Tune Logistic Regression `C` on a logarithmic grid. Compare class-only, patient-only and combined training weights. Use one tree challenger; Random Forest is already implemented and is the first candidate. Defer a model zoo and do not start with SMOTE.
6. Compare rolling score smoothing (3–6 windows), K-of-N alarm rules and short-gap merging on inner OOF data only. Report the delay cost.
7. Select/report sensitivity at predeclared false-alarm budgets (0.1, 0.5, 1.0 FA/hour as research operating points), with no clinical-safety implication.
8. Complete all 23 nested outer LOPO folds after freezing the method. Report per-patient event sensitivity, FA/hour, delay, AUROC, AUPRC and window metrics, plus patient-macro median/IQR/mean.
9. Defer trailing-baseline normalization and Siena external validation. Learning curves are optional.
10. API/dashboard work may prepare a clearly labelled baseline interface in parallel, but real inference must use the frozen, validated preprocessing/model pipeline and must not be described as diagnosis.

### Important methodological safeguards

- Preserve the existing 221-feature Logistic Regression baseline and its saved artifacts as the comparison reference.
- The current 170-feature robust representation includes `log_std` and is extracted after fold-fitted channel standardization. It is not identical to the proposed scale-free core. Create a new version or explicit ablation; do not silently change feature semantics or reuse incompatible caches.
- Any model-level scaler is fitted inside each training fold only.
- All feature/model/weighting/calibration/threshold/alarm choices are made using inner training/OOF data. Outer-test labels are used once for final evaluation only.
- Thresholds selected from OOF scores may not transfer to a final refit on all 22 outer-training patients. Validate score calibration/transfer using inner data and freeze the protocol before outer-test scoring.
- The patient_01 threshold curve is a post-hoc diagnostic only; it must never be used to tune the model or threshold.
- Current first-fold baseline and threshold-sweep findings remain exploratory; no 23-patient performance claim is established.

### Immediate next action

Implement and test duration integration into `scripts/evaluate_first_fold_events.py` (or a reusable inventory loader) first. Then review the running robust-feature experiment's actual completion/result before launching any new expensive job. Preserve current checkpoints and caches. The reusable feature cache and patient-grouped OOF pipeline follow after these two gates.

See [Accuracy Improvement Roadmap](ACCURACY_IMPROVEMENT_ROADMAP.md) for the full approved sequence and [Event-Level Evaluation](../EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/docs/EVENT_LEVEL_EVALUATION.md) for event metric semantics.


---

## Exact recording-duration integration — implementation committed (5 November 2026)

The prior statement that exact durations were unavailable is superseded. The
repository-root `docs/signal_inventory.csv` was re-audited against the
annotation audit using normalized recording identity:

- 686 inventory rows; 683 primary-cohort recordings.
- 683/683 primary recordings matched; 0 missing and 0 identity mismatches.
- 0 duplicate inventory paths and 0 duration arithmetic inconsistencies.
- Every inventory duration agrees with `n_samples / sampling_frequency_hz`
  within 0.01 seconds.
- Three inventory rows are outside the primary cohort.
- Raw primary-cohort exposure is 979.9286 hours; this is not the non-seizure
  denominator for false alarms/hour.

Committed implementation on `feature/threshold-strategy-score-artifacts`:

- Added `evaluation/recording_inventory.py` for fail-closed, identity-based
  duration joins.
- Updated `scripts/evaluate_first_fold_events.py` to use the inventory,
  clip annotations to recording bounds, and report per-recording, patient-pooled
  and cohort-pooled non-seizure exposure and false alarms/hour.
- Preserved the v1 event result; the new evaluator writes
  `results/baselines/first_fold_patient_01_event_metrics_v2.json`.
- Added tests for inventory identity, duplicate/missing paths, duration
  arithmetic, per-recording FA/hour, patient-level pooled exposure, overlapping
  seizure interval union and zero non-seizure exposure.
- No model was trained, no feature cache/checkpoint was changed, and no
  outer-test threshold or model selection was performed.

**Verification pending:** the user must pull the latest branch, run the focused
tests and execute the v2 saved-score evaluator locally. Do not claim these
tests or the real saved-score evaluation have passed until their output is
reviewed. The robust-feature result JSON remains a local, untracked artifact;
the console summary alone is insufficient to audit its complete metrics.
