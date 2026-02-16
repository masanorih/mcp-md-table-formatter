"""MCP server for formatting Markdown tables with CJK-aware column alignment."""

import re
import unicodedata

from mcp.server.fastmcp import FastMCP


def display_width(s: str) -> int:
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("F", "W") else 1
    return width


def pad(s: str, width: int) -> str:
    return s + " " * (width - display_width(s))


def format_md_table(text: str) -> str:
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return text

    separator_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\|[\s\-:|]+(\|[\s\-:|]+)+\|?$", line.strip()):
            separator_idx = i
            break

    if separator_idx is None:
        return text

    parsed_rows: list[list[str]] = []
    for i, line in enumerate(lines):
        if i == separator_idx:
            parsed_rows.append([])
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        parsed_rows.append(cells)

    num_cols = max(len(row) for row in parsed_rows if row)
    col_widths = [0] * num_cols
    for row in parsed_rows:
        for j, cell in enumerate(row):
            col_widths[j] = max(col_widths[j], display_width(cell))

    result_lines: list[str] = []
    for i, row in enumerate(parsed_rows):
        if i == separator_idx:
            parts = ["-" * w for w in col_widths]
            result_lines.append("| " + " | ".join(parts) + " |")
        else:
            padded = []
            for j in range(num_cols):
                cell = row[j] if j < len(row) else ""
                padded.append(pad(cell, col_widths[j]))
            result_lines.append("| " + " | ".join(padded) + " |")

    return "\n".join(result_lines)


mcp = FastMCP("md-table-formatter")


@mcp.tool()
def format_markdown_table(table_text: str) -> str:
    """Format a Markdown table with CJK-aware column alignment.

    Args:
        table_text: A Markdown table string with pipe-delimited columns.

    Returns:
        The formatted Markdown table with aligned columns.
    """
    return format_md_table(table_text)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
