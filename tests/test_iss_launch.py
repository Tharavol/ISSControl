from __future__ import annotations

import pytest

from isscontrol import iss_launch
from isscontrol.iss_launch import build_args
from isscontrol.settings import DEFAULT_SETTINGS


class TestBuildArgs:
    def test_no_settings_produces_no_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)

        args, stdin_data = build_args(dict(DEFAULT_SETTINGS))

        assert args == []
        assert stdin_data is None

    def test_host_and_user_become_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "user": "me"}

        args, _ = build_args(settings)

        assert args == ["--host", "mac.local", "-u", "me"]

    def test_optional_string_fields_are_omitted_when_blank(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)

        args, _ = build_args(dict(DEFAULT_SETTINGS))

        assert "--advertise" not in args
        assert "--hidpi" not in args
        assert "--decoder" not in args

    def test_optional_string_fields_are_included_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)
        settings = {
            **DEFAULT_SETTINGS,
            "advertise": "1920x1080",
            "hidpi": "on",
            "decoder": "vt-hevc444",
        }

        args, _ = build_args(settings)

        assert "--advertise" in args and "1920x1080" in args
        assert "--hidpi" in args and "on" in args
        assert "--decoder" in args and "vt-hevc444" in args

    def test_audio_and_curtain_true_add_no_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)
        settings = {**DEFAULT_SETTINGS, "audio": True, "curtain": True}

        args, _ = build_args(settings)

        assert "--no-audio" not in args
        assert "--no-curtain" not in args

    def test_audio_and_curtain_false_add_flags(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)
        settings = {**DEFAULT_SETTINGS, "audio": False, "curtain": False}

        args, _ = build_args(settings)

        assert "--no-audio" in args
        assert "--no-curtain" in args

    def test_stored_password_adds_flag_and_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            iss_launch.iss_credentials, "get_password", lambda host, user: "hunter2"
        )
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "user": "me"}

        args, stdin_data = build_args(settings)

        assert "--password-stdin" in args
        assert stdin_data == "hunter2\n"

    def test_no_stored_password_omits_flag_and_stdin(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "user": "me"}

        args, stdin_data = build_args(settings)

        assert "--password-stdin" not in args
        assert stdin_data is None

    def test_iss_args_appended_last(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "iss_args": ["--port", "5901"]}

        args, _ = build_args(settings)

        assert args[-2:] == ["--port", "5901"]
