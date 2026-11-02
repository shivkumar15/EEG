# Development Log

Record verified actions only. Planned work is not marked complete.

## 2026-11-02 — Working repository established
- Active working repository: https://github.com/shivkumar15/EEG
- Original source repository: https://github.com/student-anshu/EEG-seizure-detection
- Connected GitHub identity verified as `shivkumar15`.
- Write permission to `shivkumar15/EEG` verified.
- Default branch: `main`.
- Repository contains `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection` and sibling `EEG_Seizure_Detection_Phase1/dataset/chbmit` paths with CHB01–CHB03 folders.
- Added repository-level project plan documentation. No scientific source code, dataset files, EDF files or model artifacts were changed.

## Current phase
**Phase 0 — audit and correctness.**

## Next actions
1. Audit segmentation, channel handling and EDF metadata consistency.
2. Validate one EDF end-to-end before processing the full cohort.
3. Reproduce processed-window counts and label distributions; do not treat previously reported counts as results until reproduced.

## Reported but unverified
A previous progress report stated 8 CHB01 EDFs and 5,497 windows (5,397 normal, 100 seizure), 17 channels, 256 Hz, 10-second windows and 5-second stride. These are not independently reproduced in this repository yet.

## 2026-11-02 — Phase 0, Task 1: annotation parser correction and verification

### Changes
- Updated `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/annotations.py` to support numbered and unnumbered CHB-MIT seizure time labels.
- Parser checks the declared seizure count, rejects missing/mismatched annotations, rejects negative or non-positive intervals, returns an empty list only for recordings explicitly declaring zero seizures, and errors when the EDF is absent from the summary.
- Added `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_annotations.py` with six unit tests.
- Added `tests/__init__.py` for package/discovery compatibility.

### Verified by user on the local Windows checkout
Command: `python -m unittest discover -s tests -v`
- Result: **6 tests passed, 0 failures**.

Command: `python verify_annotations.py`
- `chb01_03.edf` → `[(2996.0, 3036.0)]`
- `chb01_05.edf` → `[]`
- `chb03_01.edf` → `[(362.0, 414.0)]`
- `chb03_05.edf` → `[]`
- Result: **4 actual CHB-MIT summary-file checks passed**.

The temporary `verify_annotations.py` is a local verification script and is not part of the committed implementation unless separately added. No EDF, dataset, model, or other preprocessing source files were changed.

## 2026-11-02 — Phase 0, Task 2: dataset path correction — VERIFIED
- Updated `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/config.py`: `DATASET_DIR` resolves as `PROJECT_ROOT.parent / "dataset" / "chbmit"`, matching the repository layout where `dataset` is a sibling of `EEG_Seizure_Detection`.
- Added `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_config_paths.py` with two path tests.
- User created and activated a Python 3.11 environment at repository root (`.venv311`) after the original Python 3.14 environment could not install the pinned NumPy 1.26.x line from a compatible wheel. The existing `.venv` was left untouched.
- Installed dependencies from `requirements.txt`; imports of NumPy, pandas, SciPy and MNE succeeded.
- User ran `python -m unittest discover -s tests -v`: **8 tests passed**.
- User ran `python main.py --inspect`: **10 EDF files found** at `EEG_Seizure_Detection_Phase1/dataset/chbmit` (CHB01: 8, CHB02: 1, CHB03: 1).

## Next task
Review import/package execution conventions and then validate the single-EDF preprocessing path. Do not begin model training yet.


## 2026-11-02 — Phase 0, Task 3: import/execution convention — VERIFIED
- Updated `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/check_processed_data.py` to import `PROCESSED_DIR` using `from config import PROCESSED_DIR`, consistent with the script-style execution convention used by `main.py`.
- User ran `python -m unittest discover -s tests -v`: **8 tests passed**.
- User ran `python check_processed_data.py`: completed successfully and reported zero processed recordings/windows, which is expected because no processed dataset had yet been generated.
- User ran `python main.py --inspect`: **10 EDF files found**.
- No package restructuring was performed; scripts continue to be run from the `EEG_Seizure_Detection` directory.

## 2026-11-02 — Phase 0, Task 4: signal-processing hardening — VERIFIED
### Changes
- Updated `preprocessing/signal_processing.py` with validation for 2D non-empty EEG arrays, finite values, valid sampling frequency and cutoff parameters.
- Kept the existing fourth-order Butterworth bandpass configuration and the default 0.5–40 Hz passband, with the upper edge capped below Nyquist.
- Changed notch filtering to second-order-section forward-backward filtering for numerical stability; the notch is skipped when disabled or at/above Nyquist.
- Added explicit errors for recordings too short for forward-backward filtering.
- Retained per-channel median/IQR normalization and documented that its statistics are computed over the entire supplied recording (offline, non-causal behavior).
- Added `tests/test_signal_processing.py` with 10 tests covering filter behavior, notch attenuation/skip behavior, invalid inputs, normalization, and constant channels.

### Verified by user on the local Windows checkout
- `python -m unittest discover -s tests -v` — **18 tests passed, 0 failures** (8 existing + 10 new).
- `python main.py --inspect` — **10 EDF files found**.
- A navigation command attempted to enter a nested project path while already inside the project directory; it failed harmlessly. Tests and inspection were then run successfully from the correct directory.

### Methodology note
- The current normalization is an offline per-recording transform. It must not be described as causal real-time normalization. A causal or training-fitted transform will need a separate design if real-time inference or a different evaluation protocol is selected.
