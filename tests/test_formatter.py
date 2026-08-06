"""Tests for Markdown table formatter core logic."""

import textwrap
import tempfile
import pathlib

from server import (
    display_width,
    format_md_table,
    format_md_tables_in_text,
    format_markdown_file,
    pad,
    replace_ambiguous_chars,
)


class TestDisplayWidth:
    def test_ascii_only(self):
        assert display_width("hello") == 5

    def test_fullwidth_only(self):
        assert display_width("日本語") == 6

    def test_mixed(self):
        assert display_width("abc日本") == 7

    def test_empty(self):
        assert display_width("") == 0

    def test_ambiguous_default_width_1(self):
        assert display_width("×") == 1
        assert display_width("※") == 1
        assert display_width("→") == 1

    def test_ambiguous_cjk_mode_width_2(self):
        assert display_width("×", cjk_mode=True) == 2
        assert display_width("※", cjk_mode=True) == 2
        assert display_width("→", cjk_mode=True) == 2

    def test_narrow_cjk_mode_still_width_1(self):
        assert display_width("A", cjk_mode=True) == 1
        assert display_width("hello", cjk_mode=True) == 5

    def test_wide_cjk_mode_still_width_2(self):
        assert display_width("日", cjk_mode=True) == 2
        assert display_width("日本語", cjk_mode=True) == 6

    def test_mixed_cjk_mode(self):
        # × (A=2) + 口 (W=2) + a (Na=1) = 5
        assert display_width("×口a", cjk_mode=True) == 5


class TestPad:
    def test_ascii_padding(self):
        assert pad("hello", 10) == "hello     "

    def test_fullwidth_padding(self):
        assert pad("日本語", 10) == "日本語    "

    def test_exact_width(self):
        assert pad("hello", 5) == "hello"

    def test_cjk_mode_pads_ambiguous_as_width_2(self):
        # × is treated as width 2, target 6 -> 4 spaces padding
        assert pad("×", 6, cjk_mode=True) == "×    "

    def test_cjk_mode_default_pads_ambiguous_as_width_1(self):
        # × is treated as width 1, target 6 -> 5 spaces padding
        assert pad("×", 6) == "×     "


class TestReplaceAmbiguousChars:
    def test_right_arrow(self):
        assert replace_ambiguous_chars("→") == "->"

    def test_left_arrow(self):
        assert replace_ambiguous_chars("←") == "<-"

    def test_up_arrow(self):
        assert replace_ambiguous_chars("↑") == "^"

    def test_down_arrow(self):
        assert replace_ambiguous_chars("↓") == "v"

    def test_double_right_arrow(self):
        assert replace_ambiguous_chars("⇒") == "=>"

    def test_double_left_arrow(self):
        assert replace_ambiguous_chars("⇐") == "<="

    def test_multiplication(self):
        assert replace_ambiguous_chars("×") == "x"

    def test_plus_minus(self):
        assert replace_ambiguous_chars("±") == "+/-"

    def test_division(self):
        assert replace_ambiguous_chars("÷") == "/"

    def test_less_equal(self):
        assert replace_ambiguous_chars("≤") == "<="

    def test_greater_equal(self):
        assert replace_ambiguous_chars("≥") == ">="

    def test_not_equal(self):
        assert replace_ambiguous_chars("≠") == "!="

    def test_approx_equal(self):
        assert replace_ambiguous_chars("≈") == "~="

    def test_identical(self):
        assert replace_ambiguous_chars("≡") == "=="

    def test_ellipsis(self):
        assert replace_ambiguous_chars("…") == "..."

    def test_em_dash(self):
        assert replace_ambiguous_chars("—") == "--"

    def test_en_dash(self):
        assert replace_ambiguous_chars("–") == "-"

    def test_left_double_quote(self):
        assert replace_ambiguous_chars("“") == '"'

    def test_right_double_quote(self):
        assert replace_ambiguous_chars("”") == '"'

    def test_left_single_quote(self):
        assert replace_ambiguous_chars("‘") == "'"

    def test_right_single_quote(self):
        assert replace_ambiguous_chars("’") == "'"

    def test_reference_mark(self):
        assert replace_ambiguous_chars("※") == "*"

    def test_mixed_text(self):
        assert replace_ambiguous_chars("a → b × c") == "a -> b x c"

    def test_no_ambiguous_chars(self):
        assert replace_ambiguous_chars("hello world") == "hello world"

    def test_cjk_unchanged(self):
        assert replace_ambiguous_chars("日本語") == "日本語"

    def test_empty(self):
        assert replace_ambiguous_chars("") == ""


class TestFormatMdTable:
    def test_ascii_table(self):
        input_text = textwrap.dedent("""\
            | Name | Age |
            |---|---|
            | Alice | 30 |""")
        expected = textwrap.dedent("""\
            | Name  | Age |
            | ----- | --- |
            | Alice | 30  |""")
        assert format_md_table(input_text) == expected

    def test_cjk_mixed_table(self):
        input_text = textwrap.dedent("""\
            | 名前 | 説明 |
            |---|---|
            | fields[0] | NTT支店名 |""")
        expected = textwrap.dedent("""\
            | 名前      | 説明      |
            | --------- | --------- |
            | fields[0] | NTT支店名 |""")
        assert format_md_table(input_text) == expected

    def test_separator_width_adjustment(self):
        input_text = textwrap.dedent("""\
            | A | BB |
            |---|---|
            | CCC | D |""")
        expected = textwrap.dedent("""\
            | A   | BB |
            | --- | -- |
            | CCC | D  |""")
        assert format_md_table(input_text) == expected

    def test_invalid_input_returns_as_is(self):
        input_text = "This is not a table"
        assert format_md_table(input_text) == input_text

    def test_replaces_ambiguous_chars_in_cells(self):
        input_text = textwrap.dedent("""\
            | A | B |
            |---|---|
            | foo→bar | 3×4 |""")
        expected = textwrap.dedent("""\
            | A        | B   |
            | -------- | --- |
            | foo->bar | 3x4 |""")
        assert format_md_table(input_text) == expected

    def test_replaces_ambiguous_chars_in_header(self):
        input_text = textwrap.dedent("""\
            | A→B | C |
            |---|---|
            | x | y |""")
        expected = textwrap.dedent("""\
            | A->B | C |
            | ---- | - |
            | x    | y |""")
        assert format_md_table(input_text) == expected

    def test_strips_cell_whitespace(self):
        input_text = textwrap.dedent("""\
            |  Name  |  Age  |
            |---|---|
            |  Alice  |  30  |""")
        expected = textwrap.dedent("""\
            | Name  | Age |
            | ----- | --- |
            | Alice | 30  |""")
        assert format_md_table(input_text) == expected

    def test_cjk_mode_preserves_multiplication_sign(self):
        input_text = textwrap.dedent("""\
            | A | B |
            |---|---|
            | × | 口 |""")
        result = format_md_table(input_text, cjk_mode=True)
        assert "×" in result
        # Ensure × did not get replaced with x in the cell
        assert "| x " not in result

    def test_cjk_mode_preserves_reference_mark(self):
        input_text = textwrap.dedent("""\
            | id | note |
            |---|---|
            | 1 | ※注 |""")
        result = format_md_table(input_text, cjk_mode=True)
        assert "※" in result
        assert "*" not in result

    def test_cjk_mode_aligns_ambiguous_as_width_2(self):
        # In cjk_mode, × (A) is width 2, 口 (W) is width 2
        # col1: max("A"=1, "×"=2) = 2 -> "A " / "×"
        # col2: max("B"=1, "口"=2) = 2 -> "B " / "口"
        input_text = textwrap.dedent("""\
            | A | B |
            |---|---|
            | × | 口 |""")
        expected = textwrap.dedent("""\
            | A  | B  |
            | -- | -- |
            | ×  | 口 |""")
        # Note: pad("×", 2, cjk_mode=True) = "×" + " " * (2-2) = "×"
        # But "| " + "×" + " | " = "| × | " - actually format is "| " + part + " | "
        # so cell "×" becomes "| × |" with no trailing pad - hmm let me reconsider
        # Actually pad("×", 2, cjk_mode=True) returns "×" (no padding needed since width already 2)
        # Then format becomes "| × | 口 |"
        # While "| A  | B  |" has "A " padded to width 2
        # These differ in char count but match in CJK visual width
        expected = textwrap.dedent("""\
            | A  | B  |
            | -- | -- |
            | × | 口 |""")
        assert format_md_table(input_text, cjk_mode=True) == expected

    def test_cjk_mode_false_still_replaces(self):
        # Explicit cjk_mode=False should behave identically to omitting the arg
        input_text = textwrap.dedent("""\
            | A | B |
            |---|---|
            | × | 口 |""")
        expected_default = format_md_table(input_text)
        expected_explicit = format_md_table(input_text, cjk_mode=False)
        assert expected_default == expected_explicit
        # × should have been replaced with x in the explicit form
        assert "x" in expected_explicit
        assert "×" not in expected_explicit


class TestFormatMdTableAlignment:
    def test_preserves_left_alignment(self):
        input_text = textwrap.dedent("""\
            | Name | Age |
            | :--- | :--- |
            | Alice | 30 |""")
        expected = textwrap.dedent("""\
            | Name  | Age |
            | :---- | :-- |
            | Alice | 30  |""")
        assert format_md_table(input_text) == expected

    def test_preserves_right_alignment(self):
        input_text = textwrap.dedent("""\
            | Name | Age |
            | ---: | ---: |
            | Alice | 30 |""")
        expected = textwrap.dedent("""\
            | Name  | Age |
            | ----: | --: |
            | Alice | 30  |""")
        assert format_md_table(input_text) == expected

    def test_preserves_center_alignment(self):
        input_text = textwrap.dedent("""\
            | Name | Age |
            | :---: | :---: |
            | Alice | 30 |""")
        expected = textwrap.dedent("""\
            | Name  | Age |
            | :---: | :-: |
            | Alice | 30  |""")
        assert format_md_table(input_text) == expected

    def test_preserves_mixed_alignment(self):
        input_text = textwrap.dedent("""\
            | A | 日本語カラム | c |
            | :- | -: | :-: |
            | 1 | あいうえお | x |
            | 22 | か | yy |""")
        expected = textwrap.dedent("""\
            | A  | 日本語カラム | c   |
            | :- | -----------: | :-: |
            | 1  | あいうえお   | x   |
            | 22 | か           | yy  |""")
        assert format_md_table(input_text) == expected

    def test_no_colons_stays_plain(self):
        # Regression guard: tables without alignment markers keep bare dashes
        input_text = textwrap.dedent("""\
            | A | B |
            |---|---|
            | x | y |""")
        expected = textwrap.dedent("""\
            | A | B |
            | - | - |
            | x | y |""")
        assert format_md_table(input_text) == expected

    def test_center_alignment_widens_narrow_column(self):
        # ":-:" needs 3 chars, so a width-1 column must widen to 3
        input_text = textwrap.dedent("""\
            | A | B |
            | :-: | :-: |
            | x | y |""")
        expected = textwrap.dedent("""\
            | A   | B   |
            | :-: | :-: |
            | x   | y   |""")
        assert format_md_table(input_text) == expected

    def test_side_alignment_widens_narrow_column(self):
        # ":-" and "-:" need 2 chars, so a width-1 column must widen to 2
        input_text = textwrap.dedent("""\
            | A | B |
            | :- | -: |
            | x | y |""")
        expected = textwrap.dedent("""\
            | A  | B  |
            | :- | -: |
            | x  | y  |""")
        assert format_md_table(input_text) == expected

    def test_alignment_with_cjk_mode(self):
        # col1: max("記号"=4, "×"=2) = 4, centered -> ":--:"
        # col2: max("意味"=4, "不可"=4) = 4, right -> "---:"
        input_text = textwrap.dedent("""\
            | 記号 | 意味 |
            | :-: | ---: |
            | × | 不可 |""")
        expected = textwrap.dedent("""\
            | 記号 | 意味 |
            | :--: | ---: |
            | ×   | 不可 |""")
        assert format_md_table(input_text, cjk_mode=True) == expected


class TestFormatMdTablesInText:
    def test_single_table_in_document(self):
        input_text = textwrap.dedent("""\
            # Title

            Some text.

            | Name | Age |
            |---|---|
            | Alice | 30 |

            More text.""")
        expected = textwrap.dedent("""\
            # Title

            Some text.

            | Name  | Age |
            | ----- | --- |
            | Alice | 30  |

            More text.""")
        assert format_md_tables_in_text(input_text) == expected

    def test_preserves_alignment_in_document(self):
        input_text = textwrap.dedent("""\
            # Doc

            | A | BB |
            | ---: | :-: |
            | CCC | D |

            End.""")
        expected = textwrap.dedent("""\
            # Doc

            | A   | BB  |
            | --: | :-: |
            | CCC | D   |

            End.""")
        assert format_md_tables_in_text(input_text) == expected

    def test_multiple_tables_in_document(self):
        input_text = textwrap.dedent("""\
            # Doc

            | A | B |
            |---|---|
            | C | D |

            Paragraph.

            | 名前 | 値 |
            |---|---|
            | X | Y |""")
        expected = textwrap.dedent("""\
            # Doc

            | A | B |
            | - | - |
            | C | D |

            Paragraph.

            | 名前 | 値 |
            | ---- | -- |
            | X    | Y  |""")
        assert format_md_tables_in_text(input_text) == expected

    def test_no_tables(self):
        input_text = "# Title\n\nJust text.\n"
        assert format_md_tables_in_text(input_text) == input_text

    def test_ambiguous_chars_outside_tables_unchanged(self):
        input_text = textwrap.dedent("""\
            # Title

            Arrow → here in paragraph.

            | A | B |
            |---|---|
            | foo→bar | bar |""")
        expected = textwrap.dedent("""\
            # Title

            Arrow → here in paragraph.

            | A        | B   |
            | -------- | --- |
            | foo->bar | bar |""")
        assert format_md_tables_in_text(input_text) == expected

    def test_table_inside_code_block_untouched(self):
        input_text = textwrap.dedent("""\
            # Doc

            ```
            | A | B |
            |---|---|
            | C | D |
            ```

            | E | F |
            |---|---|
            | G | H |""")
        expected = textwrap.dedent("""\
            # Doc

            ```
            | A | B |
            |---|---|
            | C | D |
            ```

            | E | F |
            | - | - |
            | G | H |""")
        assert format_md_tables_in_text(input_text) == expected

    def test_cjk_mode_preserves_in_document(self):
        input_text = textwrap.dedent("""\
            # Doc

            | char | meaning |
            |---|---|
            | × | corrupted |""")
        result = format_md_tables_in_text(input_text, cjk_mode=True)
        assert "×" in result
        # × should not have been replaced with x in the table cell
        assert "| x " not in result

    def test_cjk_mode_default_replaces_in_document(self):
        input_text = textwrap.dedent("""\
            # Doc

            | char | meaning |
            |---|---|
            | × | corrupted |""")
        # Explicit cjk_mode=False matches omission
        assert format_md_tables_in_text(input_text, cjk_mode=False) == format_md_tables_in_text(input_text)
        # And × is replaced
        result = format_md_tables_in_text(input_text)
        assert "×" not in result
        assert "x" in result


class TestFormatMarkdownFile:
    def test_rejects_rst_file(self):
        with tempfile.NamedTemporaryFile(suffix=".rst", delete=False) as f:
            path = pathlib.Path(f.name)
        try:
            result = format_markdown_file(str(path))
            assert "Error" in result
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_txt_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            path = pathlib.Path(f.name)
        try:
            result = format_markdown_file(str(path))
            assert "Error" in result
        finally:
            path.unlink(missing_ok=True)

    def test_accepts_md_file(self):
        content = "| A | B |\n|---|---|\n| C | D |\n"
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = pathlib.Path(f.name)
        try:
            result = format_markdown_file(str(path))
            assert "Error" not in result
        finally:
            path.unlink(missing_ok=True)

    def test_cjk_mode_preserves_ambiguous_in_file(self):
        content = "| id | char |\n|---|---|\n| 1 | × |\n"
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = pathlib.Path(f.name)
        try:
            result = format_markdown_file(str(path), cjk_mode=True)
            assert "Error" not in result
            written = path.read_text(encoding="utf-8")
            assert "×" in written
        finally:
            path.unlink(missing_ok=True)

    def test_cjk_mode_default_replaces_in_file(self):
        content = "| id | char |\n|---|---|\n| 1 | × |\n"
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(content)
            path = pathlib.Path(f.name)
        try:
            format_markdown_file(str(path))
            written = path.read_text(encoding="utf-8")
            assert "×" not in written
            assert "x" in written
        finally:
            path.unlink(missing_ok=True)
