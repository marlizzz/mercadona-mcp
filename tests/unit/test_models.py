"""Tests for framework-independent domain models."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.models import CartChange, CartMutation, Money


def test_money_serializes_exact_decimal_amount() -> None:
    money = Money(amount=Decimal("1.20"))

    assert money.amount == Decimal("1.20")
    assert money.model_dump(mode="json") == {"amount": "1.20", "currency": "EUR"}


@pytest.mark.parametrize("amount", ["-0.01", "1.0001"])
def test_money_rejects_negative_or_overprecise_amounts(amount: str) -> None:
    with pytest.raises(ValidationError):
        Money(amount=Decimal(amount))


@pytest.mark.parametrize("quantity", [-1, 1.5])
def test_cart_change_rejects_invalid_quantities(quantity: object) -> None:
    with pytest.raises(ValidationError):
        CartChange.model_validate({"product_id": "123", "quantity": quantity})


def test_cart_mutation_rejects_duplicate_product_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate product IDs"):
        CartMutation(
            changes=(
                CartChange(product_id="123", quantity=1),
                CartChange(product_id="123", quantity=2),
            ),
            operation_id="operation-1",
        )


def test_domain_error_exposes_only_safe_code_and_message() -> None:
    error = MercadonaMCPError(ErrorCode.NOT_AUTHENTICATED, "Please run login.")

    assert error.as_dict() == {
        "code": "not_authenticated",
        "message": "Please run login.",
    }
