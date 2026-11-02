import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from config import DATASET_DIR, PROCESSED_DIR, LOW_CUT_HZ, HIGH_CUT_HZ, NOTCH_HZ, WINDOW_SECONDS, STRIDE_SECONDS, PREFERRED_CHANNELS
from preprocessing.load_data import load_edf
from preprocessing.annotations import read_seizure_intervals
from preprocessing.signal_processing import bandpass_and_notch, robust_normalize
from preprocessing.segmentation import make_windows


def _normalize_channel_name(name: str) -> str:
    return "".join(str(name).upper().split())


def choose_channels(raw):
    """Select all canonical channels in fixed order or reject the recording."""
    lookup = {_normalize_channel_name(name): name for name in raw.ch_names}
    missing = [name for name in PREFERRED_CHANNELS if _normalize_channel_name(name) not in lookup]
    if missing:
        raise ValueError(
            "Recording is incompatible with the fixed 17-channel primary montage. "
            "Missing channels: " + ", ".join(missing)
        )
    return [lookup[_normalize_channel_name(name)] for name in PREFERRED_CHANNELS]


def process_edf(edf_path: str | Path):
    edf_path = Path(edf_path)
    print(f"\nLoading: {edf_path}")
    raw = load_edf(edf_path)
    channels = choose_channels(raw)
    raw.pick(channels)
    sfreq = float(raw.info["sfreq"])
    data = raw.get_data()
    intervals = read_seizure_intervals(edf_path)
    print(f"Channels selected: {len(channels)}")
    print(f"Sampling frequency: {sfreq:g} Hz")
    print(f"Seizure intervals: {intervals if intervals else 'None'}")
    filtered = bandpass_and_notch(data, sfreq, LOW_CUT_HZ, HIGH_CUT_HZ, NOTCH_HZ)
    normalized = robust_normalize(filtered)
    X, y, starts = make_windows(normalized, sfreq, intervals, WINDOW_SECONDS, STRIDE_SECONDS)
    if len(y) == 0:
        print("Recording is shorter than one configured window; skipped.")
        return None
    subject = edf_path.parent.name
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_name = f"{subject}_{edf_path.stem}"
    npz_path = PROCESSED_DIR / f"{output_name}.npz"
    np.savez_compressed(npz_path, X=X, y=y, starts=starts, channels=np.asarray(channels),
                        sfreq=sfreq, subject=subject, source_file=edf_path.name)
    metadata = pd.DataFrame({
        "subject": subject, "source_file": edf_path.name,
        "window_start_seconds": starts, "window_end_seconds": starts + WINDOW_SECONDS,
        "sampling_frequency_hz": sfreq, "channels": "|".join(channels), "label": y,
    })
    metadata.to_csv(PROCESSED_DIR / f"{output_name}_metadata.csv", index=False)
    print(f"Saved {len(y)} windows: {np.bincount(y, minlength=2).tolist()} [normal, seizure]")
    print(f"Saved: {npz_path}")
    return npz_path


def inspect_dataset():
    if not DATASET_DIR.exists():
        raise FileNotFoundError(f"Dataset folder not found: {DATASET_DIR}\nDownload and extract CHB-MIT into dataset/chbmit.")
    edfs = sorted(DATASET_DIR.rglob("*.edf"))
    print(f"Dataset directory: {DATASET_DIR}")
    print(f"EDF files found: {len(edfs)}")
    for path in edfs[:20]:
        print(f"  {path.relative_to(DATASET_DIR)}")
    if len(edfs) > 20:
        print(f"  ... and {len(edfs) - 20} more")


def main():
    parser = argparse.ArgumentParser(description="EEG seizure data preparation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inspect", action="store_true")
    group.add_argument("--edf", type=str, help="Process one EDF file")
    group.add_argument("--all", action="store_true", help="Process all compatible EDF files")
    args = parser.parse_args()
    if args.inspect:
        inspect_dataset()
    elif args.edf:
        process_edf(args.edf)
    elif args.all:
        edfs = sorted(DATASET_DIR.rglob("*.edf"))
        if not edfs:
            raise FileNotFoundError(f"No EDF files found under {DATASET_DIR}")
        processed = skipped = 0
        for path in edfs:
            try:
                result = process_edf(path)
                processed += result is not None
                skipped += result is None
            except Exception as exc:
                skipped += 1
                print(f"SKIPPED {path}: {exc}")
        print(f"\nDataset processing finished: processed={processed}, skipped={skipped}")


if __name__ == "__main__":
    main()
