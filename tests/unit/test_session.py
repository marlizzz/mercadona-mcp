"""Tests for minimized session capture and secret-store persistence."""

import pytest

from mercadona_mcp.companion.session import (
    delete_session,
    extract_session_material,
    load_session,
    store_session,
)
from mercadona_mcp.errors import MercadonaMCPError
from mercadona_mcp.security import InMemorySecretStore


def test_session_capture_minimizes_observed_browser_storage() -> None:
    session = extract_session_material(
        '{"token":"access","refreshToken":"refresh","userUuid":"user","uuid":"unused"}'
    )

    assert session.user_uuid == "user"
    assert "unused" not in repr(session)


@pytest.mark.parametrize("raw", ["not-json", "{}", '{"token":"access"}'])
def test_invalid_browser_storage_requires_reauthentication(raw: str) -> None:
    with pytest.raises(MercadonaMCPError) as raised:
        extract_session_material(raw)

    assert raised.value.code.value == "reauthentication_required"


def test_session_is_stored_and_deleted_through_secret_store() -> None:
    store = InMemorySecretStore()
    session = extract_session_material(
        '{"token":"access","refreshToken":"refresh","userUuid":"user"}'
    )

    store_session(store, session)

    assert load_session(store) == session
    assert "access" not in repr(store.load("mercadona-session"))

    delete_session(store)

    assert load_session(store) is None
