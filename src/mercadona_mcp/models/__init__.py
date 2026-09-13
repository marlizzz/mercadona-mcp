"""Framework-independent MercadonaMCP domain models."""

from mercadona_mcp.models.auth import AuthStatus
from mercadona_mcp.models.cart import CartItem, CartSnapshot, CartVersion
from mercadona_mcp.models.mutation import CartChange, CartMutation, CartMutationResult
from mercadona_mcp.models.product import Money, ProductDetails, ProductSummary

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
    "ProductSummary",
]
