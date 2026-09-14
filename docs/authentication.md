# Authentication and secret storage

## Mercadona login

Run `uv run mercadona login`. MercadonaMCP starts a dedicated, visible Google
Chrome instance at `https://tienda.mercadona.es`; the user completes
Mercadona email/password, Google, and any second-factor flow directly in that
browser.

The companion permits only `tienda.mercadona.es` and `accounts.google.com`
during this flow. It reads the observed `MO-user` browser local-storage value
only from a Mercadona page, retains only `token` and `userUuid`, validates the
session with a cart read, then closes the browser context.

## Keychain lifecycle

The session is stored as one redacted Keychain secret under service
`com.mercadona-mcp` and key `mercadona-session`. `mercadona auth status` only
reports whether a usable session is present. `uv run mercadona logout` deletes
the local session from Keychain.

Do not export, print, copy into fixtures, or commit the stored session.

## Tunnel authentication

The tunnel runtime API key is distinct from Mercadona session material. The
repository launcher loads it at runtime from the local login Keychain item
`mercadona-mcp-control-plane-api-key` and supplies it as
`CONTROL_PLANE_API_KEY` only to `tunnel-client`. See
[chatgpt-web.md](chatgpt-web.md).
