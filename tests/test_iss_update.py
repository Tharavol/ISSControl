from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from isscontrol import iss_update
from isscontrol.iss_update import (
    UpdateState,
    UpstreamCheckError,
    check_for_update,
    get_upstream_head,
)


def _make_installed(tmp_path: Path, commit: str | None) -> Path:
    env_root = tmp_path / "Python312"
    scripts = env_root / "Scripts"
    scripts.mkdir(parents=True)
    iss_path = scripts / "iss.exe"
    iss_path.touch()
    dist_info = env_root / "site-packages" / "isharescreen-0.1.0.dist-info"
    dist_info.mkdir(parents=True)
    if commit is not None:
        direct_url = {"vcs_info": {"commit_id": commit}}
        (dist_info / "direct_url.json").write_text(json.dumps(direct_url), encoding="utf-8")
    return iss_path


class _FakeCompletedProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class TestGetUpstreamHead:
    def test_parses_sha_from_ls_remote_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sha = "a" * 40
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: _FakeCompletedProcess(stdout=f"{sha}\tHEAD\n"),
        )

        assert get_upstream_head() == sha

    def test_git_not_found_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a, **k):
            raise FileNotFoundError

        monkeypatch.setattr(subprocess, "run", _raise)

        with pytest.raises(UpstreamCheckError):
            get_upstream_head()

    def test_nonzero_exit_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **k: _FakeCompletedProcess(stderr="fatal: could not read", returncode=128),
        )

        with pytest.raises(UpstreamCheckError):
            get_upstream_head()

    def test_timeout_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise(*a, **k):
            raise subprocess.TimeoutExpired(cmd="git", timeout=10)

        monkeypatch.setattr(subprocess, "run", _raise)

        with pytest.raises(UpstreamCheckError):
            get_upstream_head()


class TestCheckForUpdate:
    def test_matching_commits_is_up_to_date(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sha = "b" * 40
        iss_path = _make_installed(tmp_path, commit=sha)
        monkeypatch.setattr(iss_update, "get_upstream_head", lambda *a, **k: sha)

        status = check_for_update(iss_path)

        assert status.state is UpdateState.UP_TO_DATE

    def test_differing_commits_is_update_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        iss_path = _make_installed(tmp_path, commit="c" * 40)
        monkeypatch.setattr(iss_update, "get_upstream_head", lambda *a, **k: "d" * 40)

        status = check_for_update(iss_path)

        assert status.state is UpdateState.UPDATE_AVAILABLE

    def test_no_local_commit_is_unversioned_without_checking_upstream(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        iss_path = _make_installed(tmp_path, commit=None)

        def _fail(*a, **k):
            raise AssertionError("should not query upstream when there's no local commit")

        monkeypatch.setattr(iss_update, "get_upstream_head", _fail)

        status = check_for_update(iss_path)

        assert status.state is UpdateState.UNVERSIONED
