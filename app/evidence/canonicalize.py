"""
app.evidence.canonicalize — deterministic evidence structuring and canonicalization.

Constructs canonical evidence dictionaries and serialises them deterministically
into UTF-8 bytes for cryptographic fingerprinting.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

SCHEMA_VERSION = "1.0"
PIPELINE_VERSION = "1.0.0"


def normalize_url(url: str) -> str:
    """
    Deterministically normalize a URL.
    - Lowers scheme and hostname.
    - Removes fragments.
    - Sorts query parameters deterministically.
    - Normalizes empty path to '/' if query/scheme present, but preserves specific paths.
    - Removes default ports (80 for http, 443 for https).
    """
    if not url:
        return ""

    parsed = urlparse(url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed.path
    if not path and (netloc or parsed.query):
        path = "/"
    elif len(path) > 1 and path.endswith("/"):
        # Normalize trailing slash for non-root paths (strip trailing slash)
        path = path.rstrip("/")

    # Sort query parameters stably
    query_params = parse_qsl(parsed.query, keep_blank_values=True)
    query_params.sort(key=lambda item: (item[0], item[1]))
    normalized_query = urlencode(query_params)

    # Fragment is strictly removed
    normalized = urlunparse((scheme, netloc, path, parsed.params, normalized_query, ""))
    return normalized


def build_evidence(
    source_url: str,
    final_url: str | None,
    search_provider: str,
    match_type: str | None,
    title: str | None,
    image_sha256: str,
    discovered_at_utc: str | None = None,
    schema_version: str = SCHEMA_VERSION,
    pipeline_version: str = PIPELINE_VERSION,
) -> dict:
    """
    Construct a deterministic evidence dictionary according to the official schema.
    If discovered_at_utc is omitted, the current UTC time is used.
    When verifying existing evidence, pass the existing discovered_at_utc.
    """
    if discovered_at_utc is None:
        discovered_at_utc = datetime.now(timezone.utc).isoformat()

    norm_source = normalize_url(source_url)
    norm_final = normalize_url(final_url) if final_url else norm_source

    evidence = {
        "schema_version": schema_version,
        "source_url": norm_source,
        "final_url": norm_final,
        "search_provider": search_provider,
        "match_type": match_type or "unknown",
        "title": (title or "").strip(),
        "image_sha256": image_sha256.lower().strip(),
        "discovered_at_utc": discovered_at_utc,
        "pipeline_version": pipeline_version,
    }
    return evidence


def canonical_json_str(data: dict) -> str:
    """
    Serialize dictionary into deterministic JSON string.
    Keys are sorted, separators are compact (",", ":"), and ensure_ascii is False.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json_bytes(data: dict) -> bytes:
    """Serialize dictionary into deterministic UTF-8 bytes."""
    return canonical_json_str(data).encode("utf-8")
