"""
app.config — pipeline settings (no global state).

Each component instantiates Settings() directly; nothing is module-level.
Model files (YuNet, SFace) must be present in the models/ directory.
Run scripts/download_models.py to fetch them if missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Default model paths (relative to CWD / project root)
_DEFAULT_YUNET_MODEL = Path("models") / "face_detection_yunet_2023mar.onnx"
_DEFAULT_SFACE_MODEL = Path("models") / "face_recognition_sface_2021dec.onnx"


@dataclass(frozen=True)
class Settings:
    # Supported image MIME types (Pillow format strings)
    supported_formats: frozenset[str] = field(
        default_factory=lambda: frozenset({"JPEG", "PNG", "WEBP"})
    )

    # Minimum shortest image side in pixels (below this face detection is unreliable)
    min_side_px: int = 100

    # Where per-run artifacts are stored  (runs/<run_id>/)
    run_dir: Path = field(default_factory=lambda: Path("runs"))

    # Paths to ONNX model files (must exist; see scripts/download_models.py)
    yunet_model: Path = field(default_factory=lambda: _DEFAULT_YUNET_MODEL)
    sface_model: Path = field(default_factory=lambda: _DEFAULT_SFACE_MODEL)

    # YuNet detector parameters
    face_score_threshold: float = 0.6
    face_nms_threshold: float = 0.3
    face_top_k: int = 5000

    # SFace embedding vector length
    sface_embedding_dim: int = 128

    # Human-readable model label stored in FaceResult
    embedding_model: str = "SFace-2021-12"

    # Max long-side pixel dimension before resizing for search image (Phase 2)
    search_max_px: int = 1024


def get_settings() -> Settings:
    """Return a fresh Settings instance (reads env vars if any future overrides added)."""
    return Settings()
