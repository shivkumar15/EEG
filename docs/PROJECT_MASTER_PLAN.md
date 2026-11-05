# EEG Seizure Detection — Project Master Plan

**Working repository:** https://github.com/shivkumar15/EEG  
**Original source repository:** https://github.com/student-anshu/EEG-seizure-detection  
**Current development stage:** Phase 4 — baseline model workflow and recovery engineering.  
**Active branch:** `feature/threshold-strategy-score-artifacts`

## 1. Research objective

Build an academic binary EEG-window seizure-detection system using the CHB-MIT Scalp EEG Database. The task is **seizure detection in an EEG window**, not prediction of a future seizure. This is a research prototype, not a medical device; it must not be used for diagnosis or treatment decisions.

The research question is whether EEG models can detect seizure activity while generalizing to patients not used during model fitting or validation.

## 2. Research architecture

### Proposed deep-learning model

EEG preprocessing and channel harmonization → training-fold-only channel selection → multichannel 1D CNN → BiLSTM → temporal attention → Dense sigmoid output.

This is a proposed architecture and research hypothesis, not an assumed best model. It must be evaluated against simpler baselines and ablations under identical patient-wise splits.

### Required comparisons

1. Feature-based classical baselines: Logistic Regression, SVM and Random Forest.
2. 1D CNN.
3. CNN + BiLSTM.
4. CNN + BiLSTM + temporal attention.

Keep split definitions, preprocessing rules and evaluation metrics consistent across comparisons. Tune hyperparameters only within training/validation patients. The outer-test patient must remain untouched until final evaluation.

## 3. Dataset and cohort definition

- Source: CHB-MIT Scalp EEG Database, PhysioNet v1.0.0.
- DOI: `10.13026/C2K01R`.
- Full archive audit: 686 EDF recordings, 198 seizure events, 24 subject folders, zero annotation parse failures.
- CHB01 and CHB21 represent the same individual and are grouped as `patient_01`.
- Three CHB12 recordings are excluded from the primary cohort because of incompatible montage:
  - `chb12/chb12_27.edf`
  - `chb12/chb12_28.edf`
  - `chb12/chb12_29.edf`
- These excluded recordings contain 13 annotated seizure events.
- **Primary cohort:** 683 recordings, 185 seizure events, 23 independent patients.
- All 686 EDF headers were inspected; all have 256 Hz sampling. The preferred 17-channel montage is available in 683/686 recordings.

The full audit manifest is `docs/full_annotation_audit.csv`. The three incompatible recordings must remain excluded unless a separately justified harmonization strategy is developed and documented.

## 4. Signal and window configuration

- Sampling frequency: 256 Hz.
- Fixed longitudinal bipolar montage: 17 selected channels.
- Omit T8-P8 from the primary montage because it is not consistently available under the expected name.
- Window duration: 10 seconds (2,560 samples).
- Window stride: 5 seconds (50% overlap).
- A window is positive when it overlaps a seizure annotation interval.
- Preserve patient, recording, window start/end, sampling rate, channels and label in metadata.
- Annotation parsing failures must never silently become non-seizure labels.

The preprocessing implementation uses a 0.5–40 Hz Butterworth bandpass and optional 60 Hz notch filtering. At 256 Hz, the 60 Hz notch is below Nyquist. The existing whole-recording median/IQR normalization is offline and non-causal; its suitability and consistency with deployment inference must be explicitly considered.

## 5. Verified data preparation

The full-cohort preprocessing integrity audit reported:

- 683/683 primary-cohort recordings valid.
- 704,836 windows total.
- 702,280 normal windows.
- 2,556 seizure windows.
- Zero invalid recordings in that integrity audit.

The audit verifies output structure, metadata and loader consistency. It does not demonstrate model accuracy or clinical usefulness.

## 6. Evaluation protocol and leakage safeguards

Preferred evaluation: 23-fold Leave-One-Patient-Out (LOPO/LOSO) evaluation with patient-wise inner validation.

For each outer fold:
- One patient is held out for outer testing.
- The remaining 22 patients are divided into 17 inner-fit patients and 5 validation patients.
- Fit normalization/scalers using inner-fit patients only.
- Fit feature/channel selection, class weights and model parameters without outer-test data.
- Select thresholds and hyperparameters using validation data only.
- Evaluate once on the held-out outer-test patient using the frozen choices.

Verified split inspection found 23 outer folds, with every eligible recording tested exactly once and no patient leakage. These inspection checks verify split construction, not model performance.

**Never randomly split overlapping EEG windows from the same patient across training and testing.** Never fit scalers, channel selectors, thresholds or hyperparameters using the outer-test patient.

## 7. Feature engineering

Current feature extractor produces 13 features per channel:
1. Mean
2. Standard deviation
3. Variance
4. RMS
5. Line length
6. Skewness
7. Excess kurtosis
8. Delta power (0.5–4 Hz)
9. Theta power (4–8 Hz)
10. Alpha power (8–13 Hz)
11. Beta power (13–30 Hz)
12. Gamma power (30–40 Hz)
13. Spectral entropy

With 17 channels, each window produces 221 features. Welch PSD uses up to 2-second segments, and band powers integrate between configured edges using interpolated PSD values. Synthetic tests have checked pure tones, boundary-near frequencies, a mixed-frequency signal and a noisy alpha signal.

These synthetic checks validate selected implementation behaviors; they do not establish performance on real EEG. After fold-wise standardization, absolute band-power features must not be described as calibrated physical power in microvolt-squared units.

## 8. Checkpoint and reproducibility policy

Training/evaluation workflows must:
- Persist expensive completed units at safe boundaries.
- Use signatures that identify data, split, preprocessing, feature/model configuration and random seed.
- Write artifacts atomically and validate integrity before reuse.
- Reject corrupted or incompatible checkpoints.
- Preserve run logs and machine-readable manifests.
- Test interruption and restart behavior.
- Keep runtime caches and model artifacts out of Git unless explicitly selected as small reports.

The current first-fold implementation includes scaler, feature and model-stage checkpoints. Logistic Regression with the configured `liblinear` solver cannot safely resume an in-progress `fit()`; an interrupted fit restarts. The first-fold runner is not yet the completed 23-fold experiment runner. See:
- `docs/ML_TRAINING_CHECKPOINT_POLICY.md`
- `docs/SCALER_CHECKPOINTS.md`
- `docs/MODEL_STAGE_CHECKPOINTS.md`

Do not claim end-to-end 23-fold resumability until fold scheduling, durable fold results, aggregation and controlled interruption/restart tests are implemented.

## 9. Current phase status

### Completed / verified
- Phase 0: initial audit, annotation correctness, preprocessing correctness, data provenance and repository hygiene.
- Phase 1: full primary-cohort preprocessing and integrity audit.
- Phase 2: patient-wise LOPO and nested split construction/inspection.
- Phase 3: fold-wise data preparation, fit-only standardization and feature iteration.
- Phase 4.1: feature extraction implementation and synthetic signal validation.
- Phase 4.2: fold-wise feature integration.
- Phase 4.3: baseline utilities and first-fold preflight.
- Phase 4.5.1: scaler checkpoint implementation and focused local tests previously reported as passing.
- Phase 4.5.2: model-stage checkpoint implementation and documentation are present on the active branch. On 5 November 2026, the user reported 136 tests and 4 subtests passing in 3.95 seconds (4 skipped); robust-feature focused tests passed 6/6 in 1.20 seconds. These results confirm the repository regression suite, not an actual long-running interruption/restart. Controlled runner-recovery verification remains pending.

### In progress
- Verify the current model-stage checkpoint branch using Python 3.11 environment and the correct nested project directory.
- Add/verify controlled interruption tests for the first-fold runner.
- Build a complete 23-fold baseline runner with per-fold result reuse, durable aggregation and interruption recovery.

### Not yet completed
- Full 23-fold classical baseline evaluation and metrics.
- 1D CNN, CNN-BiLSTM and attention experiments.
- Final window-level and event-level evaluation.
- Explainability.
- FastAPI model inference integration.
- React integration with a validated model/API.
- Final submission validation and research report.

## 10. Evaluation outputs to report

At minimum:
- Sensitivity/recall
- Specificity
- Precision
- F1-score
- AUROC
- AUPRC
- Confusion matrix and class support
- Per-patient and fold-wise metrics
- Fold variability and confidence intervals where feasible

Report window-level and event-level performance separately. Before calculating false alarms per hour, define event matching, merging of nearby positive windows and alarm refractory period. Discuss class imbalance and patient variability. Do not present a single aggregate score without its fold/patient context.

## 11. Explainability

Add SHAP or another justified explanation method only after model selection and evaluation are stable. Specify what output is explained, the reference samples, aggregation method and limitations. Explanations are not clinical evidence.

## 12. Application architecture

- Python for signal processing, model development and inference.
- MNE, NumPy, SciPy, pandas and scikit-learn for the classical pipeline.
- Select and consistently use one deep-learning framework; TensorFlow/Keras is the current proposal.
- FastAPI backend with versioned request/response contracts.
- React + Vite + TypeScript + Tailwind frontend; Plotly for signal and metric charts.
- Start with file-based experiment metadata/results; add a database only for a concrete requirement.
- Inference preprocessing must exactly match the validated model's preprocessing.
- UI language must describe model estimates, not diagnoses.

## 13. Dataset provenance and distribution policy

- Dataset source: [PhysioNet CHB-MIT v1.0.0](https://physionet.org/content/chbmit/1.0.0/).
- DOI: `10.13026/C2K01R`.
- PhysioNet lists the Open Data Commons Attribution License v1.0 (ODC-By).
- ODC-By governs database rights; it does not automatically resolve separate rights in individual contents. This project does not make a blanket legal determination about every recording.
- Raw EDFs and subject summary files are excluded from the current Git tree. Keep local copies; do not delete the dataset during code cleanup.
- Do not copy raw EDFs or summaries to the original team repository. Team members should obtain the dataset independently from PhysioNet and preserve attribution/license notices.
- Earlier Git history contains raw dataset files that were removed from the current tree; no history rewrite was performed.

## 14. Upstream synchronization

Develop and test in `shivkumar15/EEG` first. Synchronize to `student-anshu/EEG-seizure-detection` only after the working version is stable and the user explicitly proceeds. Back up the original code, review diffs, preserve the dataset, and exclude virtual environments, processed outputs, logs and caches. Verify tests and `python main.py --inspect` in the upstream checkout before claiming synchronization.

## 15. Working rules

1. Read the current status and relevant design docs before code changes.
2. Work one milestone at a time and wait for user verification before moving on.
3. Explain the issue and expected behavior before modifying code.
4. Make the smallest safe change and add tests.
5. Record exact commands and actual test output.
6. Update `CURRENT_STATUS.md` and `DEVELOPMENT_LOG.md` after milestones.
7. Keep planned, implemented, locally tested, scientifically validated and deployed work clearly distinguished.
