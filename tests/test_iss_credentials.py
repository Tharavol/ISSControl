from __future__ import annotations

import keyring.errors
import pytest

from isscontrol import iss_credentials


@pytest.fixture(autouse=True)
def _fake_keyring(monkeypatch: pytest.MonkeyPatch) -> dict:
    """An in-memory stand-in so tests never touch the real credential store."""
    store: dict[tuple[str, str], str] = {}

    def fake_get(service: str, account: str) -> str | None:
        return store.get((service, account))

    def fake_set(service: str, account: str, password: str) -> None:
        store[(service, account)] = password

    def fake_delete(service: str, account: str) -> None:
        try:
            del store[(service, account)]
        except KeyError as error:
            raise keyring.errors.PasswordDeleteError("not found") from error

    monkeypatch.setattr(iss_credentials.keyring, "get_password", fake_get)
    monkeypatch.setattr(iss_credentials.keyring, "set_password", fake_set)
    monkeypatch.setattr(iss_credentials.keyring, "delete_password", fake_delete)
    return store


class TestCredentials:
    def test_round_trip(self) -> None:
        iss_credentials.set_password("mac.local", "me", "hunter2")

        assert iss_credentials.get_password("mac.local", "me") == "hunter2"

    def test_different_account_is_isolated(self) -> None:
        iss_credentials.set_password("mac.local", "me", "hunter2")

        assert iss_credentials.get_password("mac.local", "someone-else") is None
        assert iss_credentials.get_password("other.local", "me") is None

    def test_missing_host_or_user_returns_none_without_querying(self) -> None:
        assert iss_credentials.get_password("", "me") is None
        assert iss_credentials.get_password("mac.local", "") is None

    def test_delete_removes_it(self) -> None:
        iss_credentials.set_password("mac.local", "me", "hunter2")

        iss_credentials.delete_password("mac.local", "me")

        assert iss_credentials.get_password("mac.local", "me") is None

    def test_delete_when_nothing_stored_does_not_raise(self) -> None:
        iss_credentials.delete_password("mac.local", "nobody")

    def test_get_password_swallows_keyring_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(service: str, account: str) -> str:
            raise keyring.errors.KeyringError("backend unavailable")

        monkeypatch.setattr(iss_credentials.keyring, "get_password", _raise)

        assert iss_credentials.get_password("mac.local", "me") is None
