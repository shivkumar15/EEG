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
