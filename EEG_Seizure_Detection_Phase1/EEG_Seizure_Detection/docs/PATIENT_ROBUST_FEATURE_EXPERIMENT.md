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

The first-fold experiment runner is added separately after the feature extractor
passes its unit tests. Do not replace or delete legacy feature definitions or
baseline results.
