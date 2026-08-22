"""Turning connection-default settings into iss's argv and stdin.

build_args() reads the fields #14 added to settings.json and turns them
into iss's argv, then appends `iss_args` (#11) as an escape hatch for
anything not exposed by the settings dialog. Resolution and Display scale
combine into a single --advertise flag the same way isharescreen's own web
connect form (isharescreen.gui.connect._launch) does it: Resolution is the
encoded BACKING size (what drives bandwidth), Display scale is how large
the host draws its UI, and --advertise itself takes *logical* points --
backing ÷ scale -- which the host then redraws at `scale` so the UI is
sharp without changing what's actually encoded. Picking "auto" leaves
nothing to divide, so the scale rides --hidpi on its own instead. Matching
this (rather than passing Resolution straight through as --advertise) is
what makes the settings dialog's numbers mean what they say next to the web
form's identical-looking dropdowns.

The password is handled separately from every other field here: it never
touches settings.json (see iss_credentials.py for why), and it can't go on
argv either -- iss's own --help says so, since anything on argv shows up in
`ps` / Task Manager. --password-stdin plus piping it as the first line of
stdin is the mechanism iss's own design assumes for this.
"""

from __future__ import annotations

from . import iss_credentials

DEFAULT_SCALE = "2.0"


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

    args += _resolution_args(settings)

    decoder = (settings.get("decoder") or "auto").strip()
    if decoder and decoder != "auto":
        args += ["--decoder", decoder]

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


def _resolution_args(settings: dict) -> list[str]:
    advertise = (settings.get("advertise") or "auto").strip() or "auto"
    scale = (settings.get("hidpi") or DEFAULT_SCALE).strip() or DEFAULT_SCALE

    if advertise.lower() == "auto":
        return ["--hidpi", scale]

    try:
        backing_w, backing_h = (int(x) for x in advertise.lower().split("x", 1))
        s = float(scale)
        # Even logical dims, same rounding the web form uses.
        logical_w = max(2, round(backing_w / s / 2) * 2)
        logical_h = max(2, round(backing_h / s / 2) * 2)
        return ["--advertise", f"{logical_w}x{logical_h}@{scale}"]
    except (ValueError, ZeroDivisionError):
        # Not "WxH" or scale isn't a number (a hand-edited settings.json,
        # say) -- pass it through as-is rather than silently dropping it.
        return ["--advertise", advertise]
