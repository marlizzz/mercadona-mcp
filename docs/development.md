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

## Bounded product-search contract

Normal product search must never traverse catalog categories. It uses an
isolated, short-lived visible Chrome context to issue the website's observed
read-only request:

```text
GET https://tornillos.mercadona.es/search?q=<Spanish phrase>&wh=<warehouse>&lang=es
```

The provider rejects the equivalent `httpx` transport, so do not add a raw HTTP
fallback or capture browser credentials, cookies, or provider API keys. The
browser context is not the user's normal Chrome profile and is closed after the
request. No response body, headers, or browser state belongs in logs or tests.

`search_products` accepts one concise Spanish phrase and returns five candidates
by default (ten maximum). `search_products_batch` accepts at most ten keyed
phrases, deduplicates equivalent phrases, runs at most four at once, retries a
transient failure once, and returns successful candidates even if another query
fails. Empty phrases are rejected locally. A non-empty phrase may still produce
fuzzy provider matches; callers must inspect candidates before choosing an ID.

## Local commands

```bash
uv run mercadona --help
uv run mercadona-mcp
```

Use `uv run mercadona-mcp` only for direct local STDIO work. For ChatGPT Web,
follow [chatgpt-web.md](chatgpt-web.md), which uses the official tunnel client
to launch the command.
