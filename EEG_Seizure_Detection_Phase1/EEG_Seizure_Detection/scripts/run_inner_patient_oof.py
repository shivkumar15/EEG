"""Run patient-held-out OOF Logistic Regression on the 22 outer-training patients.

Prerequisites:
  1. Existing robust_feature_first_fold_v1/inner_fit and inner_validation caches.
  2. cache/oof_recording_stats_v1/manifest.json.
  3. cache/oof_window_std_v1/manifest.json (build with the companion script).

No outer-test recording is opened. Completed patient folds are reused on restart.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from config import PROCESSED_DIR, PREFERRED_CHANNELS, RANDOM_STATE
from data_management.cohort import filter_primary_cohort
from data_management.dataset_split import build_lopo_folds
from data_management.fold_data import processed_path_for_recording
from data_management.patient_mapping import load_recording_manifest
from data_management.validation_split import build_patient_validation_split
from evaluation.oof_scaler_cache import (
    finalize_channel_statistics, log_std_from_raw_standard_deviations,
    merge_channel_statistics,
)
from modeling.baseline import calculate_metrics

FEATURES_PER_CHANNEL = 10
FEATURE_COUNT = len(PREFERRED_CHANNELS) * FEATURES_PER_CHANNEL
CACHE_VERSION = "patient_grouped_oof_robust_v1"


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_complete_manifest(path, expected_version=None):
    if not path.is_file():
        raise FileNotFoundError(f"Required cache manifest missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not value.get("complete"):
        raise RuntimeError(f"Cache is not marked complete: {path}")
    if expected_version and value.get("cache_version", value.get("version")) != expected_version:
        raise RuntimeError(f"Unexpected cache version in {path}")
    return value


def validate_split_cache(directory, expected_features):
    manifest = load_complete_manifest(directory / "manifest.json")
    x = np.load(directory / "X.npy", mmap_mode="r", allow_pickle=False)
    y = np.load(directory / "y.npy", mmap_mode="r", allow_pickle=False)
    shape = manifest.get("shape")
    if (shape != list(x.shape) or x.ndim != 2 or x.shape[1] != expected_features
            or x.dtype != np.float32 or y.shape != (len(x),) or y.dtype != np.int8
            or not np.isin(y, (0, 1)).all()):
        raise RuntimeError(f"Feature cache integrity check failed: {directory}")
    if int(manifest.get("completed_recordings", -1)) <= 0:
        raise RuntimeError(f"Feature cache has no completed recordings: {directory}")
    return x, y, manifest


def build_feature_matrix(project_cache, std_root, stats_manifest, std_manifest, audit_recordings, outer_train):
    """Join existing invariant features with fold-specific log_std in a row-audited memmap."""
    split = build_patient_validation_split(outer_train, validation_fraction=0.2, random_state=RANDOM_STATE)
    fit_x, fit_y, fit_m = validate_split_cache(project_cache / "inner_fit", FEATURE_COUNT)
    val_x, val_y, val_m = validate_split_cache(project_cache / "inner_validation", FEATURE_COUNT)
    if len(fit_m.get("shape", [])) != 2 or len(val_m.get("shape", [])) != 2:
        raise RuntimeError("Unexpected robust feature cache manifests")

    stats_by_path = {e["relative_path"]: e for e in stats_manifest["entries"]}
    std_by_path = {e["relative_path"]: e for e in std_manifest["entries"]}
    if len(stats_by_path) != 608 or len(std_by_path) != 608:
        raise RuntimeError("Expected exactly 608 per-recording cache entries")
    if set(stats_by_path) != {r.relative_path for r in outer_train}:
        raise RuntimeError("Scaler-stat cache recording identities do not match outer training")
    if set(std_by_path) != {r.relative_path for r in outer_train}:
        raise RuntimeError("Window-std cache recording identities do not match outer training")

    cache_signature = sha({
        "version": CACHE_VERSION, "feature_version": "relative_spectral_shape_v1",
        "feature_count": FEATURE_COUNT, "fit_manifest_signature": fit_m.get("signature"),
        "validation_manifest_signature": val_m.get("signature"),
        "stats_manifest": sha(stats_manifest), "std_manifest": sha(std_manifest),
        "ordered_recordings": [r.relative_path for r in outer_train],
    })
    output = project_cache.parent / "oof_window_features_v1"
    output.mkdir(parents=True, exist_ok=True)
    manifest_path, x_path, y_path = output / "manifest.json", output / "X.npy", output / "y.npy"
    if manifest_path.is_file() and x_path.is_file() and y_path.is_file():
        try:
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            x_saved = np.load(x_path, mmap_mode="r", allow_pickle=False)
            y_saved = np.load(y_path, mmap_mode="r", allow_pickle=False)
            if (saved.get("signature") == cache_signature and saved.get("complete")
                    and x_saved.shape == (sum(e["window_count"] for e in stats_manifest["entries"]), FEATURE_COUNT)
                    and x_saved.dtype == np.float32 and y_saved.shape == (len(x_saved),)
                    and y_saved.dtype == np.int8):
                print("Reusing complete OOF feature matrix.", flush=True)
                return x_saved, y_saved, saved, split
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            pass

    # Reconstruct exact split-cache row ranges; no row ordering is inferred from labels.
    split_arrays = {
        "inner_fit": (fit_x, fit_y, split.train_recordings),
        "inner_validation": (val_x, val_y, split.validation_recordings),
    }
    row_lookup = {}
    for split_name, (sx, sy, records) in split_arrays.items():
        cursor = 0
        for rec in records:
            source = processed_path_for_recording(PROCESSED_DIR, rec)
            with np.load(source, allow_pickle=False) as z:
                count = len(z["y"])
                labels = np.asarray(z["y"], dtype=np.int8)
            end = cursor + count
            if end > len(sy) or not np.array_equal(np.asarray(sy[cursor:end]), labels):
                raise RuntimeError(f"Cached labels/order mismatch for {rec.relative_path}")
            if bool(np.any(labels == 1)) != (rec.seizure_count > 0):
                raise RuntimeError(f"Annotation/label mismatch for {rec.relative_path}")
            row_lookup[rec.relative_path] = (sx, sy, cursor, end, split_name)
            cursor = end
        if cursor != len(sy):
            raise RuntimeError(f"{split_name} recording offsets do not cover the cache")

    total = sum(int(std_by_path[r.relative_path]["window_count"]) for r in outer_train)
    if total != len(fit_y) + len(val_y):
        raise RuntimeError("OOF cache window count differs from robust feature caches")
    X = np.lib.format.open_memmap(x_path, mode="w+", dtype=np.float32, shape=(total, FEATURE_COUNT))
    y = np.lib.format.open_memmap(y_path, mode="w+", dtype=np.int8, shape=(total,))
    # Aggregate recording sufficient statistics by patient once, then construct
    # each held-out patient's scaler from the other 21 patients only.
    patient_states = {}
    for rec in outer_train:
        entry = stats_by_path[rec.relative_path]
        artifact = project_cache.parent / "oof_recording_stats_v1" / "recordings" / entry["artifact"]
        with np.load(artifact, allow_pickle=False) as z:
            if str(z["signature"].item()) != entry["signature"]:
                raise RuntimeError(f"Stale channel-stat artifact: {rec.relative_path}")
            state = {"count": int(z["count"]), "mean": z["mean"], "m2": z["m2"]}
        if state["count"] <= 0 or state["mean"].shape != (len(PREFERRED_CHANNELS),) or state["m2"].shape != (len(PREFERRED_CHANNELS),):
            raise RuntimeError(f"Invalid channel-stat state: {rec.relative_path}")
        if rec.patient_id not in patient_states:
            patient_states[rec.patient_id] = state
        else:
            patient_states[rec.patient_id] = merge_channel_statistics(patient_states[rec.patient_id], state)
    fold_scales = {}
    for heldout_patient in sorted(patient_states):
        states = [value for patient, value in patient_states.items() if patient != heldout_patient]
        merged = states[0]
        for state in states[1:]:
            merged = merge_channel_statistics(merged, state)
        _, fold_scales[heldout_patient] = finalize_channel_statistics(merged)
    del patient_states

    offsets, cursor = [], 0
    for index, rec in enumerate(outer_train, 1):
        if rec.relative_path not in row_lookup:
            raise RuntimeError(f"Missing robust feature rows for {rec.relative_path}")
        source_x, source_y, start, end, split_name = row_lookup[rec.relative_path]
        count = end - start
        stat_entry, std_entry = stats_by_path[rec.relative_path], std_by_path[rec.relative_path]
        if int(stat_entry["count"]) <= 0 or int(std_entry["window_count"]) != count:
            raise RuntimeError(f"Statistics/window count mismatch: {rec.relative_path}")
        std_path = std_root / "recordings" / std_entry["artifact"]
        try:
            with np.load(std_path, allow_pickle=False) as z:
                raw_std = z["std"]
                if str(z["signature"].item()) != std_entry["signature"] or raw_std.shape != (count, len(PREFERRED_CHANNELS)):
                    raise RuntimeError(f"Invalid raw std artifact: {rec.relative_path}")
        except (OSError, EOFError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            raise RuntimeError(f"Could not load OOF cache for {rec.relative_path}") from exc
        fold_scale = fold_scales[rec.patient_id]

        for chunk_start in range(start, end, 4096):
            chunk_end = min(chunk_start + 4096, end)
            block = np.asarray(source_x[chunk_start:chunk_end], dtype=np.float32).copy()
            std_start, std_end = chunk_start - start, chunk_end - start
            block[:, np.arange(len(PREFERRED_CHANNELS)) * FEATURES_PER_CHANNEL] = (
                log_std_from_raw_standard_deviations(raw_std[std_start:std_end], fold_scale)
            )
            dest_start = cursor + (chunk_start - start)
            X[dest_start:dest_start + len(block)] = block
        X.flush()
        y[cursor:cursor + count] = source_y[start:end]
        offsets.append({"relative_path": rec.relative_path, "patient_id": rec.patient_id,
                        "start": cursor, "end": cursor + count, "split_source": split_name})
        cursor += count
        if index % 25 == 0 or index == len(outer_train):
            print(f"OOF feature matrix: {index}/{len(outer_train)} recordings", flush=True)
        del raw_std, fold_scale

    y.flush()
    if cursor != total or not np.isfinite(X).all() or not np.isin(y, (0, 1)).all():
        raise RuntimeError("Constructed OOF matrix failed final integrity checks")
    manifest = {"version": CACHE_VERSION, "signature": cache_signature, "complete": True,
                "window_count": total, "feature_count": FEATURE_COUNT,
                "recording_count": len(offsets), "recordings": offsets,
                "feature_definition": "existing nine invariant features plus fold-specific log_std",
                "log_std_note": "Derived from cached raw per-window std divided by fold-training channel scale; float32 rounding approximation validated by unit test.",
                "outer_test_patient_excluded": "patient_01"}
    atomic_json(manifest_path, manifest)
    del X, y
    return np.load(x_path, mmap_mode="r", allow_pickle=False), np.load(y_path, mmap_mode="r", allow_pickle=False), manifest, split


def run(audit, seed=RANDOM_STATE):
    recordings = filter_primary_cohort(load_recording_manifest(audit))
    outer = build_lopo_folds(recordings)[0]
    if outer.test_patient_id != "patient_01" or len(outer.train_recordings) != 608:
        raise RuntimeError("Unexpected outer cohort; stopping before OOF")
    if "patient_01" in {r.patient_id for r in outer.train_recordings}:
        raise RuntimeError("Outer-test patient leaked into OOF training")

    cache_root = ROOT / "cache"
    robust_root = cache_root / "robust_feature_first_fold_v1"
    stats_root = cache_root / "oof_recording_stats_v1"
    std_root = cache_root / "oof_window_std_v1"
    stats_manifest = load_complete_manifest(stats_root / "manifest.json", "oof_recording_channel_stats_v1")
    std_manifest = load_complete_manifest(std_root / "manifest.json", "oof_window_channel_std_v1")
    if stats_manifest.get("excluded_outer_test_patient") != "patient_01" or std_manifest.get("excluded_outer_test_patient") != "patient_01":
        raise RuntimeError("A prerequisite cache was not built with patient_01 excluded")

    X, y, matrix_manifest, split = build_feature_matrix(
        robust_root, std_root, stats_manifest, std_manifest, recordings, outer.train_recordings
    )
    offsets = matrix_manifest["recordings"]
    if len(offsets) != 608 or len(X) != len(y):
        raise RuntimeError("Unexpected OOF feature matrix dimensions")
    patient_ids = sorted({r.patient_id for r in outer.train_recordings})
    if len(patient_ids) != 22:
        raise RuntimeError("Expected 22 inner patient folds")

    output = cache_root / "oof_patient_scores_v1"
    fold_dir = output / "folds"
    fold_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output / "progress.json"
    results, all_y, all_scores = [], [], []
    for fold_index, heldout in enumerate(patient_ids, 1):
        test_records = [e for e in offsets if e["patient_id"] == heldout]
        train_records = [e for e in offsets if e["patient_id"] != heldout]
        if not test_records or not train_records:
            raise RuntimeError(f"Empty OOF split for {heldout}")
        signature = sha({"version": CACHE_VERSION, "matrix_signature": matrix_manifest["signature"],
                         "heldout_patient": heldout, "seed": seed,
                         "model": "LogisticRegression(liblinear,class_weight=balanced,max_iter=1000)"})
        artifact = fold_dir / f"{heldout}.npz"
        cached = False
        if artifact.is_file():
            try:
                with np.load(artifact, allow_pickle=False) as z:
                    cached = (str(z["signature"].item()) == signature
                              and len(z["y_true"]) == sum(e["end"] - e["start"] for e in test_records)
                              and np.isfinite(z["scores"]).all())
            except (OSError, EOFError, ValueError, KeyError, zipfile.BadZipFile):
                cached = False
        if cached:
            with np.load(artifact, allow_pickle=False) as z:
                fold_y, fold_scores = z["y_true"], z["scores"]
            print(f"Reusing completed OOF fold {heldout}.", flush=True)
        else:
            # Fit fold-specific feature scaler from training patients only.
            scaler = StandardScaler()
            for rec in train_records:
                for start in range(rec["start"], rec["end"], 8192):
                    end = min(start + 8192, rec["end"])
                    scaler.partial_fit(X[start:end])
            temp_train_x = output / f".{heldout}_train_X.npy"
            temp_train_y = output / f".{heldout}_train_y.npy"
            n_train = sum(e["end"] - e["start"] for e in train_records)
            train_x = np.lib.format.open_memmap(temp_train_x, mode="w+", dtype=np.float32, shape=(n_train, FEATURE_COUNT))
            train_y = np.lib.format.open_memmap(temp_train_y, mode="w+", dtype=np.int8, shape=(n_train,))
            cursor = 0
            for rec in train_records:
                for start in range(rec["start"], rec["end"], 8192):
                    end = min(start + 8192, rec["end"])
                    block = scaler.transform(X[start:end]).astype(np.float32, copy=False)
                    train_x[cursor:cursor + len(block)] = block
                    train_y[cursor:cursor + len(block)] = y[start:end]
                    cursor += len(block)
            train_x.flush(); train_y.flush()
            if cursor != n_train or len(np.unique(train_y)) != 2:
                raise RuntimeError(f"Invalid training rows/classes for {heldout}")
            model = LogisticRegression(solver="liblinear", class_weight="balanced",
                                       max_iter=1000, random_state=seed)
            print(f"Training OOF fold {fold_index}/22: held-out {heldout} ({n_train:,} windows)", flush=True)
            model.fit(train_x, train_y)
            fold_y_parts, fold_score_parts, fold_offsets = [], [], []
            test_cursor = 0
            for rec in test_records:
                start, end = rec["start"], rec["end"]
                rec_start = test_cursor
                for chunk_start in range(start, end, 8192):
                    chunk_end = min(chunk_start + 8192, end)
                    transformed = scaler.transform(X[chunk_start:chunk_end])
                    scores = model.predict_proba(transformed)[:, 1].astype(np.float32)
                    fold_score_parts.append(scores)
                    fold_y_parts.append(np.asarray(y[chunk_start:chunk_end], dtype=np.int8))
                    test_cursor += len(scores)
                fold_offsets.append({"relative_path": rec["relative_path"], "start": rec_start, "end": test_cursor})
            fold_y = np.concatenate(fold_y_parts)
            fold_scores = np.concatenate(fold_score_parts)
            tmp = artifact.with_suffix(".npz.tmp")
            with tmp.open("wb") as handle:
                np.savez_compressed(handle, signature=np.asarray(signature), y_true=fold_y,
                                    scores=fold_scores, recording_offsets=np.asarray(
                                        json.dumps(fold_offsets)))
                handle.flush(); os.fsync(handle.fileno())
            os.replace(tmp, artifact)
            del model, scaler, train_x, train_y
            temp_train_x.unlink(missing_ok=True); temp_train_y.unlink(missing_ok=True)
        metrics = calculate_metrics(fold_y, fold_scores, threshold=0.5)
        results.append({"patient_id": heldout, "recording_count": len(test_records),
                        "window_count": len(fold_y), "positive_windows": int(np.sum(fold_y == 1)),
                        "metrics_at_probability_0_5": metrics, "artifact": str(artifact.relative_to(ROOT))})
        all_y.append(np.asarray(fold_y, dtype=np.int8))
        all_scores.append(np.asarray(fold_scores, dtype=np.float32))
        atomic_json(progress_path, {"completed_folds": fold_index, "total_folds": 22,
                                    "last_completed_patient": heldout, "complete": False})
        print(f"Completed {heldout}: AUROC={metrics['auroc']} AUPRC={metrics['auprc']}", flush=True)

    pooled_y = np.concatenate(all_y)
    pooled_scores = np.concatenate(all_scores)
    # OOF F2 threshold is descriptive/provisional; probabilities from distinct
    # patient-fold models can have calibration differences and require review.
    from sklearn.metrics import precision_recall_curve
    precision, recall, thresholds = precision_recall_curve(pooled_y, pooled_scores)
    p, r = precision[:-1], recall[:-1]
    f2 = np.divide(5.0 * p * r, 4.0 * p + r, out=np.zeros_like(p), where=(4.0 * p + r) > 0)
    chosen = float(thresholds[int(np.argmax(f2))]) if len(thresholds) else 0.5
    pooled_metrics = calculate_metrics(pooled_y, pooled_scores, chosen)
    np.savez_compressed(output / "pooled_oof_scores.npz", y_true=pooled_y, scores=pooled_scores)
    report = {"version": CACHE_VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "outer_test_patient_excluded": "patient_01", "patient_fold_count": 22,
              "window_count": len(pooled_y), "positive_windows": int(np.sum(pooled_y == 1)),
              "model": "LogisticRegression(solver=liblinear,class_weight=balanced,max_iter=1000)",
              "feature_matrix_signature": matrix_manifest["signature"],
              "threshold": {"value": chosen, "objective": "pooled OOF window F2",
                            "status": "provisional; assess patient/event metrics and fold calibration before freezing"},
              "pooled_metrics_at_oof_f2_threshold": pooled_metrics,
              "patient_folds": results,
              "limitations": ["OOF uses 21-patient training sets; final outer model may be refit on 22 patients.",
                              "Pooled probabilities come from distinct fold models and may differ in calibration.",
                              "This is inner OOF only; no outer-test result is included.",
                              "Not a clinical device or clinical performance claim."]}
    atomic_json(output / "report.json", report)
    atomic_json(progress_path, {"completed_folds": 22, "total_folds": 22,
                                "last_completed_patient": patient_ids[-1], "complete": True})
    print(f"Saved OOF report: {output / 'report.json'}", flush=True)
    print(f"Provisional pooled OOF F2 threshold: {chosen:.8f}", flush=True)
    print("Outer-test patient_01 was not opened.", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=ROOT.parent.parent / "docs" / "full_annotation_audit.csv")
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    args = parser.parse_args()
    run(args.audit, args.seed)

if __name__ == "__main__":
    main()
