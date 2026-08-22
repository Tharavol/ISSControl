"""Reading what iShareScreen is actually installed.

iShareScreen's own version string is static in its packaging regardless of
which commit is actually installed -- pip does not bump it per-commit -- so
the version alone can't answer "is this stale". The commit SHA pip recorded
at install time is the only reliable signal, and for a `pip install
git+...` it isn't exposed by the package itself: pip writes it to a
direct_url.json file (PEP 610) next to the dist-info, as
`vcs_info.commit_id`.

Locating *which* dist-info matters as much as reading it: iss_locate.py
exists because iss's console script can be installed to a per-user Scripts
directory or a venv that is not the same Python environment ISSControl
itself is running under. importlib.metadata only sees the current
interpreter's environment, so it can't be used here -- instead this derives
the install's site-packages directory from the resolved iss launcher path
and reads dist-info straight off disk.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

DISTRIBUTION_NAME = "isharescreen"
UPSTREAM_REPO_URL = "https://github.com/renegadelink/iShareScreen.git"


class NotInstalledError(RuntimeError):
    """Raised when no isharescreen dist-info can be found for the resolved install."""


@dataclass(frozen=True)
class InstalledInfo:
    version: str
    # None if iss wasn't installed from a VCS URL (e.g. a local/editable
    # install, or a plain PyPI release) -- there's no commit to compare then.
    commit: str | None


def get_installed_info(iss_path: Path) -> InstalledInfo:
    """Return version/commit info for the iss install that *iss_path* resolves to.

    Raises NotInstalledError if no matching dist-info is found in any of the
    site-packages directories associated with that launcher.
    """
    for site_packages in _site_packages_dirs(iss_path):
        if not site_packages.is_dir():
            continue
        matches = sorted(site_packages.glob(f"{DISTRIBUTION_NAME}-*.dist-info"))
        if matches:
            # Newest (highest-sorting version string) if more than one somehow
            # lingers, though pip normally leaves just the one.
            return _read_dist_info(matches[-1])

    raise NotInstalledError(
        f"Could not find {DISTRIBUTION_NAME} package metadata alongside {iss_path}."
    )


def _site_packages_dirs(iss_path: Path) -> list[Path]:
    """The site-packages dirs an env whose Scripts/bin dir holds *iss_path* could use."""
    env_root = iss_path.parent.parent
    return [
        env_root / "site-packages",  # per-user Python install layout (no venv)
        env_root / "Lib" / "site-packages",  # venv layout on Windows
        *sorted(env_root.glob("lib/python3.*/site-packages")),  # venv layout on POSIX
    ]


def _read_dist_info(dist_info: Path) -> InstalledInfo:
    version = dist_info.name.removeprefix(f"{DISTRIBUTION_NAME}-").removesuffix(".dist-info")
    commit = None
    direct_url_path = dist_info / "direct_url.json"
    if direct_url_path.is_file():
        try:
            data = json.loads(direct_url_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        commit = data.get("vcs_info", {}).get("commit_id")
    return InstalledInfo(version=version, commit=commit)


def python_for_install(iss_path: Path) -> Path | None:
    """Return the interpreter that owns the environment *iss_path* lives in.

    Used to run `pip install --upgrade` (#10) against the *same* environment
    iss is actually installed in, which is frequently not the Python running
    ISSControl itself -- see iss_locate.py's module docstring for why.
    """
    env_root = iss_path.parent.parent
    exe = "python.exe" if sys.platform == "win32" else "python"
    candidates = [env_root / exe, env_root / "bin" / exe, iss_path.parent / exe]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
