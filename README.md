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

## ChatGPT Web development tunnel

The private Developer Mode integration uses OpenAI's official
`tunnel-client`. Its runtime API key and tunnel ID are local configuration and
must never be committed. The repository provides a Keychain-backed launcher:

```bash
./scripts/mercadona-tunnel doctor --explain
./scripts/mercadona-tunnel run
```

Complete the one-time profile setup and ChatGPT Web smoke test in
[docs/chatgpt-web.md](docs/chatgpt-web.md).
