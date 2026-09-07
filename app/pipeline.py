"""
app.pipeline — end-to-end orchestrator for face identification and blockchain verification.

Executes the complete 8-stage runtime pipeline:
1. Validate input image
2. Detect & encode face
3. Reverse image search
4. Validate & score candidates
5. Select best evidence
6. Canonicalize evidence
7. Generate SHA-256 fingerprint
8. Anchor fingerprint to blockchain
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.blockchain.client import BlockchainClient
from app.config import Settings, get_settings
from app.evidence.canonicalize import build_evidence, canonical_json_bytes, canonical_json_str
from app.evidence.fingerprint import evidence_hash_bytes32, evidence_hash_hex
from app.face.engine import FaceEngine
from app.face.preprocess import validate_image
from app.models import FaceResult, PipelineError
from app.search.base import SearchResponse
from app.search.serpapi_lens import GoogleLensProvider
from app.social.validator import SelectedEvidence, SocialValidator

logger = logging.getLogger(__name__)


def generate_run_id() -> str:
    """Generate a unique run ID: YYYYMMDDTHHMMSSZ_<hex4>."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    salt = uuid.uuid4().hex[:4]
    return f"{ts}_{salt}"


class PipelineResult(BaseModel):
    """Result returned upon successful execution of the complete pipeline."""

    run_id: str
    run_dir: str
    face_result: FaceResult
    search_provider: str
    match_type: str
    selected_url: str
    evidence_hash: str
    network: str
    contract_address: str
    transaction_hash: str
    evidence_id: int
    is_verified: bool


class Pipeline:
    """
    End-to-end pipeline orchestrator.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        search_provider: GoogleLensProvider | None = None,
        social_validator: SocialValidator | None = None,
        blockchain_client: BlockchainClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.face_engine = FaceEngine(settings=self.settings)
        self.search_provider = search_provider or GoogleLensProvider()
        self.social_validator = social_validator or SocialValidator()
        self.blockchain_client = blockchain_client or BlockchainClient()

    def run(
        self,
        image_path: Path,
        run_id: str | None = None,
        progress_callback=None,
    ) -> PipelineResult:
        """
        Execute the complete runtime pipeline on the input image.
        """
        run_id = run_id or generate_run_id()
        run_dir = self.settings.run_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        def report_step(step_num: int, name: str, status: str = "PASS") -> None:
            if progress_callback:
                progress_callback(step_num, name, status)

        # -------------------------------------------------------------
        # Step 1: Validate input image
        # -------------------------------------------------------------
        validate_image(image_path, self.settings)
        file_stat = image_path.stat()
        input_metadata = {
            "image_path": str(image_path),
            "file_size_bytes": file_stat.st_size,
            "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        (run_dir / "input_metadata.json").write_text(
            json.dumps(input_metadata, indent=2),
            encoding="utf-8",
        )
        report_step(1, "Face detection")

        # -------------------------------------------------------------
        # Step 2: Detect & encode face
        # -------------------------------------------------------------
        face_result = self.face_engine.process(image_path, run_id=run_id)
        (run_dir / "face_result.json").write_text(
            json.dumps(face_result.model_dump(), indent=2),
            encoding="utf-8",
        )
        report_step(2, "Face encoding")

        # -------------------------------------------------------------
        # Step 3: Reverse image search
        # -------------------------------------------------------------
        search_resp = self.search_provider.search(image_path, run_dir=run_dir)
        if not search_resp.candidates:
            raise PipelineError(
                "Reverse image search returned 0 matching candidates for the input face image.",
                code="NO_SEARCH_MATCHES",
            )
        report_step(3, "Reverse image search")

        # -------------------------------------------------------------
        # Step 4: Validate candidates & select evidence
        # -------------------------------------------------------------
        selected: SelectedEvidence | None = self.social_validator.validate_and_select(
            candidates=search_resp.candidates,
            run_dir=run_dir,
        )
        if not selected:
            raise PipelineError(
                "None of the discovered reverse-image candidates passed validation.",
                code="NO_VALID_CANDIDATE",
            )
        report_step(4, "Candidate validation")

        # -------------------------------------------------------------
        # Step 5: Canonicalize evidence
        # -------------------------------------------------------------
        evidence_dict = build_evidence(
            source_url=selected.source_url,
            final_url=selected.final_url,
            search_provider=search_resp.provider,
            match_type=selected.match_type,
            title=selected.title,
            image_sha256=face_result.crop_sha256,
        )
        (run_dir / "evidence.json").write_text(
            canonical_json_str(evidence_dict),
            encoding="utf-8",
        )
        report_step(5, "Evidence canonicalization")

        # -------------------------------------------------------------
        # Step 6: SHA-256 fingerprint
        # -------------------------------------------------------------
        fingerprint_hex = evidence_hash_hex(evidence_dict)
        fingerprint_b32 = evidence_hash_bytes32(evidence_dict)
        (run_dir / "evidence_hash.txt").write_text(fingerprint_hex + "\n", encoding="utf-8")
        report_step(6, "SHA-256 fingerprint")

        # -------------------------------------------------------------
        # Step 7: Blockchain anchoring
        # -------------------------------------------------------------
        receipt = self.blockchain_client.anchor_evidence(
            evidence_hash_bytes=fingerprint_b32,
            source_url=selected.final_url or selected.source_url,
            search_provider=search_resp.provider,
            run_dir=run_dir,
        )
        evidence_id = receipt["evidence_id"]
        report_step(7, "Blockchain anchoring")

        # -------------------------------------------------------------
        # Step 8: On-chain re-verification
        # -------------------------------------------------------------
        is_verified = self.blockchain_client.verify_evidence(
            evidence_id=evidence_id,
            evidence_hash_bytes=fingerprint_b32,
        )
        if not is_verified:
            report_step(8, "Verification", status="MISMATCH")
            raise PipelineError(
                f"On-chain verification failed for newly anchored evidence ID {evidence_id}.",
                code="VERIFICATION_MISMATCH",
            )
        report_step(8, "Verification", status="PASS")

        return PipelineResult(
            run_id=run_id,
            run_dir=str(run_dir),
            face_result=face_result,
            search_provider=search_resp.provider,
            match_type=selected.match_type or "visual_match",
            selected_url=selected.final_url or selected.source_url,
            evidence_hash=fingerprint_hex,
            network=receipt.get("network", "sepolia"),
            contract_address=receipt.get("contract_address", ""),
            transaction_hash=receipt.get("transaction_hash", ""),
            evidence_id=evidence_id,
            is_verified=is_verified,
        )
