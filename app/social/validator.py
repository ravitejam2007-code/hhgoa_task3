"""
app.social.validator — candidate validation and scoring for web and social evidence.

Validates URLs, queries HTTP status within bounded limits, scores candidates
deterministically, and selects the highest-scoring candidate.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.search.base import SearchCandidate

logger = logging.getLogger(__name__)

RECOGNIZED_SOCIAL_DOMAINS = frozenset(
    {
        "instagram.com",
        "facebook.com",
        "x.com",
        "twitter.com",
        "tiktok.com",
        "linkedin.com",
    }
)


class SelectedEvidence(BaseModel):
    """Structured representation of the winning validated evidence candidate."""

    source_url: str
    final_url: str | None = None
    title: str | None = None
    source_domain: str
    match_type: str | None = None
    score: int = Field(default=0, ge=0)
    http_status: int | None = None


def extract_registered_domain(hostname: str) -> str:
    """
    Extract the main domain and TLD from hostname (e.g. www.instagram.com -> instagram.com).
    """
    parts = hostname.lower().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname.lower()


def is_recognized_social(hostname: str) -> bool:
    """Check if the hostname belongs to an allowed social platform."""
    reg = extract_registered_domain(hostname)
    return reg in RECOGNIZED_SOCIAL_DOMAINS


class SocialValidator:
    """
    Validates candidates found by reverse search, scores them deterministically,
    and returns the best candidate.
    """

    def __init__(self, timeout: float = 2.5, max_redirects: int = 5) -> None:
        self.timeout = timeout
        self.max_redirects = max_redirects

    def validate_url_syntax(self, url: str) -> tuple[bool, str]:
        """
        Check basic URL validity:
        - Must have http or https scheme
        - Must have a valid non-empty hostname with at least one dot (or localhost/ip)
        """
        if not url:
            return False, "URL is empty"
        try:
            parsed = urlparse(url)
            if parsed.scheme.lower() not in ("http", "https"):
                return False, f"Unsupported scheme '{parsed.scheme}' (must be http/https)"
            if not parsed.netloc:
                return False, "Missing hostname"
            hostname = parsed.netloc.split(":")[0].strip()
            if not hostname or "." not in hostname:
                return False, f"Invalid hostname '{hostname}'"
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def check_url_reachability(
        self,
        url: str,
        session: requests.Session | None = None,
    ) -> tuple[int | None, str]:
        """
        Bounded HTTP check to verify reachability and follow redirects.
        Returns (http_status, final_url).
        Uses HEAD first, falling back to GET with stream=True if HEAD fails.
        """
        http = session or requests.Session()
        http.max_redirects = self.max_redirects
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            # Try HEAD first (fast, minimal bandwidth)
            resp = http.head(
                url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
            )
            # Some platforms return 405 or 403 on HEAD but 200 on GET
            if resp.status_code in (403, 405):
                resp = http.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=True,
                )
            return resp.status_code, resp.url
        except requests.RequestException as exc:
            logger.warning("HTTP check failed for %s: %s", url, exc)
            return None, url

    def score_candidate(
        self,
        candidate: SearchCandidate,
        http_status: int | None,
        is_social: bool,
    ) -> int:
        """
        Calculate deterministic candidate score:
        +40: exact image match
        +30: recognized social domain
        +15: URL successfully resolves (HTTP 200–399)
        +10: useful non-empty title
        """
        score = 0
        match_type = (candidate.match_type or "").lower()
        if "exact" in match_type:
            score += 40
        elif "visual" in match_type:
            score += 20

        if is_social:
            score += 30

        if http_status is not None and 200 <= http_status < 400:
            score += 15

        if candidate.title and candidate.title.strip():
            score += 10

        return score

    def validate_and_select(
        self,
        candidates: list[SearchCandidate],
        run_dir: Path | None = None,
        session: requests.Session | None = None,
        check_http: bool = True,
        max_candidates_to_check: int = 10,
    ) -> SelectedEvidence | None:
        """
        Process candidates, score each valid one, and return the best.
        Optionally saves runs/<run_id>/selected_evidence.json if run_dir provided.
        """
        valid_candidates: list[tuple[SearchCandidate, str, str, bool]] = []

        for cand in candidates:
            valid_syntax, _ = self.validate_url_syntax(cand.url)
            if not valid_syntax:
                continue

            parsed = urlparse(cand.url)
            hostname = parsed.netloc.split(":")[0].lower()
            source_domain = extract_registered_domain(hostname)
            is_social = is_recognized_social(hostname)
            valid_candidates.append((cand, hostname, source_domain, is_social))

        if not valid_candidates:
            return None

        # Prioritize candidates: social domains first, exact matches next
        valid_candidates.sort(
            key=lambda item: (
                1 if item[3] else 0,  # is_social
                1 if "exact" in (item[0].match_type or "").lower() else 0,
                1 if item[0].title else 0,
            ),
            reverse=True,
        )

        evaluated: list[SelectedEvidence] = []
        candidates_to_evaluate = valid_candidates[:max_candidates_to_check]

        for cand, hostname, source_domain, is_social in candidates_to_evaluate:
            final_url = cand.url
            http_status = None

            if check_http:
                http_status, final_url = self.check_url_reachability(cand.url, session=session)
                # If HTTP explicitly returned a client error (e.g. 404, 410), do not select dead links
                if http_status in (404, 410):
                    continue

            score = self.score_candidate(cand, http_status=http_status, is_social=is_social)

            evidence = SelectedEvidence(
                source_url=cand.url,
                final_url=final_url,
                title=cand.title,
                source_domain=source_domain,
                match_type=cand.match_type,
                score=score,
                http_status=http_status,
            )
            evaluated.append(evidence)

        if not evaluated:
            # Fallback if top candidates were 404: evaluate next candidates
            for cand, hostname, source_domain, is_social in valid_candidates[max_candidates_to_check:max_candidates_to_check * 2]:
                score = self.score_candidate(cand, http_status=None, is_social=is_social)
                evaluated.append(
                    SelectedEvidence(
                        source_url=cand.url,
                        final_url=cand.url,
                        title=cand.title,
                        source_domain=source_domain,
                        match_type=cand.match_type,
                        score=score,
                        http_status=None,
                    )
                )

        if not evaluated:
            return None

        # Sort highest score first. For tie-breaking, prefer recognized social domain, then title length
        evaluated.sort(
            key=lambda e: (
                e.score,
                1 if is_recognized_social(e.source_domain) else 0,
                len(e.title or ""),
            ),
            reverse=True,
        )

        best = evaluated[0]

        if run_dir:
            run_dir.mkdir(parents=True, exist_ok=True)
            out_file = run_dir / "selected_evidence.json"
            out_file.write_text(best.model_dump_json(indent=2), encoding="utf-8")

        return best
