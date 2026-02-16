# MCP Markdown Table Formatter 実装計画書

## 概要

Claude Code が出力する Markdown テーブルの列幅を、全角/半角文字の表示幅を考慮して自動的に揃える MCP サーバーを Python で実装する。

## 背景と目的

- Markdown テーブルを直接エディタで表示した際、全角文字(日本語)と半角文字が混在すると列幅がずれる
- Claude のテキスト生成では正確な表示幅計算ができないため、プログラム的な整形が必要
- MCP サーバーとして実装することで、CLAUDE.md の指示と組み合わせて全プロジェクトで自動的に適用可能にする

## 技術選定

| 項目         | 選定             | 理由                                                     |
| ------------ | ---------------- | -------------------------------------------------------- |
| 言語         | Python 3.12      | unicodedata が標準ライブラリにあり外部依存を最小化できる |
| MCP SDK      | mcp (PyPI)       | Anthropic 公式の Python MCP SDK                          |
| パッケージ管理 | uv/uvx         | 環境に既にインストール済み、仮想環境不要で実行可能       |
| 通信方式     | stdio            | Claude Code のローカル MCP サーバー標準方式              |

## ディレクトリ構成

```
~/.claude/mcp-servers/md-table-formatter/
  pyproject.toml
  server.py
```

全プロジェクト共通で使うため `~/.claude/` 配下に配置する。

## 実装詳細

### 1. MCP ツール定義

ツール名: `format_md_table`

- 入力: Markdown テーブル文字列(パイプ区切りの複数行テキスト)
- 出力: 列幅を揃えた Markdown テーブル文字列

```
入力例:
| 名前 | 説明 |
|---|---|
| fields[0] | NTT支店名 |

出力例:
| 名前      | 説明      |
| --------- | --------- |
| fields[0] | NTT支店名 |
```

### 2. コアロジック

- `unicodedata.east_asian_width()` で文字幅を判定(F, W = 幅2、それ以外 = 幅1)
- 各列の最大表示幅を算出
- セパレータ行は最大幅に合わせてハイフンを生成
- 各セルを表示幅ベースでパディング
- アライメントは左寄せ固定
- パイプ `|` の前後は 1 スペース固定

### 3. pyproject.toml

- 依存: `mcp` (Anthropic 公式 MCP SDK)、`pytest` (テスト用)
- unicodedata は標準ライブラリのため追加不要
- コンソールスクリプト: `md-table-formatter = "server:main"` (`uvx --from` で起動するため必要)

### 4. server.py 構成

```
server.py
  - display_width(s: str) -> int       # 文字列の表示幅を計算
  - pad(s: str, width: int) -> str      # 表示幅ベースの右パディング
  - format_md_table(text: str) -> str   # テーブル整形メイン処理
  - MCP サーバー定義(stdio transport)  # ツール登録と起動
```

## 登録設定

### ~/.claude/settings.json への追記

```json
{
  "mcpServers": {
    "md-table-formatter": {
      "command": "uvx",
      "args": ["--from", "$HOME/.claude/mcp-servers/md-table-formatter", "md-table-formatter"],
      "type": "stdio"
    }
  }
}
```

### ~/.claude/CLAUDE.md への追記

```markdown
### Markdown Table Formatting

- Markdown の table を出力する際は、必ず format_md_table ツールで整形してから出力する
```

## テスト方針

TDD に従い、以下の順序で進める。

### テスト対象

1. display_width: 半角のみ、全角のみ、混在文字列の幅計算
2. pad: 半角文字列のパディング、全角混在文字列のパディング
3. format_md_table:
   - 半角のみのテーブル
   - 全角混在テーブル
   - セパレータ行の幅調整
   - 列数が異なる不正入力のハンドリング

### テストファイル

```
~/.claude/mcp-servers/md-table-formatter/
  tests/
    test_formatter.py
```

## 実装手順

1. ディレクトリ作成と pyproject.toml の記述
2. テストファイル (test_formatter.py) を作成
3. テスト実行 -> 失敗を確認 -> コミット
4. server.py のコアロジック (display_width, pad, format_md_table) を実装
5. テスト実行 -> 全パスを確認 -> コミット
6. MCP サーバー部分(ツール登録、stdio transport)を実装
7. settings.json に MCP サーバーを登録
8. CLAUDE.md にテーブル整形ルールを追記
9. Claude Code を再起動して動作確認
