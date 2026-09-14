"""Safe, verified absolute-quantity mutations for a Mercadona cart."""

import hashlib
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.cart import normalize_cart
from mercadona_mcp.models import CartMutation, CartMutationResult

_OPERATION_RETENTION_SECONDS = 600


class CartWriter(Protocol):
    @property
    def user_uuid(self) -> str: ...

    async def request_json(
        self, method: str, path: str, payload: Mapping[str, Any] | None = None
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class _StoredOperation:
    fingerprint: str
    result: CartMutationResult
    expires_at: float


OperationCache = dict[str, _StoredOperation]


class CartMutationClient:
    """Set exact cart quantities with version checks and idempotent replay."""

    def __init__(
        self, writer: CartWriter, operations: OperationCache | None = None
    ) -> None:
        self._writer = writer
        self._operations = operations if operations is not None else {}

    async def update_cart(self, mutation: CartMutation) -> CartMutationResult:
        """Apply absolute final quantities once, then verify the resulting cart."""
        fingerprint = _fingerprint(mutation)
        cached = self._operations.get(mutation.operation_id)
        if cached and cached.expires_at > time.monotonic():
            if cached.fingerprint != fingerprint:
                raise MercadonaMCPError(
                    ErrorCode.OPERATION_ID_CONFLICT,
                    "This operation ID was already used for a different cart change.",
                )
            return cached.result

        path = f"/api/customers/{self._writer.user_uuid}/cart/"
        before_payload = await self._writer.request_json("GET", path)
        before = normalize_cart(before_payload)
        if mutation.expected_cart_version and (
            before.version is None or before.version != mutation.expected_cart_version
        ):
            raise MercadonaMCPError(
                ErrorCode.CART_VERSION_CONFLICT,
                "The cart changed. Fetch the current cart before trying again.",
            )
        payload = _build_write_payload(before_payload, mutation)
        try:
            await self._writer.request_json("PUT", path, payload)
        except MercadonaMCPError:
            after_payload = await self._writer.request_json("GET", path)
            after = normalize_cart(after_payload)
            if not _matches_requested_state(after, mutation):
                raise MercadonaMCPError(
                    ErrorCode.MUTATION_RESULT_AMBIGUOUS,
                    "The cart write result is ambiguous. Check the current cart "
                    "before retrying.",
                )
            return self._record(mutation.operation_id, fingerprint, before, after)

        after = normalize_cart(await self._writer.request_json("GET", path))
        if not _matches_requested_state(after, mutation):
            raise MercadonaMCPError(
                ErrorCode.MUTATION_RESULT_AMBIGUOUS,
                "Mercadona did not return the requested final cart quantities.",
            )
        return self._record(mutation.operation_id, fingerprint, before, after)

    def _record(
        self, operation_id: str, fingerprint: str, before: Any, after: Any
    ) -> CartMutationResult:
        result = CartMutationResult(
            operation_id=operation_id, before=before, after=after
        )
        self._operations[operation_id] = _StoredOperation(
            fingerprint=fingerprint,
            result=result,
            expires_at=time.monotonic() + _OPERATION_RETENTION_SECONDS,
        )
        return result


def _build_write_payload(
    cart: Mapping[str, Any], mutation: CartMutation
) -> dict[str, Any]:
    cart_id = cart.get("id")
    version = cart.get("version")
    lines = cart.get("lines")
    if (
        not isinstance(cart_id, str)
        or not isinstance(version, int)
        or not isinstance(lines, list)
    ):
        raise MercadonaMCPError(
            ErrorCode.UNSUPPORTED_API_CHANGE, "Mercadona cart write shape changed."
        )
    requested = {change.product_id: change.quantity for change in mutation.changes}
    output_lines: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        if not isinstance(line, dict) or not isinstance(line.get("product"), dict):
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE, "Mercadona cart line shape changed."
            )
        product_id = line["product"].get("id")
        if not isinstance(product_id, str):
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE, "Mercadona cart product ID changed."
            )
        quantity = requested.get(product_id, line.get("quantity"))
        if not isinstance(quantity, int | float) or quantity < 0:
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE, "Mercadona cart quantity changed."
            )
        seen.add(product_id)
        if quantity:
            sources = line.get("sources", [])
            output_lines.append(
                {"product_id": product_id, "quantity": quantity, "sources": sources}
            )
    for product_id, quantity in requested.items():
        if product_id not in seen and quantity:
            output_lines.append(
                {"product_id": product_id, "quantity": quantity, "sources": []}
            )
    return {"id": cart_id, "version": version, "lines": output_lines}


def _matches_requested_state(cart: Any, mutation: CartMutation) -> bool:
    quantities = {item.product.product_id: item.quantity for item in cart.items}
    return all(
        quantities.get(change.product_id, 0) == change.quantity
        for change in mutation.changes
    )


def _fingerprint(mutation: CartMutation) -> str:
    payload = mutation.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()
