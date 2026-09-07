"""
app.evidence — evidence structuring, canonicalization, and SHA-256 fingerprinting.
"""

from app.evidence.canonicalize import (
    PIPELINE_VERSION,
    SCHEMA_VERSION,
    build_evidence,
    canonical_json_bytes,
    canonical_json_str,
    normalize_url,
)
from app.evidence.fingerprint import (
    evidence_hash,
    evidence_hash_bytes32,
    evidence_hash_hex,
)

__all__ = [
    "SCHEMA_VERSION",
    "PIPELINE_VERSION",
    "normalize_url",
    "build_evidence",
    "canonical_json_str",
    "canonical_json_bytes",
    "evidence_hash",
    "evidence_hash_hex",
    "evidence_hash_bytes32",
]
