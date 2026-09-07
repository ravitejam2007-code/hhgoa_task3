"""
app.search.serpapi_lens — SerpApi Google Lens reverse image search implementation.

Performs genuine runtime reverse image search using SerpApi Google Lens API.
Never hardcodes search result URLs.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import requests
from PIL import Image

from app.search.base import ReverseSearchProvider, SearchCandidate, SearchResponse

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
SERPAPI_MAX_UPLOAD_BYTES = 500 * 1024  # 500 KB limit for SerpApi Image API


class SearchProviderError(Exception):
    """Raised when reverse search fails."""

    def __init__(self, message: str, code: str = "SEARCH_ERROR") -> None:
        super().__init__(message)
        self.code = code


def scrub_secrets(obj: Any, secret: str | None = None) -> Any:
    """Recursively remove API keys or secrets from serializable objects."""
    if not secret:
        return obj
    if isinstance(obj, str):
        return obj.replace(secret, "[REDACTED]")
    if isinstance(obj, dict):
        return {
            k: ("[REDACTED]" if "api_key" in k.lower() or "secret" in k.lower() else scrub_secrets(v, secret))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [scrub_secrets(v, secret) for v in obj]
    return obj


class GoogleLensProvider(ReverseSearchProvider):
    """
    Genuine reverse image search implementation via SerpApi Google Lens.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("SERPAPI_KEY", "").strip()
        self.timeout = timeout
        self.session = session or requests.Session()

    def _validate_and_prepare_image(self, image_path: Path, run_dir: Path) -> Path:
        """
        Validate image existence, readability, format, and size.
        If file exceeds 500KB, generate a compressed temporary copy in run_dir.
        """
        if not image_path.exists():
            raise SearchProviderError(
                f"Image file does not exist: {image_path}",
                code="IMAGE_NOT_FOUND",
            )
        if not image_path.is_file():
            raise SearchProviderError(
                f"Image path is not a file: {image_path}",
                code="INVALID_IMAGE_PATH",
            )

        ext = image_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise SearchProviderError(
                f"Unsupported image extension '{ext}'. Must be one of: {sorted(SUPPORTED_EXTENSIONS)}",
                code="UNSUPPORTED_IMAGE_FORMAT",
            )

        try:
            file_size = image_path.stat().st_size
        except OSError as exc:
            raise SearchProviderError(
                f"Could not read image metadata: {exc}",
                code="FILE_READ_ERROR",
            )

        # If file is within size limits, return original path
        if file_size <= SERPAPI_MAX_UPLOAD_BYTES:
            return image_path

        # Oversized image: compress to JPEG in run_dir without modifying original
        logger.info("Image size (%d bytes) exceeds 500KB limit; compressing for upload...", file_size)
        run_dir.mkdir(parents=True, exist_ok=True)
        compressed_path = run_dir / f"compressed_{image_path.stem}.jpg"
        try:
            with Image.open(image_path) as img:
                rgb_img = img.convert("RGB")
                max_dim = 1000
                quality = 85
                while True:
                    copy_img = rgb_img.copy()
                    copy_img.thumbnail((max_dim, max_dim))
                    copy_img.save(compressed_path, format="JPEG", quality=quality, optimize=True)
                    if compressed_path.stat().st_size <= SERPAPI_MAX_UPLOAD_BYTES or (max_dim <= 300 and quality <= 40):
                        break
                    max_dim = int(max_dim * 0.8)
                    quality = max(40, quality - 10)
            return compressed_path
        except Exception as exc:
            raise SearchProviderError(
                f"Failed to compress oversized image: {exc}",
                code="IMAGE_COMPRESSION_ERROR",
            )

    def _upload_image(self, prepared_image_path: Path) -> str:
        """
        Upload image to SerpApi Image API to obtain image_id or public URL.
        """
        upload_url = "https://serpapi.com/image"
        headers = {"User-Agent": "HHGoa-Task3-Lens/1.0"}

        try:
            with open(prepared_image_path, "rb") as f:
                # SerpApi /image endpoint expects multipart form with 'image'
                files = {"image": (prepared_image_path.name, f, "image/jpeg")}
                data = {"api_key": self.api_key}
                resp = self.session.post(
                    upload_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.timeout,
                )
        except requests.Timeout:
            raise SearchProviderError(
                f"Upload to SerpApi timed out after {self.timeout}s. Check internet connectivity.",
                code="UPLOAD_TIMEOUT",
            )
        except requests.RequestException as exc:
            raise SearchProviderError(
                f"Network failure while uploading image to SerpApi: {exc}",
                code="UPLOAD_NETWORK_ERROR",
            )

        if resp.status_code == 401 or resp.status_code == 403:
            raise SearchProviderError(
                "Invalid or unauthorized SERPAPI_KEY. Please verify your SerpApi API key.",
                code="AUTH_ERROR",
            )
        elif resp.status_code == 429:
            raise SearchProviderError(
                "SerpApi rate limit or monthly search quota exceeded.",
                code="QUOTA_EXCEEDED",
            )
        elif not resp.ok:
            raise SearchProviderError(
                f"SerpApi upload failed with HTTP status {resp.status_code}: {resp.text}",
                code="UPLOAD_HTTP_ERROR",
            )

        try:
            resp_json = resp.json()
        except ValueError:
            raise SearchProviderError(
                f"Malformed JSON response from SerpApi upload: {resp.text[:200]}",
                code="MALFORMED_UPLOAD_JSON",
            )

        image_id = resp_json.get("image_id") or resp_json.get("url")
        if not image_id:
            raise SearchProviderError(
                f"SerpApi upload succeeded but did not return 'image_id' or 'url': {resp_json}",
                code="MISSING_IMAGE_ID",
            )
        return str(image_id)

    def _query_google_lens(self, image_ref: str) -> dict:
        """
        Query SerpApi Google Lens engine using the uploaded image ID or URL.
        """
        search_url = "https://serpapi.com/search"
        params = {
            "engine": "google_lens",
            "api_key": self.api_key,
        }
        if image_ref.startswith("http://") or image_ref.startswith("https://"):
            params["url"] = image_ref
        else:
            params["image_id"] = image_ref

        try:
            resp = self.session.get(
                search_url,
                params=params,
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise SearchProviderError(
                f"SerpApi Google Lens query timed out after {self.timeout}s.",
                code="SEARCH_TIMEOUT",
            )
        except requests.RequestException as exc:
            raise SearchProviderError(
                f"Network failure during SerpApi Google Lens query: {exc}",
                code="SEARCH_NETWORK_ERROR",
            )

        if resp.status_code == 401 or resp.status_code == 403:
            raise SearchProviderError(
                "Invalid or unauthorized SERPAPI_KEY. Check your .env file.",
                code="AUTH_ERROR",
            )
        elif resp.status_code == 429:
            raise SearchProviderError(
                "SerpApi rate limit or monthly search quota exceeded.",
                code="QUOTA_EXCEEDED",
            )
        elif not resp.ok:
            raise SearchProviderError(
                f"Google Lens search failed with HTTP status {resp.status_code}: {resp.text}",
                code="SEARCH_HTTP_ERROR",
            )

        try:
            return resp.json()
        except ValueError:
            raise SearchProviderError(
                f"Malformed JSON returned by SerpApi Google Lens: {resp.text[:200]}",
                code="MALFORMED_SEARCH_JSON",
            )

    def _parse_candidates(self, response_data: dict) -> list[SearchCandidate]:
        """
        Extract search candidates, checking exact_matches first, then visual_matches.
        """
        candidates: list[SearchCandidate] = []

        # 1. Check exact matches
        exact_matches = response_data.get("exact_matches", [])
        if isinstance(exact_matches, list):
            for item in exact_matches:
                if isinstance(item, dict):
                    link = item.get("link") or item.get("url")
                    if link and isinstance(link, str):
                        candidates.append(
                            SearchCandidate(
                                title=item.get("title"),
                                url=link,
                                source=item.get("source"),
                                match_type="exact_match",
                                thumbnail=item.get("thumbnail"),
                                raw=item,
                            )
                        )

        # 2. Check visual matches
        visual_matches = response_data.get("visual_matches", [])
        if isinstance(visual_matches, list):
            for item in visual_matches:
                if isinstance(item, dict):
                    link = item.get("link") or item.get("url")
                    if link and isinstance(link, str):
                        candidates.append(
                            SearchCandidate(
                                title=item.get("title"),
                                url=link,
                                source=item.get("source"),
                                match_type="visual_match",
                                thumbnail=item.get("thumbnail"),
                                raw=item,
                            )
                        )

        return candidates

    def search(self, image_path: Path, run_dir: Path) -> SearchResponse:
        """
        Execute full SerpApi Google Lens reverse image search pipeline.
        """
        if not self.api_key:
            raise SearchProviderError(
                "ERROR: SERPAPI_KEY is missing.\n"
                "Add it to your .env file before running reverse image search.\n"
                "Sign up for a free key at https://serpapi.com",
                code="MISSING_API_KEY",
            )

        run_dir.mkdir(parents=True, exist_ok=True)
        prepared_image = self._validate_and_prepare_image(image_path, run_dir)

        # Upload image to SerpApi
        image_ref = self._upload_image(prepared_image)

        # Query Google Lens
        raw_response = self._query_google_lens(image_ref)

        # Scrub API key before persisting raw response
        scrubbed_response = scrub_secrets(raw_response, self.api_key)
        raw_response_path = run_dir / "search_response.json"
        raw_response_path.write_text(
            json.dumps(scrubbed_response, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        candidates = self._parse_candidates(raw_response)
        if not candidates:
            logger.warning("Google Lens search returned 0 matching candidates.")

        return SearchResponse(
            provider="serpapi_google_lens",
            candidates=candidates,
            raw_response_path=str(raw_response_path),
        )
