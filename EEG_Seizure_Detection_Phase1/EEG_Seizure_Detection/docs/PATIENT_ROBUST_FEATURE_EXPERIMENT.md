# Patient-robust feature experiment

## Motivation
The first-fold Logistic Regression baseline has highly variable sensitivity across
validation patients. The current 13-per-channel representation includes several
absolute-amplitude statistics and absolute spectral powers. The new representation
tests whether relative spectral composition and scale-normalized temporal shape
generalize better across patients.

## New representation
For each channel and 10-second window, extract 10 deterministic features:
- log standard deviation
- line length divided by standard deviation
- skewness
- excess kurtosis
- relative delta, theta, alpha, beta, and gamma power
- normalized spectral entropy

This produces 170 features for the configured 17-channel montage, compared with
221 in the legacy representation. Relative band power is invariant to uniform
amplitude scaling (up to floating-point tolerance).

## Scientific safeguards
- Feature extraction is deterministic and does not inspect labels.
- The channel standardizer is fitted on inner-fit recordings only.
- The same fitted model is used to select a threshold on inner validation and
  score the held-out outer-test patient. This deliberately avoids transferring
  a threshold between two separately fitted models in this diagnostic experiment.
- Outer-test labels are used only for final metric calculation, never for model
  selection, threshold selection, or feature design.
- Compare patient-wise and pooled AUPRC, AUROC, F2, sensitivity, and precision.
- This is a first-fold engineering experiment, not final 23-fold evidence.

## Run
From the EEG project root:
```powershell
python -m pytest tests/test_robust_feature_extraction.py -q
```

Run the first-fold experiment from the project root:

```powershell
python -m pytest tests/test_robust_feature_extraction.py -q
python -u .\\scripts\\run_robust_feature_first_fold.py
```

The runner caches completed feature extraction per recording and resumes from
its manifest after interruption. Feature extraction is processed in 256-window
chunks so temporary float64 and Welch PSD arrays remain bounded; a recording is
marked complete only after all its chunks have been written. The default run
uses Logistic Regression only, matching the legacy baseline model and keeping
the first comparison controlled. Random Forest remains available explicitly:
`--models logistic_regression random_forest`. Results and model/score artifacts
are written under `results/baselines/robust_feature_first_fold_v1/`. The original
baseline features, result JSON, and checkpoints are preserved.
