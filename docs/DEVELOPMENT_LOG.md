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
- Total windows: 704,836.
  - Normal windows: 702,280.
  - Seizure windows: 2,556.
- Verification command: `python .\verify_full_cohort.py`.
- Reported success means all recordings and metadata passed the implemented integrity checks; it is not, by itself, proof of scientific model performance.

### Phase 2 — patient-wise evaluation splits: VERIFIED
- 23 outer Leave-One-Patient-Out folds.
- Every eligible recording is in the test set exactly once.
- No patient leakage between training and test.
- Inner validation: 17 fit patients, 5 validation patients, 1 outer test patient per fold.
- All split groups are patient-disjoint and include seizure events as checked by the split-inspection scripts.
- Commands:
  - `python .\scripts\inspect_lopo_splits.py`
  - `python .\scripts\inspect_nested_validation.py`
- Protocol: `docs/LOPO_EVALUATION_PROTOCOL.md`.
- These scripts verify split construction; they do not train models or generate performance metrics.

### Phase 3 — preprocessing and full-cohort integrity: COMPLETE
- Primary cohort preprocessing and saved-window validation completed.
- Fold-wise standardization is implemented in `data_management/fold_data.py`.
- `prepare_lopo_fold()` fits the standardizer using inner-fit patients only; the same fitted transform is applied to validation and outer-test data.
- `PreparedFold.iter_split("fit"|"validation"|"test")` streams recordings one at a time.
- Earlier whole-recording normalization code remains in the project for preprocessing workflows; model evaluation must use the fold-wise path and must not fit transforms on validation/test patients.

### Phase 4 — baseline model development: IN PROGRESS
Current milestone: **4.1 — feature extraction and scientific validation**.

#### Implemented locally, awaiting user push
- Added `feature_selection/feature_extraction.py`.
- 13 features per channel:
  - mean, standard deviation, variance, RMS, line length, skewness, excess kurtosis;
  - delta, theta, alpha, beta and gamma band power;
  - spectral entropy.
- Frequency bands: delta 0.5–4 Hz, theta 4–8 Hz, alpha 8–13 Hz, beta 13–30 Hz, gamma 30–40 Hz.
- Input shape: `(n_windows, n_channels, n_samples)`.
- Output shape: `(n_windows, n_channels * 13)`, float32; features are channel-major.
- Uses Welch PSD and SciPy trapezoidal integration.
- Constant/near-constant signal skewness and kurtosis are handled as zero to avoid NaN output.
- Added `tests/test_feature_extraction.py` with 10 tests.
- Latest local regression result reported by user: **95 tests passed, 0 failures**.
- The feature-extraction implementation and these latest tests are not yet confirmed on GitHub main. Do not assume they are pushed.

#### Still pending in milestone 4.1
- Create and run `scripts/validate_frequency_features.py` to test known synthetic delta/theta/alpha/beta/gamma signals.
- Review Welch frequency resolution and band-edge integration before freezing the feature definition.
- Document that fold-standardized input changes the scale of absolute band-power features; do not describe them as calibrated physical EEG power in microvolt-squared units.
- Integrate feature extraction into the fold-wise data pipeline only after the scientific checks pass.

#### Not started
- Feature-based SVM and Random Forest baselines.
- 1D CNN baseline.
- CNN + BiLSTM model.
- Attention model and ablation experiments.
- Final window/event-level model evaluation.

### React dashboard
- Separate branch: `feature/react-dashboard-foundation`.
- Commit: `2a08eb9a921db5d84e953510539b6ecdc5e5733d`.
- Open PR #1: https://github.com/shivkumar15/EEG/pull/1
- React 19 + TypeScript + Vite frontend foundation; uses clearly labelled illustrative mock data.
- Local frontend build has not been confirmed. PR is not merged.
- Dashboard is not connected to a trained model or inference API.

## Current milestone order
1. User pushes the local feature extraction implementation and tests.
2. Verify GitHub contains the same code and test files.
3. Complete synthetic frequency-band validation and resolve any issues.
4. Review and freeze feature definitions.
5. Integrate fold-wise feature generation.
6. Train SVM and Random Forest baselines using the verified nested patient-wise folds.
7. Record fold-wise predictions and metrics before moving to deep learning.

## Important scientific safeguards
- Do not randomly split overlapping windows across train/test.
- Do not fit scalers, feature selectors, thresholds or hyperparameters using outer-test patients.
- Channel ranking must be performed inside the training fold only.
- Separate window-level and event-level evaluation.
- This is an academic research prototype, not a medical device or diagnostic tool.
