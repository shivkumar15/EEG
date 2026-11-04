# ML Training Checkpoint and Resume Policy

## Status

This policy is mandatory for all future model-training and evaluation workflows in this repository. A workflow must not be described as fully resumable unless every expensive stage that may be interrupted has a verified recovery strategy.

## Required principles

1. **Never lose completed expensive work.** Persist validated intermediate outputs at safe boundaries.
2. **Resume from the last completed unit.** On restart, validate existing checkpoints and skip only complete, compatible units.
3. **Use deterministic identities.** Cache/checkpoint signatures must include all inputs that affect results: dataset/cohort identity, split identity, preprocessing and feature configuration, scaler parameters, model configuration, random seed, and relevant source-file fingerprints.
4. **Prevent leakage.** Checkpointing must preserve the exact patient-wise split and fit-only preprocessing rules. Never reuse artifacts across incompatible folds or scaler contexts.
5. **Write atomically.** Write temporary checkpoint data, flush it, and atomically advance a manifest only after the unit is complete. A partial unit must be recomputed.
6. **Validate before reuse.** Check schema/version, shapes, dtypes, configuration signature, and integrity metadata. Invalid checkpoints must be rejected safely.
7. **Keep checkpoints out of Git.** Large runtime caches, model checkpoints, and generated experiment artifacts must be ignored by version control unless explicitly selected for a small tracked report.
8. **Report progress and recovery.** Log the current fold, model, stage, completed units, and resume position. Preserve logs and a machine-readable run manifest.
9. **Do not silently restart.** If a compatible checkpoint is unavailable or invalid, clearly report which stage must be recomputed.
10. **Test interruption behavior.** Each new checkpoint mechanism needs tests for interruption, restart, completed-unit skipping, incompatible configuration, corrupted checkpoint handling, and cleanup.

## Stages that need independent recovery

For every future training pipeline, assess and checkpoint the following expensive stages where applicable:

- Dataset loading / preprocessing and feature extraction, preferably per recording or bounded batch.
- Fold-specific preprocessing and scaler fitting, with enough metadata to verify/recompute safely.
- Model fitting, using a supported estimator checkpoint mechanism (for example, incremental training, estimator-native persistence, or deterministic sub-iterations). If the estimator cannot safely resume, save completed model results and explicitly document that an interrupted fit restarts from the beginning.
- Validation scoring and threshold selection, so completed model/validation results are not repeated unnecessarily.
- Outer-test evaluation, with immutable fold/model/config identifiers and results written atomically.
- Full experiment aggregation, so a restart skips folds that have complete, validated results.

## Current implementation scope (Fold 1 baseline)

The first-fold runner supports per-recording feature extraction checkpoints through disk-backed NumPy arrays and an atomic manifest. Completed feature recordings can be reused after interruption when the cache signature matches.

Fold-specific channel-scaler fitting now supports per-recording checkpoints of the running sample count, channel mean and M2 accumulator. The scaler checkpoint signature binds the exact ordered recordings, patient/fold context, processed NPZ source fingerprints, algorithm version and epsilon. The manifest advances only after a complete recording's accumulator state has been flushed and atomically stored. Inner-fit and outer-training scaler contexts use separate checkpoint directories.

**Important limitations:** estimator fitting itself is not checkpointed. If interrupted during Logistic Regression or Random Forest fitting, that fit must currently be repeated; compatible scaler and feature caches remain reusable. Validation scoring/threshold selection and final test scoring are not independently checkpointed. The runner currently handles the first LOPO fold only; it is not yet a resumable 23-fold experiment runner. See `docs/SCALER_CHECKPOINTS.md` for the scaler checkpoint format and validation coverage.

Do not claim full end-to-end resume until model-fitting recovery and fold-level recovery have been implemented and tested.

## Definition of done for a resumable experiment

A run is resumable only when a forced interruption at each expensive stage can be followed by a restart that:
- validates the run configuration and checkpoint;
- skips all previously completed compatible work;
- recomputes only the interrupted/incomplete unit;
- produces the same fold/model outputs as an uninterrupted run within documented numerical tolerances; and
- records the recovery action in its run log/manifest.
