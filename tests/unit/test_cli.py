"""Tests for the read-only catalog CLI spike."""

from decimal import Decimal

import pytest
import typer
from typer.testing import CliRunner

from mercadona_mcp import cli
from mercadona_mcp.cli import app
from mercadona_mcp.models import Money, ProductDetails, ProductSummary

_runner = CliRunner()
_PRODUCT = ProductSummary(
    product_id="4241",
    name="Aceite de oliva Hacendado",
    price=Money(amount=Decimal("17.25")),
    package_size="5 l",
    unit_price=Money(amount=Decimal("3.45")),
    available=True,
)


class _FakeCatalogClient:
    async def aclose(self) -> None:
        return None

    async def resolve_warehouse(self, postal_code: str) -> str:
        assert postal_code == "28001"
        return "mad3"

    async def search_products(
        self, query: str, *, warehouse: str, limit: int
    ) -> list[ProductSummary]:
        assert query == "aceite"
        assert warehouse == "mad3"
        assert limit == 1
        return [_PRODUCT]

    async def get_product(self, product_id: str, *, warehouse: str) -> ProductDetails:
        assert product_id == "4241"
        assert warehouse == "mad3"
        return ProductDetails(**_PRODUCT.model_dump(), description="Aceite de oliva.")


class _FakeSearchClient:
    async def search_products(
        self, query: str, *, warehouse: str, limit: int
    ) -> list[ProductSummary]:
        assert query == "aceite"
        assert warehouse == "mad3"
        assert limit == 1
        return [_PRODUCT]


def test_search_prints_human_readable_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_catalog_client_factory", _FakeCatalogClient)
    monkeypatch.setattr(cli, "_search_client_factory", _FakeSearchClient)

    result = _runner.invoke(
        app, ["search", "aceite", "--postal-code", "28001", "--limit", "1"]
    )

    assert result.exit_code == 0
    assert "4241" in result.stdout
    assert "17.25 EUR" in result.stdout


def test_product_prints_normalized_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_catalog_client_factory", _FakeCatalogClient)

    result = _runner.invoke(app, ["product", "4241", "--warehouse", "mad3", "--json"])

    assert result.exit_code == 0
    assert '"product_id": "4241"' in result.stdout
    assert '"description": "Aceite de oliva."' in result.stdout


def test_catalog_commands_require_one_delivery_area_argument() -> None:
    result = _runner.invoke(app, ["search", "aceite"])

    assert result.exit_code != 0
    with pytest.raises(
        typer.BadParameter,
        match="one of --postal-code or --warehouse is required",
    ):
        cli._warehouse_argument(None, None)
