# MercadonaMCP

> Status: pre-alpha, personal macOS MVP under development.

MercadonaMCP is an unofficial, privacy-first MCP companion for searching
Mercadona Online products and managing a user's cart from ChatGPT.

It is not affiliated with, endorsed by, or supported by Mercadona or OpenAI.

## Development bootstrap

```bash
uv sync --locked
uv run ruff check .
uv run mypy src tests
uv run pytest
```
