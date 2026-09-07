"""
app.face.preprocess — image validation and loading helpers.

Responsibilities:
- Accept JPEG, PNG, or WebP only.
- Reject corrupt files.
- Reject images that are too small for reliable face detection.
- Return a BGR ndarray ready for OpenCV DNN processing.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.config import Settings
from app.models import ImageValidationError


def validate_image(image_path: str | Path, settings: Settings) -> None:
    """
    Validate that *image_path* is a readable JPEG, PNG, or WebP image
    that meets minimum dimension requirements.

    Raises:
        ImageValidationError: with a descriptive message if any check fails.
    """
    path = Path(image_path)

    if not path.exists():
        raise ImageValidationError(f"File not found: {path}", code="IMAGE_NOT_FOUND")

    if not path.is_file():
        raise ImageValidationError(f"Path is not a file: {path}", code="IMAGE_NOT_FOUND")

    # --- Format + corruption check via Pillow ---
    try:
        with Image.open(path) as img:
            fmt = img.format  # e.g. "JPEG", "PNG", "WEBP"
            img.verify()      # detects truncated / corrupt files
    except UnidentifiedImageError:
        raise ImageValidationError(
            f"Unsupported or unrecognisable image format: {path}",
            code="UNSUPPORTED_FORMAT",
        )
    except Exception as exc:
        raise ImageValidationError(
            f"Corrupt or unreadable image ({exc}): {path}",
            code="CORRUPT_IMAGE",
        )

    if fmt not in settings.supported_formats:
        raise ImageValidationError(
            f"Format '{fmt}' is not supported. Accepted: {sorted(settings.supported_formats)}",
            code="UNSUPPORTED_FORMAT",
        )

    # --- Dimension check via a second open (verify() closes the file) ---
    with Image.open(path) as img:
        w, h = img.size

    if min(w, h) < settings.min_side_px:
        raise ImageValidationError(
            f"Image too small ({w}×{h}). Minimum shortest side: {settings.min_side_px}px.",
            code="IMAGE_TOO_SMALL",
        )


def load_as_bgr(image_path: str | Path) -> np.ndarray:
    """
    Load an image file as a BGR ndarray (OpenCV convention).

    Pillow is used first to handle WebP and orientation metadata,
    then the result is converted to BGR for OpenCV DNN.

    Raises:
        ImageValidationError: if the file cannot be decoded.
    """
    path = Path(image_path)
    try:
        with Image.open(path) as img:
            # Convert to RGB (handles palette, RGBA, CMYK, etc.)
            rgb = img.convert("RGB")
            bgr = cv2.cvtColor(np.array(rgb, dtype=np.uint8), cv2.COLOR_RGB2BGR)
        return bgr
    except Exception as exc:
        raise ImageValidationError(
            f"Failed to decode image to array ({exc}): {path}",
            code="DECODE_ERROR",
        )
