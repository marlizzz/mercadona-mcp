# Changelog

All notable changes to MercadonaMCP are documented here.

## 0.1.1 — 2026-09-14

- Replaced normal product-search catalog traversal with bounded direct website
  search through a short-lived, isolated headed Chrome context.
- Added a concurrent `search_products_batch` MCP tool for up to ten concise
  Spanish product phrases, with deduplication, per-query limits, retries,
  timeouts, and partial-failure results.
- Preserved catalog product-detail reads and all cart safety boundaries.

## 0.1.0 — 2026-09-14

Initial personal macOS MVP.

- Dedicated, visible Chrome login with minimized Mercadona session persistence
  in macOS Keychain.
- Delivery-area catalog search and product details.
- Authenticated cart reads and exact final-quantity cart updates with version
  checks, idempotent operation IDs, and post-write verification.
- FastMCP tools for local STDIO and private ChatGPT Web development through
  OpenAI Secure MCP Tunnel.
- Offline contract, security, and end-to-end regression coverage; CI includes
  linting, type checking, package build, dependency review, and secret scans.
- Architecture, security, threat-model, manual-testing, and development docs.

This release is not a public Plugin Directory submission and does not provide
checkout, order placement, payment, or delivery-slot functionality.
