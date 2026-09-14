"""Stable, safe domain errors exposed by MercadonaMCP."""

from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-readable error codes safe to return to tool callers."""

    NOT_AUTHENTICATED = "not_authenticated"
    REAUTHENTICATION_REQUIRED = "reauthentication_required"
    PRODUCT_NOT_FOUND = "product_not_found"
    PRODUCT_UNAVAILABLE = "product_unavailable"
    AMBIGUOUS_PRODUCT = "ambiguous_product"
    CART_VERSION_CONFLICT = "cart_version_conflict"
    OPERATION_ID_CONFLICT = "operation_id_conflict"
    MUTATION_RESULT_AMBIGUOUS = "mutation_result_ambiguous"
    INVALID_QUANTITY = "invalid_quantity"
    INVALID_SEARCH_QUERY = "invalid_search_query"
    SEARCH_TIMEOUT = "search_timeout"
    SEARCH_FAILED = "search_failed"
    MERCADONA_RATE_LIMITED = "mercadona_rate_limited"
    MERCADONA_UNAVAILABLE = "mercadona_unavailable"
    NETWORK_ERROR = "network_error"
    UNSUPPORTED_API_CHANGE = "unsupported_api_change"


class MercadonaMCPError(Exception):
    """A domain failure with a safe, actionable message."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

    def as_dict(self) -> dict[str, str]:
        """Return the safe representation intended for external callers."""
        return {"code": self.code, "message": self.message}
