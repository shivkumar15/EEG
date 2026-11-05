# Patient 14 OOF model-contribution audit

## Purpose

Patient 14 has weak threshold-independent discrimination (AUROC about 0.44 and
AUPRC about 0.0026) despite selected individual robust features showing
within-recording separation in some of its seven seizure-containing recordings.
This diagnostic asks whether the fitted multivariate Logistic Regression model
is combining those features in an unhelpful way.

## Method and safeguards

`scripts/audit_patient14_model_contributions.py` deterministically reconstructs
the existing patient_14 inner-OOF fold using the same 21-patient training set,
patient-excluded channel scaler, fold feature matrix, incremental
`StandardScaler.partial_fit` sequence, and balanced liblinear Logistic
Regression configuration.

**The audit will not interpret coefficients unless reconstructed probabilities
match the saved patient_14 OOF artifact within an absolute tolerance of 2e-6.**
It validates recording order, labels, and score count before writing results.

- Outer-test patient_01 is excluded before processed recording access.
- No threshold is selected or changed.
- Existing OOF score artifacts and event metrics are not overwritten.
- This is a deterministic reconstruction of one already evaluated fold, not a
  new candidate model or performance claim.
- Coefficients and additive logit contributions are associations within this
  fitted model, not causal or physiological effects.

## Run

From `EEG_Seizure_Detection` with the project's `.venv311` activated:

```powershell
git pull origin feature/threshold-strategy-score-artifacts
python -m pytest tests/test_patient14_model_contributions.py -q
python -m scripts.audit_patient14_model_contributions --audit ..\..\docs\full_annotation_audit.csv
```

The full diagnostic rebuilds the 608-recording feature matrix for the patient_14
fold from existing caches and fits one Logistic Regression model. It may take
some time and needs several hundred MB of temporary memory/disk. It does not
require EDF downloads or reprocessing.

## Outputs

- `results/diagnostics/patient_14_model_contribution_audit_v1.json`
  - score reconstruction check;
  - average additive logit contribution by feature family, split by positive
    and negative windows;
  - largest absolute coefficients, with channel and feature names;
  - interpretation limitations.
- `results/diagnostics/patient_14_recording_contributions_v1.csv`
  - per-recording positive/negative mean contribution for each feature family.

A negative contribution pushes the model logit downward relative to zero; it
does not mean a feature is biologically protective. Only 48 positive windows
exist across these recordings, and overlapping windows are correlated. Treat
per-recording summaries as descriptive, not independent-sample inference.

## Decision gate

1. If reconstruction fails, stop and investigate the pipeline discrepancy;
   do not interpret the coefficient report.
2. If reconstruction passes, inspect whether feature families consistently
   push positive windows toward lower logits, and whether that differs by
   recording.
3. Do not reverse features, remove channels, or retrain based on this one
   patient. Any model change must be justified across the full patient-grouped
   OOF cohort and evaluated under the sealed outer-test protocol later.
