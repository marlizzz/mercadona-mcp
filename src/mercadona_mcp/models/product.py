"""Normalized product and money models."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Money(BaseModel):
    """A non-negative monetary amount represented exactly in decimal currency units."""

    model_config = ConfigDict(frozen=True)

    amount: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=3)
    currency: str = Field(default="EUR", pattern=r"^[A-Z]{3}$")

    @field_validator("amount")
    @classmethod
    def require_two_decimal_places(cls, value: Decimal) -> Decimal:
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -3:
            raise ValueError("amount must have at most three decimal places")
        return value


class ProductSummary(BaseModel):
    """Safe product fields suitable for search results."""

    model_config = ConfigDict(frozen=True)

    product_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price: Money
    package_size: str | None = None
    unit_price: Money | None = None
    image_url: str | None = None
    available: bool
    canonical_url: str | None = None


class ProductDetails(ProductSummary):
    """Normalized detail view for a single product."""

    description: str | None = None
    categories: tuple[str, ...] = ()
