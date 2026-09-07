"""
app.face.engine — deterministic face detection, alignment, and embedding.

Pipeline:
    image → YuNet detector → select largest face → SFace align+embed
          → SHA-256 crop → FaceResult + JSON artifact

Design decisions:
- YuNet and SFace are bundled with opencv-contrib-python (no external download).
- FaceEngine is a plain class; no module-level singletons → no global state.
- All output is deterministic for the same input image + settings.
- Aligned crop is saved to runs/<run_id>/crop_<run_id>.jpg.
- Metadata is saved to runs/<run_id>/input.json.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from app.config import Settings, get_settings
from app.face.preprocess import load_as_bgr, validate_image
from app.models import FaceError, FaceResult


class FaceEngine:
    """
    Stateless face processing engine.

    Instantiate once per run (or per call). Holds no mutable shared state.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._cfg = settings or get_settings()
        self._ensure_models()

    def _ensure_models(self) -> None:
        """Raise FaceError early if ONNX model files are missing."""
        for attr, label in [
            ("yunet_model", "YuNet detector"),
            ("sface_model", "SFace recognizer"),
        ]:
            path = getattr(self._cfg, attr)
            if not Path(path).exists():
                raise FaceError(
                    f"{label} model not found at '{path}'. "
                    "Run: python scripts/download_models.py",
                    code="MODEL_NOT_FOUND",
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, image_path: str | Path, run_id: str | None = None) -> FaceResult:
        """
        Run the full face pipeline on *image_path*.

        Args:
            image_path: Path to the input JPEG / PNG / WebP file.
            run_id:     Optional run identifier. Auto-generated if omitted.

        Returns:
            FaceResult with detection metadata, embedding info, and crop SHA-256.

        Raises:
            ImageValidationError: If the image is invalid/unsupported.
            FaceError:            If no face is detected or embedding fails.
        """
        t_start = time.perf_counter()
        run_id = run_id or uuid.uuid4().hex[:12]

        # 1. Validate format and dimensions
        validate_image(image_path, self._cfg)

        # 2. Load as BGR ndarray
        bgr = load_as_bgr(image_path)

        # 3. Detect faces with YuNet
        faces = self._detect_faces(bgr)
        if not faces:
            raise FaceError(
                "No face detected in the image.",
                code="NO_FACE_FOUND",
            )

        face_count = len(faces)

        # 4. Select the largest face by bounding-box area
        selected = self._select_largest(faces)

        # 5. Align + crop via SFace helper
        crop_bgr = self._align_crop(bgr, selected)

        # 6. Generate SFace embedding (returns 1-D float32 array)
        embedding = self._embed(bgr, selected)

        # 7. SHA-256 of aligned crop bytes (deterministic)
        crop_sha256 = self._sha256_of_image(crop_bgr)

        # 8. Save crop and JSON artifact
        run_dir = self._cfg.run_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        crop_path = run_dir / f"crop_{run_id}.jpg"
        cv2.imwrite(str(crop_path), crop_bgr)

        # Bounding box as integer list [x1, y1, x2, y2]
        x, y, w, h = (int(v) for v in selected[:4])
        bbox = [x, y, x + w, y + h]

        processing_time_ms = (time.perf_counter() - t_start) * 1000.0

        result = FaceResult(
            face_count=face_count,
            bbox=bbox,
            embedding_model=self._cfg.embedding_model,
            embedding_dim=int(embedding.shape[0]),
            crop_sha256=crop_sha256,
            crop_path=str(crop_path),
            processing_time_ms=round(processing_time_ms, 2),
        )

        # 9. Write JSON artifact under runs/<run_id>/input.json
        self._write_artifact(run_dir, result, image_path)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _detect_faces(self, bgr: np.ndarray) -> list[np.ndarray]:
        """
        Run YuNet on *bgr* and return a list of detected face rows.

        Each row is a float32 array: [x, y, w, h, score, lm0x, lm0y, …, lm4x, lm4y]
        (15 values total — 4 bbox + 1 score + 5×2 landmarks).
        """
        h, w = bgr.shape[:2]

        detector = cv2.FaceDetectorYN.create(
            model=str(self._cfg.yunet_model),
            config="",
            input_size=(w, h),
            score_threshold=self._cfg.face_score_threshold,
            nms_threshold=self._cfg.face_nms_threshold,
            top_k=self._cfg.face_top_k,
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU,
        )
        detector.setInputSize((w, h))

        _, detections = detector.detect(bgr)

        if detections is None:
            return []

        return [detections[i] for i in range(detections.shape[0])]

    def _select_largest(self, faces: list[np.ndarray]) -> np.ndarray:
        """Return the face with the largest bounding-box area."""
        return max(faces, key=lambda f: float(f[2]) * float(f[3]))

    def _align_crop(self, bgr: np.ndarray, face_row: np.ndarray) -> np.ndarray:
        """
        Produce a 112×112 aligned face crop using SFace's built-in alignment.

        SFace.alignCrop handles the five-point landmark warp internally.
        """
        recognizer = cv2.FaceRecognizerSF.create(
            model=str(self._cfg.sface_model),
            config="",
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU,
        )
        aligned = recognizer.alignCrop(bgr, face_row)
        return aligned

    def _embed(self, bgr: np.ndarray, face_row: np.ndarray) -> np.ndarray:
        """
        Generate an L2-normalised SFace embedding for the selected face.

        Returns a 1-D float32 array of length 128.
        """
        recognizer = cv2.FaceRecognizerSF.create(
            model=str(self._cfg.sface_model),
            config="",
            backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
            target_id=cv2.dnn.DNN_TARGET_CPU,
        )
        aligned = recognizer.alignCrop(bgr, face_row)
        feature = recognizer.feature(aligned)
        # feature shape is (1, 128); flatten to 1-D
        return feature.flatten()

    @staticmethod
    def _sha256_of_image(bgr: np.ndarray) -> str:
        """Return lowercase hex SHA-256 of the raw BGR image bytes."""
        return hashlib.sha256(bgr.tobytes()).hexdigest()

    @staticmethod
    def _write_artifact(
        run_dir: Path,
        result: FaceResult,
        image_path: str | Path,
    ) -> None:
        """Write runs/<run_id>/input.json with pipeline metadata."""
        artifact = {
            "run_id": run_dir.name,
            "input_file": str(Path(image_path).resolve()),
            "input_sha256": hashlib.sha256(
                Path(image_path).read_bytes()
            ).hexdigest(),
            "face_result": result.model_dump(),
        }
        artifact_path = run_dir / "input.json"
        artifact_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
