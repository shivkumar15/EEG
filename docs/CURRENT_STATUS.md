# Current Project Status — 3 November 2026

Active repository: https://github.com/shivkumar15/EEG

## Completed and verified
- Full CHB-MIT audit: 686 EDF recordings, 198 seizure events, 24 subject folders; no annotation parsing failures.
- Primary cohort: 683 recordings, 185 seizure events, 23 independent patients.
- Three CHB12 recordings excluded for incompatible montage; CHB01 and CHB21 grouped as one person.
- Full preprocessing integrity: 683/683 recordings valid; 704,836 windows (702,280 normal; 2,556 seizure).
- Patient-wise evaluation: 23 LOPO folds; every eligible recording tested once; patient leakage checks passed.
- Nested validation: 17 fit patients, 5 validation patients, 1 outer test patient per fold.
- Fold-wise standardization is fitted on inner-fit patients only.
- Feature extraction source and its 10 focused tests are pushed to GitHub main:
  - `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/feature_selection/feature_extraction.py`
  - `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_feature_extraction.py`
- Full regression suite rerun by the user after GitHub synchronization: **95 tests passed, 0 failures** (0.470 seconds).
- Synthetic pure-tone validation: **5/5 passed** (2 Hz delta, 6 Hz theta, 10 Hz alpha, 20 Hz beta, 35 Hz gamma); each tone's expected band had the highest extracted power.

## In progress — Phase 4, Milestone 4.1
Feature extraction implements 13 features per channel: mean, standard deviation, variance, RMS, line length, skewness, excess kurtosis, five EEG band powers, and spectral entropy. Ten focused unit tests cover shape, dtype, finite values, invalid inputs and constant signals.

**Important:** Passing unit tests confirms implementation behavior for the tested cases; it does not yet establish scientific correctness of frequency-band estimates.

## Next steps
1. Extend synthetic validation to frequencies near band edges and noisy/mixed signals.
2. Review Welch frequency resolution and band-edge integration; adjust only if validation supports a change.
3. Integrate validated feature extraction into the fold-wise pipeline.
4. Train SVM and Random Forest baselines using nested patient-wise splits.

## Not started
- Classical baseline model training and final metrics.
- 1D CNN, CNN-BiLSTM and attention model experiments.
- Explainability.
- FastAPI inference integration.
- React dashboard integration with a trained model.

## React frontend
A separate foundation branch exists: `feature/react-dashboard-foundation`, commit `2a08eb9a921db5d84e953510539b6ecdc5e5733d`, with open PR #1: https://github.com/shivkumar15/EEG/pull/1. It contains illustrative mock data only; the local frontend build is not yet verified and the PR is not merged.

## Research safeguards
No random window-level train/test split. Fit all preprocessing, feature selection, thresholds and hyperparameters using training/validation patients only. Report window-level and event-level results separately. This is an academic research prototype, not a medical device.
