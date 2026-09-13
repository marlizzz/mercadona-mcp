"""Normalized cart models."""

from pydantic import BaseModel, ConfigDict, Field

from mercadona_mcp.models.product import Money, ProductSummary


class CartVersion(BaseModel):
    """Opaque optimistic-lock value supplied by Mercadona."""

    model_config = ConfigDict(frozen=True)

    value: str = Field(min_length=1)


class CartItem(BaseModel):
    """One product and its final quantity in a cart."""

    model_config = ConfigDict(frozen=True)

    product: ProductSummary
    quantity: int = Field(ge=0)
    line_total: Money


class CartSnapshot(BaseModel):
    """A normalized read-only view of a Mercadona cart."""

    model_config = ConfigDict(frozen=True)

    items: tuple[CartItem, ...] = ()
    total: Money
    version: CartVersion | None = None
