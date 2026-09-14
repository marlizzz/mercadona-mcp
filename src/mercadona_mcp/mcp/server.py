"""Read-only FastMCP server for MercadonaMCP."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from mercadona_mcp.companion.session import load_session
from mercadona_mcp.errors import MercadonaMCPError
from mercadona_mcp.mercadona.auth import AuthenticatedMercadonaClient
from mercadona_mcp.mercadona.cart import CartClient
from mercadona_mcp.mercadona.catalog import CatalogClient
from mercadona_mcp.mercadona.mutation import CartMutationClient, OperationCache
from mercadona_mcp.mercadona.search import BrowserProductSearchClient
from mercadona_mcp.models import (
    CartChange,
    CartMutation,
    CartVersion,
    ProductSearchQuery,
)
from mercadona_mcp.security import KeychainSecretStore

mcp = FastMCP(
    "MercadonaMCP",
    instructions=(
        "Use read-only tools to inspect Mercadona products and carts. "
        "Never claim a cart change occurred unless a mutation tool returns success."
    ),
)
_operation_cache: OperationCache = {}


@mcp.tool()
async def auth_status() -> dict[str, bool]:
    """Return whether a usable local Mercadona session is available."""
    try:
        return {"connected": load_session(KeychainSecretStore()) is not None}
    except MercadonaMCPError:
        return {"connected": False}


@mcp.tool()
async def search_products(
    query: Annotated[str, Field(min_length=1)],
    warehouse: Annotated[str, Field(min_length=1)],
    limit: Annotated[int, Field(ge=1, le=10)] = 5,
) -> list[dict[str, object]]:
    """Search one concise Spanish product phrase; never send a full instruction.

    Use product nouns and important constraints, for example ``helado chocolate``
    or ``pepino holandés``. For several products use ``search_products_batch``.
    For conceptual requests, try a few plausible Spanish phrases. This tool never
    traverses the complete catalogue as a fallback.
    """
    products = await BrowserProductSearchClient().search_products(
        query, warehouse=warehouse, limit=limit
    )
    return [product.model_dump(mode="json") for product in products]


@mcp.tool()
async def search_products_batch(
    queries: Annotated[list[ProductSearchQuery], Field(min_length=1, max_length=10)],
    warehouse: Annotated[str, Field(min_length=1)],
) -> dict[str, object]:
    """Search several concise Spanish product phrases concurrently and independently.

    Use one query per requested product or product family. Preserve each caller
    key, inspect candidates before selecting a product ID, and do not submit a
    whole shopping instruction as one query. A failure for one query is returned
    in that query's result without discarding successful candidates.
    """
    result = await BrowserProductSearchClient().search_batch(
        queries, warehouse=warehouse
    )
    return result.model_dump(mode="json")


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


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
async def update_cart(
    items: list[CartChange], expected_cart_version: str, operation_id: str
) -> dict[str, object]:
    """Set exact final quantities after the host obtains explicit user confirmation."""
    async with AuthenticatedMercadonaClient(KeychainSecretStore()) as client:
        result = await CartMutationClient(client, _operation_cache).update_cart(
            CartMutation(
                changes=tuple(items),
                expected_cart_version=CartVersion(value=expected_cart_version),
                operation_id=operation_id,
            )
        )
    return result.model_dump(mode="json")


def main() -> None:
    """Run the MCP server over STDIO."""
    mcp.run(transport="stdio")
