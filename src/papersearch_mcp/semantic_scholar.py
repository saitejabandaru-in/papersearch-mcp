"""Semantic Scholar API client for paper search and citation retrieval.

Uses the Semantic Scholar Academic Graph API (https://api.semanticscholar.org/)
to search for papers across multiple sources and retrieve citation graphs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx

# Semantic Scholar API base URL
S2_API_BASE = "https://api.semanticscholar.org/graph/v1"

# Default fields to request for paper objects
PAPER_FIELDS = ",".join([
    "paperId",
    "externalIds",
    "title",
    "abstract",
    "venue",
    "year",
    "referenceCount",
    "citationCount",
    "influentialCitationCount",
    "isOpenAccess",
    "openAccessPdf",
    "fieldsOfStudy",
    "authors",
    "publicationDate",
    "journal",
    "url",
])

# Citation/reference fields
CITATION_FIELDS = ",".join([
    "paperId",
    "title",
    "abstract",
    "venue",
    "year",
    "citationCount",
    "authors",
    "url",
    "externalIds",
    "isOpenAccess",
    "openAccessPdf",
])

# Rate limiting: S2 allows 100 requests per 5 minutes for unauthenticated
# We'll be conservative: ~1 request per 3 seconds
RATE_LIMIT_SECONDS = 3.0


@dataclass
class S2Author:
    """Represents an author from Semantic Scholar."""

    author_id: Optional[str]
    name: str

    def to_dict(self) -> dict:
        return {"author_id": self.author_id, "name": self.name}


@dataclass
class S2Paper:
    """Represents a paper from Semantic Scholar."""

    paper_id: str
    title: str
    abstract: Optional[str]
    authors: list[S2Author]
    year: Optional[int]
    venue: Optional[str]
    citation_count: int
    reference_count: int
    influential_citation_count: int
    is_open_access: bool
    open_access_pdf_url: Optional[str]
    fields_of_study: list[str]
    external_ids: dict[str, str]
    publication_date: Optional[str]
    url: Optional[str]
    journal: Optional[dict]

    def to_dict(self) -> dict:
        """Convert to a dictionary for JSON serialization."""
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": [a.to_dict() for a in self.authors],
            "year": self.year,
            "venue": self.venue,
            "citation_count": self.citation_count,
            "reference_count": self.reference_count,
            "influential_citation_count": self.influential_citation_count,
            "is_open_access": self.is_open_access,
            "open_access_pdf_url": self.open_access_pdf_url,
            "fields_of_study": self.fields_of_study,
            "external_ids": self.external_ids,
            "publication_date": self.publication_date,
            "url": self.url,
            "journal": self.journal,
        }


def _parse_author(data: dict) -> S2Author:
    """Parse an author dict into an S2Author."""
    return S2Author(
        author_id=data.get("authorId"),
        name=data.get("name", "Unknown"),
    )


def _parse_paper(data: dict) -> S2Paper:
    """Parse a paper dict from the S2 API into an S2Paper."""
    authors = [_parse_author(a) for a in (data.get("authors") or [])]

    # Extract open access PDF URL
    oa_pdf = data.get("openAccessPdf")
    oa_pdf_url = oa_pdf.get("url") if isinstance(oa_pdf, dict) else None

    # External IDs
    external_ids = data.get("externalIds") or {}
    # Convert all values to strings for consistency
    external_ids = {k: str(v) for k, v in external_ids.items() if v is not None}

    return S2Paper(
        paper_id=data.get("paperId", ""),
        title=data.get("title", ""),
        abstract=data.get("abstract"),
        authors=authors,
        year=data.get("year"),
        venue=data.get("venue"),
        citation_count=data.get("citationCount", 0),
        reference_count=data.get("referenceCount", 0),
        influential_citation_count=data.get("influentialCitationCount", 0),
        is_open_access=data.get("isOpenAccess", False),
        open_access_pdf_url=oa_pdf_url,
        fields_of_study=data.get("fieldsOfStudy") or [],
        external_ids=external_ids,
        publication_date=data.get("publicationDate"),
        url=data.get("url"),
        journal=data.get("journal"),
    )


async def search_semantic_scholar(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    fields_of_study: Optional[list[str]] = None,
    open_access_only: bool = False,
    min_citation_count: Optional[int] = None,
    api_key: Optional[str] = None,
) -> list[S2Paper]:
    """Search Semantic Scholar for papers.

    Args:
        query: Search query string.
        max_results: Maximum number of results (1-100).
        year: Year filter. Can be a single year ("2023"), a range ("2020-2023"),
            or open-ended ("2020-" or "-2023").
        fields_of_study: Filter by fields (e.g., ["Computer Science", "Medicine"]).
        open_access_only: If True, only return open-access papers.
        min_citation_count: Minimum citation count filter.
        api_key: Optional Semantic Scholar API key for higher rate limits.

    Returns:
        List of S2Paper objects matching the query.

    Raises:
        httpx.HTTPStatusError: If the API request fails.
    """
    max_results = max(1, min(100, max_results))

    params: dict[str, str] = {
        "query": query,
        "limit": str(max_results),
        "fields": PAPER_FIELDS,
    }

    if year:
        params["year"] = year
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)
    if open_access_only:
        params["openAccessPdf"] = ""
    if min_citation_count is not None:
        params["minCitationCount"] = str(min_citation_count)

    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{S2_API_BASE}/paper/search",
            params=params,
            headers=headers,
        )

        if response.status_code == 429:
            # Rate limited - wait and retry once
            retry_after = int(response.headers.get("Retry-After", "5"))
            await asyncio.sleep(retry_after)
            response = await client.get(
                f"{S2_API_BASE}/paper/search",
                params=params,
                headers=headers,
            )

        response.raise_for_status()

    result = response.json()
    papers_data = result.get("data", [])

    return [_parse_paper(p) for p in papers_data]


async def get_paper_details(
    paper_id: str,
    api_key: Optional[str] = None,
) -> Optional[S2Paper]:
    """Get detailed information about a specific paper.

    Args:
        paper_id: Semantic Scholar paper ID, arXiv ID (prefixed with "ARXIV:"),
            DOI (prefixed with "DOI:"), or other supported identifier.
        api_key: Optional API key.

    Returns:
        S2Paper if found, None otherwise.
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{S2_API_BASE}/paper/{paper_id}",
            params={"fields": PAPER_FIELDS},
            headers=headers,
        )

        if response.status_code == 404:
            return None
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "5"))
            await asyncio.sleep(retry_after)
            response = await client.get(
                f"{S2_API_BASE}/paper/{paper_id}",
                params={"fields": PAPER_FIELDS},
                headers=headers,
            )

        response.raise_for_status()

    return _parse_paper(response.json())


async def get_citations(
    paper_id: str,
    max_results: int = 20,
    direction: str = "citations",
    api_key: Optional[str] = None,
) -> list[S2Paper]:
    """Get papers that cite or are cited by the given paper.

    Args:
        paper_id: Semantic Scholar paper ID or supported identifier
            (e.g., "ARXIV:2301.00001", "DOI:10.1234/...").
        max_results: Maximum number of results (1-1000).
        direction: Either "citations" (papers that cite this one) or
            "references" (papers this one cites).
        api_key: Optional API key.

    Returns:
        List of S2Paper objects.

    Raises:
        ValueError: If direction is not "citations" or "references".
        httpx.HTTPStatusError: If the API request fails.
    """
    if direction not in ("citations", "references"):
        raise ValueError(f"direction must be 'citations' or 'references', got '{direction}'")

    max_results = max(1, min(1000, max_results))

    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key

    params = {
        "fields": CITATION_FIELDS,
        "limit": str(max_results),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{S2_API_BASE}/paper/{paper_id}/{direction}",
            params=params,
            headers=headers,
        )

        if response.status_code == 404:
            return []
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "5"))
            await asyncio.sleep(retry_after)
            response = await client.get(
                f"{S2_API_BASE}/paper/{paper_id}/{direction}",
                params=params,
                headers=headers,
            )

        response.raise_for_status()

    result = response.json()
    data = result.get("data", [])

    papers = []
    for item in data:
        # Citations/references are nested under "citingPaper" or "citedPaper"
        paper_key = "citingPaper" if direction == "citations" else "citedPaper"
        paper_data = item.get(paper_key, item)
        if paper_data and paper_data.get("paperId"):
            papers.append(_parse_paper(paper_data))

    return papers
