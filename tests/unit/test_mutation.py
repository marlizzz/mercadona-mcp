"""Tests for idempotent absolute-quantity cart mutations."""

import asyncio
import json
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.mutation import CartMutationClient
from mercadona_mcp.models import CartChange, CartMutation, CartVersion

_FIXTURE = Path(__file__).parents[1] / "fixtures" / "cart" / "populated_cart.json"


class _Writer:
    user_uuid = "user"

    def __init__(self) -> None:
        self.cart = json.loads(_FIXTURE.read_text())
        self.puts = 0
        self.fail_after_put = False

    async def request_json(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if method == "GET":
            return deepcopy(self.cart)
        assert method == "PUT"
        assert isinstance(payload, dict)
        self.puts += 1
        self.cart["lines"] = [
            {
                "quantity": line["quantity"],
                "sources": line["sources"],
                "version": self.cart["version"] + 1,
                "product": next(
                    old["product"]
                    for old in json.loads(_FIXTURE.read_text())["lines"]
                    if old["product"]["id"] == line["product_id"]
                ),
            }
            for line in payload["lines"]
        ]
        self.cart["version"] += 1
        if self.fail_after_put:
            raise MercadonaMCPError(ErrorCode.NETWORK_ERROR, "lost response")
        return deepcopy(self.cart)


def _mutation(quantity: int, operation_id: str = "operation") -> CartMutation:
    return CartMutation(
        changes=(CartChange(product_id="4241", quantity=quantity),),
        expected_cart_version=CartVersion(value="7"),
        operation_id=operation_id,
    )


def test_absolute_update_and_replay_do_not_duplicate_effect() -> None:
    async def run() -> None:
        writer = _Writer()
        client = CartMutationClient(writer)
        result = await client.update_cart(_mutation(3))
        replay = await client.update_cart(_mutation(3))

        assert result.after.items[0].quantity == 3
        assert replay == result
        assert writer.puts == 1

    asyncio.run(run())


def test_stale_version_rejects_before_write() -> None:
    async def run() -> None:
        writer = _Writer()
        with pytest.raises(MercadonaMCPError) as raised:
            await CartMutationClient(writer).update_cart(
                _mutation(3, "stale").model_copy(
                    update={"expected_cart_version": CartVersion(value="6")}
                )
            )
        assert raised.value.code is ErrorCode.CART_VERSION_CONFLICT
        assert writer.puts == 0

    asyncio.run(run())


def test_lost_write_response_is_reconciled_without_retry() -> None:
    async def run() -> None:
        writer = _Writer()
        writer.fail_after_put = True
        result = await CartMutationClient(writer).update_cart(_mutation(3, "lost"))

        assert result.after.items[0].quantity == 3
        assert writer.puts == 1

    asyncio.run(run())
