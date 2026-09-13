"""Tests for the secure secret-storage boundary."""

from mercadona_mcp.security.keychain import (
    InMemorySecretStore,
    KeychainSecretStore,
    SecretValue,
)


class _FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.values.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.values[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.values.pop((service_name, username), None)


def test_keychain_adapter_stores_loads_and_deletes_secrets() -> None:
    backend = _FakeKeyring()
    store = KeychainSecretStore(service_name="test.mercadona-mcp", backend=backend)
    secret = SecretValue("access-token-value")

    store.store("session", secret)

    assert store.contains("session")
    loaded = store.load("session")
    assert loaded is not None
    assert loaded.reveal() == "access-token-value"

    store.delete("session")

    assert not store.contains("session")
    assert store.load("session") is None


def test_in_memory_store_has_safe_status_only() -> None:
    store = InMemorySecretStore()
    store.store("session", SecretValue("access-token-value"))

    assert store.safe_status() == {"session": True}


def test_secret_representations_are_redacted() -> None:
    secret = SecretValue("access-token-value")

    assert "access-token-value" not in repr(secret)
    assert "access-token-value" not in str(secret)
    assert str(secret) == "[REDACTED]"
