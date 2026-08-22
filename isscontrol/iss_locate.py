"""Locating the `iss` launcher.

`pip install`ing iShareScreen drops its console scripts into whichever
Python's Scripts directory is active at install time -- a venv, or (very
often on Windows) the per-user site directory under
%APPDATA%\\Python\\PythonXY. Neither is reliably on PATH, which is why a
plain `iss` at a shell often does nothing (see issue #4).

Resolution order: an explicit override, the interpreter ISSControl itself
is running under (covers a shared venv), whatever PATH does have, then a
scan of the well-known per-user install locations pip uses.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ENV_OVERRIDE = "ISSCONTROL_ISS_PATH"

_EXE_NAME = "iss.exe" if sys.platform == "win32" else "iss"


class IssNotFoundError(RuntimeError):
    """Raised when no iss launcher could be found anywhere searched."""


def find_iss(override: str | Path | None = None) -> Path:
    """Return a path to the iss launcher, or raise IssNotFoundError.

    *override* (or the ISSCONTROL_ISS_PATH env var if *override* is not
    given) is trusted as-is and must point directly at the launcher, or at
    a directory containing it -- it exists so a settings dialog (#11) has
    something to plug into without this module changing.
    """
    explicit = override if override is not None else os.environ.get(ENV_OVERRIDE)
    if explicit:
        path = Path(explicit)
        if path.is_dir():
            path = path / _EXE_NAME
        if path.is_file():
            return path
        raise IssNotFoundError(f"Configured iss path does not exist: {path}")

    candidates = [
        # Same environment as ISSControl itself, if it happens to be installed
        # alongside iss (a shared venv).
        Path(sys.exec_prefix) / "Scripts" / _EXE_NAME,
        Path(sys.exec_prefix) / "bin" / _EXE_NAME,
    ]

    on_path = shutil.which("iss")
    if on_path:
        candidates.append(Path(on_path))

    candidates.extend(_well_known_user_installs())

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise IssNotFoundError(
        "Could not find the iss launcher anywhere searched. It's usually "
        "installed to a per-user Scripts folder that isn't on PATH -- set "
        f"the {ENV_OVERRIDE} environment variable to its full path if this "
        "keeps happening."
    )


def _well_known_user_installs() -> list[Path]:
    """Scripts dirs pip's per-user (no-venv) install uses.

    Windows: %APPDATA%\\Python\\PythonXY\\Scripts, newest version first,
    since a fresh install is more likely to be the one meant. POSIX:
    ~/.local/bin, which is not versioned by Python release.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return []
        root = Path(appdata) / "Python"
        if not root.is_dir():
            return []
        versions = sorted(
            (p for p in root.glob("Python3*") if p.is_dir()),
            key=lambda p: p.name,
            reverse=True,
        )
        return [version / "Scripts" / _EXE_NAME for version in versions]
    return [Path.home() / ".local" / "bin" / _EXE_NAME]
