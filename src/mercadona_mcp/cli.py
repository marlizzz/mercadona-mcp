"""Command-line entry point for MercadonaMCP."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Annotated

import typer

from mercadona_mcp.companion.login import LoginService
from mercadona_mcp.companion.session import delete_session, load_session
from mercadona_mcp.errors import MercadonaMCPError
from mercadona_mcp.mercadona.auth import AuthenticatedMercadonaClient
from mercadona_mcp.mercadona.cart import CartClient
from mercadona_mcp.mercadona.catalog import CatalogClient
from mercadona_mcp.mercadona.mutation import CartMutationClient
from mercadona_mcp.mercadona.search import BrowserProductSearchClient
from mercadona_mcp.models import (
    CartChange,
    CartMutation,
    CartMutationResult,
    CartSnapshot,
    CartVersion,
    ProductDetails,
    ProductSummary,
)
from mercadona_mcp.security import KeychainSecretStore

app = typer.Typer(
    add_completion=False,
    help="MercadonaMCP local companion.",
    no_args_is_help=True,
)
auth_app = typer.Typer(help="Inspect or clear the local Mercadona session.")
cart_app = typer.Typer(help="Read the current Mercadona cart.")
app.add_typer(auth_app, name="auth")
app.add_typer(cart_app, name="cart")

_catalog_client_factory: Callable[[], CatalogClient] = CatalogClient
_search_client_factory: Callable[[], BrowserProductSearchClient] = (
    BrowserProductSearchClient
)


@app.command()
def login() -> None:
    """Open dedicated Chrome for manual Mercadona authentication."""
    try:
        asyncio.run(LoginService(KeychainSecretStore()).login())
    except MercadonaMCPError as error:
        typer.echo(f"{error.code}: {error.message}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo("Connected")


@auth_app.command("status")
def auth_status() -> None:
    """Report whether a locally stored Mercadona session is available."""
    try:
        connected = load_session(KeychainSecretStore()) is not None
    except MercadonaMCPError:
        connected = False
    typer.echo("Connected" if connected else "Not connected")


@app.command()
def logout() -> None:
    """Delete locally stored Mercadona session material."""
    delete_session(KeychainSecretStore())
    typer.echo("Disconnected")


@cart_app.command("show")
def cart_show(
    json_output: Annotated[
        bool, typer.Option("--json", help="Print normalized JSON.")
    ] = False,
) -> None:
    """Show the current authenticated Mercadona cart without changing it."""
    try:

        async def read_cart() -> CartSnapshot:
            async with AuthenticatedMercadonaClient(KeychainSecretStore()) as client:
                return await CartClient(client).get_cart()

        cart = asyncio.run(read_cart())
    except MercadonaMCPError as error:
        typer.echo(f"{error.code}: {error.message}", err=True)
        raise typer.Exit(code=1) from error
    if json_output:
        typer.echo(json.dumps(cart.model_dump(mode="json"), ensure_ascii=False))
        return
    typer.echo(f"Cart total: {cart.total.amount} {cart.total.currency}")
    for item in cart.items:
        typer.echo(
            f"{item.quantity} × {item.product.name} — {item.line_total.amount} EUR"
        )


def _warehouse_argument(postal_code: str | None, warehouse: str | None) -> str:
    if postal_code and warehouse:
        raise typer.BadParameter("use either --postal-code or --warehouse, not both")
    if not postal_code and not warehouse:
        raise typer.BadParameter("one of --postal-code or --warehouse is required")
    return warehouse or postal_code or ""


async def _with_catalog(
    postal_code: str | None,
    warehouse: str | None,
    action: Callable[
        [CatalogClient, str], Awaitable[ProductDetails | list[ProductSummary]]
    ],
) -> ProductDetails | list[ProductSummary]:
    area = _warehouse_argument(postal_code, warehouse)
    client = _catalog_client_factory()
    try:
        resolved_warehouse = (
            await client.resolve_warehouse(area) if postal_code else area
        )
        return await action(client, resolved_warehouse)
    finally:
        await client.aclose()


def _emit_json(value: ProductDetails | list[ProductSummary]) -> None:
    if isinstance(value, list):
        payload: object = [product.model_dump(mode="json") for product in value]
    else:
        payload = value.model_dump(mode="json")
    typer.echo(json.dumps(payload, ensure_ascii=False))


def _format_price(product: ProductSummary) -> str:
    return f"{product.price.amount} {product.price.currency}"


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Product name or terms to search for.")],
    postal_code: Annotated[
        str | None,
        typer.Option(help="Five-digit delivery-area postal code."),
    ] = None,
    warehouse: Annotated[
        str | None,
        typer.Option(help="Observed Mercadona warehouse code, such as mad3."),
    ] = None,
    limit: Annotated[int, typer.Option(min=1, max=10)] = 5,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print normalized JSON.")
    ] = False,
) -> None:
    """Search a bounded set of products for one delivery area."""

    try:
        selected_warehouse = _warehouse_argument(postal_code, warehouse)
        if postal_code:
            async def resolve_warehouse() -> str:
                client = _catalog_client_factory()
                try:
                    return await client.resolve_warehouse(selected_warehouse)
                finally:
                    await client.aclose()

            selected_warehouse = asyncio.run(resolve_warehouse())
        products = asyncio.run(
            _search_client_factory().search_products(
                query, warehouse=selected_warehouse, limit=limit
            )
        )
    except MercadonaMCPError as error:
        typer.echo(f"{error.code}: {error.message}", err=True)
        raise typer.Exit(code=1) from error

    if not isinstance(products, list):
        raise AssertionError("search returned an unexpected result type")
    if json_output:
        _emit_json(products)
        return
    if not products:
        typer.echo("No matching products found.")
        return
    for product in products:
        details = f" — {product.package_size}" if product.package_size else ""
        typer.echo(
            f"{product.product_id}  {product.name}  {_format_price(product)}{details}"
        )


@app.command()
def product(
    product_id: Annotated[str, typer.Argument(help="Mercadona product ID.")],
    postal_code: Annotated[
        str | None,
        typer.Option(help="Five-digit delivery-area postal code."),
    ] = None,
    warehouse: Annotated[
        str | None,
        typer.Option(help="Observed Mercadona warehouse code, such as mad3."),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print normalized JSON.")
    ] = False,
) -> None:
    """Show normalized details for one public catalog product."""

    try:
        result = asyncio.run(
            _with_catalog(
                postal_code,
                warehouse,
                lambda client, selected_warehouse: client.get_product(
                    product_id, warehouse=selected_warehouse
                ),
            )
        )
    except MercadonaMCPError as error:
        typer.echo(f"{error.code}: {error.message}", err=True)
        raise typer.Exit(code=1) from error

    if not isinstance(result, ProductDetails):
        raise AssertionError("product returned an unexpected result type")
    if json_output:
        _emit_json(result)
        return
    typer.echo(f"{result.product_id}  {result.name}")
    typer.echo(f"Price: {_format_price(result)}")
    if result.package_size:
        typer.echo(f"Package: {result.package_size}")
    if result.description:
        typer.echo(result.description)


@cart_app.command("set")
def cart_set(
    product_id: str,
    quantity: int,
    expected_version: Annotated[str, typer.Option("--expected-version")],
    operation_id: Annotated[str, typer.Option("--operation-id")],
    allow_live_write: Annotated[bool, typer.Option("--allow-live-write")] = False,
) -> None:
    """Set one product's exact final quantity after explicit confirmation."""
    if not allow_live_write:
        typer.echo("Live cart writes require --allow-live-write.", err=True)
        raise typer.Exit(code=2)
    if quantity < 0:
        typer.echo("invalid_quantity: Quantity must be non-negative.", err=True)
        raise typer.Exit(code=2)

    async def update() -> CartMutationResult:
        async with AuthenticatedMercadonaClient(KeychainSecretStore()) as client:
            before = await CartClient(client).get_cart()
            existing = next(
                (
                    item.quantity
                    for item in before.items
                    if item.product.product_id == product_id
                ),
                0,
            )
            typer.echo(f"Preview: {product_id}: {existing} → {quantity}")
            if not typer.confirm("Apply this exact cart quantity?"):
                raise typer.Abort()
            return await CartMutationClient(client).update_cart(
                CartMutation(
                    changes=(CartChange(product_id=product_id, quantity=quantity),),
                    expected_cart_version=CartVersion(value=expected_version),
                    operation_id=operation_id,
                )
            )

    try:
        result = asyncio.run(update())
    except MercadonaMCPError as error:
        typer.echo(f"{error.code}: {error.message}", err=True)
        raise typer.Exit(code=1) from error
    version = result.after.version.value if result.after.version else "unavailable"
    typer.echo(f"Updated cart; resulting version: {version}")
