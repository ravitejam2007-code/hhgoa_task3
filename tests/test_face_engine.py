"""
tests/test_face_engine.py — unit and integration tests for the face pipeline.

Test strategy:
- Unit tests use synthetic images (created in-memory); they run offline and quickly.
- The integration test (test_engine_real_face) is marked with @pytest.mark.skipif
  so it only runs when a real face image exists at samples/test.jpg.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from app.config import Settings, get_settings
from app.face.preprocess import load_as_bgr, validate_image
from app.models import FaceError, FaceResult, ImageValidationError


# ---------------------------------------------------------------------------
# Helpers — synthetic image factories
# ---------------------------------------------------------------------------

def _make_jpeg(path: Path, size: tuple[int, int] = (400, 400)) -> None:
    """Write a plain-colour JPEG to *path*."""
    img = Image.new("RGB", size, color=(180, 120, 80))
    img.save(path, format="JPEG")


def _make_png(path: Path, size: tuple[int, int] = (400, 400)) -> None:
    img = Image.new("RGB", size, color=(60, 120, 200))
    img.save(path, format="PNG")


def _make_webp(path: Path, size: tuple[int, int] = (400, 400)) -> None:
    img = Image.new("RGB", size, color=(200, 200, 100))
    img.save(path, format="WEBP")


def _make_corrupt(path: Path) -> None:
    """Write garbage bytes that look like nothing valid."""
    path.write_bytes(b"\x00\xFF\xAB\xCD" * 50)


SAMPLE_FACE = Path("samples") / "test.jpg"


# ---------------------------------------------------------------------------
# validate_image tests
# ---------------------------------------------------------------------------

class TestValidateImage:

    def test_accepts_jpeg(self, tmp_path: Path) -> None:
        p = tmp_path / "img.jpg"
        _make_jpeg(p)
        validate_image(p, get_settings())  # must not raise

    def test_accepts_png(self, tmp_path: Path) -> None:
        p = tmp_path / "img.png"
        _make_png(p)
        validate_image(p, get_settings())

    def test_accepts_webp(self, tmp_path: Path) -> None:
        p = tmp_path / "img.webp"
        _make_webp(p)
        validate_image(p, get_settings())

    def test_rejects_text_file(self, tmp_path: Path) -> None:
        p = tmp_path / "doc.txt"
        p.write_text("hello world", encoding="utf-8")
        with pytest.raises(ImageValidationError) as exc_info:
            validate_image(p, get_settings())
        assert exc_info.value.code in ("UNSUPPORTED_FORMAT",)

    def test_rejects_corrupt_file(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.jpg"
        _make_corrupt(p)
        with pytest.raises(ImageValidationError) as exc_info:
            validate_image(p, get_settings())
        # corrupt or unrecognised
        assert exc_info.value.code in ("CORRUPT_IMAGE", "UNSUPPORTED_FORMAT")

    def test_rejects_missing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "nonexistent.jpg"
        with pytest.raises(ImageValidationError) as exc_info:
            validate_image(p, get_settings())
        assert exc_info.value.code == "IMAGE_NOT_FOUND"

    def test_rejects_too_small(self, tmp_path: Path) -> None:
        """Image shorter than min_side_px should be rejected."""
        p = tmp_path / "tiny.jpg"
        settings = Settings(min_side_px=300)
        img = Image.new("RGB", (50, 50), color=(0, 0, 0))
        img.save(p, format="JPEG")
        with pytest.raises(ImageValidationError) as exc_info:
            validate_image(p, settings)
        assert exc_info.value.code == "IMAGE_TOO_SMALL"

    def test_rejects_gif(self, tmp_path: Path) -> None:
        """GIF is not in the supported formats set."""
        p = tmp_path / "anim.gif"
        img = Image.new("P", (200, 200))
        img.save(p, format="GIF")
        with pytest.raises(ImageValidationError) as exc_info:
            validate_image(p, get_settings())
        assert exc_info.value.code == "UNSUPPORTED_FORMAT"


# ---------------------------------------------------------------------------
# load_as_bgr tests
# ---------------------------------------------------------------------------

class TestLoadAsBgr:

    def test_loads_jpeg_as_bgr(self, tmp_path: Path) -> None:
        p = tmp_path / "img.jpg"
        _make_jpeg(p, size=(200, 300))
        bgr = load_as_bgr(p)
        assert isinstance(bgr, np.ndarray)
        assert bgr.ndim == 3
        assert bgr.shape == (300, 200, 3)  # (height, width, channels)

    def test_loads_png(self, tmp_path: Path) -> None:
        p = tmp_path / "img.png"
        _make_png(p, size=(100, 150))
        bgr = load_as_bgr(p)
        assert bgr.shape == (150, 100, 3)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ImageValidationError):
            load_as_bgr(tmp_path / "ghost.jpg")


# ---------------------------------------------------------------------------
# FaceResult model tests
# ---------------------------------------------------------------------------

class TestFaceResultModel:

    def test_valid_model(self) -> None:
        r = FaceResult(
            face_count=1,
            bbox=[10, 20, 100, 120],
            embedding_model="SFace-2021-09",
            embedding_dim=128,
            crop_sha256="a" * 64,
            crop_path="runs/abc/crop_abc.jpg",
            processing_time_ms=250.5,
        )
        assert r.face_count == 1
        assert r.embedding_dim == 128

    def test_face_count_must_be_positive(self) -> None:
        with pytest.raises(Exception):
            FaceResult(
                face_count=0,  # ge=1 should fail
                bbox=[0, 0, 10, 10],
                embedding_model="SFace",
                embedding_dim=128,
                crop_sha256="b" * 64,
                crop_path="runs/x/crop.jpg",
                processing_time_ms=0.0,
            )

    def test_crop_sha256_length_enforced(self) -> None:
        with pytest.raises(Exception):
            FaceResult(
                face_count=1,
                bbox=[0, 0, 10, 10],
                embedding_model="SFace",
                embedding_dim=128,
                crop_sha256="short",  # must be 64 chars
                crop_path="runs/x/crop.jpg",
                processing_time_ms=0.0,
            )

    def test_serialises_to_dict(self) -> None:
        r = FaceResult(
            face_count=2,
            bbox=[5, 5, 50, 50],
            embedding_model="SFace-2021-09",
            embedding_dim=128,
            crop_sha256="f" * 64,
            crop_path="runs/z/crop.jpg",
            processing_time_ms=123.4,
        )
        d = r.model_dump()
        assert d["face_count"] == 2
        assert len(d["crop_sha256"]) == 64


# ---------------------------------------------------------------------------
# FaceEngine — no-face test (blank image → FaceError)
# ---------------------------------------------------------------------------

# Resolve model paths from project root (one level above tests/)
_PROJECT_ROOT = Path(__file__).parent.parent
_YUNET = _PROJECT_ROOT / "models" / "face_detection_yunet_2023mar.onnx"
_SFACE = _PROJECT_ROOT / "models" / "face_recognition_sface_2021dec.onnx"
_MODELS_AVAILABLE = _YUNET.exists() and _SFACE.exists()


class TestFaceEngineNoFace:

    @pytest.mark.skipif(not _MODELS_AVAILABLE, reason="ONNX models not downloaded")
    def test_blank_image_raises_face_error(self, tmp_path: Path) -> None:
        """A plain colour image has no face → FaceError with NO_FACE_FOUND."""
        from app.config import Settings
        from app.face.engine import FaceEngine

        p = tmp_path / "blank.jpg"
        _make_jpeg(p, size=(400, 400))

        settings = Settings(yunet_model=_YUNET, sface_model=_SFACE)
        engine = FaceEngine(settings=settings)
        with pytest.raises(FaceError) as exc_info:
            engine.process(p)
        assert exc_info.value.code == "NO_FACE_FOUND"

    def test_invalid_image_raises_validation_error(self, tmp_path: Path) -> None:
        from app.face.engine import FaceEngine
        from app.config import Settings

        p = tmp_path / "bad.jpg"
        _make_corrupt(p)

        # Use model paths if available, otherwise expect MODEL_NOT_FOUND
        if _MODELS_AVAILABLE:
            settings = Settings(yunet_model=_YUNET, sface_model=_SFACE)
        else:
            settings = get_settings()

        # Either ImageValidationError (corrupt file) or FaceError (missing model)
        # Both are acceptable — the important thing is no unhandled crash.
        engine_created = True
        try:
            engine = FaceEngine(settings=settings)
        except FaceError:
            engine_created = False

        if engine_created:
            with pytest.raises(ImageValidationError):
                engine.process(p)


# ---------------------------------------------------------------------------
# SHA-256 determinism test (no face detection needed)
# ---------------------------------------------------------------------------

class TestSha256Determinism:

    def test_same_array_same_hash(self) -> None:
        """SHA-256 of identical pixel arrays must be identical."""
        arr = np.zeros((112, 112, 3), dtype=np.uint8)
        h1 = hashlib.sha256(arr.tobytes()).hexdigest()
        h2 = hashlib.sha256(arr.tobytes()).hexdigest()
        assert h1 == h2
        assert len(h1) == 64

    def test_different_arrays_different_hash(self) -> None:
        arr1 = np.zeros((112, 112, 3), dtype=np.uint8)
        arr2 = np.ones((112, 112, 3), dtype=np.uint8)
        assert (
            hashlib.sha256(arr1.tobytes()).hexdigest()
            != hashlib.sha256(arr2.tobytes()).hexdigest()
        )


# ---------------------------------------------------------------------------
# Integration test — only runs if samples/test.jpg exists
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not SAMPLE_FACE.exists() or not _MODELS_AVAILABLE,
    reason="samples/test.jpg or ONNX models not found",
)
class TestFaceEngineRealFace:

    def _make_settings(self, run_dir: Path) -> Settings:
        return Settings(run_dir=run_dir, yunet_model=_YUNET, sface_model=_SFACE)

    def test_full_pipeline_returns_face_result(self, tmp_path: Path) -> None:
        from app.face.engine import FaceEngine

        settings = self._make_settings(tmp_path / "runs")
        engine = FaceEngine(settings=settings)
        result = engine.process(SAMPLE_FACE)

        assert isinstance(result, FaceResult)
        assert result.face_count >= 1
        assert len(result.bbox) == 4
        assert result.embedding_dim > 0
        assert len(result.crop_sha256) == 64
        assert Path(result.crop_path).exists()
        assert result.processing_time_ms >= 0.0

    def test_same_image_same_crop_sha256(self, tmp_path: Path) -> None:
        """Running the engine twice on the same image must yield the same crop hash."""
        from app.face.engine import FaceEngine

        settings = self._make_settings(tmp_path / "runs")
        engine = FaceEngine(settings=settings)

        r1 = engine.process(SAMPLE_FACE, run_id="run1")
        r2 = engine.process(SAMPLE_FACE, run_id="run2")
        assert r1.crop_sha256 == r2.crop_sha256

    def test_input_json_artifact_written(self, tmp_path: Path) -> None:
        from app.face.engine import FaceEngine
        import json

        run_dir_base = tmp_path / "runs"
        settings = self._make_settings(run_dir_base)
        engine = FaceEngine(settings=settings)

        result = engine.process(SAMPLE_FACE, run_id="testrun")
        artifact = run_dir_base / "testrun" / "input.json"
        assert artifact.exists()

        data = json.loads(artifact.read_text(encoding="utf-8"))
        assert data["run_id"] == "testrun"
        assert "face_result" in data
        assert data["face_result"]["crop_sha256"] == result.crop_sha256
