"""PDF text extraction using PyMuPDF (fitz).

Downloads PDFs from URLs and extracts their text content,
with support for page-level extraction and text truncation
for large documents.
"""

from __future__ import annotations

import io
import tempfile
from typing import Optional

import fitz  # PyMuPDF
import httpx

# Maximum PDF size to download (50 MB)
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024

# Maximum text length to return (to avoid overwhelming context windows)
MAX_TEXT_LENGTH = 100_000

# Default timeout for PDF downloads
DOWNLOAD_TIMEOUT = 60.0


async def download_pdf(url: str, timeout: float = DOWNLOAD_TIMEOUT) -> bytes:
    """Download a PDF from a URL.

    Args:
        url: URL of the PDF to download.
        timeout: Request timeout in seconds.

    Returns:
        Raw PDF bytes.

    Raises:
        httpx.HTTPStatusError: If the download fails.
        ValueError: If the file is too large or not a valid PDF.
    """
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": "papersearch-mcp/0.1.0 (academic research tool)",
        },
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    content = response.content

    if len(content) > MAX_PDF_SIZE_BYTES:
        raise ValueError(
            f"PDF is too large: {len(content) / (1024 * 1024):.1f} MB "
            f"(max {MAX_PDF_SIZE_BYTES / (1024 * 1024):.0f} MB)"
        )

    # Basic PDF validation
    if not content[:5] == b"%PDF-":
        raise ValueError("Downloaded file does not appear to be a valid PDF")

    return content


def extract_text_from_bytes(
    pdf_bytes: bytes,
    max_pages: Optional[int] = None,
    max_length: int = MAX_TEXT_LENGTH,
) -> dict:
    """Extract text content from PDF bytes.

    Args:
        pdf_bytes: Raw PDF file bytes.
        max_pages: Maximum number of pages to extract. None for all pages.
        max_length: Maximum total text length to return.

    Returns:
        Dictionary with:
            - text: Extracted text content
            - total_pages: Total number of pages in the PDF
            - pages_extracted: Number of pages text was extracted from
            - truncated: Whether the text was truncated
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        total_pages = len(doc)
        pages_to_extract = total_pages if max_pages is None else min(max_pages, total_pages)

        text_parts: list[str] = []
        total_length = 0
        pages_extracted = 0
        truncated = False

        for page_num in range(pages_to_extract):
            page = doc[page_num]
            page_text = page.get_text("text")

            if not page_text.strip():
                # Try alternative extraction methods
                page_text = page.get_text("blocks")
                if isinstance(page_text, list):
                    page_text = "\n".join(
                        block[4] for block in page_text if len(block) > 4 and isinstance(block[4], str)
                    )

            if page_text and page_text.strip():
                # Add page header for readability
                page_header = f"\n--- Page {page_num + 1} ---\n"
                page_content = page_header + page_text.strip()

                if total_length + len(page_content) > max_length:
                    # Truncate to fit within limits
                    remaining = max_length - total_length
                    if remaining > 100:  # Only add if there's meaningful space left
                        text_parts.append(page_content[:remaining] + "\n[... truncated ...]")
                        pages_extracted += 1
                    truncated = True
                    break

                text_parts.append(page_content)
                total_length += len(page_content)
                pages_extracted += 1

        full_text = "\n".join(text_parts)

        return {
            "text": full_text,
            "total_pages": total_pages,
            "pages_extracted": pages_extracted,
            "truncated": truncated,
        }

    finally:
        doc.close()


async def extract_text_from_url(
    url: str,
    max_pages: Optional[int] = None,
    max_length: int = MAX_TEXT_LENGTH,
) -> dict:
    """Download a PDF and extract its text content.

    Args:
        url: URL of the PDF to download and extract.
        max_pages: Maximum number of pages to extract.
        max_length: Maximum total text length.

    Returns:
        Dictionary with extracted text and metadata.

    Raises:
        httpx.HTTPStatusError: If the download fails.
        ValueError: If the file is invalid or too large.
        fitz.FileDataError: If the PDF cannot be parsed.
    """
    pdf_bytes = await download_pdf(url)
    result = extract_text_from_bytes(pdf_bytes, max_pages=max_pages, max_length=max_length)
    result["source_url"] = url
    result["pdf_size_bytes"] = len(pdf_bytes)
    return result
