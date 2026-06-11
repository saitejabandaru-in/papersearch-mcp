import asyncio

from papersearch_mcp.server import mcp


def test_tool_registration():
    """Verify that all tools are successfully registered on the FastMCP instance."""
    tools = asyncio.run(mcp.list_tools())
    registered_tools = [tool.name for tool in tools]

    expected_tools = [
        "search_arxiv_papers",
        "get_arxiv_paper_details",
        "search_semantic_scholar_papers",
        "get_citation_graph",
        "extract_pdf_content",
    ]

    for tool_name in expected_tools:
        assert tool_name in registered_tools, f"Tool {tool_name} was not registered!"

