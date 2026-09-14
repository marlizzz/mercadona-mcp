# MercadonaMCP

> Status: personal macOS MVP. Unofficial, pre-release software.

MercadonaMCP is a local [Model Context Protocol](https://modelcontextprotocol.io/)
companion for searching Mercadona Online products and reading or carefully
updating a user's cart from the command line or ChatGPT Web.

It is not affiliated with, endorsed by, or supported by Mercadona or OpenAI.
It never checks out, places an order, accesses payment data, or reserves a
delivery slot.

## What it does

- Opens a dedicated, visible Chrome session for the user to log into
  Mercadona; the project does not receive or store the password.
- Keeps minimized Mercadona session material in macOS Keychain.
- Searches the delivery-area-dependent catalog and returns normalized products.
- Reads the authenticated cart.
- Sets exact final cart quantities with version checks, idempotent operation
  IDs, and post-write verification.
- Exposes those capabilities to ChatGPT through a private OpenAI Secure MCP
  Tunnel during development.

## Architecture

```text
ChatGPT Web -- OpenAI Secure MCP Tunnel -- tunnel-client -- STDIO -- MercadonaMCP
                                                                    |
                                                          macOS Keychain
                                                                    |
                                                        Mercadona HTTPS APIs
```

The Mercadona token remains on the Mac. Product and cart data requested in a
ChatGPT conversation necessarily travel through ChatGPT to answer that request.
Read the detailed [architecture](docs/architecture.md),
[data flow](docs/data-flow.md), and [network boundary](docs/network-boundary.md)
before connecting an account.

## Requirements

- macOS with an unlocked login Keychain session.
- Python 3.12+ and [uv](https://docs.astral.sh/uv/).
- Google Chrome.
- A Mercadona Online account in a supported delivery area, for authenticated
  cart use.
- ChatGPT Developer Mode and OpenAI's `tunnel-client`, only for ChatGPT Web
  integration.

## Install

From a checkout of this repository:

```bash
uv sync --locked
uv run playwright install chrome
uv run ruff check .
uv run mypy src tests
uv run pytest
```

The default test suite is offline. It does not need Chrome, a Keychain secret,
a Mercadona account, or network access.

## First local use

Check the starting state, then authenticate in the Chrome window that opens:

```bash
uv run mercadona auth status
uv run mercadona login
uv run mercadona auth status
```

Search products using either a five-digit delivery-area postal code or a known
Mercadona warehouse code:

```bash
uv run mercadona search "leche" --postal-code 28001 --limit 5
uv run mercadona product PRODUCT_ID --postal-code 28001
uv run mercadona cart show
```

`PRODUCT_ID` and postal code must be appropriate for the user's own delivery
area. Catalog reads do not alter the cart.

## Cart updates

Cart updates are deliberately explicit. The CLI requires a live-write opt-in,
a fresh cart version, a caller-provided operation ID, and an interactive
confirmation after showing a preview:

```bash
uv run mercadona cart set PRODUCT_ID FINAL_QUANTITY \
  --expected-version CURRENT_CART_VERSION \
  --operation-id unique-operation-id \
  --allow-live-write
```

`FINAL_QUANTITY` is absolute: `0` removes the product, while `2` means the
cart should contain exactly two. After the write, MercadonaMCP re-reads the
cart and verifies the requested result. Reusing the same operation ID with the
same request returns the prior result instead of making another write.

For a safe manual procedure—including restoring the original quantity—follow
the [manual testing runbook](docs/manual-testing.md). Never use this project
for checkout, payment, delivery-slot, or order-placement workflows.

## ChatGPT Web (private development integration)

The Web integration uses OpenAI's official `tunnel-client`; it is not a public
deployment. Configure a tunnel profile and store its distinct runtime API key
in macOS Keychain as described in [ChatGPT Web setup](docs/chatgpt-web.md).

Normal use is:

```bash
./scripts/mercadona-tunnel doctor --explain
./scripts/mercadona-tunnel run
```

Keep the tunnel process running while creating or using the ChatGPT plugin. The
profile launches `uv run mercadona-mcp` itself, so do not start a second STDIO
server manually.

## MCP tool reference

| Tool | Effect |
| --- | --- |
| `auth_status` | Reports whether a usable local Mercadona session exists. |
| `search_products` | Searches products for an opaque warehouse code. |
| `get_product` | Returns normalized details for one product. |
| `get_cart` | Reads the current authenticated cart. |
| `update_cart` | Destructive: sets absolute quantities after the host obtains confirmation. |

`update_cart` requires `items`, `expected_cart_version`, and `operation_id`.
It is marked destructive in MCP metadata. ChatGPT must display the proposed
change and obtain confirmation before calling it. The server cannot itself
prove that a host rendered a human-confirmation UI; do not enable cart updates
on a host where that assurance is unreliable.

## Security and privacy

- Passwords are entered only on the user-visible Mercadona or Google pages.
- Session material is stored through macOS Keychain; no plaintext session file
  is created by the project.
- The authenticated client only permits HTTPS requests to
  `tienda.mercadona.es`.
- Tool results use normalized models and do not contain tokens, cookies,
  authorization headers, browser state, or raw upstream responses.
- Product names and descriptions are untrusted data, not instructions.

These are implementation boundaries, not a claim that the system is risk-free.
For details, tradeoffs, and reporting guidance, read [SECURITY.md](SECURITY.md)
and [THREAT_MODEL.md](THREAT_MODEL.md).

## Limitations

- macOS and Google Chrome are the only supported login environment.
- Mercadona endpoints are observed web behavior, not a documented partner API;
  they can change or stop working.
- Availability and prices depend on delivery area and can change.
- The tunnel is intended for personal/private development. It is not a public
  hosted MCP endpoint or a Plugin Directory submission path.
- The idempotency replay cache is in memory for ten minutes; restarting the MCP
  server clears it.
- A compromised Mac, browser, Mercadona account, ChatGPT account, or external
  service can exceed the protections of this local project.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `Not connected` | Run `uv run mercadona login`; complete login in the Chrome window. |
| Chrome cannot launch | Confirm Chrome is installed at the standard macOS location and run `uv run playwright install chrome`. |
| Cart version conflict | Read the cart again and retry with its current version; do not overwrite it blindly. |
| Cart-write result is ambiguous | Read the cart and compare requested final quantities before trying another operation ID. |
| ChatGPT cannot reach tools | Keep `./scripts/mercadona-tunnel run` active and run `./scripts/mercadona-tunnel doctor --explain`. |
| Tunnel missing from ChatGPT | Associate the tunnel with the target ChatGPT workspace and confirm **Tunnels Read + Use**; see [ChatGPT Web setup](docs/chatgpt-web.md). |

## Development and documentation

- [Development guide](docs/development.md)
- [Authentication and secret storage](docs/authentication.md)
- [Manual testing runbook](docs/manual-testing.md)
- [ChatGPT Web tunnel setup](docs/chatgpt-web.md)
- [Security policy](SECURITY.md)
- [Threat model](THREAT_MODEL.md)

## License

[MIT](LICENSE)
