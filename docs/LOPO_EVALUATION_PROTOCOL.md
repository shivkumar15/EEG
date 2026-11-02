# CHB-MIT Patient Mapping and LOPO Evaluation Protocol

## Purpose

This protocol defines the outer evaluation split for cross-patient EEG seizure
detection. The unit of separation is the patient, not the EDF recording or
segmented EEG window.

## Patient identity mapping

The CHB-MIT dataset contains 24 subject folders. CHB01 and CHB21 represent
the same individual, so they must never be treated as independent patients
for model evaluation.

The code maps:

- CHB01 -> patient_01
- CHB21 -> patient_01
- Every other CHB folder retains its numeric identity (for example,
  CHB12 -> patient_12).

This produces 23 independent patient groups.

## Audit manifest

The source of recording-level metadata is
`docs/full_annotation_audit.csv`. The manifest loader:

- Requires the expected audit columns.
- Accepts only rows with status `SUCCESS`.
- Rejects empty recording identities and duplicate relative paths.
- Validates non-negative seizure counts.
- Checks that the number of listed seizure intervals matches the seizure
  count.
- Loads the CSV with UTF-8 BOM support.

Raw EDF files and processed EEG arrays are not required to generate the
outer split definitions.

## Leave-One-Patient-Out (LOPO)

The outer evaluation creates one fold per independent patient:

- 23 folds in total.
- In each fold, all recordings from one patient form the test set.
- All recordings from the other 22 patients form the training set.
- Each patient is the test patient exactly once.
- Every audited recording appears in exactly one outer test set.
- No patient can appear in both training and test sets in the same fold.

The fold generator is deterministic: patient IDs and recording paths are
sorted before folds are returned.

## Validation and model selection

LOPO defines the outer test boundary; it does not itself define a validation
set. Any hyperparameter selection, early stopping, threshold selection,
normalization fitting, channel selection, or other learned preprocessing must
be performed using only the 22 training patients in that fold.

If a validation set is needed, it must be created with a patient-grouped
split inside the outer training set. The held-out outer test patient must not
influence model selection or preprocessing.

## Inner patient-grouped validation

For each outer LOPO fold, the inner validation split is built only from that
fold's 22 outer-training patients. The outer test patient is never passed to
the validation splitter.

The current implementation uses a deterministic patient-grouped holdout:

- Validation fraction: 20% of the outer-training patients.
- Selection: seeded shuffle with random state 42.
- Rounding: ceiling, so each fold holds out 5 of its 22 training patients.
- All recordings from a patient stay together.
- The remaining 17 patients are used for model fitting.
- Train, validation, and outer test patient IDs are pairwise disjoint.

The current audit contains seizure events for all 23 independent patients.
The inspection script checks that both inner training and validation contain
annotated seizure events in every outer fold. The split is a reproducible
holdout for model development; it is not an additional independent test set.
Do not use outer test metrics to select hyperparameters, thresholds, epochs,
or preprocessing settings.

Run the inner split inspection from the project code directory:

```powershell
python .\scripts\inspect_nested_validation.py
```

## Run the split inspection

From the project code directory, after pulling the implementation:

```powershell
python .\scripts\inspect_lopo_splits.py
```

The script reads the committed audit CSV from the repository-level `docs`
directory, builds the LOPO folds, and checks the expected 686 recordings and
23 independent patient groups.

## Current audited dataset reference

The annotation audit recorded:

- 686 EDF recordings.
- 198 annotated seizure events.
- 23 independent patient groups after merging CHB01 and CHB21.

These are dataset-audit counts, not model performance results.

## Scope

This protocol creates metadata-level outer folds only. It does not load EDF
signals, segment windows, train models, choose channels, fit normalization,
or produce performance metrics. Those steps will be implemented and verified
separately while preserving the patient-level outer test boundary.
