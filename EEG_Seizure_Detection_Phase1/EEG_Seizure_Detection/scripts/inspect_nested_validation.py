"""Inspect patient-grouped inner validation splits inside every LOPO fold."""

from __future__ import annotations

import sys
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(CODE_ROOT))

from data_management.dataset_split import build_lopo_folds
from data_management.patient_mapping import load_recording_manifest
from data_management.validation_split import build_patient_validation_split


def main() -> None:
    audit_csv = REPOSITORY_ROOT / "docs" / "full_annotation_audit.csv"
    recordings = load_recording_manifest(audit_csv)
    outer_folds = build_lopo_folds(recordings)

    print("========== NESTED PATIENT VALIDATION SUMMARY ==========")
    print(f"Audit CSV: {audit_csv}")
    print(f"Outer LOPO folds: {len(outer_folds)}")
    print("Inner validation fraction: 0.20")
    print("Inner validation seed: 42")
    print("\nFold details:")

    for fold in outer_folds:
        split = build_patient_validation_split(
            fold.train_recordings,
            validation_fraction=0.2,
            random_state=42,
        )
        outer_test_patients = {item.patient_id for item in fold.test_recordings}
        train_patients = set(split.train_patient_ids)
        validation_patients = set(split.validation_patient_ids)
        assert not (outer_test_patients & train_patients)
        assert not (outer_test_patients & validation_patients)
        assert train_patients.isdisjoint(validation_patients)
        assert len(train_patients | validation_patients | outer_test_patients) == 23

        validation_events = sum(item.seizure_count for item in split.validation_recordings)
        train_events = sum(item.seizure_count for item in split.train_recordings)
        assert validation_events > 0, (
            f"No seizure events in validation for outer fold {fold.fold_id}"
        )
        assert train_events > 0, (
            f"No seizure events in training for outer fold {fold.fold_id}"
        )

        print(
            f"Fold {fold.fold_id:02d}: "
            f"outer_test={fold.test_patient_id}, "
            f"inner_train_patients={len(train_patients)}, "
            f"validation_patients={len(validation_patients)}, "
            f"inner_train_recordings={len(split.train_recordings)}, "
            f"validation_recordings={len(split.validation_recordings)}, "
            f"train_events={train_events}, "
            f"validation_events={validation_events}"
        )

    assert len(outer_folds) == 23
    print("\nPASS: inner train, validation, and outer test patients are disjoint.")
    print("PASS: every outer fold retains seizure events in inner train and validation.")
    print("PASS: validation contains complete patients, never partial patient recordings.")
    print("PASS: all 23 outer LOPO folds have a valid inner validation split.")


if __name__ == "__main__":
    main()
