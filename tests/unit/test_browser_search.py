"""Offline coverage for bounded browser-backed product search."""

import asyncio
from typing import Any

import pytest

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.search import BrowserProductSearchClient
from mercadona_mcp.models import ProductSearchQuery


def _payload(*names: str) -> dict[str, Any]:
    return {
        "hits": [
            {
                "id": str(index),
                "display_name": name,
                "thumbnail": None,
                "unavailable_from": None,
                "price_instructions": {
                    "unit_price": "2.50",
                    "unit_size": 1,
                    "size_format": "l",
                    "reference_price": "2.50",
                    "reference_format": "l",
                },
            }
            for index, name in enumerate(names, start=1)
        ]
    }


def test_single_search_is_bounded_and_uses_the_selected_warehouse() -> None:
    calls: list[tuple[str, str]] = []

    async def fetch(query: str, warehouse: str) -> dict[str, Any]:
        calls.append((query, warehouse))
        return _payload(*(f"Helado {number}" for number in range(6)))

    products = asyncio.run(
        BrowserProductSearchClient(payload_fetcher=fetch).search_products(
            "helado", warehouse="vlc1"
        )
    )

    assert calls == [("helado", "vlc1")]
    assert len(products) == 5


def test_batch_deduplicates_queries_and_preserves_each_callers_key() -> None:
    calls: list[str] = []

    async def fetch(query: str, warehouse: str) -> dict[str, Any]:
        assert warehouse == "vlc1"
        calls.append(query)
        return _payload(query)

    result = asyncio.run(
        BrowserProductSearchClient(payload_fetcher=fetch).search_batch(
            (
                ProductSearchQuery(key="first", query="  Pepino holandés "),
                ProductSearchQuery(key="second", query="pepino   HOLANDÉS", limit=1),
                ProductSearchQuery(key="third", query="helado chocolate"),
            ),
            warehouse="vlc1",
        )
    )

    assert sorted(calls) == ["Pepino holandés", "helado chocolate"]
    assert [item.key for item in result.results] == ["first", "second", "third"]
    assert [item.products[0].name for item in result.results] == [
        "Pepino holandés",
        "Pepino holandés",
        "helado chocolate",
    ]


def test_batch_keeps_successes_when_one_query_fails() -> None:
    async def fetch(query: str, warehouse: str) -> dict[str, Any]:
        if query == "broken":
            raise RuntimeError("upstream detail must not be exposed")
        return _payload("Pepino holandés")

    result = asyncio.run(
        BrowserProductSearchClient(
            payload_fetcher=fetch, retry_attempts=1
        ).search_batch(
            (
                ProductSearchQuery(key="ok", query="pepino holandés"),
                ProductSearchQuery(key="bad", query="broken"),
            ),
            warehouse="vlc1",
        )
    )

    assert result.results[0].products[0].name == "Pepino holandés"
    assert result.results[1].error is not None
    assert result.results[1].error.code == ErrorCode.SEARCH_FAILED
    assert "upstream" not in result.results[1].error.message


def test_search_retries_a_transient_failure_once() -> None:
    calls = 0

    async def fetch(query: str, warehouse: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary")
        return _payload("Helado")

    products = asyncio.run(
        BrowserProductSearchClient(
            payload_fetcher=fetch, retry_attempts=2
        ).search_products(
            "helado", warehouse="vlc1"
        )
    )

    assert calls == 2
    assert products[0].name == "Helado"


def test_timeout_returns_a_safe_machine_readable_error() -> None:
    async def fetch(query: str, warehouse: str) -> dict[str, Any]:
        await asyncio.sleep(0.1)
        return _payload("too late")

    result = asyncio.run(
        BrowserProductSearchClient(
            payload_fetcher=fetch, timeout_seconds=0.01, retry_attempts=1
        ).search_batch(
            (ProductSearchQuery(key="slow", query="helado"),), warehouse="vlc1"
        )
    )

    assert result.results[0].error is not None
    assert result.results[0].error.code == ErrorCode.SEARCH_TIMEOUT


def test_searches_run_concurrently_within_the_batch_cap() -> None:
    active = 0
    peak = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def fetch(query: str, warehouse: str) -> dict[str, Any]:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 4:
            started.set()
        await release.wait()
        active -= 1
        return _payload(query)

    async def run() -> None:
        client = BrowserProductSearchClient(payload_fetcher=fetch)
        task = asyncio.create_task(
            client.search_batch(
                tuple(
                    ProductSearchQuery(key=str(i), query=f"producto {i}")
                    for i in range(4)
                ),
                warehouse="vlc1",
            )
        )
        await asyncio.wait_for(started.wait(), timeout=1)
        release.set()
        await task

    asyncio.run(run())
    assert peak == 4


def test_invalid_and_oversized_queries_are_rejected_before_search() -> None:
    client = BrowserProductSearchClient(payload_fetcher=_unreachable_fetch)
    with pytest.raises(MercadonaMCPError, match="must not be empty") as raised:
        asyncio.run(client.search_products("  ", warehouse="vlc1"))
    assert raised.value.code is ErrorCode.INVALID_SEARCH_QUERY

    with pytest.raises(MercadonaMCPError, match="At most 10"):
        asyncio.run(
            client.search_batch(
                tuple(
                    ProductSearchQuery(key=str(i), query="helado")
                    for i in range(11)
                ),
                warehouse="vlc1",
            )
        )


async def _unreachable_fetch(query: str, warehouse: str) -> dict[str, Any]:
    raise AssertionError("validation must run before network work")
