"""
tests/test_search_adapter.py — unit tests for SerpApi Google Lens search provider.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.search.serpapi_lens import GoogleLensProvider, SearchProviderError


def test_missing_api_key_raises_error(tmp_path: Path):
    """Verify that calling search with missing API key raises clear human-readable error."""
    provider = GoogleLensProvider(api_key="")
    dummy_img = tmp_path / "test.jpg"
    dummy_img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    with pytest.raises(SearchProviderError) as exc_info:
        provider.search(dummy_img, tmp_path)

    assert "SERPAPI_KEY is missing" in str(exc_info.value)
    assert exc_info.value.code == "MISSING_API_KEY"


def test_nonexistent_image_raises_error(tmp_path: Path):
    """Verify that non-existent image file raises error."""
    provider = GoogleLensProvider(api_key="mock_key")
    missing_path = tmp_path / "nonexistent.jpg"

    with pytest.raises(SearchProviderError) as exc_info:
        provider.search(missing_path, tmp_path)

    assert exc_info.value.code == "IMAGE_NOT_FOUND"


def test_unsupported_image_extension_raises_error(tmp_path: Path):
    """Verify that unsupported image extension raises error."""
    provider = GoogleLensProvider(api_key="mock_key")
    bad_file = tmp_path / "image.gif"
    bad_file.write_bytes(b"GIF89a" + b"\x00" * 50)

    with pytest.raises(SearchProviderError) as exc_info:
        provider.search(bad_file, tmp_path)

    assert exc_info.value.code == "UNSUPPORTED_IMAGE_FORMAT"


def test_parse_candidates_exact_and_visual_matches():
    """Verify parsing of exact_matches and visual_matches into SearchCandidate models."""
    provider = GoogleLensProvider(api_key="mock_key")

    mock_lens_json = {
        "exact_matches": [
            {
                "title": "Exact Instagram Portrait",
                "link": "https://www.instagram.com/p/exact123",
                "source": "Instagram",
                "thumbnail": "https://thumb.url/1.jpg",
            }
        ],
        "visual_matches": [
            {
                "title": "Similar Looking Face on Facebook",
                "link": "https://facebook.com/photo/visual456",
                "source": "Facebook",
                "thumbnail": "https://thumb.url/2.jpg",
            }
        ],
    }

    candidates = provider._parse_candidates(mock_lens_json)
    assert len(candidates) == 2

    c1 = candidates[0]
    assert c1.match_type == "exact_match"
    assert c1.url == "https://www.instagram.com/p/exact123"
    assert c1.title == "Exact Instagram Portrait"

    c2 = candidates[1]
    assert c2.match_type == "visual_match"
    assert c2.url == "https://facebook.com/photo/visual456"


def test_mocked_full_search_flow(tmp_path: Path):
    """Verify end-to-end search adapter flow with mocked HTTP session."""
    dummy_img = tmp_path / "portrait.png"
    dummy_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    mock_session = MagicMock()

    # Mock upload response
    mock_upload_resp = MagicMock()
    mock_upload_resp.ok = True
    mock_upload_resp.status_code = 200
    mock_upload_resp.json.return_value = {"image_id": "img_mock_12345"}

    # Mock search response
    mock_search_resp = MagicMock()
    mock_search_resp.ok = True
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {
        "visual_matches": [
            {
                "title": "Social Profile",
                "link": "https://x.com/person/photo",
                "source": "X",
            }
        ]
    }

    mock_session.post.return_value = mock_upload_resp
    mock_session.get.return_value = mock_search_resp

    provider = GoogleLensProvider(api_key="valid_test_key", session=mock_session)
    response = provider.search(dummy_img, tmp_path)

    assert response.provider == "serpapi_google_lens"
    assert len(response.candidates) == 1
    assert response.candidates[0].url == "https://x.com/person/photo"

    # Verify search_response.json was written and api_key was scrubbed
    raw_path = tmp_path / "search_response.json"
    assert raw_path.exists()
    content = raw_path.read_text(encoding="utf-8")
    assert "valid_test_key" not in content


def test_malformed_json_handling(tmp_path: Path):
    """Verify that malformed JSON response raises appropriate SearchProviderError."""
    dummy_img = tmp_path / "portrait.jpg"
    dummy_img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    mock_session = MagicMock()
    mock_upload_resp = MagicMock()
    mock_upload_resp.ok = True
    mock_upload_resp.status_code = 200
    mock_upload_resp.json.side_effect = ValueError("Invalid JSON")
    mock_upload_resp.text = "<html>502 Bad Gateway</html>"
    mock_session.post.return_value = mock_upload_resp

    provider = GoogleLensProvider(api_key="valid_key", session=mock_session)

    with pytest.raises(SearchProviderError) as exc_info:
        provider.search(dummy_img, tmp_path)

    assert exc_info.value.code == "MALFORMED_UPLOAD_JSON"
