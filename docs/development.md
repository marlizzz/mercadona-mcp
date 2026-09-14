# Development

## Prerequisites

- macOS with an unlocked Keychain session.
- Python 3.12 or newer and `uv`.
- Google Chrome for the visible login flow.
- An optional Mercadona account and supported delivery area for manually
  enabled live checks.

## Install and verify

```bash
uv sync --locked
uv run playwright install chrome
uv run ruff check .
uv run mypy src tests
uv run pytest
```

The default suite is offline: it must not require Chrome, Keychain secrets, a
Mercadona account, or network access. Do not add live credentials or cart
fixtures to tests.

## Local commands

```bash
uv run mercadona --help
uv run mercadona-mcp
```

Use `uv run mercadona-mcp` only for direct local STDIO work. For ChatGPT Web,
follow [chatgpt-web.md](chatgpt-web.md), which uses the official tunnel client
to launch the command.
