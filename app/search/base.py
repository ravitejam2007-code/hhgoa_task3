"""
app.search.base — abstract search provider interface and data models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel, Field


class SearchCandidate(BaseModel):
    """A single candidate search result discovered via reverse image search."""

    title: str | None = None
    url: str
    source: str | None = None
    match_type: str | None = None
    thumbnail: str | None = None
    raw: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Container for search results returned by a reverse image search provider."""

    provider: str
    candidates: list[SearchCandidate] = Field(default_factory=list)
    raw_response_path: str | None = None


class ReverseSearchProvider(ABC):
    """Abstract interface for reverse image search providers."""

    @abstractmethod
    def search(self, image_path: Path, run_dir: Path) -> SearchResponse:
        """
        Execute reverse image search for the given image.
        Results and raw response artifacts are stored in run_dir.
        """
        ...
