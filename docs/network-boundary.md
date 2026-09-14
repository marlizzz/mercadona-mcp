# Network boundary

MercadonaMCP does not create a public HTTP listener.

| Origin / destination | Purpose | Data boundary |
| --- | --- | --- |
| `https://tienda.mercadona.es` | Visible login, public catalog reads, authenticated cart reads and updates. | Mercadona session token is sent only as a Bearer authorization header to this origin. |
| `https://tornillos.mercadona.es` | Read-only bounded product search, issued from an isolated Chrome context. | The search request includes only phrase, warehouse, and language; no Mercadona session token is attached. |
| `https://accounts.google.com` | User-managed Google sign-in when selected from Mercadona's login flow. | Credentials are entered in Chrome; MercadonaMCP does not read them. |
| `https://api.openai.com` | OpenAI `tunnel-client` outbound control-plane traffic. | MCP requests and normalized tool results traverse the tunnel; the Mercadona token does not. |
| `127.0.0.1` | Tunnel health/admin surface. | Loopback only; use an ephemeral health port in the local profile to avoid collisions. |

The local authenticated client rejects any base URL other than HTTPS
`tienda.mercadona.es`. The tunnel client must remain running for ChatGPT Web to
discover or invoke the local MCP server.
