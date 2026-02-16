"""Markdown テーブル整形 MCP サーバー

全角/半角文字の表示幅を考慮して Markdown テーブルの列幅を揃える。
"""

import pathlib
import re
import unicodedata

from mcp.server.fastmcp import FastMCP


def display_width(s: str) -> int:
    """文字列の表示幅を計算する

    unicodedata.east_asian_width() で判定し、F/W は幅2、それ以外は幅1 とする。

    Args:
        s: 対象文字列
    Returns:
        表示幅（int）
    """
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("F", "W") else 1
    return width


def pad(s: str, width: int) -> str:
    """表示幅ベースで右スペースパディングする

    Args:
        s: 対象文字列
        width: 目標表示幅
    Returns:
        右側にスペースを追加した文字列
    """
    return s + " " * (width - display_width(s))


def format_md_table(text: str) -> str:
    """単一 Markdown テーブルの列幅を揃える

    パイプ区切りのテーブル文字列をパースし、各列の最大表示幅に合わせて
    セルをパディングする。セパレータ行がない場合は入力をそのまま返す。

    Args:
        text: Markdown テーブル文字列
    Returns:
        整形済みテーブル文字列
    """
    lines = text.strip().splitlines()
    if len(lines) < 2:
        return text

    # セパレータ行を検出
    separator_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\|[\s\-:|]+(\|[\s\-:|]+)+\|?$", line.strip()):
            separator_idx = i
            break

    if separator_idx is None:
        return text

    # 各行をセルに分割（セパレータ行は空リスト）
    parsed_rows: list[list[str]] = []
    for i, line in enumerate(lines):
        if i == separator_idx:
            parsed_rows.append([])
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        parsed_rows.append(cells)

    # 各列の最大表示幅を算出
    num_cols = max(len(row) for row in parsed_rows if row)
    col_widths = [0] * num_cols
    for row in parsed_rows:
        for j, cell in enumerate(row):
            col_widths[j] = max(col_widths[j], display_width(cell))

    # セルをパディングして再構築
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
    """テキスト内の全 Markdown テーブルを検出して整形する

    コードブロック内のテーブルはスキップする。

    Args:
        text: Markdown ドキュメント全体の文字列
    Returns:
        テーブル部分のみ整形された文字列
    """
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    i = 0
    in_code_block = False
    separator_re = re.compile(r"^\|[\s\-:|]+(\|[\s\-:|]+)+\|?\s*$")
    pipe_re = re.compile(r"^\|.+\|")

    while i < len(lines):
        stripped = lines[i].rstrip("\n")

        # コードブロックの開始/終了を追跡
        if stripped.lstrip().startswith("```"):
            in_code_block = not in_code_block
            result.append(lines[i])
            i += 1
            continue

        if in_code_block or not pipe_re.match(stripped.strip()):
            result.append(lines[i])
            i += 1
            continue

        # 連続するパイプ行をテーブル候補として収集
        table_lines: list[str] = []
        j = i
        while j < len(lines):
            s = lines[j].rstrip("\n").strip()
            if pipe_re.match(s) or separator_re.match(s):
                table_lines.append(s)
                j += 1
            else:
                break

        # セパレータの有無で実際のテーブルか判定
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
    """Markdown テーブル文字列を整形する

    全角/半角文字の表示幅を考慮して列幅を揃える。

    Args:
        table_text: パイプ区切りの Markdown テーブル文字列
    Returns:
        整形済みテーブル文字列
    """
    return format_md_table(table_text)


@mcp.tool()
def format_markdown_file(file_path: str) -> str:
    """Markdown ファイル内の全テーブルを整形する

    ファイルを読み込み、コードブロック外の全テーブルを整形して書き戻す。

    Args:
        file_path: Markdown ファイルの絶対パス
    Returns:
        処理結果のメッセージ
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
    """MCP サーバーを stdio トランスポートで起動する"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
