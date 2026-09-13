"""Minimal Mercadona session material held only in Keychain-backed storage."""

import json
from dataclasses import dataclass

from mercadona_mcp.errors import ErrorCode, MercadonaMCPError
from mercadona_mcp.security import SecretStore, SecretValue

SESSION_SECRET_KEY = "mercadona-session"


@dataclass(frozen=True, repr=False)
class SessionMaterial:
    """The verified minimum fields needed for authenticated Mercadona API calls."""

    token: str
    refresh_token: str
    user_uuid: str

    def __repr__(self) -> str:
        return "SessionMaterial([REDACTED])"


def extract_session_material(raw_storage_value: str) -> SessionMaterial:
    """Validate and minimize the observed `MO-user` browser-storage value."""
    try:
        payload = json.loads(raw_storage_value)
    except json.JSONDecodeError as error:
        raise _invalid_session() from error
    if not isinstance(payload, dict):
        raise _invalid_session()
    token = payload.get("token")
    refresh_token = payload.get("refreshToken")
    user_uuid = payload.get("userUuid")
    if not isinstance(token, str) or not token:
        raise _invalid_session()
    if not isinstance(refresh_token, str) or not refresh_token:
        raise _invalid_session()
    if not isinstance(user_uuid, str) or not user_uuid:
        raise _invalid_session()
    return SessionMaterial(
        token=token,
        refresh_token=refresh_token,
        user_uuid=user_uuid,
    )


def store_session(store: SecretStore, session: SessionMaterial) -> None:
    """Store one minimized JSON session value in the configured secret store."""
    store.store(
        SESSION_SECRET_KEY,
        SecretValue(
            json.dumps(
                {
                    "token": session.token,
                    "refreshToken": session.refresh_token,
                    "userUuid": session.user_uuid,
                },
                separators=(",", ":"),
            )
        ),
    )


def load_session(store: SecretStore) -> SessionMaterial | None:
    """Load and validate the stored session without exposing it in status output."""
    secret = store.load(SESSION_SECRET_KEY)
    return extract_session_material(secret.reveal()) if secret is not None else None


def delete_session(store: SecretStore) -> None:
    """Remove all locally stored Mercadona session material."""
    store.delete(SESSION_SECRET_KEY)


def _invalid_session() -> MercadonaMCPError:
    return MercadonaMCPError(
        ErrorCode.REAUTHENTICATION_REQUIRED,
        "Mercadona session data is invalid. Please run login again.",
    )
