"""MCP server for formatting Markdown tables with CJK-aware column alignment."""

import pathlib
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


def format_md_tables_in_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    i = 0
    in_code_block = False
    separator_re = re.compile(r"^\|[\s\-:|]+(\|[\s\-:|]+)+\|?\s*$")
    pipe_re = re.compile(r"^\|.+\|")

    while i < len(lines):
        stripped = lines[i].rstrip("\n")
        if stripped.lstrip().startswith("```"):
            in_code_block = not in_code_block
            result.append(lines[i])
            i += 1
            continue

        if in_code_block or not pipe_re.match(stripped.strip()):
            result.append(lines[i])
            i += 1
            continue

        # Collect consecutive pipe lines (potential table)
        table_lines: list[str] = []
        j = i
        while j < len(lines):
            s = lines[j].rstrip("\n").strip()
            if pipe_re.match(s) or separator_re.match(s):
                table_lines.append(s)
                j += 1
            else:
                break

        # Check if it has a separator (i.e., it's a real table)
        has_separator = any(separator_re.match(line) for line in table_lines)
        if has_separator and len(table_lines) >= 2:
            formatted = format_md_table("\n".join(table_lines))
            result.append(formatted + "\n" if lines[j - 1].endswith("\n") else formatted)
            i = j
        else:
            result.append(lines[i])
            i += 1

    return "".join(result)


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


@mcp.tool()
def format_markdown_file(file_path: str) -> str:
    """Format all Markdown tables in a file with CJK-aware column alignment.

    Reads the file, formats all Markdown tables found in it, and writes
    the result back to the file. Tables inside code blocks are left untouched.

    Args:
        file_path: Absolute path to the Markdown file to format.

    Returns:
        A message indicating the result.
    """
    path = pathlib.Path(file_path).expanduser()
    if not path.is_file():
        return f"Error: file not found: {file_path}"
    content = path.read_text(encoding="utf-8")
    formatted = format_md_tables_in_text(content)
    if content == formatted:
        return f"No tables to format in {file_path}"
    path.write_text(formatted, encoding="utf-8")
    return f"Formatted tables in {file_path}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
