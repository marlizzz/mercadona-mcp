# Threat model

## Assets

- Mercadona session token and user UUID.
- OpenAI tunnel runtime API key and tunnel identifier.
- Cart, product, delivery-area, and conversation data.
- The user's ability to control their Mercadona cart.

## Trust boundaries

```text
User + macOS Keychain
        |
Chrome login / local companion ----> Mercadona HTTPS APIs
        |
        +----> tunnel-client ----> OpenAI tunnel service ----> ChatGPT
```

The Keychain, controlled Chrome context, Python companion, and tunnel client
run on the user's Mac. Mercadona and OpenAI/ChatGPT are external services with
their own security and privacy policies.

## Threats and mitigations

| Threat | Mitigation | Residual risk |
| --- | --- | --- |
| Password capture | Credentials are entered only in user-visible authentic login pages; the companion reads no password fields. | A compromised browser or phishing page can still steal credentials. |
| Token leakage | Keychain persistence, redacted secret representations, no plaintext session artifact, safe normalized tool models. | A compromised local user account can access running-process memory or Keychain after authorization. |
| Prompt injection in product text | Catalog strings are normalized as data and do not alter server control flow or tool registration. | ChatGPT may still display untrusted catalog text to the user. |
| Duplicate cart writes | Absolute quantities, expected version, operation ID cache, post-write verification, ambiguous-write reconciliation. | Cache retention is in memory for 10 minutes; a server restart loses replay history. |
| Stale-cart overwrite | Expected version is checked before the write. | The upstream API contract may change. |
| Unsafe ChatGPT tool use | `update_cart` has destructive metadata and must be called only after host confirmation. | The server cannot cryptographically verify the host's human-confirmation UI. |
| Public exposure of local MCP | Official tunnel client uses an outbound HTTPS path; no public listener is created by this project. | Tunnel availability and access configuration remain an OpenAI account responsibility. |

## Explicit non-goals

Automated checkout, placing orders, payment access, payment-method access,
delivery-slot reservation, hosted multi-user access, and public Plugin
Directory publication are all outside scope.
