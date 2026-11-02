# Upstream Change Log — Mirror to Original Repository

**Working copy:** https://github.com/shivkumar15/EEG  
**Original repository:** https://github.com/student-anshu/EEG-seizure-detection

This ledger tracks changes developed in the working repository that the team must also apply to the original repository. The original repository has not yet been synchronized or tested.

## Documentation baseline
The working repository contains:
- `README.md`
- `docs/PROJECT_MASTER_PLAN.md`
- `docs/DEVELOPMENT_LOG.md`
- `docs/AI_HANDOFF.md`
- `docs/CHANGELOG_FOR_UPSTREAM.md`

The baseline documentation should be copied to the original repository only if the team agrees to replace or merge its existing documentation.

## Phase 0, Tasks 1–5: code changes to mirror

### Task 1 — annotation parser
Files:
1. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/annotations.py`
2. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_annotations.py`
3. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/__init__.py`

Supports numbered/unnumbered seizure fields, validates declared seizure counts and intervals, handles explicit zero-seizure recordings, and reports missing/mismatched summaries.

### Task 2 — dataset path
Files:
1. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/config.py`
2. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_config_paths.py`

Dataset path resolves to the sibling `dataset/chbmit` directory.

### Task 3 — import convention
File:
- `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/check_processed_data.py`

Uses `from config import PROCESSED_DIR` when scripts are run from the project code directory.

### Task 4 — signal processing
Files:
1. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/signal_processing.py`
2. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_signal_processing.py`

Adds validation, stable SOS notch filtering, explicit short-recording errors, and documents whole-recording median/IQR normalization as offline/non-causal.

### Task 5 — segmentation, feature/channel selection and channel matching
Files:
1. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/preprocessing/segmentation.py`
2. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/feature_selection/channel_selection.py`
3. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/main.py`
4. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_segmentation.py`
5. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_channel_selection.py`
6. `EEG_Seizure_Detection_Phase1/EEG_Seizure_Detection/tests/test_channel_matching.py`

Behavior:
- Validates EEG arrays, sampling rate, window/stride parameters and seizure intervals.
- Labels windows by overlap with half-open window intervals.
- Validates channel feature inputs and binary labels; channel ranking is intended for training-fold data only.
- Makes preferred-channel matching case/whitespace insensitive, with a restricted EEG-like fallback.
- Adds window end time, sampling frequency and selected channel names to metadata.

Verification in the working checkout: **35 unit tests passed**.

## Phase 0, Task 6 — root Git ignore and dataset policy

File added:
- Repository-root `.gitignore` (commit `e5c27c0`).

It excludes Python virtual environments (including `.venv311`), Python caches, generated logs, IDE folders and OS metadata.

Important: the 10 existing EDF files are already tracked in the working repository. The root/nested ignore rules do not remove already tracked files. Current provisional policy is to preserve these 10 files, add no further raw EDFs, and avoid deleting/untracking them during synchronization. Final dataset provenance/license and long-term storage policy remains to be decided and documented.

## Phase 0, Task 7 — verified preprocessing results (current working subset)

User ran `python main.py --all` from the project code directory. All 10 EDFs were processed; no `SKIPPED` lines appeared.

Generated-file validation:
- 10 NPZ files and 10 metadata CSV files.
- Every pair passed shape, finite-value, binary-label, row-count, label equality, timestamp equality and missing-value checks.
- **6,935 total windows: 6,823 normal and 112 seizure.**
- CHB01: 5,497 windows (5,397 normal; 100 seizure).
- CHB02: 719 windows (719 normal; 0 seizure).
- CHB03: 719 windows (707 normal; 12 seizure).
- All 10 inspected EDFs had 256 Hz sampling and 17 selected channels.

Do not mirror generated `processed/` NPZ/CSV files by default. They are reproducible outputs and should remain excluded unless the team explicitly decides otherwise.

## Synchronization procedure for the original repository

After Phase 0 is fully complete:
1. Back up the original repository's existing code folder.
2. Copy the complete updated `EEG_Seizure_Detection` code folder from the working repository into the matching location in the original repository.
3. Preserve the original dataset directory. Do not copy `.venv`, `.venv311`, generated `processed/`, logs, model weights, or additional raw EDFs.
4. Review the resulting Git diff and ensure no unrelated original files were removed.
5. Commit and push to `student-anshu/EEG-seizure-detection` using the user's authorized access.
6. From the original repository's `EEG_Seizure_Detection` directory, run:
   ```powershell
   python -m unittest discover -s tests -v
   python main.py --inspect
   ```
7. Report the actual test count and EDF inventory. Do not claim upstream synchronization/verification until the user confirms the push and test output.

## Still pending before upstream synchronization
- Finalize raw EDF provenance/license and storage policy.
- Correct README dataset path/setup examples to match the actual layout.
- Complete Task 8 final Phase 0 validation.
