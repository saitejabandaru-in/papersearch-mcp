# Contributing to papersearch-mcp

Thank you for your interest in contributing to `papersearch-mcp`! This project aims to make academic literature search and analysis seamless inside AI coding assistants like Claude.

## Code of Conduct

Please be respectful and helpful in all interactions. We aim to foster a collaborative and welcoming environment.

## How to Contribute

### 1. Report Bugs or Request Features
If you find a bug or have an idea for a feature, please search the existing issues first. If it's new, open a GitHub Issue and provide:
- A clear description of the issue or feature.
- Steps to reproduce (for bugs).
- What behavior you expected vs what happened.

### 2. Make Code Changes
If you'd like to submit a pull request (PR) to fix a bug or add a feature:
1. **Fork the repository** and create your branch from `main`.
2. **Set up the environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. **Write tests**: If you are adding new functionality or fixing a bug, write unit tests to cover your changes.
4. **Run tests**:
   ```bash
   pytest
   ```
5. **Format/Lint the code**: We use `ruff` to format and lint:
   ```bash
   ruff format .
   ruff check .
   ```
6. **Submit a Pull Request**: Push your branch to GitHub and open a PR. Please write a descriptive PR title and explain your changes.

## Development Stack
- **Python >= 3.10**
- **FastMCP** (from `mcp`) for defining server and tools.
- **httpx** for asynchronous HTTP requests.
- **PyMuPDF** (`fitz`) for parsing PDF layouts.
- **pytest** for testing.

If you have any questions, feel free to start a discussion or open an issue!
