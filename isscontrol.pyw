"""ISSControl, without a console window behind it.

Double-clicking a plain .py file on Windows runs it under python.exe, which
opens a console window and leaves it there for as long as the app is up. The
.pyw extension is the fix: Windows hands the file to pyw.exe, which runs it
under pythonw.exe instead, and that has no console at all.

**This file must not have a shebang line, and that is not an oversight.**
pyw.exe defaults to pythonw.exe, but a shebang overrides that default, and
`#!/usr/bin/env python3` names the *console* interpreter -- so adding one
puts the console window straight back. (Measured in the sibling pwgen
project on Windows 11: no shebang runs pythonw.exe with no console; `python3`
runs python.exe with a conhost window; `pythonw` fails to start anything at
all.)

No shebang also means Windows picks the interpreter on its own -- the `py`
launcher's registered default, which is not necessarily the one `pip install
-e .` was run under (a machine with several Pythons installed can easily have
ISSControl's dependencies in one and the .pyw default pointing at another;
this is the same environment-mismatch problem iss_locate.py works around for
`iss` itself, just on ISSControl's own side this time). Under a normal
console that would at least show a traceback; under pythonw it wouldn't --
the exception has nowhere to print to, so the double-click would just
silently do nothing. The try/except below exists solely so that failure
mode surfaces as a message box instead of vanishing.
"""

import sys
import tkinter as tk
from tkinter import messagebox


def _show_startup_error(error: BaseException) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "ISSControl failed to start",
        f"{type(error).__name__}: {error}\n\n"
        f"Running under: {sys.executable}\n\n"
        "If this looks like a missing dependency, that Python isn't the one "
        "ISSControl was installed into. Install it there with:\n\n"
        f'"{sys.executable}" -m pip install -e .',
    )


if __name__ == "__main__":
    try:
        from isscontrol.app import run
    except Exception as error:
        _show_startup_error(error)
        raise SystemExit(1) from error

    run()
