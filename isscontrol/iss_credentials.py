"""Storing the connection password in Windows Credential Manager.

iss deliberately has no --password flag -- its own --help text notes argv
is visible in `ps` / shell history / Task Manager's command-line column, so
it only accepts a password via --password-stdin (piped) or an interactive
prompt. settings.json is plaintext and already used for the rest of the
connection defaults (#14), so that's not a place to put a secret either.
`keyring` puts it in Windows Credential Manager instead, keyed by the
host/user pair it belongs to (the same password rarely applies to two
different Macs or accounts); iss_launch.py is what actually pipes it over
stdin rather than argv, matching what iss's own design already assumes.

This was filed as "discuss the approach" (#15) rather than a locked-in
design -- keyring + Credential Manager is what got picked, being the
standard way to do this on Windows and needing no infrastructure of our
own to keep secure.
"""

from __future__ import annotations

import contextlib

import keyring
import keyring.errors

SERVICE_NAME = "ISSControl"


def _account(host: str, user: str) -> str:
    return f"{user}@{host}"


def get_password(host: str, user: str) -> str | None:
    """The stored password for this host/user, or None if nothing is stored.

    Also None (rather than raising) if the platform's credential store is
    unavailable for some reason -- a missing password must not be worse
    than not knowing whether one might exist.
    """
    if not host or not user:
        return None
    try:
        return keyring.get_password(SERVICE_NAME, _account(host, user))
    except keyring.errors.KeyringError:
        return None


def set_password(host: str, user: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, _account(host, user), password)


def delete_password(host: str, user: str) -> None:
    """Remove any stored password for this host/user. Never raises."""
    # Nothing stored is already the goal state, so PasswordDeleteError (the
    # only failure mode keyring documents for this) is not worth surfacing.
    with contextlib.suppress(keyring.errors.PasswordDeleteError):
        keyring.delete_password(SERVICE_NAME, _account(host, user))
