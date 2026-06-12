"""arXiv API client for searching and retrieving paper metadata.

Uses the arXiv API (https://info.arxiv.org/help/api/index.html) to search
for papers and retrieve detailed metadata including titles, authors,
abstracts, categories, and PDF links.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

# arXiv API base URL
ARXIV_API_BASE = "http://export.arxiv.org/api/query"

# Namespace for Atom feed parsing
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

# Rate limiting: arXiv asks for max 1 request per 3 seconds
RATE_LIMIT_SECONDS = 3.0


@dataclass
class ArxivPaper:
    """Represents a paper from arXiv."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    pdf_url: str
    abs_url: str
    comment: str | None = None
    journal_ref: str | None = None
    doi: str | None = None

    def to_dict(self) -> dict:
        """Convert to a dictionary for JSON serialization."""
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "categories": self.categories,
            "primary_category": self.primary_category,
            "published": self.published,
            "updated": self.updated,
            "pdf_url": self.pdf_url,
            "abs_url": self.abs_url,
            "comment": self.comment,
            "journal_ref": self.journal_ref,
            "doi": self.doi,
        }


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract the arXiv ID from the full entry URL.

    Examples:
        http://arxiv.org/abs/2301.00001v1 -> 2301.00001
        http://arxiv.org/abs/cs/0601001v1 -> cs/0601001
    """
    # Remove version suffix and extract ID
    raw_id = entry_id.split("/abs/")[-1]
    # Remove version number (e.g., v1, v2)
    if raw_id and raw_id[-1].isdigit() and "v" in raw_id:
        raw_id = raw_id.rsplit("v", 1)[0]
    return raw_id


def _parse_entry(entry: ET.Element) -> ArxivPaper:
    """Parse a single Atom entry element into an ArxivPaper."""
    # Helper to find text with namespace
    def find_text(tag: str, ns: str = ATOM_NS) -> str:
        elem = entry.find(f"{{{ns}}}{tag}")
        return elem.text.strip() if elem is not None and elem.text else ""

    # Extract entry ID and arXiv ID
    entry_id = find_text("id")
    arxiv_id = _extract_arxiv_id(entry_id)

    # Extract title (may contain newlines in multi-line titles)
    title = find_text("title")
    title = " ".join(title.split())  # Normalize whitespace

    # Extract authors
    authors = []
    for author_elem in entry.findall(f"{{{ATOM_NS}}}author"):
        name_elem = author_elem.find(f"{{{ATOM_NS}}}name")
        if name_elem is not None and name_elem.text:
            authors.append(name_elem.text.strip())

    # Extract abstract
    abstract = find_text("summary")
    abstract = " ".join(abstract.split())  # Normalize whitespace

    # Extract categories
    categories = []
    for cat_elem in entry.findall(f"{{{ATOM_NS}}}category"):
        term = cat_elem.get("term", "")
        if term:
            categories.append(term)

    # Primary category
    primary_cat_elem = entry.find(f"{{{ARXIV_NS}}}primary_category")
    primary_category = primary_cat_elem.get("term", "") if primary_cat_elem is not None else ""

    # Dates
    published = find_text("published")
    updated = find_text("updated")

    # Links
    pdf_url = ""
    abs_url = entry_id
    for link_elem in entry.findall(f"{{{ATOM_NS}}}link"):
        link_title = link_elem.get("title", "")
        link_href = link_elem.get("href", "")
        link_type = link_elem.get("type", "")
        if link_title == "pdf" or link_type == "application/pdf":
            pdf_url = link_href

    if not pdf_url and arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

    # Optional fields
    comment = find_text("comment", ARXIV_NS) or None
    journal_ref = find_text("journal_ref", ARXIV_NS) or None
    doi_elem = entry.find(f"{{{ARXIV_NS}}}doi")
    doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else None

    return ArxivPaper(
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        abstract=abstract,
        categories=categories,
        primary_category=primary_category,
        published=published,
        updated=updated,
        pdf_url=pdf_url,
        abs_url=abs_url,
        comment=comment,
        journal_ref=journal_ref,
        doi=doi,
    )


async def search_arxiv(
    query: str,
    max_results: int = 10,
    start: int = 0,
    sort_by: str = "relevance",
    sort_order: str = "descending",
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[ArxivPaper]:
    """Search arXiv for papers matching the query.

    Args:
        query: Search query string. Supports arXiv search syntax
            (e.g., "ti:transformers AND cat:cs.CL").
        max_results: Maximum number of results to return (1-100).
        start: Starting index for pagination.
        sort_by: Sort criterion - "relevance", "lastUpdatedDate", or "submittedDate".
        sort_order: Sort order - "ascending" or "descending".
        category: Optional arXiv category filter (e.g., "cs.CL", "physics.hep-th").
        date_from: Optional start date filter (YYYY-MM-DD format).
        date_to: Optional end date filter (YYYY-MM-DD format).

    Returns:
        List of ArxivPaper objects matching the query.

    Raises:
        httpx.HTTPStatusError: If the API request fails.
        ValueError: If parameters are invalid.
    """
    max_results = max(1, min(100, max_results))

    # Build the search query
    search_query = query

    # Add category filter if specified
    if category:
        if search_query:
            search_query = f"({search_query}) AND cat:{category}"
        else:
            search_query = f"cat:{category}"

    # Map sort_by to arXiv API values
    sort_map = {
        "relevance": "relevance",
        "lastUpdatedDate": "lastUpdatedDate",
        "last_updated": "lastUpdatedDate",
        "submittedDate": "submittedDate",
        "submitted": "submittedDate",
    }
    api_sort_by = sort_map.get(sort_by, "relevance")

    params = {
        "search_query": search_query,
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": api_sort_by,
        "sortOrder": sort_order,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ARXIV_API_BASE, params=params)
        response.raise_for_status()

    # Parse the Atom XML response
    root = ET.fromstring(response.text)
    entries = root.findall(f"{{{ATOM_NS}}}entry")

    papers = []
    for entry in entries:
        try:
            paper = _parse_entry(entry)

            # Apply date filtering if specified
            if date_from or date_to:
                try:
                    pub_date = paper.published[:10]  # YYYY-MM-DD
                    if date_from and pub_date < date_from:
                        continue
                    if date_to and pub_date > date_to:
                        continue
                except (ValueError, IndexError):
                    pass  # Skip date filtering if date parsing fails

            papers.append(paper)
        except Exception:
            # Skip entries that fail to parse
            continue

    return papers


async def get_paper_by_id(arxiv_id: str) -> ArxivPaper | None:
    """Retrieve a specific paper by its arXiv ID.

    Args:
        arxiv_id: The arXiv paper ID (e.g., "2301.00001" or "cs/0601001").

    Returns:
        ArxivPaper if found, None otherwise.

    Raises:
        httpx.HTTPStatusError: If the API request fails.
    """
    # Clean up the ID - remove any URL prefix
    if "arxiv.org" in arxiv_id:
        arxiv_id = arxiv_id.split("/abs/")[-1].split("/pdf/")[-1]
    arxiv_id = arxiv_id.strip().rstrip("/")

    # Remove version suffix for the query
    clean_id = arxiv_id
    if clean_id and clean_id[-1].isdigit() and "v" in clean_id:
        parts = clean_id.rsplit("v", 1)
        if parts[1].isdigit():
            clean_id = parts[0]

    params = {
        "id_list": clean_id,
        "max_results": "1",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ARXIV_API_BASE, params=params)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    entries = root.findall(f"{{{ATOM_NS}}}entry")

    if not entries:
        return None

    # Check if the entry is actually a valid result (not an error entry)
    entry = entries[0]
    title_elem = entry.find(f"{{{ATOM_NS}}}title")
    if title_elem is not None and title_elem.text:
        title_text = title_elem.text.strip()
        if title_text.startswith("Error"):
            return None

    try:
        return _parse_entry(entry)
    except Exception:
        return None
