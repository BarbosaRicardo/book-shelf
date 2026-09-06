#!/usr/bin/env python3
"""Download the credit risk dataset from Kaggle into `data/`.

    pip install kagglehub
    python download_data.py

Needs Kaggle credentials: either `~/.kaggle/kaggle.json` (Kaggle account ->
Settings -> API -> Create New Token) or the KAGGLE_USERNAME and KAGGLE_KEY
environment variables.

`run_analysis.py` calls the same code path on its own, so running this first is
optional — it is here to make the download step explicit and easy to debug.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from data import KAGGLE_DATASET, download_via_kagglehub  # noqa: E402


def main() -> int:
    try:
        destination = download_via_kagglehub()
    except Exception as exc:
        print(f"Download failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        print(
            "\nCheck that `kagglehub` is installed, that Kaggle credentials are in place,\n"
            "and that this machine can reach kaggle.com. Without the real file,\n"
            "run_analysis.py falls back to the calibrated stand-in and labels its reports\n"
            "accordingly.",
            file=sys.stderr,
        )
        return 1
    print(f"Path to dataset files: {destination.parent}")
    print(f"Dataset ready at: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
