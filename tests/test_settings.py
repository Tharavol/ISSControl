from __future__ import annotations

import json
from pathlib import Path

import pytest

from isscontrol import settings as settings_module
from isscontrol.settings import DEFAULT_SETTINGS, load_settings, save_settings


@pytest.fixture(autouse=True)
def _isolated_settings_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "settings_path", lambda: path)
    return path


class TestLoadSettings:
    def test_missing_file_returns_defaults(self) -> None:
        loaded = load_settings()

        assert loaded == DEFAULT_SETTINGS

    def test_not_json_returns_defaults(self, _isolated_settings_path: Path) -> None:
        _isolated_settings_path.write_text("not json{", encoding="utf-8")

        assert load_settings() == DEFAULT_SETTINGS

    def test_not_a_dict_returns_defaults(self, _isolated_settings_path: Path) -> None:
        _isolated_settings_path.write_text("[1, 2, 3]", encoding="utf-8")

        assert load_settings() == DEFAULT_SETTINGS

    def test_valid_fields_round_trip(self, _isolated_settings_path: Path) -> None:
        saved = {
            "window_x": 100,
            "window_y": 200,
            "window_width": 800,
            "window_height": 600,
            "iss_path_override": r"C:\tools\iss.exe",
            "iss_args": ["--extra-flag"],
            "host": "mac.local",
            "user": "me",
            "advertise": "1920x1080",
            "hidpi": "on",
            "decoder": "vt-hevc444",
            "audio": False,
            "curtain": False,
        }
        _isolated_settings_path.write_text(json.dumps(saved), encoding="utf-8")

        assert load_settings() == saved

    def test_window_width_below_minimum_is_clamped(self, _isolated_settings_path: Path) -> None:
        _isolated_settings_path.write_text(
            json.dumps({"window_width": 10, "window_height": 10}), encoding="utf-8"
        )

        loaded = load_settings()

        assert loaded["window_width"] == settings_module.MIN_WIDTH
        assert loaded["window_height"] == settings_module.MIN_HEIGHT

    def test_bool_is_not_accepted_as_int(self, _isolated_settings_path: Path) -> None:
        _isolated_settings_path.write_text(
            json.dumps({"window_x": True, "window_y": False}), encoding="utf-8"
        )

        loaded = load_settings()

        assert loaded["window_x"] is None
        assert loaded["window_y"] is None

    def test_non_string_args_are_dropped(self, _isolated_settings_path: Path) -> None:
        _isolated_settings_path.write_text(
            json.dumps({"iss_args": ["--host", 5, None, "mac.local"]}), encoding="utf-8"
        )

        assert load_settings()["iss_args"] == ["--host", "mac.local"]

    def test_stale_unknown_keys_are_ignored(self, _isolated_settings_path: Path) -> None:
        _isolated_settings_path.write_text(
            json.dumps({"window_width": 800, "some_removed_field": "x"}), encoding="utf-8"
        )

        loaded = load_settings()

        assert "some_removed_field" not in loaded
        assert loaded["window_width"] == 800


class TestSaveSettings:
    def test_writes_only_known_fields(self, _isolated_settings_path: Path) -> None:
        ok = save_settings({**DEFAULT_SETTINGS, "window_width": 900, "junk": "dropped"})

        assert ok is True
        on_disk = json.loads(_isolated_settings_path.read_text(encoding="utf-8"))
        assert on_disk["window_width"] == 900
        assert "junk" not in on_disk

    def test_creates_parent_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        nested = tmp_path / "nested" / "dir" / "settings.json"
        monkeypatch.setattr(settings_module, "settings_path", lambda: nested)

        assert save_settings(dict(DEFAULT_SETTINGS)) is True
        assert nested.is_file()

    def test_round_trips_through_load(self, _isolated_settings_path: Path) -> None:
        original = {
            **DEFAULT_SETTINGS,
            "window_x": 50,
            "window_y": 60,
            "window_width": 700,
            "window_height": 500,
        }
        save_settings(original)

        assert load_settings() == original
