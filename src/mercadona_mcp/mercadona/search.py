"""Bounded browser-backed Mercadona product search.

Mercadona's public search provider rejects the project's direct HTTP transport.
This adapter uses an isolated visible Chrome context, which is the transport the
website itself uses. It never attaches to the user's normal Chrome profile.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.catalog import normalize_product_summary
from mercadona_mcp.models import (
    ProductSearchBatchResult,
    ProductSearchError,
    ProductSearchQuery,
    ProductSearchResult,
    ProductSummary,
)

_CHROME_EXECUTABLE = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
_SEARCH_PAGE_URL = "https://tienda.mercadona.es"
_SEARCH_TIMEOUT_SECONDS = 8.0
_SEARCH_RETRY_ATTEMPTS = 2
_MAX_BATCH_QUERIES = 10
_MAX_CONCURRENT_SEARCHES = 4
_LOGGER = logging.getLogger(__name__)

_FETCH_SEARCH_SCRIPT = """async ({query, warehouse}) => {
  const params = new URLSearchParams({q: query, wh: warehouse, lang: "es"});
  try {
    const response = await fetch(`https://tornillos.mercadona.es/search?${params}`);
    if (!response.ok) return {status: response.status, payload: null};
    return {status: response.status, payload: await response.json()};
  } catch (_) {
    return {status: null, payload: null};
  }
}"""

PayloadFetcher = Callable[[str, str], Awaitable[Mapping[str, Any]]]


class BrowserProductSearchClient:
    """Search concrete Spanish product phrases without catalog traversal."""

    def __init__(
        self,
        *,
        chrome_executable: str = _CHROME_EXECUTABLE,
        payload_fetcher: PayloadFetcher | None = None,
        timeout_seconds: float = _SEARCH_TIMEOUT_SECONDS,
        retry_attempts: int = _SEARCH_RETRY_ATTEMPTS,
    ) -> None:
        self._chrome_executable = chrome_executable
        self._payload_fetcher = payload_fetcher
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = retry_attempts

    async def search_products(
        self, query: str, *, warehouse: str, limit: int = 5
    ) -> list[ProductSummary]:
        """Return a small candidate set for one concrete product phrase."""
        if not query.strip():
            raise MercadonaMCPError(
                ErrorCode.INVALID_SEARCH_QUERY, "Search query must not be empty."
            )
        if not 1 <= limit <= 10:
            raise MercadonaMCPError(
                ErrorCode.INVALID_SEARCH_QUERY,
                "Search limit must be between 1 and 10.",
            )
        result = await self.search_batch(
            (ProductSearchQuery(key="single", query=query, limit=limit),),
            warehouse=warehouse,
        )
        item = result.results[0]
        if item.error is not None:
            raise MercadonaMCPError(ErrorCode(item.error.code), item.error.message)
        return list(item.products)

    async def search_batch(
        self,
        queries: Sequence[ProductSearchQuery],
        *,
        warehouse: str,
    ) -> ProductSearchBatchResult:
        """Search unique phrases concurrently and preserve caller ordering."""
        if not warehouse.strip():
            raise MercadonaMCPError(
                ErrorCode.INVALID_SEARCH_QUERY, "Warehouse must not be empty."
            )
        if not queries:
            raise MercadonaMCPError(
                ErrorCode.INVALID_SEARCH_QUERY, "At least one search query is required."
            )
        if len(queries) > _MAX_BATCH_QUERIES:
            raise MercadonaMCPError(
                ErrorCode.INVALID_SEARCH_QUERY,
                f"At most {_MAX_BATCH_QUERIES} search queries are allowed.",
            )

        started = time.monotonic()
        unique: dict[str, ProductSearchQuery] = {}
        for item in queries:
            unique.setdefault(_normalized_query(item.query), item)
        _LOGGER.info(
            "search_started query_count=%d unique_query_count=%d",
            len(queries),
            len(unique),
        )

        responses = await self._search_unique(tuple(unique.values()), warehouse)
        ordered = tuple(
            _result_for_query(item, responses[_normalized_query(item.query)])
            for item in queries
        )
        failed = sum(result.error is not None for result in ordered)
        _LOGGER.info(
            "search_completed successful=%d failed=%d duration_ms=%d",
            len(ordered) - failed,
            failed,
            round((time.monotonic() - started) * 1000),
        )
        return ProductSearchBatchResult(results=ordered)

    async def _search_unique(
        self, queries: Sequence[ProductSearchQuery], warehouse: str
    ) -> dict[str, list[ProductSummary] | ProductSearchError]:
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SEARCHES)
        if self._payload_fetcher is not None:
            tasks = [
                self._search_with_fetcher(item, warehouse, semaphore)
                for item in queries
            ]
            values = await asyncio.gather(*tasks)
        else:
            values = await self._search_in_browser(queries, warehouse, semaphore)
        return {
            _normalized_query(item.query): value for item, value in zip(queries, values)
        }

    async def _search_with_fetcher(
        self,
        item: ProductSearchQuery,
        warehouse: str,
        semaphore: asyncio.Semaphore,
    ) -> list[ProductSummary] | ProductSearchError:
        if self._payload_fetcher is None:
            raise AssertionError("payload fetcher is required for this search path")
        async with semaphore:
            return await self._fetch_with_retry(
                item.query, warehouse, self._payload_fetcher
            )

    async def _search_in_browser(
        self,
        queries: Sequence[ProductSearchQuery],
        warehouse: str,
        semaphore: asyncio.Semaphore,
    ) -> list[list[ProductSummary] | ProductSearchError]:
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    executable_path=self._chrome_executable,
                    headless=False,
                )
                context = await browser.new_context()
                try:
                    tasks = [
                        self._search_in_page(context, item.query, warehouse, semaphore)
                        for item in queries
                    ]
                    return list(await asyncio.gather(*tasks))
                finally:
                    await browser.close()
        except Exception as error:
            safe_error = _safe_search_error(error)
            return [safe_error for _ in queries]

    async def _search_in_page(
        self,
        context: BrowserContext,
        query: str,
        warehouse: str,
        semaphore: asyncio.Semaphore,
    ) -> list[ProductSummary] | ProductSearchError:
        async with semaphore:
            page = await context.new_page()
            try:
                await page.goto(
                    _SEARCH_PAGE_URL,
                    wait_until="domcontentloaded",
                    timeout=_milliseconds(self._timeout_seconds),
                )
                return await self._fetch_with_retry(
                    query, warehouse, lambda q, wh: _fetch_from_page(page, q, wh)
                )
            except Exception as error:
                return _safe_search_error(error)
            finally:
                await page.close()

    async def _fetch_with_retry(
        self, query: str, warehouse: str, fetcher: PayloadFetcher
    ) -> list[ProductSummary] | ProductSearchError:
        for attempt in range(self._retry_attempts):
            try:
                payload = await asyncio.wait_for(
                    fetcher(query, warehouse), timeout=self._timeout_seconds
                )
                return _products_from_payload(payload)
            except asyncio.TimeoutError:
                if attempt + 1 == self._retry_attempts:
                    return ProductSearchError(
                        code=ErrorCode.SEARCH_TIMEOUT,
                        message=(
                            "Mercadona search did not respond within the allowed time."
                        ),
                    )
            except MercadonaMCPError as error:
                return ProductSearchError(code=error.code, message=error.message)
            except Exception as error:
                if attempt + 1 == self._retry_attempts:
                    return _safe_search_error(error)
            await asyncio.sleep(0)
        raise AssertionError("search retry loop ended unexpectedly")


async def _fetch_from_page(
    page: Page, query: str, warehouse: str
) -> Mapping[str, Any]:
    result = await page.evaluate(
        _FETCH_SEARCH_SCRIPT, {"query": query, "warehouse": warehouse}
    )
    if not isinstance(result, dict) or result.get("status") != 200:
        raise MercadonaMCPError(
            ErrorCode.SEARCH_FAILED, "Mercadona search could not be completed."
        )
    payload = result.get("payload")
    if not isinstance(payload, dict):
        raise MercadonaMCPError(
            ErrorCode.SEARCH_FAILED, "Mercadona search returned an invalid response."
        )
    return payload


def _products_from_payload(payload: Mapping[str, Any]) -> list[ProductSummary]:
    hits = payload.get("hits")
    if not isinstance(hits, list):
        raise MercadonaMCPError(
            ErrorCode.SEARCH_FAILED, "Mercadona search returned an invalid response."
        )
    products: list[ProductSummary] = []
    for hit in hits:
        if isinstance(hit, dict):
            products.append(normalize_product_summary(hit))
    return products


def _result_for_query(
    query: ProductSearchQuery,
    response: list[ProductSummary] | ProductSearchError,
) -> ProductSearchResult:
    if isinstance(response, ProductSearchError):
        return ProductSearchResult(key=query.key, query=query.query, error=response)
    return ProductSearchResult(
        key=query.key, query=query.query, products=tuple(response[: query.limit])
    )


def _normalized_query(query: str) -> str:
    return " ".join(query.split()).casefold()


def _safe_search_error(error: Exception) -> ProductSearchError:
    _LOGGER.warning("search_failed error_type=%s", type(error).__name__)
    return ProductSearchError(
        code=ErrorCode.SEARCH_FAILED,
        message="Mercadona search could not be completed. Please try again later.",
    )


def _milliseconds(seconds: float) -> float:
    return seconds * 1000
