"""
tests/test_canonicalization.py — unit tests for deterministic evidence canonicalization.
"""

from __future__ import annotations

import json
from app.evidence.canonicalize import (
    build_evidence,
    canonical_json_bytes,
    canonical_json_str,
    normalize_url,
)
from app.evidence.fingerprint import evidence_hash, evidence_hash_hex


def test_url_canonicalization_rules():
    """Test URL normalization: casing, fragment removal, query parameter sorting, trailing slashes."""
    # Scheme and netloc lowering
    assert normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"

    # Default port stripping
    assert normalize_url("http://example.com:80/feed") == "http://example.com/feed"
    assert normalize_url("https://example.com:443/feed") == "https://example.com/feed"

    # Fragment removal
    assert normalize_url("https://instagram.com/p/123#comments") == "https://instagram.com/p/123"

    # Trailing slash normalization on non-root paths
    assert normalize_url("https://x.com/user/status/1/") == "https://x.com/user/status/1"

    # Deterministic query sorting
    assert (
        normalize_url("https://example.com/search?b=2&a=1&c=3")
        == "https://example.com/search?a=1&b=2&c=3"
    )


def test_a_dict_key_order_does_not_change_hash():
    """Test A: Dictionary key order does not change the resulting hash."""
    fixed_time = "2026-09-07T12:00:00+00:00"
    base_evidence = build_evidence(
        source_url="https://instagram.com/p/test123",
        final_url="https://instagram.com/p/test123",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="Sample User Portrait",
        image_sha256="a" * 64,
        discovered_at_utc=fixed_time,
    )

    # Construct two dictionaries with intentionally different insertion order
    keys = list(base_evidence.keys())
    reversed_keys = list(reversed(keys))

    dict_a = {k: base_evidence[k] for k in keys}
    dict_b = {k: base_evidence[k] for k in reversed_keys}

    assert evidence_hash_hex(dict_a) == evidence_hash_hex(dict_b)
    assert evidence_hash(dict_a) == evidence_hash(dict_b)


def test_b_equivalent_evidence_produces_identical_canonical_json():
    """Test B: Equivalent evidence produces identical canonical JSON bytes."""
    fixed_time = "2026-09-07T12:00:00+00:00"

    ev1 = build_evidence(
        source_url="https://INSTAGRAM.COM/p/test123#ref",
        final_url="https://instagram.com/p/test123/",
        search_provider="serpapi_google_lens",
        match_type="visual_match",
        title="Title Test",
        image_sha256="B" * 64,
        discovered_at_utc=fixed_time,
    )

    ev2 = build_evidence(
        source_url="https://instagram.com/p/test123",
        final_url="https://instagram.com/p/test123",
        search_provider="serpapi_google_lens",
        match_type="visual_match",
        title="Title Test",
        image_sha256="b" * 64,  # casing normalized
        discovered_at_utc=fixed_time,
    )

    bytes1 = canonical_json_bytes(ev1)
    bytes2 = canonical_json_bytes(ev2)

    assert bytes1 == bytes2
    assert evidence_hash_hex(ev1) == evidence_hash_hex(ev2)


def test_c_fragment_normalization_behaves_deterministically():
    """Test C: Fragment normalization behaves deterministically across different fragments."""
    fixed_time = "2026-09-07T12:00:00+00:00"

    ev_with_frag1 = build_evidence(
        source_url="https://x.com/profile/status/999#header",
        final_url=None,
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="X Post",
        image_sha256="c" * 64,
        discovered_at_utc=fixed_time,
    )

    ev_with_frag2 = build_evidence(
        source_url="https://x.com/profile/status/999#footer",
        final_url=None,
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="X Post",
        image_sha256="c" * 64,
        discovered_at_utc=fixed_time,
    )

    assert canonical_json_bytes(ev_with_frag1) == canonical_json_bytes(ev_with_frag2)
    assert evidence_hash_hex(ev_with_frag1) == evidence_hash_hex(ev_with_frag2)


def test_d_modifying_field_changes_fingerprint():
    """Test D: Adding or modifying a meaningful evidence field changes the fingerprint."""
    fixed_time = "2026-09-07T12:00:00+00:00"

    original = build_evidence(
        source_url="https://tiktok.com/@user/video/1",
        final_url="https://tiktok.com/@user/video/1",
        search_provider="serpapi_google_lens",
        match_type="exact_match",
        title="TikTok Original",
        image_sha256="d" * 64,
        discovered_at_utc=fixed_time,
    )

    # Modify title
    modified_title = dict(original)
    modified_title["title"] = "TikTok Tampered"

    # Modify match_type
    modified_match = dict(original)
    modified_match["match_type"] = "visual_match"

    # Modify image_sha256
    modified_image = dict(original)
    modified_image["image_sha256"] = "e" * 64

    orig_hash = evidence_hash_hex(original)
    assert orig_hash != evidence_hash_hex(modified_title)
    assert orig_hash != evidence_hash_hex(modified_match)
    assert orig_hash != evidence_hash_hex(modified_image)
