from __future__ import annotations

from isscontrol.settings import DEFAULT_SETTINGS
from isscontrol.settings_dialog import describe_connection


class TestDescribeConnection:
    def test_never_mentions_password(self) -> None:
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "user": "me"}

        summary = describe_connection(settings)

        assert "password" not in summary.lower()

    def test_blank_host_and_user_show_placeholder(self) -> None:
        summary = describe_connection(dict(DEFAULT_SETTINGS))

        assert "(not set)" in summary

    def test_host_and_user_appear_verbatim(self) -> None:
        settings = {**DEFAULT_SETTINGS, "host": "mac.local", "user": "me"}

        summary = describe_connection(settings)

        assert "mac.local" in summary
        assert "me" in summary

    def test_frontend_uses_dialog_labels_not_raw_value(self) -> None:
        settings = {**DEFAULT_SETTINGS, "frontend": "desktop"}

        summary = describe_connection(settings)

        assert "Native window" in summary
        assert "desktop" not in summary.lower()

    def test_unrecognized_value_falls_back_to_raw_string(self) -> None:
        settings = {**DEFAULT_SETTINGS, "decoder": "some-future-decoder"}

        summary = describe_connection(settings)

        assert "some-future-decoder" in summary

    def test_audio_and_curtain_state_are_shown(self) -> None:
        settings = {**DEFAULT_SETTINGS, "audio": False, "curtain": False}

        summary = describe_connection(settings)

        assert "audio off" in summary
        assert "curtain off" in summary
