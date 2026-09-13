"""Models for idempotent, absolute cart mutations."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mercadona_mcp.models.cart import CartSnapshot, CartVersion


class CartChange(BaseModel):
    """Requested final quantity for one product."""

    model_config = ConfigDict(frozen=True)

    product_id: str = Field(min_length=1)
    quantity: int = Field(ge=0)


class CartMutation(BaseModel):
    """A request to set final quantities for selected cart products."""

    model_config = ConfigDict(frozen=True)

    changes: tuple[CartChange, ...] = Field(min_length=1)
    expected_cart_version: CartVersion | None = None
    operation_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_products(self) -> "CartMutation":
        product_ids = [change.product_id for change in self.changes]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("changes must not contain duplicate product IDs")
        return self


class CartMutationResult(BaseModel):
    """Verified outcome for a cart mutation."""

    model_config = ConfigDict(frozen=True)

    operation_id: str = Field(min_length=1)
    before: CartSnapshot
    after: CartSnapshot
    warnings: tuple[str, ...] = ()
