# Security policy

MercadonaMCP is a personal macOS development project. It is not a public
service, is not affiliated with Mercadona or OpenAI, and must not be treated as
a payment or ordering integration.

## Security boundaries

- Mercadona passwords are entered only in the user-visible Mercadona or Google
  pages opened by Chrome. MercadonaMCP does not read, submit, log, or persist a
  password.
- The minimum observed session material required for authenticated API calls is
  stored in macOS Keychain under the `com.mercadona-mcp` service. It is never
  written to project files, `.env` files, source, fixtures, or Git.
- The OpenAI tunnel runtime key is a separate macOS Keychain item used only by
  `scripts/mercadona-tunnel`; it is not a Mercadona credential.
- Product and cart data returned by MCP tools pass to ChatGPT when the user
  requests them. Mercadona access tokens do not.
- The project exposes no checkout, ordering, payment, payment-method, or
  delivery-slot tool.

## Cart-write safeguards

`update_cart` accepts absolute final quantities, requires an expected cart
version and opaque operation ID, re-reads the cart after writing, and replays a
matching operation ID without a second write. A reused ID with different input
is rejected.

The MCP tool is marked destructive. ChatGPT is expected to obtain user
confirmation before invocation; the server receives no independently verifiable
human-confirmation token, so do not enable a client or host that cannot provide
reliable confirmation. The local CLI additionally requires
`--allow-live-write`, prints a preview, and prompts interactively.

## Reporting a vulnerability

Do not open a public issue with credentials, tokens, cookies, cart contents,
addresses, screenshots containing private data, or tunnel configuration.
Report the issue privately to the repository owner with a minimal reproduction
and sanitized logs. Rotate a possibly exposed Mercadona session by running
`uv run mercadona logout` and create a new tunnel runtime key if it may have
been exposed.

## Supported scope

The current scope is a personal macOS MVP. Security properties have automated
coverage but no external security audit. Local malware, a compromised macOS
account, a compromised browser, or a compromised ChatGPT/OpenAI/Mercadona
account are outside the protections this project can provide.
