# Known limitations

MercadonaMCP v0.1.0 is a personal macOS MVP, not a public integration.

- **Platform:** Login support is macOS-only and requires Google Chrome at its
  standard application location.
- **Private tunnel:** ChatGPT Web support requires the user's own Developer
  Mode access, a configured OpenAI Secure MCP Tunnel, and a Mac that stays
  online while tools are used. It is not a publicly reachable service.
- **Observed APIs:** Catalog and cart adapters rely on observed Mercadona web
  behavior, which can change without notice. This is not an official Mercadona
  partner API.
- **Delivery area:** Product availability, price, and catalog results depend on
  the selected delivery area.
- **Confirmation boundary:** The MCP update tool is destructive and relies on
  the host to obtain human confirmation. The server cannot independently prove
  the host displayed a confirmation UI.
- **Replay retention:** Idempotency results are held in the MCP server's memory
  for ten minutes; a restart clears them.
- **No public/multi-user support:** There is no hosted service, account pairing,
  tenant isolation, or public Plugin Directory distribution.
- **Permanent exclusions:** No checkout, order placement, payment data,
  payment-method access, or delivery-slot reservation is implemented.

See [SECURITY.md](../SECURITY.md) and [THREAT_MODEL.md](../THREAT_MODEL.md) for
the corresponding security assumptions and residual risks.
