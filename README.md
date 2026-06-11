# papersearch-mcp 📄🔍

An Model Context Protocol (MCP) server for searching, analyzing, and extracting text from academic research papers. Built for Claude Code and Claude Desktop, it integrates **arXiv** and **Semantic Scholar** directly into your AI assistant's toolkit.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0.0-orange.svg)](https://modelcontextprotocol.io)

---

## Features

- **arXiv Integration**:
  - `search_arxiv_papers`: Query arXiv with support for filters like primary category (e.g., `cs.CL` for NLP, `cs.LG` for Machine Learning) and sort order.
  - `get_arxiv_paper_details`: Retrieve full paper metadata, primary and secondary categories, author list, abstract, published/updated dates, and PDF/DOI URLs.
- **Semantic Scholar Integration**:
  - `search_semantic_scholar_papers`: Broader academic graph search across multiple publishers. Includes citation and reference counts, open-access status, and journal/venue metadata.
  - `get_citation_graph`: Query citing or cited papers for any paper ID (supporting Semantic Scholar ID, DOI, or arXiv ID).
- **Document Analysis**:
  - `extract_pdf_content`: Downloads open-access paper PDFs and extracts the text content page-by-page using `PyMuPDF` (fitz). Truncation limits prevent overwhelming AI context windows.

---

## Installation

### Prerequisites
- Python >= 3.10
- pip (or uv / poetry)

### Install via PyPI
```bash
pip install papersearch-mcp
```

### Install from Source (Development)
```bash
git clone https://github.com/saitejabandaru/papersearch-mcp.git
cd papersearch-mcp
pip install -e .
```

---

## Configuration

### 1. Claude Code
To add this server to your Claude Code CLI instance, run:

```bash
claude mcp add papersearch-mcp -- python -m papersearch_mcp.server
```

Or manually add it to your Claude Code settings file (usually located at `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "papersearch": {
      "command": "python",
      "args": ["-m", "papersearch_mcp.server"]
    }
  }
}
```

### 2. Claude Desktop
Add the following configuration to your Claude Desktop config (usually located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "papersearch": {
      "command": "python",
      "args": ["-m", "papersearch_mcp.server"]
    }
  }
}
```

---

## Available Tools

### 1. `search_arxiv_papers`
Search the arXiv database for preprints and published papers.
- **Arguments**:
  - `query` (string, required): Search query, e.g. `"transformers attention"` or `"ti:\"Attention Is All You Need\""`.
  - `max_results` (integer, optional): Maximum papers to return (default 10, max 100).
  - `category` (string, optional): Specific category filter, e.g. `"cs.CL"`.
  - `sort_by` (string, optional): Criteria to sort by: `"relevance"`, `"lastUpdatedDate"`, `"submittedDate"`.
  - `sort_order` (string, optional): `"descending"` (default) or `"ascending"`.

### 2. `get_arxiv_paper_details`
Fetch full metadata for a specific arXiv ID.
- **Arguments**:
  - `arxiv_id` (string, required): The unique paper ID, e.g., `"2301.00001"` or `"cs/0601001"`.

### 3. `search_semantic_scholar_papers`
Search the wider Semantic Scholar database for peer-reviewed papers and citations.
- **Arguments**:
  - `query` (string, required): Search query.
  - `max_results` (integer, optional): Maximum papers to return (default 10).
  - `year` (string, optional): Filter by year or range, e.g. `"2023"`, `"2020-2023"`, `"2020-"`.
  - `fields_of_study` (string, optional): Comma-separated fields, e.g. `"Computer Science, Art"`.
  - `open_access_only` (boolean, optional): Only return papers with open-access PDFs.

### 4. `get_citation_graph`
Retrieve the bibliography (references) or citations for a given academic paper.
- **Arguments**:
  - `paper_id` (string, required): Paper identifier (supporting Semantic Scholar ID, `"ARXIV:2301.00001"`, or `"DOI:10.1234/example"`).
  - `direction` (string, optional): `"citations"` (default) or `"references"`.
  - `max_results` (integer, optional): Limit results (default 20).

### 5. `extract_pdf_content`
Download a paper PDF and extract its text layout for study.
- **Arguments**:
  - `url` (string, required): A direct link to the PDF file (e.g. `"https://arxiv.org/pdf/2301.00001"`).
  - `max_pages` (integer, optional): Maximum pages to extract (to manage context limits).

---

## Development

Run tests using `pytest`:

```bash
pip install -e ".[dev]"
pytest
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
