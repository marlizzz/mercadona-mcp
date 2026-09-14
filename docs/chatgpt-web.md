# ChatGPT Web development setup

This private macOS development setup connects ChatGPT Web to the local
MercadonaMCP STDIO server through OpenAI's official `tunnel-client`. It is not
a public deployment. The Mac, this tunnel process, and the internet must be
available for ChatGPT to use the tools.

## What stays local

- Mercadona session material is stored by MercadonaMCP in macOS Keychain.
- The OpenAI tunnel runtime API key is stored separately in macOS Keychain.
- The tunnel ID and runtime API key are local configuration. Do not commit,
  paste, log, or screenshot them.

## One-time setup

Install OpenAI's `tunnel-client` and create a tunnel in the OpenAI Tunnels
settings. Create a separate runtime API key with **Tunnels Read + Use**; do
not use an administrative API key for the local daemon.

In the tunnel's settings, associate it with both the Platform organization that
owns it and the target ChatGPT workspace. A tunnel that is associated only
with a Platform organization will not appear in ChatGPT's Tunnel picker. The
user creating the ChatGPT app also needs **Tunnels Read + Use**. If the
Platform organization and ChatGPT workspace cannot be linked in the settings
UI, request an OpenAI-reviewed manual association override; creating another
tunnel does not fix a missing workspace association.

Save the runtime API key into the local login Keychain. The first command
accepts the key without echoing it:

```zsh
read -rs "CONTROL_PLANE_API_KEY?Paste runtime API key, then press Enter: "; echo
security add-generic-password -U -a "$USER" -s "mercadona-mcp-control-plane-api-key" -w "$CONTROL_PLANE_API_KEY"
unset CONTROL_PLANE_API_KEY
```

Create the local STDIO tunnel profile. Replace the placeholder locally; do not
put its value in any repository file:

```zsh
tunnel-client init \
  --sample sample_mcp_stdio_local \
  --profile mercadona-mcp \
  --tunnel-id 'tunnel_…' \
  --mcp-command "uv run mercadona-mcp"
```

The profile belongs to `tunnel-client`, outside this repository. It starts the
Python MCP process itself, so do not separately run `uv run mercadona-mcp` in
another terminal.

## Normal use

From the repository root, validate the local setup:

```zsh
./scripts/mercadona-tunnel doctor --explain
```

Then start the foreground tunnel and leave that terminal open:

```zsh
./scripts/mercadona-tunnel run
```

The wrapper reads the runtime key from macOS Keychain at launch and exports
`CONTROL_PLANE_API_KEY` only into the `tunnel-client` process. It never writes
the secret to the repository or a shell profile.

## Connect ChatGPT Web

With the tunnel running, open ChatGPT Developer Mode and create or edit the
personal plugin:

1. Select **Tunnel** as the connection type.
2. Enter the local `tunnel_…` ID.
3. Select the non-OAuth / no-authentication option for this private tunnel.
4. Acknowledge the custom-server warning and create the plugin.
5. Start a new ChatGPT conversation, enable the plugin, and refresh its tool
   metadata if the UI offers that control.

Do not create or test the connector while the tunnel is stopped.

## Manual read-only smoke test

Before any cart mutation, use a new ChatGPT conversation and ask:

1. `Check whether my Mercadona account is connected.`
2. `Find up to five whole-milk products available in my delivery area. Do not change my cart.`
3. `Show my current Mercadona cart.`

Verify that the plugin exposes only `auth_status`, `search_products`,
`get_product`, `get_cart`, and `update_cart`. Results must not contain session
tokens, cookies, or tunnel credentials.

Only after the read-only checks succeed should a controlled cart-write test be
considered. It must use an explicit final quantity, a fresh cart version, and
the ChatGPT host's confirmation flow.
