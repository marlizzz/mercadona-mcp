"""Read-only adapter for Mercadona's delivery-area-dependent catalog."""

import asyncio
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.endpoints import (
    API_BASE_URL,
    CATEGORIES_PATH,
    CHANGE_POSTAL_CODE_PATH,
    PRODUCT_PATH,
    WAREHOUSE_HEADER,
)
from mercadona_mcp.models import Money, ProductDetails, ProductSummary

_REQUEST_TIMEOUT_SECONDS = 10.0
_MAX_READ_ATTEMPTS = 2


class CatalogClient:
    """Retrieve and normalize public catalog data without authentication."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            base_url=base_url,
            headers={"Accept": "application/json", "Accept-Language": "es-ES,es;q=0.9"},
            timeout=httpx.Timeout(_REQUEST_TIMEOUT_SECONDS),
        )
        self._owns_client = client is None

    async def __aenter__(self) -> "CatalogClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the internally created HTTP client."""
        if self._owns_client:
            await self._client.aclose()

    async def resolve_warehouse(self, postal_code: str) -> str:
        """Resolve a five-digit Spanish postal code to Mercadona's warehouse code."""
        if (
            len(postal_code) != 5
            or not postal_code.isascii()
            or not postal_code.isdigit()
        ):
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE,
                "A five-digit postal code is required to resolve the delivery area.",
            )

        response = await self._request(
            "PUT",
            CHANGE_POSTAL_CODE_PATH,
            json={"new_postal_code": postal_code},
        )
        warehouse = response.headers.get(WAREHOUSE_HEADER)
        if not isinstance(warehouse, str) or not warehouse:
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE,
                "Mercadona did not return a warehouse for this delivery area.",
            )
        return warehouse

    async def search_products(
        self, query: str, *, warehouse: str, limit: int = 10
    ) -> list[ProductSummary]:
        """Find products by matching normalized names across the selected warehouse."""
        normalized_query = query.strip().casefold()
        if not normalized_query:
            return []
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")

        root = await self._get_json(CATEGORIES_PATH, warehouse=warehouse)
        sections = _require_list(root, "results")
        category_ids = [
            _require_string(category, "id")
            for section in sections
            for category in _require_list(section, "categories")
        ]

        matches: list[ProductSummary] = []
        query_terms = normalized_query.split()
        for category_id in category_ids:
            category = await self._get_json(
                f"/categories/{category_id}/", warehouse=warehouse
            )
            for leaf in _require_list(category, "categories"):
                for product in _require_list(leaf, "products"):
                    name = _require_string(product, "display_name")
                    if all(term in name.casefold() for term in query_terms):
                        matches.append(normalize_product_summary(product))
                        if len(matches) == limit:
                            return matches
        return matches

    async def get_product(self, product_id: str, *, warehouse: str) -> ProductDetails:
        """Return normalized details for one product in the selected warehouse."""
        if not product_id:
            raise ValueError("product_id must not be empty")
        try:
            payload = await self._get_json(
                PRODUCT_PATH.format(product_id=product_id), warehouse=warehouse
            )
        except MercadonaMCPError as error:
            if error.code is ErrorCode.PRODUCT_NOT_FOUND:
                raise
            raise
        summary = normalize_product_summary(payload)
        details = _require_mapping(payload, "details", allow_missing=True)
        categories = tuple(
            _require_string(category, "name")
            for category in _require_list(payload, "categories", allow_missing=True)
        )
        description = details.get("description") if details else None
        if description is not None and not isinstance(description, str):
            raise _unsupported_payload("details.description must be a string")
        return ProductDetails(
            **summary.model_dump(), description=description, categories=categories
        )

    async def _get_json(self, path: str, *, warehouse: str) -> Mapping[str, Any]:
        response = await self._request(
            "GET", path, params={"lang": "es", "wh": warehouse}
        )
        try:
            payload = response.json()
        except ValueError as error:
            raise _unsupported_payload(
                "Mercadona returned invalid catalog JSON"
            ) from error
        if not isinstance(payload, dict):
            raise _unsupported_payload(
                "Mercadona returned an unexpected catalog response"
            )
        return payload

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(_MAX_READ_ATTEMPTS):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.RequestError as error:
                if attempt + 1 == _MAX_READ_ATTEMPTS:
                    raise MercadonaMCPError(
                        ErrorCode.NETWORK_ERROR,
                        "Mercadona could not be reached. Please try again later.",
                    ) from error
                await asyncio.sleep(0)
                continue
            if response.status_code == 404:
                raise MercadonaMCPError(
                    ErrorCode.PRODUCT_NOT_FOUND, "Product not found."
                )
            if response.status_code == 429:
                raise MercadonaMCPError(
                    ErrorCode.MERCADONA_RATE_LIMITED,
                    "Mercadona is rate limiting requests. Please try again later.",
                )
            if response.status_code >= 500 and attempt + 1 < _MAX_READ_ATTEMPTS:
                await asyncio.sleep(0)
                continue
            if response.status_code >= 500:
                raise MercadonaMCPError(
                    ErrorCode.MERCADONA_UNAVAILABLE,
                    "Mercadona is temporarily unavailable. Please try again later.",
                )
            if response.is_error:
                raise MercadonaMCPError(
                    ErrorCode.UNSUPPORTED_API_CHANGE,
                    "Mercadona rejected an expected catalog request.",
                )
            return response
        raise AssertionError("read retry loop ended unexpectedly")


def normalize_product_summary(payload: Mapping[str, Any]) -> ProductSummary:
    instructions = _require_mapping(payload, "price_instructions")
    unit_size = instructions.get("unit_size")
    size_format = instructions.get("size_format")
    package_size = (
        f"{unit_size:g} {size_format}"
        if isinstance(unit_size, (int, float)) and isinstance(size_format, str)
        else None
    )
    reference_price = instructions.get("reference_price")
    reference_format = instructions.get("reference_format")
    unit_price = (
        Money(amount=_decimal(reference_price), currency="EUR")
        if reference_price is not None and isinstance(reference_format, str)
        else None
    )
    return ProductSummary(
        product_id=_require_string(payload, "id"),
        name=_require_string(payload, "display_name"),
        price=Money(amount=_decimal(instructions.get("unit_price")), currency="EUR"),
        package_size=package_size,
        unit_price=unit_price,
        image_url=_optional_string(payload, "thumbnail"),
        available=payload.get("unavailable_from") is None,
        canonical_url=_optional_string(payload, "share_url"),
    )


def _decimal(value: object) -> Decimal:
    if not isinstance(value, (str, int, float, Decimal)):
        raise _unsupported_payload("price is missing or invalid")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as error:
        raise _unsupported_payload("price is missing or invalid") from error


def _require_mapping(
    payload: Mapping[str, Any], key: str, *, allow_missing: bool = False
) -> Mapping[str, Any]:
    value = payload.get(key)
    if value is None and allow_missing:
        return {}
    if not isinstance(value, dict):
        raise _unsupported_payload(f"{key} is missing or invalid")
    return value


def _require_list(
    payload: Mapping[str, Any], key: str, *, allow_missing: bool = False
) -> list[Mapping[str, Any]]:
    value = payload.get(key)
    if value is None and allow_missing:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise _unsupported_payload(f"{key} is missing or invalid")
    return value


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None and key == "id":
        value = payload.get("id")
    if not isinstance(value, (str, int)) or not str(value):
        raise _unsupported_payload(f"{key} is missing or invalid")
    return str(value)


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _unsupported_payload(f"{key} is invalid")
    return value


def _unsupported_payload(detail: str) -> MercadonaMCPError:
    return MercadonaMCPError(
        ErrorCode.UNSUPPORTED_API_CHANGE,
        f"Mercadona's catalog response changed unexpectedly ({detail}).",
    )
