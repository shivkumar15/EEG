# AI / Teammate Handoff

**Read this file together with `docs/CURRENT_STATUS.md` and `docs/PROJECT_MASTER_PLAN.md` before changing code.**

## 1. Repository roles

- Active working repository: https://github.com/shivkumar15/EEG
- Current branch for model-stage recovery: `feature/model-stage-checkpoints`
- Original source/team repository: https://github.com/student-anshu/EEG-seizure-detection
- Develop and verify in the working repository first. Do not modify the original repository automatically.

## 2. Research objective

Academic binary EEG-window seizure detection using CHB-MIT. This is detection of seizure activity in a window, not prediction of a future seizure. It is not a medical device and must not be used for diagnosis or treatment decisions.

Proposed deep-learning architecture: harmonized multichannel EEG → training-fold-only channel selection → 1D CNN → BiLSTM → temporal attention → sigmoid output.

Required comparisons: Logistic Regression, SVM, Random Forest, 1D CNN, CNN+BiLSTM and CNN+BiLSTM+attention. Treat the proposed architecture as a hypothesis to evaluate, not as a proven choice.

## 3. Current verified project foundation

- Primary cohort: 683 recordings, 185 seizure events, 23 independent patients.
- CHB01 and CHB21 are grouped as one individual.
- Three incompatible-montage CHB12 recordings are excluded from the primary cohort.
- Full preprocessing integrity audit: 683/683 valid, 704,836 windows (702,280 normal; 2,556 seizure).
- 23 outer patient-wise LOPO folds.
- Nested patient split: 17 fit, 5 validation, 1 outer test.
- Fold standardization fitted on inner-fit patients only.
- Feature extractor: 13 features/channel × 17 channels = 221 features/window.
- Fold-wise feature iterator streams one recording at a time.
- Baseline utilities and a first-fold runner exist.
- Scaler and model-stage checkpoint implementations exist; current model-stage verification is pending user confirmation.

See `CURRENT_STATUS.md` for exact current milestone and verification state. Do not use older Phase 0/10-recording descriptions as the current project status.

## 4. Immediate task

Current milestone: **Phase 4.5.2 — verify model-stage checkpoint recovery**.

The user has checked out `feature/model-stage-checkpoints`. On Windows, the repository root is:

`D:\2026-THE ENDGAME\byteBazzar\EEG`

The Python 3.11 environment is `.venv311` at the repository root. The project code and tests are nested under:

`EEG_Seizure_Detection_Phase1\EEG_Seizure_Detection`

Run verification from PowerShell in this order:

```powershell
# From repository root
.\.venv311\Scripts\Activate.ps1
python --version

cd .\EEG_Seizure_Detection_Phase1\EEG_Seizure_Detection

python -m py_compile .\modeling\experiment_checkpoints.py .\scripts\run_first_baseline_fold.py

python -m unittest discover -s tests -p "test_experiment_checkpoints.py" -v

python -m unittest discover -s tests -v
```

Expected interpreter is Python 3.11.x. The prompt should show `(.venv311)`, not the separate `(.venv)` environment. Do not run the test commands from repository root because `modeling`, `scripts` and `tests` are below the nested project directory.

Review the actual output before marking this milestone complete. Do not assume the full suite count.

## 5. Checkpoint implementation limits

The first-fold runner checkpoints completed scaler, feature and model stages. It does not serialize an in-progress scikit-learn Logistic Regression solver. If `LogisticRegression(solver="liblinear")` is interrupted during `fit()`, that fit restarts. Once fit returns and its estimator is saved, later stages can reuse it.

The current runner covers only the first LOPO fold. It is not the completed 23-fold runner. Do not claim end-to-end resumability until all folds, fold-result skipping, aggregation and controlled interruption/restart tests are implemented.

## 6. Mandatory research safeguards

1. Never randomly split overlapping windows from the same patient across train/test.
2. Keep the outer-test patient untouched during scaler fitting, channel/feature selection, hyperparameter tuning and threshold selection.
3. Fit fold transformations on inner-fit patients only.
4. Use validation patients for model selection and threshold selection.
5. Evaluate the held-out outer-test patient only after all choices are frozen.
6. Report window-level and event-level metrics separately.
7. Define event matching, nearby-window merging and alarm refractory period before false alarms/hour.
8. Do not describe fold-standardized band powers as calibrated physical microvolt-squared power.
9. Distinguish synthetic checks and unit tests from real-EEG performance evidence.

## 7. Required workflow for every code change

1. Read the relevant design document and inspect source/callers.
2. Explain the issue and expected behavior.
3. Make the smallest safe change.
4. Add/update tests, including recovery tests for checkpoint features.
5. Run focused tests, then the full suite when appropriate.
6. Record actual command output and test count; never invent or estimate a passing result.
7. Update `CURRENT_STATUS.md` and `DEVELOPMENT_LOG.md`.
8. Update `CHANGELOG_FOR_UPSTREAM.md` when changes need to be mirrored.
9. Tell the user what changed and what remains unverified.

## 8. Resource and data safety

- Do not delete raw EDF data, processed cohort files or required metadata during cleanup.
- Do not commit raw EDFs, generated caches, virtual environments, logs or large model artifacts.
- Inspect disk space and existing cache/process state before expensive experiments.
- Do not launch full-cohort or 23-fold training until recovery tests and resource estimates are reviewed with the user.
- Preserve PhysioNet CHB-MIT v1.0.0 provenance, DOI `10.13026/C2K01R`, and ODC-By attribution/license requirements.

## 9. Planned work after current milestone

1. Controlled interruption/restart verification for the first-fold runner.
2. Complete 23-fold baseline runner with per-fold result checkpoints and atomic aggregation.
3. Classical baseline evaluation (Logistic Regression, SVM, Random Forest).
4. CNN, CNN-BiLSTM and attention experiments with identical patient-wise splits.
5. Window/event evaluation and error analysis.
6. Explainability.
7. FastAPI integration, then React dashboard integration.
8. Final reproducibility and submission documentation.

Work one milestone at a time. Explain in beginner-friendly steps and wait for the user's verification before advancing.
