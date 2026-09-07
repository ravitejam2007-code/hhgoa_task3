"""
app.evidence.fingerprint — cryptographic SHA-256 fingerprinting of evidence.

Produces deterministic 32-byte digests and 64-character hexadecimal strings
from canonical evidence dictionaries.
"""

from __future__ import annotations

import hashlib
from app.evidence.canonicalize import canonical_json_bytes


def evidence_hash(evidence: dict) -> bytes:
    """
    Compute 32-byte SHA-256 digest of canonical evidence JSON.
    """
    canonical_bytes = canonical_json_bytes(evidence)
    return hashlib.sha256(canonical_bytes).digest()


def evidence_hash_hex(evidence: dict) -> str:
    """
    Compute 64-character lowercase hexadecimal SHA-256 digest.
    """
    return evidence_hash(evidence).hex().lower()


def evidence_hash_bytes32(evidence: dict) -> bytes:
    """
    Return the 32-byte digest explicitly formatted as bytes32 for blockchain contracts.
    """
    h = evidence_hash(evidence)
    if len(h) != 32:
        raise ValueError(f"Expected 32-byte hash, got {len(h)}")
    return h
