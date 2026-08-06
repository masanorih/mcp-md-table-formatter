"""Markdown テーブル整形 MCP サーバー

全角/半角文字の表示幅を考慮して Markdown テーブルの列幅を揃える。
"""

import pathlib
import re
import unicodedata

from mcp.server.mcpserver import MCPServer


AMBIGUOUS_CHAR_REPLACEMENTS = {
    "→": "->",
    "←": "<-",
    "↑": "^",
    "↓": "v",
    "⇒": "=>",
    "⇐": "<=",
    "×": "x",
    "±": "+/-",
    "÷": "/",
    "≤": "<=",
    "≥": ">=",
    "≠": "!=",
    "≈": "~=",
    "≡": "==",
    "…": "...",
    "—": "--",
    "–": "-",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "※": "*",
}

# アライメント指定を表現するのに最低限必要なセパレータ幅
# None: "-" / left: ":-" / right: "-:" / center: ":-:"
ALIGNMENT_MIN_WIDTHS = {None: 1, "left": 2, "right": 2, "center": 3}


def replace_ambiguous_chars(s: str) -> str:
    """East Asian Ambiguous な記号を ASCII 等価物に置換する

    フォントによって幅が変動する記号（矢印、乗算記号など）を
    幅が安定した ASCII シーケンスへ置き換える。

    Args:
        s: 対象文字列
    Returns:
        置換後の文字列
    """
    for src, dst in AMBIGUOUS_CHAR_REPLACEMENTS.items():
        s = s.replace(src, dst)
    return s


def display_width(s: str, cjk_mode: bool = False) -> int:
    """文字列の表示幅を計算する

    unicodedata.east_asian_width() で判定し、F/W は幅2、それ以外は幅1 とする。
    cjk_mode=True のときは Ambiguous (A) も幅2 として扱う。

    Args:
        s: 対象文字列
        cjk_mode: CJK ロケール前提モード。Ambiguous を幅2 扱いにする。
    Returns:
        表示幅（int）
    """
    wide_categories = ("F", "W", "A") if cjk_mode else ("F", "W")
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in wide_categories else 1
    return width


def pad(s: str, width: int, cjk_mode: bool = False) -> str:
    """表示幅ベースで右スペースパディングする

    Args:
        s: 対象文字列
        width: 目標表示幅
        cjk_mode: display_width に引き渡す CJK モードフラグ
    Returns:
        右側にスペースを追加した文字列
    """
    return s + " " * (width - display_width(s, cjk_mode))


def parse_alignments(separator_line: str) -> list[str | None]:
    """セパレータ行から列ごとのアライメント指定を読み取る

    GFM のコロン記法を判定する。":-" は左寄せ、"-:" は右寄せ、
    ":-:" は中央寄せ、コロンなしは指定なし（None）とする。

    Args:
        separator_line: テーブルのセパレータ行
    Returns:
        列順のアライメント指定リスト（"left"/"right"/"center"/None）
    """
    specs = [c.strip() for c in separator_line.strip().strip("|").split("|")]
    alignments: list[str | None] = []
    for spec in specs:
        left = spec.startswith(":")
        right = spec.endswith(":")
        if left and right:
            alignments.append("center")
        elif left:
            alignments.append("left")
        elif right:
            alignments.append("right")
        else:
            alignments.append(None)
    return alignments


def build_separator_cell(alignment: str | None, width: int) -> str:
    """アライメント指定を保ったままセパレータセルを組み立てる

    Args:
        alignment: "left"/"right"/"center"/None
        width: 目標表示幅（ALIGNMENT_MIN_WIDTHS 以上であること）
    Returns:
        コロンとハイフンからなる幅 width の文字列
    """
    if alignment == "center":
        return ":" + "-" * (width - 2) + ":"
    if alignment == "left":
        return ":" + "-" * (width - 1)
    if alignment == "right":
        return "-" * (width - 1) + ":"
    return "-" * width


def format_md_table(text: str, cjk_mode: bool = False) -> str:
    """単一 Markdown テーブルの列幅を揃える

    パイプ区切りのテーブル文字列をパースし、各列の最大表示幅に合わせて
    セルをパディングする。セパレータ行がない場合は入力をそのまま返す。

    Args:
        text: Markdown テーブル文字列
        cjk_mode: True で Ambiguous 文字を ASCII 置換せず幅2 として padding
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
        if not cjk_mode:
            cells = [replace_ambiguous_chars(c) for c in cells]
        parsed_rows.append(cells)

    # 元のセパレータ行からアライメント指定を保存
    alignments = parse_alignments(lines[separator_idx])

    # 各列の最大表示幅を算出
    num_cols = max(len(row) for row in parsed_rows if row)
    col_widths = [0] * num_cols
    for row in parsed_rows:
        for j, cell in enumerate(row):
            col_widths[j] = max(col_widths[j], display_width(cell, cjk_mode))

    # 列数をアライメント側と揃え、コロンが収まる幅を確保する
    alignments = (alignments + [None] * num_cols)[:num_cols]
    for j, alignment in enumerate(alignments):
        col_widths[j] = max(col_widths[j], ALIGNMENT_MIN_WIDTHS[alignment])

    # セルをパディングして再構築
    result_lines: list[str] = []
    for i, row in enumerate(parsed_rows):
        if i == separator_idx:
            parts = [
                build_separator_cell(a, w) for a, w in zip(alignments, col_widths)
            ]
            result_lines.append("| " + " | ".join(parts) + " |")
        else:
            padded = []
            for j in range(num_cols):
                cell = row[j] if j < len(row) else ""
                padded.append(pad(cell, col_widths[j], cjk_mode))
            result_lines.append("| " + " | ".join(padded) + " |")

    return "\n".join(result_lines)


def format_md_tables_in_text(text: str, cjk_mode: bool = False) -> str:
    """テキスト内の全 Markdown テーブルを検出して整形する

    コードブロック内のテーブルはスキップする。

    Args:
        text: Markdown ドキュメント全体の文字列
        cjk_mode: format_md_table に引き渡す CJK モードフラグ
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
            formatted = format_md_table("\n".join(table_lines), cjk_mode)
            result.append(formatted + "\n" if lines[j - 1].endswith("\n") else formatted)
            i = j
        else:
            result.append(lines[i])
            i += 1

    return "".join(result)


mcp = MCPServer("md-table-formatter")


@mcp.tool()
def format_markdown_file(file_path: str, cjk_mode: bool = False) -> str:
    """Markdown (.md) ファイル内の全テーブルを整形する

    .md ファイルを読み込み、コードブロック外の全テーブルを整形して書き戻す。
    .md 以外の拡張子のファイルはエラーを返す。

    Args:
        file_path: Markdown ファイルの絶対パス（.md 拡張子のみ対応）
        cjk_mode: True で CJK モード。Ambiguous-width 文字 (×, ※, → 等) を
                  ASCII 置換せず、表示幅2 として padding する。CJK ロケール /
                  フォントで読まれる前提のドキュメント (×口 や ※注 を含む) 用。
                  既存挙動 (置換あり・幅1) は False (デフォルト) で維持する。
                  注意: cjk_mode=True で整形した表は Western フォント表示では
                  pipe 位置がずれる。可搬性が必要なら False のままにする。
    Returns:
        処理結果のメッセージ
    """
    path = pathlib.Path(file_path).expanduser()
    if path.suffix != ".md":
        return f"Error: only .md files are supported: {file_path}"
    if not path.is_file():
        return f"Error: file not found: {file_path}"
    content = path.read_text(encoding="utf-8")
    formatted = format_md_tables_in_text(content, cjk_mode)
    if content == formatted:
        return f"No tables to format in {file_path}"
    path.write_text(formatted, encoding="utf-8")
    return f"Formatted tables in {file_path}"


def main():
    """MCP サーバーを stdio トランスポートで起動する"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
