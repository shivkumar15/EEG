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


### Local verification completed — exact-duration event evaluation v2 (5 November 2026)

The user pulled commit `63659b4`, ran the focused test suite, and executed
the saved-score evaluator successfully:

- Focused tests: **31 passed in 4.78 seconds**.
- Evaluator status: completed; `model_retrained=false`.
- Duration join: 686 inventory rows, 683/683 primary-cohort matches, 3
  non-cohort inventory rows; no missing primary recordings.
- Inner validation: 29 seizure events, 19 detected, 10 missed; event
  sensitivity 65.52%; mean detection delay 15.74 seconds; 1,327 false-alarm
  episodes over 1,078,457 seconds non-seizure exposure; **4.430 false
  alarms/hour**.
- Held-out patient_01 outer test: 11 seizure events, 1 detected, 10 missed;
  event sensitivity **9.09%**; mean detection delay 58 seconds; 40 false-alarm
  episodes over 263,536 seconds non-seizure exposure; **0.546 false
  alarms/hour**.

Interpretation: the event-level generalization result is poor. The lower
outer-test false-alarm rate does not compensate for missing 10 of 11 seizures.
This first fold is a warning about patient-level transfer, not evidence of
clinical readiness or final cohort performance. Keep the legacy model as a
research baseline; do not claim that the system is reliable for seizure
detection. The 23-fold evaluation remains necessary.

The local robust-feature result JSON is now confirmed to exist in the user's
untracked results directory, but its complete contents have not yet been
reviewed. Preserve it and its companion score/model artifacts.


---

## Robust-feature first-fold event evaluation — completed (5 November 2026)

The user pulled commit `b11d696` and ran
`python -m scripts.evaluate_robust_first_fold_events --audit ..\\..\\docs\\full_annotation_audit.csv`.
The saved-score evaluation completed successfully:

- `status=completed`; `model_retrained=false`; `features_reextracted=false`.
- Robust Logistic Regression threshold: read from the completed experiment
  result and selected using inner-validation F2.
- Same first-fold split and the same 139 validation / 75 held-out recordings
  as the legacy event evaluation.
- Exact recording-duration inventory used; validation non-seizure exposure
  1,078,457 seconds and outer-test non-seizure exposure 263,536 seconds.

**Inner validation (29 seizure events):**
- 27 detected, 2 missed; event sensitivity **93.10%**.
- Mean detection delay: **14.15 seconds**.
- 1,272 false-alarm episodes; **4.246 false alarms/hour**.

**Held-out patient_01 (11 seizure events):**
- 4 detected, 7 missed; event sensitivity **36.36%**.
- Mean detection delay: **36.5 seconds**.
- 167 false-alarm episodes; **2.281 false alarms/hour**.

**Comparison with legacy Logistic Regression on the same held-out recordings:**
- Event detections improved from 1/11 to 4/11; sensitivity from 9.09% to
  36.36% (+27.27 percentage points).
- Mean delay decreased from 58 to 36.5 seconds.
- False alarms increased from 40 to 167; false alarms/hour increased from
  0.546 to 2.281 (approximately 4.2x).
- Validation also improved: 27/29 versus 19/29 events detected, with 1,272
  versus 1,327 false alarms and 4.246 versus 4.430 false alarms/hour.

**CTO interpretation:** this is a promising sensitivity improvement on the
first held-out patient, but it is not an unqualified model win. The increase
in detected events is accompanied by a substantial false-alarm penalty on
outer test. Validation performance is encouraging, but one held-out patient
cannot establish generalization. Do not claim clinical reliability or adopt
this as the final model yet. Preserve both models and all score artifacts.

**Next action:** inspect the robust and legacy per-event/per-recording
diagnostics side by side to identify which seizure events were recovered and
where false alarms increased. Then test the approved alarm smoothing /
K-of-N and short-gap merging policies using patient-grouped inner OOF data
only. Keep the outer-test result sealed from further tuning. The complete
23-fold nested patient-level evaluation remains required.


### Research operating targets — CTO decision (5 November 2026)

For development planning, the project adopts an aspirational event-sensitivity
target of **at least 90%** at a primary research operating point of **no more
than 1.0 false alarm per non-seizure hour**. Also report event sensitivity at
0.1 and 0.5 false alarms/hour, mean/median detection delay, and per-patient
results. These are engineering/research objectives, not clinical acceptance
criteria or guarantees of safety. Report both pooled event sensitivity and
patient-macro summaries across all 23 outer LOPO folds; do not let a large
number of events from one patient conceal poor performance on others.

Current patient_01 robust first-fold result is 4/11 events (36.36%) at
2.281 false alarms/hour. This is a first-fold result only and is below the
research target. The next task is descriptive legacy-vs-robust per-event and
per-recording error analysis. Outer-test diagnostics are post-hoc only and
must not be used to tune thresholds or alarm policies. Alarm-policy selection
must use patient-grouped inner validation/OOF predictions, with a frozen
protocol before any outer-test evaluation.


### Legacy-versus-robust error comparison utility added

Added `scripts/compare_first_fold_event_results.py` and
`tests/test_event_result_comparison.py`. The utility compares the saved
legacy and robust event-evaluation JSON files by exact recording path and
seizure annotation identity. It reports events recovered by robust, events
detected only by legacy, events detected/missed by both, and per-recording
false-alarm deltas. It is descriptive only: it does not tune thresholds,
change alarm policies, retrain models, or use the outer-test result for
selection. User pull and focused test/execution are pending.


### Legacy-versus-robust first-fold event error comparison — locally verified (5 November 2026)

The user pulled the comparison utility, ran
`python -m pytest tests/test_event_result_comparison.py -q` (**3 passed**),
and ran `python -m scripts.compare_first_fold_event_results`. The comparison
completed using the saved event-evaluation JSON files, matched exact
recording paths and seizure interval identities, and did not retrain or tune.

**Inner validation (139 recordings, 29 events):**
- Legacy detected 19; robust detected 27.
- Robust recovered 9 events, regressed 1, both detected 18, both missed 1.
- Legacy false alarms 1,327; robust 1,272 (55 fewer).

**Held-out patient_01 (75 recordings, 11 events):**
- Legacy detected 1; robust detected 4.
- Robust recovered 3 events; regressed 0; both detected 1; both missed 7.
- Legacy false alarms 40; robust 167 (+127).

The three recovered held-out events were:
- `chb01/chb01_16.edf`, 1015–1066 s; robust delay 30 s.
- `chb01/chb01_18.edf`, 1720–1810 s; robust delay 10 s.
- `chb01/chb01_21.edf`, 327–420 s; robust delay 53 s.

Largest held-out per-recording false-alarm increases:
- `chb01/chb01_34.edf`: 3 to 71 (+68).
- `chb01/chb01_42.edf`: 8 to 20 (+12).
- `chb01/chb01_33.edf`: 1 to 12 (+11).
- `chb01/chb01_30.edf`: 0 to 4 (+4).

The +68 in `chb01_34.edf` accounts for about 53.5% of the total +127
false-alarm increase. This is descriptive concentration, not a proven
signal-quality or physiological cause. Outer-test findings are post-hoc and
must not be used to tune the model or alarm policy.

**Decision / next step:** preserve the robust feature candidate. Inspect
validation-only alarm temporal patterns and test a small, predeclared set of
alarm persistence/merging policies using patient-grouped inner OOF predictions.
Do not tune against patient_01 outer-test recordings or highlighted false
positive recordings. First fold only; no model winner is declared until all
23 outer folds are evaluated.


### Alarm-policy simulation v1 superseded by evidence-preserving v2 (5 November 2026)

The first validation-only 24-combination interval simulation was executed locally and its six focused tests passed. A subsequent methodological review found that v1 merged alarm envelopes before duration filtering and event matching. This could (a) let silent gaps contribute to minimum alarm duration and (b) count a seizure as detected when the seizure fell only inside a merged gap, despite no actual positive alarm interval overlapping the seizure. Therefore v1 results are exploratory/debugging output only; no policy was selected or adopted from them.

The simulation was corrected in v2:
- Minimum duration is applied independently to each actual model-positive alarm interval before grouping.
- Seizure event detection and delay use only retained actual positive intervals; gap grouping cannot create event detections.
- Gap grouping affects alarm episode counts only. A grouped episode is considered non-false only if at least one actual retained alarm interval in that group overlaps an annotated seizure.
- The 24-combination grid and exact saved non-seizure exposure are retained; outer-test data is not read.
- Updated tests explicitly cover seizure-in-gap false detection prevention and duration filtering before grouping.

Commits: script 54797174750abd2f21a934700bff439580ed5f4a; tests d60ba559b086ffd771fd1dd209f7613bd42eb392.

Verification pending: user must pull, run python -m pytest tests/test_alarm_policy_simulation.py -q, and execute python -m scripts.simulate_validation_alarm_policies. The corrected output is results/baselines/robust_validation_alarm_policy_simulation_v2.json. Do not cite v1 policy metrics as validated findings.


---

### Alarm-policy simulation v2 — locally verified (5 November 2026)

The user pulled commit `b464740`, ran the corrected focused tests, and executed the validation-only simulation:

- Focused tests: **7 passed in 0.07 seconds**.
- Simulation: `status=completed`, `model_retrained=false`,
  `outer_test_read=false`, **24/24 combinations completed**.
- Output: `results/baselines/robust_validation_alarm_policy_simulation_v2.json`.
- The output is based on the robust first-fold inner-validation recordings only
  (29 seizure events across the seizure-bearing validation patients). No model
  was retrained and the held-out patient_01 outer-test data was not read.

**Results by minimum retained alarm duration (all gap settings within a
minimum-duration row have identical event detections and delay):**

| Minimum duration | Events detected | Event sensitivity | Delay (mean seconds) | FA/hour at 0s gap | FA/hour at 30s gap |
|---:|---:|---:|---:|---:|---:|
| 0 s | 27/29 | 93.10% | 14.15 | 4.246 | 2.701 |
| 15 s | 25/29 | 86.21% | 15.24 | 2.267 | 1.505 |
| 20 s | 18/29 | 62.07% | 14.44 | 1.188 | 0.751 |
| 30 s | 10/29 | 34.48% | 24.20 | 0.624 | 0.404 |

Gap merging reduces counted false-alarm episodes/hour without changing event
sensitivity or delay in this evidence-preserving simulation. Minimum-duration
filtering reduces false alarms but also discards genuine event detections:
15 seconds loses 2 of 27 detections, 20 seconds loses 9, and 30 seconds loses
17. The 30-second filter is especially damaging to sensitivity.

**Research-target check:** none of the 24 combinations simultaneously reaches
the aspirational target of at least 90% event sensitivity and no more than
1.0 false alarm/hour. With no duration filter, sensitivity is 93.10% but the
best FA rate is 2.701/hour. At 20 seconds and a 30-second merge gap, FA rate
falls to 0.751/hour but sensitivity is only 62.07%.

**CTO decision:** do not adopt a minimum-duration filter or declare an alarm
policy winner from this experiment. A 30-second gap setting is a candidate
for further validation because it reduces episode counts without sacrificing
detections in this simulation, but it remains exploratory and depends on the
defined alarm-episode semantics. The 15/20/30-second filters are not acceptable
as default choices based on this evidence because of their sensitivity cost.
These results cover one first-fold validation partition and only its
seizure-bearing patients; they are not a substitute for patient-grouped inner
OOF evaluation across the outer-training cohort.

**Next action:** move toward patient-grouped inner OOF score generation for
the robust feature candidate, then evaluate the predeclared alarm policies on
those OOF predictions. Report patient-level event sensitivity and false
alarms/hour distributions, not only pooled totals. Keep patient_01 outer-test
scores sealed from all further model, threshold and alarm-policy selection.
Preserve the v1 and v2 simulation JSON artifacts; do not delete or overwrite
them.

---

## Patient-grouped inner OOF pipeline — implementation committed, local verification pending (5 November 2026)

The user successfully pulled commit `0b882f9`, ran the OOF scaler-cache tests (**8 passed in 1.43 seconds**), and built the reusable channel-statistics cache for all **608 outer-training recordings / 22 patients**. The builder confirmed `patient_01` outer-test recordings were not opened.

Committed follow-on implementation:
- `evaluation/oof_scaler_cache.py` now computes compact per-window/per-channel raw standard deviations and reconstructs fold-specific `log_std`; a patient-excluding channel-scale helper has a unit test.
- `scripts/build_oof_window_std_cache.py` builds resumable per-recording raw-std artifacts from existing processed NPZ files. No EDF download or feature re-extraction is required.
- `scripts/run_inner_patient_oof.py` builds one fold-specific feature matrix at a time and trains 22 patient-held-out Logistic Regression models. The same 21-patient channel scaler is applied to every recording in that fold; the model-level StandardScaler is fitted on the 21 training patients only.
- Each fold feature matrix has per-recording progress checkpoints; each completed patient score artifact is committed atomically and reused on restart.
- `docs/OOF_SCALER_CACHE.md` documents the run sequence and leakage safeguards.

**Important methodological correction:** a shared matrix in which each patient's features were normalized with a different patient-held-out scaler would leak the current fold's held-out patient into the training features. The committed OOF runner instead constructs a separate matrix for each held-out patient, using one common scaler fit on the other 21 patients. Do not run older intermediate versions of the OOF runner.

**Not yet verified locally:** the raw window-std cache, OOF runner, full 22-fold training, and resulting threshold/metrics. The newly expanded focused test file now contains 11 tests; run it before building the raw-std cache.

Next commands from the nested Python project root:

```powershell
git pull origin feature/threshold-strategy-score-artifacts
python -m pytest tests/test_oof_scaler_cache.py -q
python -m scripts.build_oof_window_std_cache --audit ..\\..\\docs\\full_annotation_audit.csv
```

Inspect `cache/oof_window_std_v1/manifest.json` and verify `complete=true`, `recording_count=608`, and `excluded_outer_test_patient=patient_01` before starting the OOF runner. Then run:

```powershell
python -m scripts.run_inner_patient_oof --audit ..\\..\\docs\\full_annotation_audit.csv
```

The OOF run is a substantial 22-model workload. Preserve all caches and score artifacts; do not delete `cache/oof_recording_stats_v1`, `cache/oof_window_std_v1`, `cache/robust_feature_first_fold_v1`, or `cache/oof_patient_scores_v1` while it is running. The pooled window-F2 threshold is provisional because probabilities from separate fold models may differ in calibration. Event-level threshold/false-alarm analysis and score-transfer review are still required before freezing a threshold. No outer-test patient_01 result is part of OOF.


**Additional numerical safety gate:** before OOF fitting, the runner compares raw-std-reconstructed `log_std` values against every existing inner-validation feature row under the original scaler. It refuses to train if any value differs by more than `5e-4` or if any `log(1e-12)` floor classification differs. This check is pending local execution.



### OOF raw-std numerical precision correction — committed, local verification pending (5 November 2026)

The first real-data numerical audit correctly stopped before OOF model fitting:
3,672,085 validation log-std values were checked; two values in
`chb17/chb17b_69.edf`, window 296 (channels P3-O1 and P4-O2), exceeded the
`5e-4` tolerance. Both windows had extremely small raw standard deviation.
The cause was a numerical difference between calculating standard deviation
after the original float32 fold-normalization transform and reconstructing it
from raw standard deviation before that float32 rounding.

Correction committed:
- Add a conservative low-normalized-variation detector for precision-sensitive
  windows.
- Recompute flagged windows from their original processed EEG samples using
  the exact float32 normalization and original log-std calculation.
- Keep the original audit tolerance (`5e-4)); do not weaken it.
- Bump the OOF runner implementation version to
  `patient_grouped_oof_robust_v3`, so old intermediate feature work cannot be
  mistaken for the corrected implementation.
- Add regression tests for near-constant signals and invalid fallback inputs.
- Add `--audit-only` mode so the complete real-data numerical audit can be run
  without beginning the expensive 22-fold training.

Relevant commits:
- `272b5b5` precision-sensitive fallback detector.
- `dee958c` exact fallback in OOF audit and fold feature construction.
- `638825e` regression tests.
- `da0a12d` near-constant test window-length correction.
- `17ef3ed` audit-only CLI mode.

**Verification pending:** user must pull the latest branch and run the focused
tests. Then run the runner with `--audit-only`. Proceed to full OOF training
only if the audit reports `over_tolerance=0` and `floor_mismatches=0`.
The audit-only mode must report that no OOF models were trained. Do not change
the tolerance or bypass this gate. Existing 608-recording raw-std cache and
recording-statistics cache are retained; no cache rebuild is currently
required. The outer-test patient `patient_01` remains excluded.



### Windows checkpoint-lock resilience — committed (5 November 2026)

During the long OOF run, Windows intermittently denied replacement of a fold's
`progress.json` checkpoint. The resumable pipeline recovered on restart, but
the repeated interruptions are avoidable operational friction.

The OOF runner's `atomic_json` now writes to a unique same-directory temporary
file, flushes it to disk, retries transient `PermissionError` failures with
bounded backoff, and cleans up its temporary file on failure. It continues to
use atomic replacement; it does not fall back to unsafe in-place JSON writes.

Commit: `6d4aa7d`.

The user had reached patient_09 feature construction (375/608) when the second
lock occurred. The last valid checkpoint should be preserved. After pulling
this fix, rerun the same OOF command; the runner should resume from the last
valid patient_09 checkpoint and reuse completed patient score artifacts.
