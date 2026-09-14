# Manual testing runbook

This runbook uses real external services only after all offline checks pass.
Never paste passwords, tokens, cookies, browser storage, addresses, raw cart
responses, runtime API keys, or tunnel identifiers into logs, issues, or chat.

## 1. Offline checks

```bash
uv sync --locked
uv run ruff check .
uv run mypy src tests
uv run pytest
```

Expected: all commands pass without external network calls or credentials.

## 2. Login and safe status

```bash
uv run mercadona auth status
uv run mercadona login
uv run mercadona auth status
```

Expected: Chrome opens at Mercadona; complete authentication there; the CLI
prints `Connected`; status reports `Connected`. Confirm only that no session
artifact appears in `git status --short`; do not print Keychain content.

## 3. Read-only product, catalog, and cart checks

Use either a five-digit postal code or an already observed warehouse code:

```bash
uv run mercadona search "leche entera" --postal-code 28001 --limit 5
uv run mercadona search "pepino holandés" --postal-code 28001 --limit 5 --json
uv run mercadona product 4241 --postal-code 28001
uv run mercadona cart show
uv run mercadona cart show --json
```

The search command briefly opens an isolated Chrome window and then closes it.
Product ID `4241` is only an example and may not be available in the current
delivery area. These commands do not change the cart.

## 4. Optional controlled cart-write check

Perform only on the user's own account and an inexpensive, explicitly selected
product. Record its product ID and original quantity `Q0` privately. Fetch the
current cart immediately before the write and use its displayed version.

```bash
uv run mercadona cart set PRODUCT_ID Q1 \
  --expected-version CURRENT_VERSION \
  --operation-id controlled-write-1 \
  --allow-live-write
```

Verify the preview, answer the interactive confirmation deliberately, then
check `uv run mercadona cart show`. Restore `Q0` with a new operation ID and a
fresh cart version. Never test checkout, payment, or delivery slots.

## 5. ChatGPT Web read-only smoke test

After the one-time [ChatGPT Web setup](chatgpt-web.md), run:

```bash
./scripts/mercadona-tunnel doctor --explain
./scripts/mercadona-tunnel run
```

Keep the second command running. In a new ChatGPT conversation with
MercadonaMCP enabled, ask:

1. `Check whether my Mercadona account is connected.`
2. `Find up to five whole-milk products and one cucumber option in my delivery area. Do not change my cart.`
3. `Show my current Mercadona cart.`

Before any ChatGPT cart write, ensure the host displays the exact final
quantity and asks for confirmation. If it does not, stop testing writes.

## 6. Logout and cleanup

```bash
uv run mercadona logout
uv run mercadona auth status
uv run pytest
```

Expected: status reports `Not connected`; the default test suite still passes.
