"""
scripts/download_models.py — download YuNet and SFace ONNX models.

Run once from the project root:
    python scripts/download_models.py

Models are saved to models/ and are NOT committed to git (add to .gitignore).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"

MODELS = [
    (
        "face_detection_yunet_2023mar.onnx",
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx",
    ),
    (
        "face_recognition_sface_2021dec.onnx",
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx",
    ),
]


def download(filename: str, url: str) -> None:
    dest = MODELS_DIR / filename
    if dest.exists():
        print(f"  [skip] {filename} already exists ({dest.stat().st_size:,} bytes)")
        return

    print(f"  [download] {filename} ...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"  [ok] {filename} ({len(data):,} bytes)")


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading models to: {MODELS_DIR}\n")
    for filename, url in MODELS:
        download(filename, url)
    print("\nAll models ready.")


if __name__ == "__main__":
    main()
