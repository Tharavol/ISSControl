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

Nothing but the launch lives here, so running this or `python -m isscontrol`
behaves identically. That does mean anything this program would have
printed, tracebacks included, goes nowhere: run `python -m isscontrol` from
a terminal to diagnose a window that will not open.
"""

from isscontrol.app import run

if __name__ == "__main__":
    run()
