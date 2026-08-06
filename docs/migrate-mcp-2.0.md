# mcp 2.0 移行ガイド

このリポジトリは mcp 1.x 系 (`mcp.server.fastmcp.FastMCP`) から mcp 2.0 系 (`mcp.server.mcpserver.MCPServer`) に切り替えた。既に導入済みのユーザは以下の手順で環境を追随させること。

## 症状

古い環境のまま起動しようとすると、uvx 経由の実行で次のエラーが発生する。

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

原因は mcp 2.0 で `mcp.server.fastmcp` が削除されたため。旧コード側の import 文が解決できなくなっている。

## 移行手順

### 1. リポジトリを更新する

```bash
cd <clone した mcp-md-table-formatter のパス>
git pull
```

`server.py` および `pyproject.toml` が更新されていることを確認する。

### 2. uvx キャッシュを refresh する

`pyproject.toml` の依存宣言が `mcp>=2.0` に変更されているため、次回起動時に uvx は自動的に依存を再解決する。ただし古いビルド成果物がキャッシュに残っているケースを避けるため、明示的な refresh を推奨する。

```bash
uvx --refresh --from <clone パス> md-table-formatter < /dev/null
```

エラーなく起動できれば OK。Ctrl+C で終了する。

### 3. MCP クライアントを再起動する

Claude Code その他の MCP クライアントを再起動して、更新後のサーバープロセスを掴み直す。

### 4. (開発者のみ) ローカル .venv を同期する

このリポジトリで開発する場合、ローカルの仮想環境も更新する。

```bash
uv lock --upgrade-package mcp
uv sync
uv run pytest
```

すべてのテストが通れば移行完了。

## トラブルシュート

- **`ModuleNotFoundError: mcp.server.fastmcp` がまだ出る**
    - `git log -1` で最新コミットが取り込めているか確認する
    - `uvx --refresh` を付けて再ビルドさせる
- **`mcp<2.0` を別プロジェクトで固定インストールしている**
    - `uv cache clean` でグローバルキャッシュを掃除してから `uvx --refresh` を再実行する
- **Claude Code が古いプロセスを掴んだまま**
    - MCP サーバーを reload するか、Claude Code 自体を再起動する

## 参考: mcp 2.0 における主な変更

- import パス: `mcp.server.fastmcp` から `mcp.server.mcpserver` へ移動
- クラス名: `FastMCP` から `MCPServer` に改名
- `@mcp.tool()` デコレータおよび `mcp.run(transport="stdio")` の API は互換維持
