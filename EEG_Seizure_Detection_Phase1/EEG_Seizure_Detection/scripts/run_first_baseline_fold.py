"""Run the first nested LOPO Logistic Regression experiment.

Run from the EEG_Seizure_Detection project directory:
    python -u .\\scripts\\run_first_baseline_fold.py

This runs only fold 1 (patient_01 held out). It is an engineering validation
run, not the final 23-fold evaluation.
"""
from __future__ import annotations

import argparse
import gc
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import PROCESSED_DIR, PREFERRED_CHANNELS, RANDOM_STATE
from data_management.cohort import filter_primary_cohort
from data_management.dataset_split import build_lopo_folds
from data_management.fold_data import prepare_lopo_fold
from data_management.patient_mapping import load_recording_manifest
from feature_selection.feature_extraction import FEATURE_NAMES
from modeling.baseline import (
    build_baseline_estimators,
    calculate_metrics,
    collect_features,
    fit_channel_standardizer,
    fit_validate_model,
    positive_scores,
)


def _split_summary(recordings):
    return {
        "recordings": len(recordings),
        "patients": sorted({item.patient_id for item in recordings}),
    }


def run_first_fold(audit_path: Path, output_path: Path, seed: int = RANDOM_STATE):
    started = perf_counter()
    recordings = filter_primary_cohort(load_recording_manifest(audit_path))
    folds = build_lopo_folds(recordings)
    fold = folds[0]
    if fold.fold_id != 1:
        raise RuntimeError("Expected the first deterministic LOPO fold")

    print(f"Primary cohort: {len(recordings)} recordings", flush=True)
    print(f"Outer fold {fold.fold_id}: held-out patient {fold.test_patient_id}", flush=True)
    cache_root = PROJECT_ROOT / "cache" / "first_fold"
    print("Preparing inner fit/validation split and fit-only channel scaler...", flush=True)
    prepared = prepare_lopo_fold(
        fold, PROCESSED_DIR, validation_fraction=0.2, random_state=seed,
        scaler_checkpoint_dir=cache_root / "scalers" / "fold_1_inner_fit",
    )
    print("Extracting/resuming inner-fit features...", flush=True)
    fit_batch = collect_features(
        prepared.fit_recordings, PROCESSED_DIR, prepared.standardizer,
        cache_dir=cache_root, cache_key="inner_fit",
    )
    print("Extracting/resuming inner-validation features...", flush=True)
    validation_batch = collect_features(
        prepared.validation_recordings, PROCESSED_DIR, prepared.standardizer,
        cache_dir=cache_root, cache_key="inner_validation",
    )

    inner_model = build_baseline_estimators(random_state=seed)["logistic_regression"]
    inner_model, threshold, validation_metrics = fit_validate_model(
        inner_model, fit_batch, validation_batch
    )
    print(f"Validation threshold selected: {threshold:.8g}", flush=True)
    print(
        "Validation metrics: "
        + json.dumps(validation_metrics, sort_keys=True),
        flush=True,
    )

    # Free the inner feature matrices before allocating outer-train matrices.
    del fit_batch, validation_batch, inner_model
    gc.collect()

    print("Refitting channel scaler on all outer-training patients...", flush=True)
    outer_scaler = fit_channel_standardizer(
        fold.train_recordings,
        PROCESSED_DIR,
        checkpoint_dir=cache_root / "scalers" / "fold_1_outer_train",
        checkpoint_context={
            "stage": "outer_train_channel_scaler",
            "fold_id": fold.fold_id,
            "outer_test_patient": fold.test_patient_id,
            "outer_train_patients": sorted({item.patient_id for item in fold.train_recordings}),
            "random_state": int(seed),
        },
    )

    print("Extracting all outer-training features...", flush=True)
    outer_train_batch = collect_features(
        fold.train_recordings, PROCESSED_DIR, outer_scaler,
        cache_dir=cache_root, cache_key="outer_train",
    )
    print("Extracting/resuming held-out test-patient features...", flush=True)
    outer_test_batch = collect_features(
        fold.test_recordings, PROCESSED_DIR, outer_scaler,
        cache_dir=cache_root, cache_key="outer_test",
    )

    print("Training final Logistic Regression on all outer-training patients...", flush=True)
    final_model = build_baseline_estimators(random_state=seed)["logistic_regression"]
    final_model.fit(outer_train_batch.X, outer_train_batch.y)
    print("Scoring held-out patient...", flush=True)
    test_scores = positive_scores(final_model, outer_test_batch.X)
    test_metrics = calculate_metrics(outer_test_batch.y, test_scores, threshold)

    result = {
        "experiment": "first_nested_lopo_logistic_regression",
        "status": "completed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "fold_id": fold.fold_id,
        "held_out_patient": fold.test_patient_id,
        "primary_cohort": {
            "recordings": len(recordings),
            "patients": len({item.patient_id for item in recordings}),
        },
        "inner_fit": _split_summary(prepared.fit_recordings),
        "inner_validation": _split_summary(prepared.validation_recordings),
        "outer_train": _split_summary(fold.train_recordings),
        "outer_test": _split_summary(fold.test_recordings),
        "model": {
            "name": "LogisticRegression",
            "solver": "liblinear",
            "class_weight": "balanced",
            "max_iter": 1000,
            "random_state": seed,
        },
        "preprocessing": {
            "sampling_rate_hz": 256,
            "window_seconds": 10,
            "stride_seconds": 5,
            "channels": list(PREFERRED_CHANNELS),
            "features_per_channel": list(FEATURE_NAMES),
            "feature_count": len(PREFERRED_CHANNELS) * len(FEATURE_NAMES),
            "channel_scaler_fit": "inner_fit_only_for_threshold_selection_then_all_outer_train_for_refit",
            "feature_scaler": "StandardScaler fitted within each LogisticRegression pipeline",
        },
        "threshold_selection": {
            "method": "maximize validation F1",
            "validation_threshold": float(threshold),
            "outer_test_used_for_selection": False,
        },
        "validation_metrics": validation_metrics,
        "outer_test_metrics": test_metrics,
        "runtime_seconds": round(perf_counter() - started, 3),
        "limitations": [
            "This is only the first LOPO fold, not the complete 23-fold evaluation.",
            "The validation-selected decision threshold is transferred to the refitted model.",
            "Metrics are window-level; event-level aggregation is not implemented in this milestone.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary_path.replace(output_path)
    print("\nFIRST-FOLD EXPERIMENT COMPLETED", flush=True)
    print(f"Saved results: {output_path}", flush=True)
    print("Outer-test metrics (held-out patient; window-level):", flush=True)
    print(json.dumps(test_metrics, indent=2, sort_keys=True), flush=True)
    print("This result is not the final 23-fold performance estimate.", flush=True)

    # Feature caches are only needed to resume an incomplete run. Preserve them
    # on any exception/interruption; remove them only after the result is saved.
    # Release read-only memory maps before deleting their backing files
    # (required on Windows).
    del outer_train_batch, outer_test_batch, final_model, test_scores
    gc.collect()
    if cache_root.exists():
        shutil.rmtree(cache_root)
        print(f"Cleaned completed fold feature cache: {cache_root}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "docs" / "full_annotation_audit.csv",
        help="Path to docs/full_annotation_audit.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "baselines" / "first_fold_patient_01.json",
        help="JSON output path for this experiment",
    )
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    args = parser.parse_args()
    run_first_fold(args.audit, args.output, args.seed)


if __name__ == "__main__":
    main()
