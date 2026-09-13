"""Tests for normalized authenticated cart reads."""

import json
from pathlib import Path

import pytest

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.cart import normalize_cart

_FIXTURE = Path(__file__).parents[1] / "fixtures" / "cart" / "populated_cart.json"


def test_normalize_populated_cart_and_opaque_version() -> None:
    cart = normalize_cart(json.loads(_FIXTURE.read_text()))

    assert cart.version is not None
    assert cart.version.value == "7"
    assert cart.total.amount == 34.50
    assert cart.items[0].quantity == 2
    assert cart.items[0].line_total.amount == 34.50
    assert cart.items[0].product.product_id == "4241"


def test_cart_payload_change_returns_safe_error() -> None:
    with pytest.raises(MercadonaMCPError) as raised:
        normalize_cart({"lines": [], "summary": {}, "version": 1})

    assert raised.value.code is ErrorCode.UNSUPPORTED_API_CHANGE
