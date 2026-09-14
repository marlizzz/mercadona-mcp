"""Bounded product-search request and result models."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mercadona_mcp.models.product import ProductSummary


class ProductSearchQuery(BaseModel):
    """One caller-labelled concrete product phrase."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)

    @field_validator("key", "query")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class ProductSearchError(BaseModel):
    """Safe per-query failure returned by a partial batch search."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class ProductSearchResult(BaseModel):
    """Candidates or one safe error for a requested search phrase."""

    model_config = ConfigDict(frozen=True)

    key: str
    query: str
    products: tuple[ProductSummary, ...] = ()
    error: ProductSearchError | None = None


class ProductSearchBatchResult(BaseModel):
    """Ordered result set for a bounded batch of product searches."""

    model_config = ConfigDict(frozen=True)

    results: tuple[ProductSearchResult, ...]
