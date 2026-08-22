"""Turning connection-default settings into iss's argv and stdin.

iss's browser connect form pre-fills entirely from CLI flags -- its own
README documents it: `iss --host mac.local -u me --advertise 1920x1080
--no-curtain` pre-fills the form instead of leaving it blank for every
launch. build_args() reads exactly the fields #14 added to settings.json
and turns them into that argv, then appends `iss_args` (#11) as an escape
hatch for anything not exposed by the settings dialog.

The password is handled separately from every other field here: it never
touches settings.json (see iss_credentials.py for why), and it can't go on
argv either -- iss's own --help says so, since anything on argv shows up in
`ps` / Task Manager. --password-stdin plus piping it as the first line of
stdin is the mechanism iss's own design assumes for this.
"""

from __future__ import annotations

from . import iss_credentials


def build_args(settings: dict) -> tuple[list[str], str | None]:
    """Return (argv, stdin_data) for launching iss from *settings*.

    stdin_data is the stored password plus a trailing newline, or None if
    nothing is stored for this host/user -- in which case --password-stdin
    is omitted too, since passing it with nothing to feed would just leave
    iss waiting on a line that never arrives.
    """
    args: list[str] = []

    host = settings.get("host", "")
    user = settings.get("user", "")
    if host:
        args += ["--host", host]
    if user:
        args += ["-u", user]

    for setting_field, flag in (
        ("advertise", "--advertise"),
        ("hidpi", "--hidpi"),
        ("decoder", "--decoder"),
    ):
        value = settings.get(setting_field, "")
        if value:
            args += [flag, value]

    if not settings.get("audio", True):
        args.append("--no-audio")
    if not settings.get("curtain", True):
        args.append("--no-curtain")

    stdin_data = None
    password = iss_credentials.get_password(host, user)
    if password:
        args.append("--password-stdin")
        stdin_data = password + "\n"

    args += settings.get("iss_args", [])
    return args, stdin_data
