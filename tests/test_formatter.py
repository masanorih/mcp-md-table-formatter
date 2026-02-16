"""Tests for Markdown table formatter core logic."""

import textwrap

from server import display_width, format_md_table, format_md_tables_in_text, pad


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
