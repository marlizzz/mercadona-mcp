"""Read-only FastMCP server for MercadonaMCP."""

from mcp.server.fastmcp import FastMCP

from mercadona_mcp.companion.session import load_session
from mercadona_mcp.errors import MercadonaMCPError
from mercadona_mcp.mercadona.auth import AuthenticatedMercadonaClient
from mercadona_mcp.mercadona.cart import CartClient
from mercadona_mcp.mercadona.catalog import CatalogClient
from mercadona_mcp.security import KeychainSecretStore

mcp = FastMCP(
    "MercadonaMCP",
    instructions=(
        "Use read-only tools to inspect Mercadona products and carts. "
        "Never claim a cart change occurred unless a mutation tool returns success."
    ),
)


@mcp.tool()
async def auth_status() -> dict[str, bool]:
    """Return whether a usable local Mercadona session is available."""
    try:
        return {"connected": load_session(KeychainSecretStore()) is not None}
    except MercadonaMCPError:
        return {"connected": False}


@mcp.tool()
async def search_products(
    query: str, warehouse: str, limit: int = 10
) -> list[dict[str, object]]:
    """Search products available in one opaque Mercadona warehouse code."""
    async with CatalogClient() as client:
        products = await client.search_products(query, warehouse=warehouse, limit=limit)
    return [product.model_dump(mode="json") for product in products]


@mcp.tool()
async def get_product(product_id: str, warehouse: str) -> dict[str, object]:
    """Get normalized details for one product in an opaque warehouse code."""
    async with CatalogClient() as client:
        product = await client.get_product(product_id, warehouse=warehouse)
    return product.model_dump(mode="json")


@mcp.tool()
async def get_cart() -> dict[str, object]:
    """Read the current authenticated Mercadona cart without changing it."""
    async with AuthenticatedMercadonaClient(KeychainSecretStore()) as client:
        cart = await CartClient(client).get_cart()
    return cart.model_dump(mode="json")


def main() -> None:
    """Run the MCP server over STDIO."""
    mcp.run(transport="stdio")
