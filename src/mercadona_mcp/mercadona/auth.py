"""Authenticated Mercadona requests with strict origin and secret boundaries."""

from collections.abc import Mapping
from typing import Any

import httpx

from mercadona_mcp.companion.session import SessionMaterial, load_session
from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.endpoints import API_BASE_URL
from mercadona_mcp.security import SecretStore

_VALIDATION_PATH = "/api/customers/{user_uuid}/cart/"


class AuthenticatedMercadonaClient:
    """Make authenticated requests only to the observed Mercadona API origin."""

    def __init__(
        self,
        secret_store: SecretStore,
        *,
        client: httpx.AsyncClient | None = None,
        base_url: str = API_BASE_URL,
    ) -> None:
        self._session = load_session(secret_store)
        self._base_url = httpx.URL(base_url)
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=10.0)
        self._owns_client = client is None

    async def __aenter__(self) -> "AuthenticatedMercadonaClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the internally owned HTTP client."""
        if self._owns_client:
            await self._client.aclose()

    async def validate_session(self) -> None:
        """Validate the local session with a harmless authenticated cart read."""
        session = self._require_session()
        response = await self._request(
            "GET", _VALIDATION_PATH.format(user_uuid=session.user_uuid)
        )
        if response.status_code in {401, 403}:
            raise _reauthentication_required()
        if response.status_code >= 500:
            raise MercadonaMCPError(
                ErrorCode.MERCADONA_UNAVAILABLE,
                "Mercadona is temporarily unavailable. Please try again later.",
            )
        if response.is_error:
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE,
                "Mercadona rejected the expected session-validation request.",
            )

    async def get_json(self, path: str) -> Mapping[str, Any]:
        """Read one authenticated JSON resource from the Mercadona API origin."""
        response = await self._request("GET", path)
        if response.status_code in {401, 403}:
            raise _reauthentication_required()
        if response.status_code >= 500:
            raise MercadonaMCPError(
                ErrorCode.MERCADONA_UNAVAILABLE,
                "Mercadona is temporarily unavailable. Please try again later.",
            )
        if response.is_error:
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE,
                "Mercadona rejected an expected authenticated request.",
            )
        try:
            payload = response.json()
        except ValueError as error:
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE,
                "Mercadona returned invalid authenticated JSON.",
            ) from error
        if not isinstance(payload, dict):
            raise MercadonaMCPError(
                ErrorCode.UNSUPPORTED_API_CHANGE,
                "Mercadona returned an unexpected authenticated response.",
            )
        return payload

    async def _request(self, method: str, path: str) -> httpx.Response:
        session = self._require_session()
        url = self._base_url.join(path)
        if url.host != "tienda.mercadona.es" or url.scheme != "https":
            raise ValueError("authenticated requests are restricted to Mercadona")
        try:
            return await self._client.request(
                method,
                url,
                headers={"Authorization": f"Bearer {session.token}"},
            )
        except httpx.RequestError as error:
            raise MercadonaMCPError(
                ErrorCode.NETWORK_ERROR,
                "Mercadona could not be reached. Please try again later.",
            ) from error

    def _require_session(self) -> SessionMaterial:
        if self._session is None:
            raise _reauthentication_required()
        return self._session


def _reauthentication_required() -> MercadonaMCPError:
    return MercadonaMCPError(
        ErrorCode.REAUTHENTICATION_REQUIRED,
        "Mercadona session expired or is unavailable. Please run login again.",
    )
