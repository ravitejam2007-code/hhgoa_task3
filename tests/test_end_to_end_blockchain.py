"""
tests/test_end_to_end_blockchain.py — full end-to-end test against a running Hardhat node.
Tests pipeline anchoring, verification, and tamper detection.
"""

import json
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.blockchain.client import BlockchainClient
from app.evidence.canonicalize import build_evidence, canonical_json_str
from app.evidence.fingerprint import evidence_hash_bytes32, evidence_hash_hex
from app.face.engine import FaceEngine
from app.models import FaceResult
from app.search.base import SearchCandidate, SearchResponse
from app.search.serpapi_lens import GoogleLensProvider
from app.social.validator import SocialValidator
from app.pipeline import Pipeline


from web3 import Web3


def _is_local_node_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8545), timeout=0.3):
            return True
    except OSError:
        return False


_NODE_REASON = "Local Hardhat node is not running on port 8545 (start with 'npm run dev')"


@pytest.fixture
def deployed_contract():
    """Deploy a fresh EvidenceRegistry instance to the local node for the test."""
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    artifact_path = Path(__file__).parent.parent / "artifacts" / "contracts" / "EvidenceRegistry.sol" / "EvidenceRegistry.json"
    with open(artifact_path, encoding="utf-8") as f:
        art = json.load(f)

    factory = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
    acct = w3.eth.accounts[0]
    tx_hash = factory.constructor().transact({"from": acct})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.contractAddress


@pytest.mark.skipif(not _is_local_node_running(), reason=_NODE_REASON)
def test_blockchain_client_local_anchor_and_verify(tmp_path: Path, deployed_contract: str):
    """Test anchoring to local Hardhat node and verifying on-chain."""
    client = BlockchainClient(
        rpc_url="http://127.0.0.1:8545",
        private_key="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        contract_address=deployed_contract,
    )

    sample_evidence = build_evidence(
        source_url="https://www.instagram.com/p/portrait_sample",
        final_url="https://www.instagram.com/p/portrait_sample",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="Sample Verified Portrait",
        image_sha256="f" * 64,
        discovered_at_utc="2026-09-07T15:00:00+00:00",
    )

    h_bytes32 = evidence_hash_bytes32(sample_evidence)
    h_hex = evidence_hash_hex(sample_evidence)

    receipt = client.anchor_evidence(
        evidence_hash_bytes=h_bytes32,
        source_url=sample_evidence["source_url"],
        search_provider=sample_evidence["search_provider"],
        run_dir=tmp_path,
    )

    evidence_id = receipt["evidence_id"]
    assert evidence_id >= 1
    assert receipt["status"] == 1

    # Verify matching hash returns True
    assert client.verify_evidence(evidence_id, h_bytes32) is True

    # Verify mismatched hash returns False
    mismatched_bytes = b"\x00" * 32
    assert client.verify_evidence(evidence_id, mismatched_bytes) is False

    # Read back record
    record = client.read_evidence(evidence_id)
    assert record["evidence_id"] == evidence_id
    assert record["source_url"] == sample_evidence["source_url"]
    assert record["search_provider"] == "serpapi_google_lens"


@pytest.mark.skipif(not _is_local_node_running(), reason=_NODE_REASON)
def test_cli_verify_match_and_mismatch(tmp_path: Path, monkeypatch, deployed_contract: str):
    """Test CLI verify subcommand with local Hardhat contract: VERIFIED -> MISMATCH -> VERIFIED."""
    # Set environment variables for the CLI to use local Hardhat
    monkeypatch.setenv("SEPOLIA_RPC_URL", "http://127.0.0.1:8545")
    monkeypatch.setenv(
        "WALLET_PRIVATE_KEY",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    )
    monkeypatch.setenv("CONTRACT_ADDRESS", deployed_contract)

    client = BlockchainClient(
        rpc_url="http://127.0.0.1:8545",
        private_key="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        contract_address=deployed_contract,
    )

    run_dir = tmp_path / "run_demo"
    run_dir.mkdir(parents=True, exist_ok=True)

    evidence = build_evidence(
        source_url="https://x.com/verified_profile/status/100",
        final_url="https://x.com/verified_profile/status/100",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="Authentic Post",
        image_sha256="7" * 64,
        discovered_at_utc="2026-09-07T16:00:00+00:00",
    )

    # Write evidence.json
    orig_json = canonical_json_str(evidence)
    evidence_file = run_dir / "evidence.json"
    evidence_file.write_text(orig_json, encoding="utf-8")

    # Anchor to contract
    h_bytes32 = evidence_hash_bytes32(evidence)
    receipt = client.anchor_evidence(
        evidence_hash_bytes=h_bytes32,
        source_url=evidence["source_url"],
        search_provider=evidence["search_provider"],
        run_dir=run_dir,
    )
    evidence_id = receipt["evidence_id"]

    # 1. Run CLI verify on original evidence -> should return 0 (VERIFIED)
    from app.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["verify", "--evidence-id", str(evidence_id), "--run", str(run_dir)])
    exit_code = args.func(args)
    assert exit_code == 0

    # 2. Tamper with evidence.json -> should return 1 (MISMATCH)
    tampered = dict(evidence)
    tampered["title"] = "Tampered Title"
    evidence_file.write_text(canonical_json_str(tampered), encoding="utf-8")

    exit_code = args.func(args)
    assert exit_code == 1

    # 3. Restore original evidence.json -> should return 0 (VERIFIED)
    evidence_file.write_text(orig_json, encoding="utf-8")
    exit_code = args.func(args)
    assert exit_code == 0


@pytest.mark.skipif(not _is_local_node_running(), reason=_NODE_REASON)
def test_full_pipeline_run_with_local_chain(tmp_path: Path, deployed_contract: str):
    """Test full 8-stage pipeline run using real face detection and local Hardhat anchoring."""
    from app.config import Settings
    project_root = Path(__file__).parent.parent
    yunet = project_root / "models" / "face_detection_yunet_2023mar.onnx"
    sface = project_root / "models" / "face_recognition_sface_2021dec.onnx"

    settings = Settings(
        run_dir=tmp_path / "runs",
        yunet_model=yunet,
        sface_model=sface,
    )

    # Mock reverse search provider that returns genuine candidate
    mock_search = MagicMock(spec=GoogleLensProvider)
    mock_search.search.return_value = SearchResponse(
        provider="serpapi_google_lens",
        candidates=[
            SearchCandidate(
                title="Barack Obama Presidential Photo",
                url="https://www.facebook.com/barackobama/photos/101",
                source="Facebook",
                match_type="exact_match",
            )
        ],
    )

    # Mock social validator session to resolve 200 without live network call
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://www.facebook.com/barackobama/photos/101"
    mock_session.head.return_value = mock_resp
    validator = SocialValidator()

    client = BlockchainClient(
        rpc_url="http://127.0.0.1:8545",
        private_key="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        contract_address=deployed_contract,
    )

    pipeline = Pipeline(
        settings=settings,
        search_provider=mock_search,
        social_validator=validator,
        blockchain_client=client,
    )

    test_img = Path("samples/test.jpg")
    result = pipeline.run(test_img)

    assert result.is_verified is True
    assert result.evidence_id >= 1
    assert result.match_type == "exact_match"
    assert "facebook.com" in result.selected_url

    # Check that all artifacts were created in run_dir
    run_dir = Path(result.run_dir)
    assert (run_dir / "input_metadata.json").exists()
    assert (run_dir / "face_result.json").exists()
    assert (run_dir / "selected_evidence.json").exists()
    assert (run_dir / "evidence.json").exists()
    assert (run_dir / "evidence_hash.txt").exists()
    assert (run_dir / "blockchain_receipt.json").exists()

