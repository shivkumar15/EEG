"""Build and summarize LOPO folds from the committed CHB-MIT audit CSV."""

from __future__ import annotations

import sys
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(CODE_ROOT))

from data_management.dataset_split import build_lopo_folds
from data_management.patient_mapping import load_recording_manifest


def main() -> None:
    audit_csv = REPOSITORY_ROOT / "docs" / "full_annotation_audit.csv"
    recordings = load_recording_manifest(audit_csv)
    folds = build_lopo_folds(recordings)

    patient_ids = {recording.patient_id for recording in recordings}
    total_events = sum(recording.seizure_count for recording in recordings)
    positive_recordings = sum(recording.seizure_count > 0 for recording in recordings)

    print("========== CHB-MIT LOPO SPLIT SUMMARY ==========")
    print(f"Audit CSV: {audit_csv}")
    print(f"Recordings: {len(recordings)}")
    print(f"Independent patients: {len(patient_ids)}")
    print(f"Seizure-positive recordings: {positive_recordings}")
    print(f"Annotated seizure events: {total_events}")
    print(f"LOPO folds: {len(folds)}")

    print("\nFold details:")
    for fold in folds:
        test_events = sum(item.seizure_count for item in fold.test_recordings)
        train_patients = {item.patient_id for item in fold.train_recordings}
        print(
            f"Fold {fold.fold_id:02d}: "
            f"test={fold.test_patient_id}, "
            f"train_patients={len(train_patients)}, "
            f"train_recordings={len(fold.train_recordings)}, "
            f"test_recordings={len(fold.test_recordings)}, "
            f"test_seizure_events={test_events}"
        )

    tested_paths = [
        item.relative_path for fold in folds for item in fold.test_recordings
    ]
    assert len(folds) == len(patient_ids)
    assert len(tested_paths) == len(recordings)
    assert len(set(tested_paths)) == len(recordings)
    assert len(patient_ids) == 23, (
        f"Expected 23 independent patient groups, found {len(patient_ids)}"
    )
    assert len(recordings) == 686, (
        f"Expected 686 audited recordings, found {len(recordings)}"
    )

    print("\nPASS: every recording is tested exactly once.")
    print("PASS: no patient appears in both train and test in any fold.")
    print("PASS: CHB01 and CHB21 are grouped as one patient.")
    print("PASS: all 686 recordings and 23 independent patients are represented.")


if __name__ == "__main__":
    main()
