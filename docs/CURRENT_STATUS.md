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
- Latest local regression suite after feature extraction: 95 tests passed, 0 failures.

## In progress — Phase 4, Milestone 4.1
Feature extraction is implemented locally in `feature_selection/feature_extraction.py`, with 13 features per channel: seven time-domain/statistical features, five EEG band powers, and spectral entropy. Ten focused tests were added in `tests/test_feature_extraction.py`.

**Important GitHub sync status:** the latest feature extraction source and tests are local work and have not yet been confirmed on GitHub main. The 95-test result is also a local user-reported result, not a CI result.

## Next steps
1. User pushes the feature extraction source and tests.
2. Verify the exact files on GitHub and rerun the full test suite.
3. Run synthetic frequency-band validation for delta, theta, alpha, beta and gamma.
4. Review Welch frequency resolution and band-edge integration.
5. Integrate feature extraction into the fold-wise data pipeline.
6. Train and evaluate SVM and Random Forest baselines using the nested patient-wise splits.

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
