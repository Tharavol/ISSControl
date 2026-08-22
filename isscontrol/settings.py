"""Remembering the window's position/size and a couple of launch preferences
between sessions.

Modelled on the sibling pwgen/AddOnTools projects' settings.py: one JSON
file, every field validated on its own so a hand-edited or truncated file
costs only the field it broke rather than stopping the app from starting.
Unlike those two -- flat scripts run from a git checkout, which keep
settings.json next to the script itself -- ISSControl is pip-installed, and
site-packages is not a place to write to. This instead follows AddOnSync's
convention and stores the file under the per-user app-data directory.

`iss_path_override` and `iss_args` predate any settings UI -- #14 added one
(SettingsDialog), but only for the connection defaults below; those two
remain reachable only by hand-editing the file, same as pwgen/AddOnTools'
settings.json before either project had a preferences dialog.

The connection defaults (host/user/advertise/hidpi/decoder/audio/curtain)
mirror the *values* isharescreen's own web connect form (isharescreen.gui.
connect) offers -- same resolution/scale/decoder presets, same defaults --
so the settings dialog reads like that form. iss_launch.py is where these
turn into iss's actual argv, including reproducing that form's own
resolution-plus-scale-become-one---advertise-flag math. The password is
deliberately not one of these fields: iss has no --password flag by design
(anything on argv is visible in ps/Task Manager), and settings.json is
plaintext read/write with no access control, so it is not a place to put a
secret either. iss_credentials.py stores it in Windows Credential Manager
instead (#15).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "ISSControl"
SETTINGS_FILENAME = "settings.json"

# Matches the fixed minsize app.py's run() applies to the window -- a saved
# size smaller than this would be shrunk right back by Tk anyway.
MIN_WIDTH = 520
MIN_HEIGHT = 440
MAX_DIMENSION = 10000

MAX_ARGS = 50
MAX_ARG_LEN = 500
MAX_PATH_LEN = 32767
MAX_FIELD_LEN = 255

DEFAULT_SETTINGS = {
    # None means "let Tk place it" -- there's nothing sensible to default a
    # position to before a screen size is known.
    "window_x": None,
    "window_y": None,
    "window_width": 640,
    "window_height": 560,
    # "" means autodetect (find_iss()'s own search order) -- see issue #4.
    "iss_path_override": "",
    "iss_args": [],
    # Connection defaults (#14). host/user: "" means the field is blank.
    # advertise/hidpi/decoder default to the same choices isharescreen's own
    # web connect form opens on (see iss_launch.py for where these two
    # combine into a single --advertise flag the way that form does) --
    # "auto"/"2.0"/"auto" are real selectable values here, not a blank
    # meaning "omit the flag".
    "host": "",
    "user": "",
    "advertise": "auto",
    "hidpi": "2.0",
    "decoder": "auto",
    # iss defaults both to on; False is the only state worth storing, since
    # it's the one that adds a flag (--no-audio/--no-curtain).
    "audio": True,
    "curtain": True,
}

# The field names the settings dialog (#14) writes as plain strings, each
# capped at MAX_FIELD_LEN -- short values, but a hand-edited file must not
# be able to put a novel in any of them.
_STRING_FIELDS = ("host", "user", "advertise", "hidpi", "decoder")


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_NAME


def settings_path() -> Path:
    return app_data_dir() / SETTINGS_FILENAME


def _clean_int(value: object, minimum: int, maximum: int) -> int | None:
    # bool is a subclass of int, so True/False would otherwise pass as 1/0.
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(minimum, min(maximum, value))


def load_settings() -> dict:
    """Last session's settings, defaulting anything missing or unusable.

    A hand-edited or truncated file must never stop the window from opening,
    so each field is validated in isolation and a bad one falls back to its
    default alone.
    """
    settings = dict(DEFAULT_SETTINGS)
    settings["iss_args"] = []
    try:
        saved = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):  # missing, or not JSON
        return settings
    if not isinstance(saved, dict):
        return settings

    for field in ("window_x", "window_y"):
        value = saved.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            settings[field] = value

    width = _clean_int(saved.get("window_width"), MIN_WIDTH, MAX_DIMENSION)
    if width is not None:
        settings["window_width"] = width
    height = _clean_int(saved.get("window_height"), MIN_HEIGHT, MAX_DIMENSION)
    if height is not None:
        settings["window_height"] = height

    override = saved.get("iss_path_override")
    if isinstance(override, str):
        settings["iss_path_override"] = override[:MAX_PATH_LEN]

    args = saved.get("iss_args")
    if isinstance(args, list):
        settings["iss_args"] = [a[:MAX_ARG_LEN] for a in args[:MAX_ARGS] if isinstance(a, str)]

    for field in _STRING_FIELDS:
        value = saved.get(field)
        if isinstance(value, str):
            settings[field] = value[:MAX_FIELD_LEN]

    for flag in ("audio", "curtain"):
        if isinstance(saved.get(flag), bool):
            settings[flag] = saved[flag]

    return settings


def save_settings(settings: dict) -> bool:
    """Write settings out. Returns True, or False if it could not be written.

    Failure never raises -- a read-only profile must not break closing the
    window -- but it is reported rather than swallowed silently.

    Only the known fields are written, so a stale key from an older version
    is dropped rather than carried forward for ever.
    """
    keep = {k: settings.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write beside the target and rename, so a save interrupted midway
        # (crash, power loss) cannot leave a truncated file behind.
        staging = path.with_suffix(".json.tmp")
        staging.write_text(json.dumps(keep, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        staging.replace(path)
    except OSError:
        return False
    return True
