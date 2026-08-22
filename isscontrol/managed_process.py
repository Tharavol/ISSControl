"""Launching and stopping a child process whose output feeds the log pane.

Originally written just for `iss` (see issue #6: it has no documented
shutdown path of its own -- its README still describes a removed terminal
UI, and the real default flow opens a browser connect GUI that just runs
until killed). The same shape -- stream output through a queue so the Tk
main thread can drain it without blocking, and take the whole process tree
down on stop rather than trusting it to exit cleanly -- is also what the
update flow (#10) needs to run `pip install --upgrade` and show its output
live, so it moved out of iss_process.py into this process-agnostic module.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path


class ManagedProcess:
    """One subprocess invocation. Not reusable -- start a new instance to relaunch."""

    def __init__(self, executable: Path, args: list[str] | None = None) -> None:
        self._executable = executable
        self._args = args or []
        self._proc: subprocess.Popen[str] | None = None
        self.output: queue.Queue[str] = queue.Queue()

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc is not None else None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def exit_code(self) -> int | None:
        return self._proc.poll() if self._proc is not None else None

    def start(self) -> None:
        # Without this, a piped Python child sees its stdout is not a real
        # console and falls back to the Windows ANSI codepage -- iss's own
        # startup banner prints a U+2192 arrow that codepage can't encode,
        # and it crashes on launch every time its output is piped rather
        # than shown in a terminal. Forcing UTF-8 on the child is the fix
        # (found by actually running this, not by reading the traceback in
        # advance). Harmless for pip, which is UTF-8 clean either way.
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        self._proc = subprocess.Popen(
            [str(self._executable), *self._args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # No console is attached to a GUI process, so anything the
            # child reads from stdin would just hang. A closed stdin makes
            # that an immediate EOF instead.
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        threading.Thread(target=self._pump_output, daemon=True).start()

    def _pump_output(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            self.output.put(line.rstrip("\n"))

    def stop(self) -> None:
        """Kill the whole process tree. There is nothing graceful to try
        first -- iss has no shutdown path of its own (see #6)."""
        if self._proc is None or self._proc.poll() is not None:
            return
        if sys.platform == "win32":
            # /T takes the whole tree down, not just the parent -- the browser
            # frontend can spawn helpers, and killing only iss.exe would orphan
            # them.
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(self._proc.pid)],
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            self._proc.terminate()
