"""
tests/test_fingerprint.py — unit tests for cryptographic SHA-256 fingerprinting.
"""

from __future__ import annotations

import re
from app.evidence.canonicalize import build_evidence
from app.evidence.fingerprint import (
    evidence_hash,
    evidence_hash_bytes32,
    evidence_hash_hex,
)


def test_sha256_output_size_and_type():
    """Test SHA-256 raw digest is exactly 32 bytes."""
    evidence = build_evidence(
        source_url="https://linkedin.com/in/test",
        final_url="https://linkedin.com/in/test",
        search_provider="serpapi_google_lens",
        match_type="visual_match",
        title="Profile",
        image_sha256="1" * 64,
        discovered_at_utc="2026-09-07T12:00:00+00:00",
    )

    digest = evidence_hash(evidence)
    assert isinstance(digest, bytes)
    assert len(digest) == 32

    digest_b32 = evidence_hash_bytes32(evidence)
    assert isinstance(digest_b32, bytes)
    assert len(digest_b32) == 32
    assert digest == digest_b32


def test_hex_representation_format():
    """Test hex representation is exactly 64 lowercase hexadecimal characters."""
    evidence = build_evidence(
        source_url="https://facebook.com/profile/123",
        final_url="https://facebook.com/profile/123",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="FB Post",
        image_sha256="2" * 64,
        discovered_at_utc="2026-09-07T12:00:00+00:00",
    )

    hex_str = evidence_hash_hex(evidence)
    assert isinstance(hex_str, str)
    assert len(hex_str) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", hex_str) is not None
    assert hex_str == evidence_hash(evidence).hex()


def test_fingerprint_determinism():
    """Test identical evidence always produces the exact same digest."""
    fixed_time = "2026-09-07T14:30:00+00:00"
    ev1 = build_evidence(
        source_url="https://x.com/user/post",
        final_url="https://x.com/user/post",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="Post Title",
        image_sha256="3" * 64,
        discovered_at_utc=fixed_time,
    )
    ev2 = build_evidence(
        source_url="https://x.com/user/post",
        final_url="https://x.com/user/post",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="Post Title",
        image_sha256="3" * 64,
        discovered_at_utc=fixed_time,
    )

    assert evidence_hash_hex(ev1) == evidence_hash_hex(ev2)
    assert evidence_hash(ev1) == evidence_hash(ev2)


def test_modified_evidence_changes_digest():
    """Test that modifying any byte in the evidence produces a completely different digest."""
    fixed_time = "2026-09-07T14:30:00+00:00"
    base = build_evidence(
        source_url="https://x.com/user/post",
        final_url="https://x.com/user/post",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="Post Title",
        image_sha256="3" * 64,
        discovered_at_utc=fixed_time,
    )

    tampered = dict(base)
    tampered["source_url"] = "https://x.com/user/post_different"

    assert evidence_hash_hex(base) != evidence_hash_hex(tampered)
    assert evidence_hash(base) != evidence_hash(tampered)
