"""Contract tests for sanitized Mercadona catalog payloads."""

import asyncio
import json
from pathlib import Path
from typing import cast

import httpx
import pytest

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.catalog import CatalogClient

_FIXTURES = Path(__file__).parents[1] / "fixtures" / "catalog"


def _fixture(name: str) -> dict[str, object]:
    return cast(dict[str, object], json.loads((_FIXTURES / name).read_text()))


def _client(handler: httpx.MockTransport) -> CatalogClient:
    return CatalogClient(
        client=httpx.AsyncClient(transport=handler, base_url="https://test")
    )


def test_search_products_normalizes_category_products() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/categories/":
            return httpx.Response(200, json=_fixture("category_root.json"))
        if request.url.path == "/categories/112/":
            return httpx.Response(200, json=_fixture("category_112.json"))
        return httpx.Response(404)

    async def run() -> None:
        client = _client(httpx.MockTransport(handler))
        results = await client.search_products("aceite oliva", warehouse="mad1")
        await client.aclose()

        assert len(results) == 1
        assert results[0].product_id == "4241"
        assert str(results[0].price.amount) == "17.25"
        assert results[0].unit_price is not None
        assert str(results[0].unit_price.amount) == "3.45"
        assert results[0].package_size == "5 l"

    asyncio.run(run())


def test_get_product_normalizes_details() -> None:
    async def run() -> None:
        client = _client(
            httpx.MockTransport(
                lambda _: httpx.Response(200, json=_fixture("product_4241.json"))
            )
        )
        product = await client.get_product("4241", warehouse="mad1")
        await client.aclose()

        assert product.description == "Aceite de oliva."
        assert product.categories == ("Section",)

    asyncio.run(run())


def test_resolve_warehouse_reads_only_the_expected_response_header() -> None:
    async def run() -> None:
        client = _client(
            httpx.MockTransport(
                lambda _: httpx.Response(200, headers={"x-customer-wh": "mad3"})
            )
        )
        assert await client.resolve_warehouse("28001") == "mad3"
        await client.aclose()

    asyncio.run(run())


def test_malformed_payload_maps_to_safe_api_change_error() -> None:
    async def run() -> None:
        client = _client(
            httpx.MockTransport(
                lambda _: httpx.Response(200, json={"results": "invalid"})
            )
        )
        with pytest.raises(MercadonaMCPError) as raised:
            await client.search_products("aceite", warehouse="mad1")
        await client.aclose()

        assert raised.value.code is ErrorCode.UNSUPPORTED_API_CHANGE
        assert "response changed unexpectedly" in raised.value.message

    asyncio.run(run())
