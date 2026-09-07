"""
tests/test_social_validation.py — unit tests for candidate validation and scoring.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.search.base import SearchCandidate
from app.social.validator import (
    RECOGNIZED_SOCIAL_DOMAINS,
    SocialValidator,
    is_recognized_social,
)


def test_recognized_social_domains():
    """Verify all required social domains are properly identified."""
    assert is_recognized_social("instagram.com")
    assert is_recognized_social("www.instagram.com")
    assert is_recognized_social("facebook.com")
    assert is_recognized_social("m.facebook.com")
    assert is_recognized_social("x.com")
    assert is_recognized_social("twitter.com")
    assert is_recognized_social("tiktok.com")
    assert is_recognized_social("linkedin.com")
    assert is_recognized_social("in.linkedin.com")

    assert not is_recognized_social("example.com")
    assert not is_recognized_social("news.google.com")
    assert not is_recognized_social("evil-instagram.com.attacker.org")


def test_url_syntax_validation():
    """Verify URL syntax validation rejects invalid schemes, hosts, or empty strings."""
    validator = SocialValidator()

    # Valid
    ok, _ = validator.validate_url_syntax("https://instagram.com/p/123")
    assert ok
    ok, _ = validator.validate_url_syntax("http://x.com/user")
    assert ok

    # Invalid schemes
    ok, _ = validator.validate_url_syntax("ftp://example.com/file")
    assert not ok
    ok, _ = validator.validate_url_syntax("javascript:alert(1)")
    assert not ok

    # Missing / invalid host
    ok, _ = validator.validate_url_syntax("http://")
    assert not ok
    ok, _ = validator.validate_url_syntax("http://nodotshere")
    assert not ok
    ok, _ = validator.validate_url_syntax("")
    assert not ok


def test_scoring_determinism():
    """Verify candidate scoring follows exact deterministic rules."""
    validator = SocialValidator()

    # Exact match (+40), social domain (+30), HTTP resolves (+15), useful title (+10) = 95
    exact_social = SearchCandidate(
        title="Valid Social Post",
        url="https://instagram.com/p/abc",
        match_type="exact_match",
    )
    score = validator.score_candidate(exact_social, http_status=200, is_social=True)
    assert score == 40 + 30 + 15 + 10  # 95

    # Visual match (+20), non-social (+0), HTTP resolves (+15), empty title (+0) = 35
    visual_web = SearchCandidate(
        title="",
        url="https://example.com/article",
        match_type="visual_match",
    )
    score2 = validator.score_candidate(visual_web, http_status=200, is_social=False)
    assert score2 == 20 + 0 + 15 + 0  # 35

    assert score > score2


def test_best_candidate_selected_with_mocked_http():
    """Verify that the highest scoring valid candidate is selected among multiple choices."""
    validator = SocialValidator()

    candidates = [
        SearchCandidate(
            title="Ordinary Web Match",
            url="https://newsblog.org/story/1",
            match_type="visual_match",
        ),
        SearchCandidate(
            title="Genuine Instagram Profile",
            url="https://www.instagram.com/user1",
            match_type="exact_match",
        ),
        SearchCandidate(
            title="Broken Link",
            url="https://invalid-schema",
            match_type="exact_match",
        ),
        SearchCandidate(
            title="TikTok Dance",
            url="https://tiktok.com/@user/v/1",
            match_type="visual_match",
        ),
    ]

    # Mock session returning 200 for valid domains
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://www.instagram.com/user1"
    mock_session.head.return_value = mock_resp

    best = validator.validate_and_select(
        candidates=candidates,
        session=mock_session,
        check_http=True,
    )

    assert best is not None
    assert "instagram.com" in best.source_domain
    assert best.match_type == "exact_match"
    assert best.score >= 95
