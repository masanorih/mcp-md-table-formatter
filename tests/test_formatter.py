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


class TestPad:
    def test_ascii_padding(self):
        assert pad("hello", 10) == "hello     "

    def test_fullwidth_padding(self):
        assert pad("日本語", 10) == "日本語    "

    def test_exact_width(self):
        assert pad("hello", 5) == "hello"


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
