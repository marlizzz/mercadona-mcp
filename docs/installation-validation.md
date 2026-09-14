# Installation validation

Use this checklist from a fresh local clone before treating a build as a
personal-MVP release candidate. It intentionally does not log into Mercadona,
start a tunnel, or perform a live cart write.

## Clean checkout commands

```bash
git clone <repository-url> mercadona-mcp
cd mercadona-mcp
uv sync --locked --all-groups
uv run playwright install chrome
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

Expected results:

- `uv sync --locked` completes without updating `uv.lock`.
- Ruff and mypy exit successfully.
- Pytest passes without external network calls, Keychain secrets, Chrome login,
  or a Mercadona account.
- `uv build` produces an sdist and wheel under the ignored `dist/` directory.

## Package metadata checks

```bash
uv run mercadona --help
uv run python -c 'from mercadona_mcp.mcp.server import mcp; print("MercadonaMCP MCP loaded")'
```

The first command must show the local companion CLI. The second confirms that
the MCP server module imports without starting the STDIO transport.

## Deliberately separate live validation

Mercadona login, catalog/cart reads, controlled cart writes, and ChatGPT Web
tunnel checks are manual opt-in tests. Follow
[manual-testing.md](manual-testing.md); do not fold those actions into an
installation check or CI.
