"""Comparing the local iShareScreen install against upstream, and updating it.

`git ls-remote <url> HEAD` is used instead of the GitHub API to find
upstream's current commit (#9): it resolves the symbolic HEAD ref for us
regardless of what the default branch is actually named, needs no
authentication or rate-limit handling, and -- unlike the API -- is a tool
this app already depends on having available, since the update action
itself (#10) shells out to `pip install git+...`, which needs git on PATH
to do its own clone.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from .iss_install import (
    UPSTREAM_REPO_URL,
    InstalledInfo,
    NotInstalledError,
    get_installed_info,
    python_for_install,
)
from .managed_process import ManagedProcess

UPSTREAM_CHECK_TIMEOUT_S = 10.0


class UpstreamCheckError(RuntimeError):
    """Raised when upstream's current commit could not be determined."""


class UpdateState(Enum):
    UP_TO_DATE = auto()
    UPDATE_AVAILABLE = auto()
    # Installed, but not from the upstream VCS URL (e.g. editable/local
    # install) -- there's no commit to compare against upstream.
    UNVERSIONED = auto()


@dataclass(frozen=True)
class UpdateStatus:
    state: UpdateState
    installed: InstalledInfo


def get_upstream_head(repo_url: str = UPSTREAM_REPO_URL) -> str:
    """Return the full commit SHA upstream's HEAD currently points at."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", repo_url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=UPSTREAM_CHECK_TIMEOUT_S,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as error:
        raise UpstreamCheckError("git is not installed or not on PATH.") from error
    except subprocess.TimeoutExpired as error:
        raise UpstreamCheckError("Timed out reaching GitHub.") from error

    if result.returncode != 0:
        raise UpstreamCheckError((result.stderr or "git ls-remote failed").strip())

    sha, _, _ref = result.stdout.strip().partition("\t")
    if len(sha) != 40:
        raise UpstreamCheckError("Unexpected output from git ls-remote.")
    return sha


def check_for_update(iss_path: Path) -> UpdateStatus:
    """Read the local install (#8) and compare it against upstream HEAD (#9).

    Raises NotInstalledError or UpstreamCheckError if either half can't be
    determined -- the caller decides how to surface that.
    """
    installed = get_installed_info(iss_path)
    if installed.commit is None:
        return UpdateStatus(UpdateState.UNVERSIONED, installed)

    upstream_commit = get_upstream_head()
    state = (
        UpdateState.UP_TO_DATE
        if installed.commit == upstream_commit
        else UpdateState.UPDATE_AVAILABLE
    )
    return UpdateStatus(state, installed)


def start_update(iss_path: Path, repo_url: str = UPSTREAM_REPO_URL) -> ManagedProcess:
    """Launch `pip install --upgrade --force-reinstall git+<repo_url>`.

    Runs against the interpreter that owns iss's own install (#8's
    site-packages resolution), not necessarily the one running ISSControl,
    so the upgrade lands in the environment iss actually runs from.
    """
    python = python_for_install(iss_path)
    if python is None:
        raise NotInstalledError(
            f"Could not find the Python interpreter for the environment iss is "
            f"installed in (looked next to {iss_path})."
        )
    proc = ManagedProcess(
        python,
        ["-m", "pip", "install", "--upgrade", "--force-reinstall", f"git+{repo_url}"],
    )
    proc.start()
    return proc
