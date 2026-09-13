"""Adapters for Mercadona's undocumented web interfaces."""

from mercadona_mcp.mercadona.auth import AuthenticatedMercadonaClient
from mercadona_mcp.mercadona.catalog import CatalogClient

__all__ = ["AuthenticatedMercadonaClient", "CatalogClient"]
