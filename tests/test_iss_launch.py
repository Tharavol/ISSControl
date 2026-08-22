from __future__ import annotations

import pytest

from isscontrol import iss_launch
from isscontrol.iss_launch import build_args
from isscontrol.settings import DEFAULT_SETTINGS


@pytest.fixture(autouse=True)
def _no_stored_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(iss_launch.iss_credentials, "get_password", lambda *a: None)


class TestBuildArgs:
    def test_defaults_send_hidpi_for_auto_resolution(self) -> None:
        args, stdin_data = build_args(dict(DEFAULT_SETTINGS))

        assert args == ["--hidpi", "2.0"]
        assert stdin_data is None

    def test_host_and_user_become_flags(self) -> None:
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "user": "me"}

        args, _ = build_args(settings)

        assert args[:4] == ["--host", "mac.local", "-u", "me"]

    def test_auto_resolution_sends_hidpi_with_chosen_scale(self) -> None:
        settings = {**DEFAULT_SETTINGS, "advertise": "auto", "hidpi": "3.0"}

        args, _ = build_args(settings)

        assert args == ["--hidpi", "3.0"]
        assert "--advertise" not in args

    def test_explicit_resolution_divides_by_scale_into_advertise(self) -> None:
        # Same math as isharescreen.gui.connect's web form: logical points =
        # backing ÷ scale, so a 1920x1080 backing at 200% scale advertises
        # 960x540 logical points (@2.0, so the host redraws it at 1920x1080).
        settings = {**DEFAULT_SETTINGS, "advertise": "1920x1080", "hidpi": "2.0"}

        args, _ = build_args(settings)

        assert "--advertise" in args
        assert args[args.index("--advertise") + 1] == "960x540@2.0"
        assert "--hidpi" not in args

    def test_malformed_resolution_falls_back_to_raw_value(self) -> None:
        settings = {**DEFAULT_SETTINGS, "advertise": "not-a-resolution", "hidpi": "2.0"}

        args, _ = build_args(settings)

        assert args == ["--advertise", "not-a-resolution"]

    def test_decoder_auto_is_omitted(self) -> None:
        settings = {**DEFAULT_SETTINGS, "decoder": "auto"}

        args, _ = build_args(settings)

        assert "--decoder" not in args

    def test_decoder_choice_is_passed_through(self) -> None:
        settings = {**DEFAULT_SETTINGS, "decoder": "qsv-hevc444"}

        args, _ = build_args(settings)

        assert args[-2:] == ["--decoder", "qsv-hevc444"]

    def test_audio_and_curtain_true_add_no_flags(self) -> None:
        settings = {**DEFAULT_SETTINGS, "audio": True, "curtain": True}

        args, _ = build_args(settings)

        assert "--no-audio" not in args
        assert "--no-curtain" not in args

    def test_audio_and_curtain_false_add_flags(self) -> None:
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

    def test_no_stored_password_omits_flag_and_stdin(self) -> None:
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "user": "me"}

        args, stdin_data = build_args(settings)

        assert "--password-stdin" not in args
        assert stdin_data is None

    def test_iss_args_appended_last(self) -> None:
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "iss_args": ["--port", "5901"]}

        args, _ = build_args(settings)

        assert args[-2:] == ["--port", "5901"]
