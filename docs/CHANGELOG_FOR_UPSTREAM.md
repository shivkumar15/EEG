# Upstream Change Log — Mirror to Original Repository

**Working copy:** https://github.com/shivkumar15/EEG  
**Original repository:** https://github.com/student-anshu/EEG-seizure-detection

This ledger tracks changes developed here that the team must also apply to the original repository.

## 2026-11-02 — Documentation baseline (working copy)

### Files added
- `README.md` — repository overview and navigation.
- `docs/PROJECT_MASTER_PLAN.md` — research architecture, roadmap, evaluation protocol and working rules.
- `docs/DEVELOPMENT_LOG.md` — verified repository baseline and progress.
- `docs/AI_HANDOFF.md` — context for teammates and future AI sessions.
- `docs/CHANGELOG_FOR_UPSTREAM.md` — this upstream mirror ledger.

### Code/data changes
None. No source code, dataset or model artifact was changed in this documentation-only update.

### What to mirror upstream
Copy these five documentation paths/files to the original repository. There is no code patch for this update.

## 2026-11-02 — Phase 0, Task 1: annotation parser correction

### Files changed in working copy
- Updated `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/annotations.py`.
- Added `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_annotations.py`.
- Added `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/__init__.py` (empty file).

### Behavior change
- Supports unnumbered CHB-MIT fields (`Seizure Start Time`, `Seizure End Time`) and numbered variants.
- Verifies annotation count against `Number of Seizures in File`.
- Returns `[]` for an explicitly zero-seizure recording.
- Raises clear errors for missing/mismatched annotations, invalid intervals, missing summary files and EDF files not listed in the summary.

### Verified tests (user's local Windows checkout)
- `python -m unittest discover -s tests -v` — **6 tests passed**.
- `python verify_annotations.py` — **4 actual CHB-MIT recording checks passed**:
  - `chb01_03.edf` → `[(2996.0, 3036.0)]`
  - `chb01_05.edf` → `[]`
  - `chb03_01.edf` → `[(362.0, 414.0)]`
  - `chb03_05.edf` → `[]`

The temporary `verify_annotations.py` was created locally for verification and is not required in the upstream mirror.

### Mirror to original repository
Copy these three files from the working repository to the exact same relative paths in `student-anshu/EEG-seizure-detection`:
1. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/annotations.py`
2. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_annotations.py`
3. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/__init__.py`

Then run `python -m unittest discover -s tests -v` from the original repository's `EEG_Seizure_Detection` directory. Do not mark upstream as updated until that is confirmed.

## Pending implementation changes
- Fix dataset path resolution for the sibling `dataset` directory.
- Normalize import/package execution conventions.
- Add tests and validate preprocessing, channel handling and normalization.
- Correct `.gitignore` scope and decide raw EDF storage policy.


## Phase 0, Task 2: dataset path correction

### Files changed in working copy
- Updated `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/config.py`.
- Added `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_config_paths.py`.

### Behavior change
- `DATASET_DIR` now resolves to `PROJECT_ROOT.parent / "dataset" / "chbmit"`, matching the actual layout where `dataset` and `EEG_Seizure_Detection` are sibling directories.

### Verification status
Verified locally by the user in Python 3.11: `python -m unittest discover -s tests -v` passed all 8 tests; `python main.py --inspect` found 10 EDF files (CHB01: 8, CHB02: 1, CHB03: 1); NumPy, pandas, SciPy and MNE imports succeeded after installing `requirements.txt` in `.venv311`.

### Mirror to original repository
Copy both files to the same relative paths in `student-anshu/EEG-seizure-detection`. Then, from the original repository's `EEG_Seizure_Detection` directory, run:
```powershell
python -m unittest discover -s tests -v
python main.py --inspect
```
Do not mark the upstream copy complete until verified.


## Phase 0, Task 3: import/execution convention

### Files changed in working copy
- Updated `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/check_processed_data.py`.

### Change
- Replaced `from EEG_Seizure_Detection.config import PROCESSED_DIR` with `from config import PROCESSED_DIR`.
- This matches the existing script-style imports in `main.py` when commands are run from the `EEG_Seizure_Detection` directory.

### Verification
- User ran the full test suite: **8 tests passed**.
- `python check_processed_data.py` completed successfully and reported zero processed recordings (expected before processing).
- `python main.py --inspect` found **10 EDF files**.

### Mirror to original repository
The Task 3 file is included in the full-folder synchronization:
`EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/check_processed_data.py`.

## Phase 0, Task 4: signal-processing hardening

### Files changed in working copy
- Updated `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/signal_processing.py`.
- Added `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_signal_processing.py`.

### Behavior changes
- Added input validation for array shape, finite values, sampling frequency and filter cutoffs.
- Retained the fourth-order Butterworth bandpass with default 0.5–40 Hz settings and Nyquist-aware upper cutoff.
- Used second-order-section forward-backward filtering for the notch stage.
- Added explicit errors for recordings too short for zero-phase filtering.
- Retained median/IQR normalization and documented its whole-recording, offline/non-causal nature.

### Verification (user's local Windows checkout)
- `python -m unittest discover -s tests -v` — **18 tests passed**.
- `python main.py --inspect` — **10 EDF files found**.

### Mirror to original repository
Copy these two files to the same relative paths in `student-anshu/EEG-seizure-detection`:
1. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/signal_processing.py`
2. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_signal_processing.py`

The existing `tests/__init__.py` is unchanged by Task 4. Use the full-folder replacement approach if desired, but preserve the original repository's dataset and do not copy virtual environments. Then run:
```powershell
python -m unittest discover -s tests -v
python main.py --inspect
```
Do not mark the upstream copy complete until verified.
