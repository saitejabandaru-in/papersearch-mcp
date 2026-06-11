"""MCP Server for academic paper search and citation retrieval.

Exposes tools to search arXiv and Semantic Scholar, retrieve details and citations,
and extract text content from paper PDFs.
"""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from papersearch_mcp.arxiv_client import get_paper_by_id, search_arxiv
from papersearch_mcp.pdf_extractor import extract_text_from_url
from papersearch_mcp.semantic_scholar import get_citations, get_paper_details, search_semantic_scholar

# Create FastMCP server
mcp = FastMCP(
    "PaperSearch",
    dependencies=["httpx", "PyMuPDF", "mcp[cli]"],
)


@mcp.tool()
async def search_arxiv_papers(
    query: str,
    max_results: int = 10,
    category: Optional[str] = None,
    sort_by: str = "relevance",
    sort_order: str = "descending",
) -> str:
    """Search arXiv for academic papers and return their details in Markdown format.

    Args:
        query: Search query (e.g. 'transformers attention' or 'ti:"Attention is all you need"').
        max_results: Maximum number of results to return (default 10, max 100).
        category: Optional category filter (e.g. 'cs.CL' for NLP, 'cs.LG' for ML).
        sort_by: Sort criteria - 'relevance', 'lastUpdatedDate', or 'submittedDate'.
        sort_order: Sort order - 'ascending' or 'descending'.
    """
    try:
        papers = await search_arxiv(
            query=query,
            max_results=max_results,
            category=category,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        if not papers:
            return f"No papers found on arXiv matching query: '{query}'"

        markdown_parts = [f"# arXiv Search Results for: '{query}'\n"]
        for idx, paper in enumerate(papers, 1):
            markdown_parts.append(
                f"### {idx}. {paper.title}\n"
                f"- **arXiv ID**: `{paper.arxiv_id}`\n"
                f"- **Authors**: {', '.join(paper.authors)}\n"
                f"- **Published**: {paper.published[:10]} | **Updated**: {paper.updated[:10]}\n"
                f"- **Categories**: {', '.join(paper.categories)} (Primary: `{paper.primary_category}`)\n"
                f"- **PDF Link**: {paper.pdf_url}\n"
                f"- **Abstract**: {paper.abstract}\n"
            )
            if paper.comment:
                markdown_parts.append(f"- **Comment**: *{paper.comment}*\n")
            if paper.journal_ref:
                markdown_parts.append(f"- **Journal Ref**: *{paper.journal_ref}*\n")
            if paper.doi:
                markdown_parts.append(f"- **DOI**: {paper.doi}\n")
            markdown_parts.append("---")

        return "\n".join(markdown_parts)

    except Exception as e:
        return f"Error searching arXiv: {str(e)}"


@mcp.tool()
async def get_arxiv_paper_details(arxiv_id: str) -> str:
    """Get detailed information about a specific arXiv paper.

    Args:
        arxiv_id: The arXiv paper ID (e.g., '2301.00001' or 'cs/0601001').
    """
    try:
        paper = await get_paper_by_id(arxiv_id)
        if not paper:
            return f"arXiv paper not found with ID: '{arxiv_id}'"

        markdown = (
            f"# {paper.title}\n\n"
            f"- **arXiv ID**: `{paper.arxiv_id}`\n"
            f"- **Authors**: {', '.join(paper.authors)}\n"
            f"- **Published**: {paper.published} | **Updated**: {paper.updated}\n"
            f"- **Categories**: {', '.join(paper.categories)} (Primary: `{paper.primary_category}`)\n"
            f"- **PDF URL**: {paper.pdf_url}\n"
            f"- **Abstract URL**: {paper.abs_url}\n"
        )
        if paper.comment:
            markdown += f"- **Comment**: *{paper.comment}*\n"
        if paper.journal_ref:
            markdown += f"- **Journal Ref**: *{paper.journal_ref}*\n"
        if paper.doi:
            markdown += f"- **DOI**: {paper.doi}\n"

        markdown += f"\n## Abstract\n{paper.abstract}\n"
        return markdown

    except Exception as e:
        return f"Error retrieving paper details: {str(e)}"


@mcp.tool()
async def search_semantic_scholar_papers(
    query: str,
    max_results: int = 10,
    year: Optional[str] = None,
    fields_of_study: Optional[str] = None,
    open_access_only: bool = False,
) -> str:
    """Search Semantic Scholar for papers across various disciplines.

    Args:
        query: Search query (e.g. 'reinforcement learning human feedback').
        max_results: Maximum number of results to return (default 10, max 100).
        year: Year or range filter (e.g., '2023', '2020-2023', '2020-', '-2023').
        fields_of_study: Comma-separated fields of study (e.g., 'Computer Science, Medicine').
        open_access_only: Only return papers with open access PDF links.
    """
    try:
        fields_list = [f.strip() for f in fields_of_study.split(",")] if fields_of_study else None
        papers = await search_semantic_scholar(
            query=query,
            max_results=max_results,
            year=year,
            fields_of_study=fields_list,
            open_access_only=open_access_only,
        )

        if not papers:
            return f"No papers found on Semantic Scholar matching query: '{query}'"

        markdown_parts = [f"# Semantic Scholar Search Results for: '{query}'\n"]
        for idx, paper in enumerate(papers, 1):
            markdown_parts.append(
                f"### {idx}. {paper.title}\n"
                f"- **Paper ID**: `{paper.paper_id}`\n"
                f"- **Authors**: {', '.join([a.name for a in paper.authors])}\n"
                f"- **Year**: {paper.year or 'N/A'} | **Venue**: {paper.venue or 'N/A'}\n"
                f"- **Citations**: {paper.citation_count} | **References**: {paper.reference_count}\n"
                f"- **Fields**: {', '.join(paper.fields_of_study)}\n"
            )
            if paper.open_access_pdf_url:
                markdown_parts.append(f"- **PDF URL**: {paper.open_access_pdf_url}\n")
            if paper.url:
                markdown_parts.append(f"- **S2 URL**: {paper.url}\n")
            if paper.external_ids:
                ids_str = ", ".join([f"{k}: `{v}`" for k, v in paper.external_ids.items()])
                markdown_parts.append(f"- **External IDs**: {ids_str}\n")
            if paper.abstract:
                markdown_parts.append(f"- **Abstract**: {paper.abstract}\n")
            markdown_parts.append("---")

        return "\n".join(markdown_parts)

    except Exception as e:
        return f"Error searching Semantic Scholar: {str(e)}"


@mcp.tool()
async def get_citation_graph(
    paper_id: str,
    direction: str = "citations",
    max_results: int = 20,
) -> str:
    """Retrieve papers citing or referenced by a specific paper using Semantic Scholar.

    Args:
        paper_id: S2 Paper ID, arXiv ID (prefixed with 'ARXIV:'), or DOI (prefixed with 'DOI:').
        direction: Either 'citations' (who cites this paper) or 'references' (what does this paper cite).
        max_results: Maximum number of papers to return (default 20, max 100).
    """
    if direction not in ("citations", "references"):
        return "Error: direction must be either 'citations' or 'references'."

    try:
        papers = await get_citations(
            paper_id=paper_id,
            max_results=max_results,
            direction=direction,
        )

        if not papers:
            return f"No {direction} found for paper: '{paper_id}'"

        markdown_parts = [f"# Citation Graph ({direction.capitalize()}) for Paper: {paper_id}\n"]
        for idx, paper in enumerate(papers, 1):
            markdown_parts.append(
                f"### {idx}. {paper.title}\n"
                f"- **Paper ID**: `{paper.paper_id}`\n"
                f"- **Authors**: {', '.join([a.name for a in paper.authors])}\n"
                f"- **Year**: {paper.year or 'N/A'} | **Venue**: {paper.venue or 'N/A'}\n"
                f"- **Citations**: {paper.citation_count}\n"
            )
            if paper.open_access_pdf_url:
                markdown_parts.append(f"- **PDF URL**: {paper.open_access_pdf_url}\n")
            if paper.url:
                markdown_parts.append(f"- **S2 URL**: {paper.url}\n")
            markdown_parts.append("---")

        return "\n".join(markdown_parts)

    except Exception as e:
        return f"Error retrieving citation graph: {str(e)}"


@mcp.tool()
async def extract_pdf_content(
    url: str,
    max_pages: Optional[int] = None,
) -> str:
    """Download a PDF paper from a URL and extract its text content.

    Args:
        url: Direct link to the PDF file (e.g. 'https://arxiv.org/pdf/2301.00001').
        max_pages: Optional maximum number of pages to extract (default is all).
    """
    try:
        result = await extract_text_from_url(url, max_pages=max_pages)
        meta = (
            f"## PDF Extraction Meta\n"
            f"- **Source URL**: {result.get('source_url')}\n"
            f"- **Total Pages**: {result.get('total_pages')}\n"
            f"- **Pages Extracted**: {result.get('pages_extracted')}\n"
            f"- **Truncated**: {result.get('truncated')}\n"
            f"- **Size**: {result.get('pdf_size_bytes', 0) / 1024:.1f} KB\n\n"
        )
        return meta + result.get("text", "")

    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def main() -> None:
    """Run the FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
