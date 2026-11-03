# Development Log

This log distinguishes confirmed repository state from local work that has not yet been pushed.

## 2026-11-03 — Current project checkpoint

### Phase 0 — dataset audit and methodology
- CHB-MIT dataset source: PhysioNet v1.0.0, DOI `10.13026/C2K01R`; preserve attribution and ODC-By license notice.
- Full archive audit: 686 EDF recordings, 198 seizure events, 24 subject folders; 0 EDF annotation parsing failures.
- All 686 EDF headers inspected; all use 256 Hz. Preferred 17-channel montage is available in 683/686 recordings.
- CHB01 and CHB21 are the same individual and are grouped as `patient_01`; the cohort therefore has 23 independent patients.
- Three CHB12 recordings are excluded from the primary cohort due to incompatible montage: `chb12_27.edf`, `chb12_28.edf`, `chb12_29.edf`. These contain 13 annotated seizure events.
- Primary cohort: 683 recordings, 185 seizure events, 23 independent patients.
- Full audit manifest: `docs/full_annotation_audit.csv`.
- The original 42.62 GB ZIP archive was removed after extraction to recover disk space. The extracted EDF dataset remains locally available. Do not delete it.

### Phase 1 — full-cohort preprocessing: COMPLETE
- Resumable `--prepare-cohort` command was added and hardened in commits:
  - `cfc0d772001825e5cb413013d45fe7a1ee8939f3`
  - `01f6d64159fad31c0f46f18b41aa3c50abeaee40`
- Latest recovery run: 65 recordings processed, 618 valid outputs skipped, 0 failed.
- Full integrity audit: 683/683 recordings checked and valid; 0 invalid.
- Total windows: 704,836: 702,280 normal and 2,556 seizure.
- Verification command: `python .\\verify_full_cohort.py`.
- This validates saved outputs and metadata against implemented integrity checks; it is not proof of model performance.

### Phase 2 — patient-wise evaluation splits: VERIFIED
- 23 outer Leave-One-Patient-Out folds.
- Every eligible recording is in the test set exactly once; no patient leakage between training and test.
- Inner validation: 17 fit patients, 5 validation patients, 1 outer test patient per fold.
- Split inspection scripts: `python .\\scripts\\inspect_lopo_splits.py` and `python .\\scripts\\inspect_nested_validation.py`.
- These scripts verify split construction; they do not train models or generate performance metrics.

### Phase 3 — preprocessing and full-cohort integrity: COMPLETE
- Fold-wise standardization is implemented in `data_management/fold_data.py`.
- `prepare_lopo_fold()` fits the standardizer using inner-fit patients only; the same fitted transform is applied to validation and outer-test data.
- `PreparedFold.iter_split("fit"|"validation"|"test")` streams recordings one at a time.
- Model evaluation must use this fold-wise path and must not fit transforms on validation/test patients.

### Phase 4 — baseline model development: IN PROGRESS
Current milestone: **4.1 — feature extraction and scientific validation**.

#### Feature extraction implementation: PUSHED AND VERIFIED ON GITHUB MAIN
- Source: `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/feature_selection/feature_extraction.py`.
- Focused tests: `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_feature_extraction.py`.
- Both files were pushed and verified on main at commit `00670a5121e2c739bbe827f05ea16b8817b99c8c`.
- Implements 13 features per channel: mean, standard deviation, variance, RMS, line length, skewness, excess kurtosis, delta/theta/alpha/beta/gamma band powers, and spectral entropy.
- Frequency bands: delta 0.5–4 Hz, theta 4–8 Hz, alpha 8–13 Hz, beta 13–30 Hz, gamma 30–40 Hz.
- Input shape: `(n_windows, n_channels, n_samples)`; output shape: `(n_windows, n_channels * 13)`, float32, channel-major ordering.
- Uses Welch PSD and SciPy trapezoidal integration. Constant/near-constant signal skewness and kurtosis are set to zero to avoid NaN output.
- Full regression suite was rerun by the user after synchronization: **95 tests passed, 0 failures** in 0.470 seconds.
- This is a unit/regression result, not yet evidence that frequency-band estimates are scientifically validated.

#### Still pending in milestone 4.1
- Create and run `scripts/validate_frequency_features.py` with synthetic pure-tone signals: 2 Hz delta, 6 Hz theta, 10 Hz alpha, 20 Hz beta, and 35 Hz gamma.
- Verify expected band dominance.
- Review Welch frequency resolution and band-edge integration before freezing feature definitions.
- Fold-standardized input changes the scale of absolute band-power features; do not describe these as calibrated physical EEG power in microvolt-squared units.
- Integrate feature extraction into the fold-wise data pipeline only after scientific checks pass.

#### Not started
- Feature-based SVM and Random Forest baselines.
- 1D CNN, CNN + BiLSTM, attention and ablation experiments.
- Final window/event-level model evaluation.

### React dashboard
- Separate branch: `feature/react-dashboard-foundation`.
- Commit: `2a08eb9a921db5d84e953510539b6ecdc5e5733d`.
- Open PR #1: https://github.com/shivkumar15/EEG/pull/1
- React 19 + TypeScript + Vite foundation uses clearly labelled illustrative mock data.
- Local frontend build has not been confirmed. PR is not merged; dashboard is not connected to a trained model or inference API.

## Current milestone order
1. Synthetic frequency-band validation.
2. Review/freeze feature definitions.
3. Integrate fold-wise feature generation.
4. Train SVM and Random Forest baselines with nested patient-wise folds.
5. Record fold-wise predictions and metrics before moving to deep learning.

## Important scientific safeguards
- Do not randomly split overlapping windows across train/test.
- Do not fit scalers, feature selectors, thresholds or hyperparameters using outer-test patients.
- Channel ranking must be performed inside the training fold only.
- Report window-level and event-level evaluation separately.
- This is an academic research prototype, not a medical device or diagnostic tool.
