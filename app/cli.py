"""
app.cli — command-line interface for the face-blockchain-verifier pipeline.

Commands:
    python -m app.cli face   --image samples/test.jpg
    python -m app.cli run    --image samples/test.jpg
    python -m app.cli verify --evidence-id 1 --run ./runs/<run_id>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Graceful fallback to load .env using standard library if python-dotenv is not installed
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Configure root logger to warning by default so raw logs don't clutter CLI output
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def cmd_face(args: argparse.Namespace) -> int:
    """
    Execute Phase 1: local face detection + embedding.
    """
    from app.config import Settings
    from app.face.engine import FaceEngine
    from app.face.preprocess import validate_image
    from app.models import FaceError, ImageValidationError

    project_root = Path(__file__).parent.parent
    yunet = project_root / "models" / "face_detection_yunet_2023mar.onnx"
    sface = project_root / "models" / "face_recognition_sface_2021dec.onnx"

    image_path = Path(args.image)

    try:
        settings = Settings(yunet_model=yunet, sface_model=sface)
        engine = FaceEngine(settings=settings)

        validate_image(image_path, settings)
        print("[1/4] Image accepted")

        result = engine.process(image_path)
        print(f"[2/4] Face detected  ({result.face_count} face(s) found, largest selected)")
        print(f"[3/4] Embedding generated  (model={result.embedding_model}, dim={result.embedding_dim})")
        print("[4/4] Face pipeline complete")
        print()
        print(json.dumps(result.model_dump(), indent=2))
        return 0

    except ImageValidationError as exc:
        print(f"\n[ERROR] {exc.code}: {exc}", file=sys.stderr)
        return 1
    except FaceError as exc:
        print(f"\n[ERROR] {exc.code}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """
    Execute complete 8-stage pipeline:
    Image -> Face -> Reverse Search -> Validate -> Canonicalize -> Hash -> Blockchain -> Verify
    """
    from app.config import Settings
    from app.pipeline import Pipeline
    from app.models import PipelineError

    project_root = Path(__file__).parent.parent
    yunet = project_root / "models" / "face_detection_yunet_2023mar.onnx"
    sface = project_root / "models" / "face_recognition_sface_2021dec.onnx"

    image_path = Path(args.image)
    settings = Settings(yunet_model=yunet, sface_model=sface)

    print("========================================")
    print("HH Goa 2026 - Task 3")
    print("Face Identification & Blockchain Verification")
    print("========================================")
    print()

    stages = [
        "Face detection",
        "Face encoding",
        "Reverse image search",
        "Candidate validation",
        "Evidence canonicalization",
        "SHA-256 fingerprint",
        "Blockchain anchoring",
        "Verification",
    ]

    def on_progress(step_num: int, name: str, status: str = "PASS"):
        dots = "." * max(2, 28 - len(name))
        print(f"[{step_num}/8] {name}{dots} {status}", flush=True)

    try:
        pipeline = Pipeline(settings=settings)
        result = pipeline.run(image_path=image_path, progress_callback=on_progress)

        print()
        print("Face detected: YES")
        print(f"Search provider: {result.search_provider}")
        print(f"Match type: {result.match_type}")
        print(f"Selected URL: {result.selected_url}")
        print()
        print("Evidence SHA-256:")
        print(result.evidence_hash)
        print()
        print(f"Network: {result.network.capitalize()}")
        print("Contract:")
        print(result.contract_address)
        print()
        print("Transaction:")
        print(result.transaction_hash)
        print()
        print("Evidence ID:")
        print(result.evidence_id)
        print()
        print("Verification:")
        print("VERIFIED" if result.is_verified else "MISMATCH")
        print()
        print("Run directory:")
        print(result.run_dir)
        return 0

    except PipelineError as exc:
        print(f"\n[ERROR] {exc.code}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        return 1


def cmd_verify(args: argparse.Namespace) -> int:
    """
    Execute standalone verification:
    Loads evidence.json from the run directory, recomputes canonical SHA-256,
    fetches on-chain record, and proves whether the evidence is unchanged.
    """
    from app.blockchain.client import BlockchainClient
    from app.evidence.canonicalize import canonical_json_bytes
    from app.evidence.fingerprint import evidence_hash_hex, evidence_hash_bytes32

    run_dir = Path(args.run)
    evidence_path = run_dir / "evidence.json"

    if not evidence_path.exists():
        print(f"ERROR: Evidence file not found at '{evidence_path}'.", file=sys.stderr)
        return 1

    try:
        raw_text = evidence_path.read_text(encoding="utf-8")
        evidence_dict = json.loads(raw_text)
    except Exception as exc:
        print(f"ERROR: Failed to read or parse evidence.json: {exc}", file=sys.stderr)
        return 1

    # Recompute local canonical SHA-256
    local_hash_hex = evidence_hash_hex(evidence_dict)
    local_hash_b32 = evidence_hash_bytes32(evidence_dict)

    client = BlockchainClient()
    try:
        on_chain_record = client.read_evidence(evidence_id=args.evidence_id)
    except Exception as exc:
        print(f"ERROR: Could not fetch record from blockchain: {exc}", file=sys.stderr)
        return 1

    # On-chain hash is hex string (or bytes)
    on_chain_hex = on_chain_record["evidence_hash"]
    if on_chain_hex.startswith("0x"):
        on_chain_hex = on_chain_hex[2:]
    on_chain_hex = on_chain_hex.lower()

    # Call on-chain contract verifyEvidence for direct cryptographic proof
    try:
        contract_verified = client.verify_evidence(args.evidence_id, local_hash_b32)
    except Exception:
        contract_verified = (local_hash_hex == on_chain_hex)

    is_verified = contract_verified and (local_hash_hex == on_chain_hex)

    print(f"Evidence ID: {args.evidence_id}")
    print(f"Local hash:  {local_hash_hex}")
    print(f"On-chain:    {on_chain_hex}")
    print()
    if is_verified:
        print("Result: VERIFIED")
        return 0
    else:
        print("Result: MISMATCH")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Face Identification & Blockchain Verification — HH Goa 2026",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- face ----
    face_parser = subparsers.add_parser(
        "face",
        help="Run Phase 1: local face detection and embedding only.",
    )
    face_parser.add_argument(
        "--image",
        required=True,
        metavar="PATH",
        help="Path to the input JPEG, PNG, or WebP image.",
    )
    face_parser.set_defaults(func=cmd_face)

    # ---- run ----
    run_parser = subparsers.add_parser(
        "run",
        help="Run the complete 8-stage identification and blockchain verification pipeline.",
    )
    run_parser.add_argument(
        "--image",
        required=True,
        metavar="PATH",
        help="Path to the input face image.",
    )
    run_parser.set_defaults(func=cmd_run)

    # ---- verify ----
    verify_parser = subparsers.add_parser(
        "verify",
        help="Recompute canonical fingerprint from local evidence and verify against on-chain record.",
    )
    verify_parser.add_argument(
        "--evidence-id",
        type=int,
        required=True,
        metavar="ID",
        help="Numeric evidence ID on the blockchain.",
    )
    verify_parser.add_argument(
        "--run",
        required=True,
        metavar="PATH",
        help="Path to the run directory containing evidence.json (e.g. ./runs/<run_id>).",
    )
    verify_parser.set_defaults(func=cmd_verify)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
