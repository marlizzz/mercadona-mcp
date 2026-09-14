# Data flow and privacy

## Login

1. The user enters credentials on Mercadona or Google pages in dedicated Chrome.
2. The companion reads only the validated Mercadona `token` and `userUuid`.
3. It stores that minimized material in macOS Keychain.
4. The companion closes the temporary browser context.

## Read requests

1. The CLI or ChatGPT invokes a catalog or cart-read operation.
2. The local companion makes the required HTTPS request to Mercadona.
3. It normalizes only product/cart fields defined by Pydantic models.
4. For MCP calls, normalized results travel through the OpenAI tunnel to
   ChatGPT. No session token, cookie, authorization header, raw browser state,
   or raw upstream body is included in a tool result.

## Cart update

1. The host shows the proposed exact final quantities and obtains confirmation.
2. `update_cart` reads the current cart and compares its version.
3. It sends an absolute final cart-line representation to Mercadona.
4. It re-reads the cart, verifies requested quantities, and returns before/after
   normalized snapshots.
5. A repeated operation ID with identical input returns the stored result;
   different input is rejected.

Product names and descriptions are untrusted upstream content. They are
returned as data and must never be treated as instructions.
