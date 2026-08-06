"""Tests for MCP server wiring."""


def test_mcp_instance_importable():
    from server import mcp

    assert mcp is not None


def test_registered_tools():
    import asyncio

    from server import mcp

    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert "format_markdown_file" in names


def test_main_callable():
    from server import main

    assert callable(main)
