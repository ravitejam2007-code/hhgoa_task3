"""
app.models — shared typed data models for the pipeline.

All models use Pydantic v2 for validation and serialisation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FaceResult(BaseModel):
    """Structured output of the local face-processing pipeline (Phase 1)."""

    # Number of faces detected in the source image
    face_count: int = Field(..., ge=1)

    # Bounding box of the selected (largest) face: [x1, y1, x2, y2] in pixels
    bbox: list[int] = Field(..., min_length=4, max_length=4)

    # Human-readable identifier of the recognition model used
    embedding_model: str

    # Length of the embedding vector (e.g. 128 for SFace)
    embedding_dim: int = Field(..., gt=0)

    # SHA-256 hex digest of the aligned face crop bytes (deterministic)
    crop_sha256: str = Field(..., min_length=64, max_length=64)

    # Path to the saved aligned crop image (relative to CWD)
    crop_path: str

    # Wall-clock processing time for the full face pipeline in milliseconds
    processing_time_ms: float = Field(..., ge=0.0)


class PipelineError(Exception):
    """Base exception for all pipeline failures."""

    code: str = "PIPELINE_ERROR"

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class FaceError(PipelineError):
    """Raised when face detection or embedding fails."""

    code = "FACE_ERROR"


class ImageValidationError(PipelineError):
    """Raised when the input image is rejected at the validation stage."""

    code = "IMAGE_VALIDATION_ERROR"
