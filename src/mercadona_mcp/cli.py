"""Command-line entry point for MercadonaMCP."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Annotated

import typer

from mercadona_mcp.companion.login import LoginService
from mercadona_mcp.companion.session import delete_session, load_session
from mercadona_mcp.errors import MercadonaMCPError
from mercadona_mcp.mercadona.catalog import CatalogClient
from mercadona_mcp.models import ProductDetails, ProductSummary
from mercadona_mcp.security import KeychainSecretStore

app = typer.Typer(
    add_completion=False,
    help="MercadonaMCP local companion.",
    no_args_is_help=True,
)
auth_app = typer.Typer(help="Inspect or clear the local Mercadona session.")
app.add_typer(auth_app, name="auth")

_catalog_client_factory: Callable[[], CatalogClient] = CatalogClient


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
    limit: Annotated[int, typer.Option(min=1, max=50)] = 10,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print normalized JSON.")
    ] = False,
) -> None:
    """Search public catalog products for one delivery area."""

    try:
        products = asyncio.run(
            _with_catalog(
                postal_code,
                warehouse,
                lambda client, selected_warehouse: client.search_products(
                    query, warehouse=selected_warehouse, limit=limit
                ),
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
