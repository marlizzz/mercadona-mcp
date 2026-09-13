"""Read-only normalization of Mercadona's authenticated cart response."""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from pydantic import ValidationError

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.models import (
    CartItem,
    CartSnapshot,
    CartVersion,
    Money,
    ProductSummary,
)


class AuthenticatedReader(Protocol):
    """The authenticated read surface needed by the cart adapter."""

    @property
    def user_uuid(self) -> str: ...

    async def get_json(self, path: str) -> Mapping[str, Any]: ...


class CartClient:
    """Retrieve the current cart without exposing upstream payloads."""

    def __init__(self, reader: AuthenticatedReader) -> None:
        self._reader = reader

    async def get_cart(self) -> CartSnapshot:
        payload = await self._reader.get_json(
            f"/api/customers/{self._reader.user_uuid}/cart/"
        )
        return normalize_cart(payload)


def normalize_cart(payload: Mapping[str, Any]) -> CartSnapshot:
    """Convert a verified cart payload to safe, framework-independent models."""
    lines = _require_list(payload, "lines")
    summary = _require_mapping(payload, "summary")
    version = payload.get("version")
    if not isinstance(version, (str, int)):
        raise _unsupported("version is missing or invalid")
    return CartSnapshot(
        items=tuple(_normalize_item(line) for line in lines),
        total=_money(summary.get("total")),
        version=CartVersion(value=str(version)),
    )


def _normalize_item(line: Mapping[str, Any]) -> CartItem:
    product = _require_mapping(line, "product")
    quantity = line.get("quantity")
    if not isinstance(quantity, (int, float)) or isinstance(quantity, bool):
        raise _unsupported("line quantity is missing or invalid")
    if quantity < 0 or not float(quantity).is_integer():
        raise _unsupported("line quantity is not a non-negative whole number")
    normalized_quantity = int(quantity)
    summary = _normalize_product(product)
    return CartItem(
        product=summary,
        quantity=normalized_quantity,
        line_total=_money(summary.price.amount * normalized_quantity),
    )


def _normalize_product(payload: Mapping[str, Any]) -> ProductSummary:
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
        _money(reference_price)
        if reference_price is not None and isinstance(reference_format, str)
        else None
    )
    return ProductSummary(
        product_id=_require_string(payload, "id"),
        name=_require_string(payload, "display_name"),
        price=_money(instructions.get("unit_price")),
        package_size=package_size,
        unit_price=unit_price,
        image_url=_optional_string(payload, "thumbnail"),
        available=payload.get("unavailable_from") is None,
        canonical_url=_optional_string(payload, "share_url"),
    )


def _decimal(value: object) -> Decimal:
    if not isinstance(value, (str, int, float, Decimal)):
        raise _unsupported("price is missing or invalid")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as error:
        raise _unsupported("price is missing or invalid") from error


def _money(value: object) -> Money:
    try:
        return Money(amount=_decimal(value))
    except ValidationError as error:
        raise _unsupported("price is missing or invalid") from error


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise _unsupported(f"{key} is missing or invalid")
    return value


def _require_list(payload: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise _unsupported(f"{key} is missing or invalid")
    return value


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, (str, int)) or not str(value):
        raise _unsupported(f"{key} is missing or invalid")
    return str(value)


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise _unsupported(f"{key} is invalid")
    return value


def _unsupported(detail: str) -> MercadonaMCPError:
    return MercadonaMCPError(
        ErrorCode.UNSUPPORTED_API_CHANGE,
        f"Mercadona's cart response changed unexpectedly ({detail}).",
    )
