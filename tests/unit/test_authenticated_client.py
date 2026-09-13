"""Tests for authenticated-request scope and reauthentication behavior."""

import asyncio

import httpx
import pytest

from mercadona_mcp.companion.session import extract_session_material, store_session
from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.mercadona.auth import AuthenticatedMercadonaClient
from mercadona_mcp.security import InMemorySecretStore


def _store() -> InMemorySecretStore:
    store = InMemorySecretStore()
    store_session(
        store, extract_session_material('{"token":"secret","userUuid":"user"}')
    )
    return store


def test_validation_scopes_bearer_token_to_mercadona() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "tienda.mercadona.es"
        assert request.headers["Authorization"] == "Bearer secret"
        assert request.url.path == "/api/customers/user/cart/"
        return httpx.Response(200)

    async def run() -> None:
        client = AuthenticatedMercadonaClient(
            _store(),
            client=httpx.AsyncClient(
                transport=httpx.MockTransport(handler),
                base_url="https://tienda.mercadona.es/api",
            ),
        )
        await client.validate_session()

    asyncio.run(run())


def test_missing_or_expired_session_requires_reauthentication() -> None:
    async def run() -> None:
        missing = AuthenticatedMercadonaClient(InMemorySecretStore())
        with pytest.raises(MercadonaMCPError) as missing_error:
            await missing.validate_session()
        assert missing_error.value.code is ErrorCode.REAUTHENTICATION_REQUIRED

        expired = AuthenticatedMercadonaClient(
            _store(),
            client=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(401)),
                base_url="https://tienda.mercadona.es/api",
            ),
        )
        with pytest.raises(MercadonaMCPError) as expired_error:
            await expired.validate_session()
        assert expired_error.value.code is ErrorCode.REAUTHENTICATION_REQUIRED

    asyncio.run(run())


def test_authenticated_client_rejects_non_mercadona_origins() -> None:
    async def run() -> None:
        client = AuthenticatedMercadonaClient(
            _store(),
            client=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(200))
            ),
            base_url="https://example.test",
        )
        with pytest.raises(ValueError, match="restricted to Mercadona"):
            await client.get_json("/private")

    asyncio.run(run())
