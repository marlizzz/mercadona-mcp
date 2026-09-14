"""Framework-independent MercadonaMCP domain models."""

from mercadona_mcp.models.auth import AuthStatus
from mercadona_mcp.models.cart import CartItem, CartSnapshot, CartVersion
from mercadona_mcp.models.mutation import CartChange, CartMutation, CartMutationResult
from mercadona_mcp.models.product import Money, ProductDetails, ProductSummary
from mercadona_mcp.models.search import (
    ProductSearchBatchResult,
    ProductSearchError,
    ProductSearchQuery,
    ProductSearchResult,
)

__all__ = [
    "AuthStatus",
    "CartChange",
    "CartItem",
    "CartMutation",
    "CartMutationResult",
    "CartSnapshot",
    "CartVersion",
    "Money",
    "ProductDetails",
    "ProductSearchBatchResult",
    "ProductSearchError",
    "ProductSearchQuery",
    "ProductSearchResult",
    "ProductSummary",
]
