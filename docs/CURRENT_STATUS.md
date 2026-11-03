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
- Feature extraction source and tests are on GitHub main:
  - `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/feature_selection/feature_extraction.py`
  - `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_feature_extraction.py`
- Latest implementation uses up to 2-second Welch segments and interpolated PSD values at configured band edges.
- User-reported verification after pulling the updated implementation:
  - Pure-tone validation: 5/5 passed.
  - Boundary-frequency diagnostic: 10 frequencies produced sensible dominant-band results.
  - Mixed 2 Hz + 10 Hz signal: PASS.
  - Noisy 10 Hz alpha signal: PASS; finite band powers and alpha remained dominant.
  - Full regression suite: **97 tests passed, 0 failures** in 0.468 seconds.

## In progress — Phase 4, Milestone 4.1
Feature extraction implements 13 features per channel: mean, standard deviation, variance, RMS, line length, skewness, excess kurtosis, five EEG band powers, and spectral entropy.

The revised spectral calculation:
- Uses up to 2-second Welch segments (512 samples at 256 Hz; 0.5 Hz bin spacing).
- Integrates band power between exact configured band edges using interpolated PSD values.
- Has synthetic expected-power regression tests: 2 Hz unit-amplitude sine gives approximately 0.5 delta power; 10 Hz amplitude-0.5 sine gives approximately 0.125 alpha power.

**Interpretation:** These results verify implementation behavior on the tested synthetic signals. They do not establish performance on real EEG or seizure detection accuracy.

## Synthetic validation records
- Pure-tone script: `scripts/validate_frequency_features.py`.
- Extended robustness script: `scripts/validate_frequency_robustness.py`.
- Tested boundary-near frequencies: 0.75, 3.5, 4.5, 7.5, 8.5, 12.5, 13.5, 29.5, 30.5 and 39.5 Hz.
- Mixed signal: 2 Hz plus 10 Hz.
- Noisy signal: 10 Hz plus Gaussian noise (standard deviation 0.3, seed 42).
- Synthetic tests do not replace validation on actual CHB-MIT EEG.

## Next steps
1. Review the feature extractor's scientific assumptions and spectral entropy definition.
2. Integrate feature extraction into the fold-wise data pipeline without patient leakage.
3. Add integration tests for fold-wise feature generation.
4. Train SVM and Random Forest baselines using nested patient-wise splits.
5. Evaluate and report window-level and event-level metrics separately.

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
