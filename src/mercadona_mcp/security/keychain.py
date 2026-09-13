"""Secret persistence through macOS Keychain, without plaintext file fallback."""

from collections.abc import Mapping
from typing import Protocol

import keyring
from keyring.errors import PasswordDeleteError

_DEFAULT_SERVICE_NAME = "com.mercadona-mcp"


class SecretValue:
    """A secret whose string representations are always redacted."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("secret value must not be empty")
        self._value = value

    def reveal(self) -> str:
        """Return the secret only for a trusted adapter/client boundary."""
        return self._value

    def __repr__(self) -> str:
        return "SecretValue([REDACTED])"

    def __str__(self) -> str:
        return "[REDACTED]"


class SecretStore(Protocol):
    """Persistent secret-store operations used by session management."""

    def store(self, key: str, secret: SecretValue) -> None: ...

    def load(self, key: str) -> SecretValue | None: ...

    def delete(self, key: str) -> None: ...

    def contains(self, key: str) -> bool: ...


class KeyringBackend(Protocol):
    """Subset of keyring's module API needed by the adapter."""

    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


class KeychainSecretStore:
    """Persist values in macOS Keychain through the active keyring backend."""

    def __init__(
        self,
        *,
        service_name: str = _DEFAULT_SERVICE_NAME,
        backend: KeyringBackend = keyring,
    ) -> None:
        self._service_name = service_name
        self._backend = backend

    def store(self, key: str, secret: SecretValue) -> None:
        self._backend.set_password(
            self._service_name, _validated_key(key), secret.reveal()
        )

    def load(self, key: str) -> SecretValue | None:
        secret = self._backend.get_password(self._service_name, _validated_key(key))
        return SecretValue(secret) if secret is not None else None

    def delete(self, key: str) -> None:
        try:
            self._backend.delete_password(self._service_name, _validated_key(key))
        except PasswordDeleteError:
            return

    def contains(self, key: str) -> bool:
        return self.load(key) is not None


class InMemorySecretStore:
    """Test-only secret store; it must never be selected in production wiring."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def store(self, key: str, secret: SecretValue) -> None:
        self._secrets[_validated_key(key)] = secret.reveal()

    def load(self, key: str) -> SecretValue | None:
        secret = self._secrets.get(_validated_key(key))
        return SecretValue(secret) if secret is not None else None

    def delete(self, key: str) -> None:
        self._secrets.pop(_validated_key(key), None)

    def contains(self, key: str) -> bool:
        return _validated_key(key) in self._secrets

    def safe_status(self) -> Mapping[str, bool]:
        """Expose key presence for tests without exposing secret values."""
        return {key: True for key in self._secrets}


def _validated_key(key: str) -> str:
    if not key:
        raise ValueError("secret key must not be empty")
    return key
