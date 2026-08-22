from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from isscontrol.iss_install import NotInstalledError, get_installed_info, python_for_install


def _make_dist_info(site_packages: Path, version: str, commit: str | None) -> None:
    dist_info = site_packages / f"isharescreen-{version}.dist-info"
    dist_info.mkdir(parents=True)
    if commit is not None:
        direct_url = {"url": "https://github.com/renegadelink/iShareScreen.git", "vcs_info": {"commit_id": commit}}
        (dist_info / "direct_url.json").write_text(json.dumps(direct_url), encoding="utf-8")


class TestGetInstalledInfo:
    def test_per_user_layout_reads_commit(self, tmp_path: Path) -> None:
        env_root = tmp_path / "Python312"
        scripts = env_root / "Scripts"
        scripts.mkdir(parents=True)
        iss_path = scripts / "iss.exe"
        iss_path.touch()
        _make_dist_info(env_root / "site-packages", "0.1.0", "abc123def456")

        info = get_installed_info(iss_path)

        assert info.version == "0.1.0"
        assert info.commit == "abc123def456"

    def test_venv_layout_reads_commit(self, tmp_path: Path) -> None:
        env_root = tmp_path / "venv"
        scripts = env_root / "Scripts"
        scripts.mkdir(parents=True)
        iss_path = scripts / "iss.exe"
        iss_path.touch()
        _make_dist_info(env_root / "Lib" / "site-packages", "0.2.0", "deadbeef")

        info = get_installed_info(iss_path)

        assert info.version == "0.2.0"
        assert info.commit == "deadbeef"

    def test_no_direct_url_means_no_commit(self, tmp_path: Path) -> None:
        env_root = tmp_path / "Python312"
        scripts = env_root / "Scripts"
        scripts.mkdir(parents=True)
        iss_path = scripts / "iss.exe"
        iss_path.touch()
        _make_dist_info(env_root / "site-packages", "0.1.0", commit=None)

        info = get_installed_info(iss_path)

        assert info.version == "0.1.0"
        assert info.commit is None

    def test_missing_dist_info_raises(self, tmp_path: Path) -> None:
        env_root = tmp_path / "Python312"
        scripts = env_root / "Scripts"
        scripts.mkdir(parents=True)
        iss_path = scripts / "iss.exe"
        iss_path.touch()

        with pytest.raises(NotInstalledError):
            get_installed_info(iss_path)


class TestPythonForInstall:
    def test_finds_interpreter_next_to_scripts_dir(self, tmp_path: Path) -> None:
        env_root = tmp_path / "Python312"
        scripts = env_root / "Scripts"
        scripts.mkdir(parents=True)
        iss_path = scripts / "iss.exe"
        iss_path.touch()
        exe = "python.exe" if sys.platform == "win32" else "python"
        (env_root / exe).touch()

        assert python_for_install(iss_path) == env_root / exe

    def test_returns_none_when_no_interpreter_found(self, tmp_path: Path) -> None:
        env_root = tmp_path / "Python312"
        scripts = env_root / "Scripts"
        scripts.mkdir(parents=True)
        iss_path = scripts / "iss.exe"
        iss_path.touch()

        assert python_for_install(iss_path) is None
