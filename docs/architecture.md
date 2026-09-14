# Architecture

MercadonaMCP is a local Python companion with two entry points:

- `mercadona`: a Typer CLI for login, status, catalog reads, cart reads, and
  explicitly confirmed local cart writes.
- `mercadona-mcp`: a FastMCP server using STDIO.

```text
ChatGPT Web -- Secure MCP Tunnel -- tunnel-client -- STDIO -- mercadona-mcp
                                                        |
                                                        +-- macOS Keychain
                                                        |
                                                        +-- Mercadona HTTPS APIs
```

The tunnel client launches the STDIO MCP command. Do not separately run
`uv run mercadona-mcp` while `tunnel-client` is managing that profile.

## Components

| Component | Responsibility |
| --- | --- |
| `companion.login` | Opens dedicated Chrome, waits for a valid Mercadona session, validates it, and persists minimized session material. |
| `security.keychain` | Secret-store interface, macOS Keychain adapter, in-memory test fake, and redacted secret wrapper. |
| `mercadona.catalog` | Public catalog and delivery-area reads, retries, and normalized product models. |
| `mercadona.auth` | Authenticated HTTPS requests constrained to `https://tienda.mercadona.es`. |
| `mercadona.cart` | Normalized authenticated cart read. |
| `mercadona.mutation` | Version-checked, absolute, idempotent cart updates with post-write verification. |
| `mcp.server` | Typed `auth_status`, catalog, cart-read, and cart-update MCP tools. |

The in-memory operation replay cache is shared by MCP tool invocations in one
server process and retains entries for ten minutes. It is intentionally not a
database.
