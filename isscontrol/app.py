"""The main window.

A process-status card, an install-status card, the Start/Stop pair, and a
log pane. Start/Stop drive a ManagedProcess (#5, #6); a recurring poll loop
drains its output into the log and notices when it exits on its own --
crashed, or closed from its own window -- so the UI never sits showing
"Running" for a session that has already ended (#7).

The install-status card runs an update check (#8, #9) in a background
thread on startup -- it shells out to git, which can stall or hang -- and
posts the result back through a queue the poll loop drains, since Tk is not
thread-safe to touch directly from a worker. The Update button (#10) drives
a second ManagedProcess running `pip install --upgrade`, polled the same
way as iss's own process.

Window position/size and the settings.json-only iss_path_override/iss_args
fields (#11) round-trip through `settings`: loaded in run() before the
window is placed, applied by App, and written back to disk when the window
closes.
"""

from __future__ import annotations

import queue
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from . import __version__, theme
from .iss_install import NotInstalledError
from .iss_locate import IssNotFoundError, find_iss
from .iss_update import UpdateState, UpdateStatus, UpstreamCheckError, check_for_update
from .iss_update import start_update as start_update_process
from .managed_process import ManagedProcess
from .settings import load_settings, save_settings

_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$")

# How often the poll loop drains iss's output and checks whether it's still
# running. Frequent enough that the log feels live, cheap enough to leave
# running for the lifetime of the window.
POLL_INTERVAL_MS = 400

# iss's own log formatter is "<timestamp> <LEVELNAME> <logger> | <message>"
# (see isharescreen.cli._setup_logging) -- matching it lets warnings/errors
# in its output stand out in the log pane instead of reading as plain text.
_LEVEL_RE = re.compile(r"^\S+\s+(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+\S+\s+\|")
_LEVEL_TAGS = {"WARNING": "warning", "ERROR": "error", "CRITICAL": "error"}


def _level_tag(line: str) -> str:
    match = _LEVEL_RE.match(line)
    return _LEVEL_TAGS.get(match.group(1), "info") if match else "info"


class App(ttk.Frame):
    def __init__(self, root: tk.Tk, settings: dict) -> None:
        super().__init__(root, padding=18)
        self.root = root
        self._settings = settings
        self.pack(fill="both", expand=True)

        self._iss: ManagedProcess | None = None
        self._was_running = False
        self._stopping = False

        self._update_proc: ManagedProcess | None = None
        self._update_results: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build()
        self._poll_process()
        self._check_for_update()

    # ---- Construction -------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._build_header()
        self._build_status_cards()
        self._build_actions()
        self._build_log()

    def _build_header(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="ISSControl", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header, text="Start/stop control for iShareScreen", style="Muted.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _build_status_cards(self) -> None:
        panel = ttk.Frame(self)
        panel.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        panel.columnconfigure(0, weight=1)

        process_card = ttk.Frame(panel, style="Card.TFrame", padding=12)
        process_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        process_card.columnconfigure(0, weight=1)
        ttk.Label(process_card, text="iss process", style="CardHeading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._process_status = ttk.Label(
            process_card, text="Not running", style="CardMuted.TLabel"
        )
        self._process_status.grid(row=1, column=0, sticky="w", pady=(4, 0))

        install_card = ttk.Frame(panel, style="Card.TFrame", padding=12)
        install_card.grid(row=1, column=0, sticky="ew")
        install_card.columnconfigure(0, weight=1)
        ttk.Label(install_card, text="iShareScreen install", style="CardHeading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self._install_status = ttk.Label(
            install_card, text="Checking...", style="CardMuted.TLabel"
        )
        self._install_status.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self._update_button = ttk.Button(
            install_card,
            text="Update",
            command=self.update_iss,
            state="disabled",
        )
        self._update_button.grid(row=1, column=1, sticky="e")

    def _build_actions(self) -> None:
        actions = ttk.Frame(self)
        actions.grid(row=2, column=0, sticky="ew", pady=(16, 0))

        self._start_button = ttk.Button(
            actions, text="Start", style="Accent.TButton", command=self.start_iss
        )
        self._start_button.pack(side="left")

        self._stop_button = ttk.Button(
            actions,
            text="Stop",
            style="Danger.TButton",
            command=self.stop_iss,
            state="disabled",
        )
        self._stop_button.pack(side="left", padx=(8, 0))

    def _build_log(self) -> None:
        holder = ttk.Frame(self)
        holder.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)

        self._log = tk.Text(
            holder,
            height=12,
            wrap="word",
            background=theme.BG_INPUT,
            foreground=theme.FG,
            insertbackground=theme.FG,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=theme.BORDER,
            highlightcolor=theme.BORDER,
            font=theme.FONT_MONO,
            padx=10,
            pady=8,
            state="disabled",
        )
        self._log.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=self._log.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._log.configure(yscrollcommand=scrollbar.set)

        for level, color in theme.LOG_COLORS.items():
            self._log.tag_configure(level, foreground=color)

        self._append_log("muted", "Ready.")

    # ---- Process control --------------------------------------------------

    def _find_iss(self) -> Path:
        return find_iss(override=self._settings.get("iss_path_override") or None)

    def start_iss(self) -> None:
        if self._iss is not None and self._iss.is_running():
            return
        try:
            iss_path = self._find_iss()
        except IssNotFoundError as error:
            self._append_log("error", str(error))
            messagebox.showerror("Can't find iss", str(error), parent=self.root)
            return

        self._append_log("step", f"Starting {iss_path}")
        self._iss = ManagedProcess(iss_path, list(self._settings.get("iss_args", [])))
        self._iss.start()
        self._was_running = True
        self._set_running_state(True, pid=self._iss.pid)

    def stop_iss(self) -> None:
        if self._iss is None or not self._iss.is_running():
            return
        self._append_log("step", "Stopping iss...")
        self._stopping = True
        self._iss.stop()
        # The button/status state resets once the poll loop below observes
        # the process has actually exited, not here -- taskkill asks it to
        # die, it doesn't confirm it has.

    # ---- Update ------------------------------------------------------------

    def update_iss(self) -> None:
        if self._update_proc is not None and self._update_proc.is_running():
            return
        try:
            iss_path = self._find_iss()
            self._update_proc = start_update_process(iss_path)
        except (IssNotFoundError, NotInstalledError) as error:
            self._append_log("error", str(error))
            return
        self._append_log("step", "Updating iShareScreen...")
        self._update_button.configure(state="disabled")

    def _check_for_update(self) -> None:
        self._install_status.configure(text="Checking for updates...", style="CardMuted.TLabel")
        threading.Thread(target=self._check_for_update_worker, daemon=True).start()

    def _check_for_update_worker(self) -> None:
        try:
            iss_path = self._find_iss()
            status = check_for_update(iss_path)
        except (IssNotFoundError, NotInstalledError, UpstreamCheckError) as error:
            self._update_results.put(("error", str(error)))
            return
        self._update_results.put(("status", status))

    def _apply_update_status(self, status: UpdateStatus) -> None:
        short = status.installed.commit[:7] if status.installed.commit else None
        if status.state is UpdateState.UP_TO_DATE:
            self._install_status.configure(text=f"Up to date ({short})", style="Ok.TLabel")
            self._update_button.configure(state="disabled")
        elif status.state is UpdateState.UPDATE_AVAILABLE:
            self._install_status.configure(
                text=f"Update available (installed {short})", style="Warn.TLabel"
            )
            self._update_button.configure(state="normal")
        else:  # UNVERSIONED
            self._install_status.configure(
                text=f"Installed v{status.installed.version} (not a tracked git checkout)",
                style="CardMuted.TLabel",
            )
            self._update_button.configure(state="disabled")

    def _poll_process(self) -> None:
        if self._iss is not None:
            self._drain_output(self._iss)
            running = self._iss.is_running()
            if self._was_running and not running:
                if self._stopping:
                    # A forced kill always reports a nonzero exit code, so
                    # that alone can't distinguish "we stopped it" (expected)
                    # from "it died" (worth a warning) -- the flag does.
                    self._append_log("success", "iss stopped.")
                else:
                    code = self._iss.exit_code()
                    self._append_log(
                        "info" if not code else "warning",
                        f"iss exited on its own (code {code})." if code else "iss exited.",
                    )
                self._stopping = False
                self._set_running_state(False)
            self._was_running = running

        if self._update_proc is not None:
            self._drain_output(self._update_proc)
            if not self._update_proc.is_running():
                code = self._update_proc.exit_code()
                if code == 0:
                    self._append_log("success", "Update complete.")
                else:
                    self._append_log("error", f"Update failed (exit code {code}).")
                self._update_proc = None
                self._check_for_update()

        self._drain_update_results()
        self.after(POLL_INTERVAL_MS, self._poll_process)

    def _drain_update_results(self) -> None:
        while True:
            try:
                kind, payload = self._update_results.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self._apply_update_status(payload)
            else:
                self._install_status.configure(text=payload, style="Warn.TLabel")
                self._update_button.configure(state="disabled")

    def _drain_output(self, proc: ManagedProcess) -> None:
        while True:
            try:
                line = proc.output.get_nowait()
            except queue.Empty:
                break
            self._append_log(_level_tag(line), line)

    def _set_running_state(self, running: bool, pid: int | None = None) -> None:
        if running:
            self._process_status.configure(text=f"Running (PID {pid})", style="Ok.TLabel")
            self._start_button.configure(state="disabled")
            self._stop_button.configure(state="normal")
        else:
            self._process_status.configure(text="Not running", style="CardMuted.TLabel")
            self._start_button.configure(state="normal")
            self._stop_button.configure(state="disabled")

    # ---- Log ------------------------------------------------------------------

    def _append_log(self, level: str, message: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", message + "\n", level)
        self._log.see("end")
        self._log.configure(state="disabled")


def _initial_geometry(root: tk.Tk, settings: dict) -> str:
    """A Tk geometry string for *settings*, clamped to the current screen.

    The saved x/y can point at a monitor that is no longer connected (a
    laptop undocked since the last session, say) -- clamping rather than
    trusting it outright means the window still opens somewhere reachable
    instead of off the visible desktop.
    """
    width = min(settings["window_width"], root.winfo_screenwidth())
    height = min(settings["window_height"], root.winfo_screenheight())
    x, y = settings["window_x"], settings["window_y"]
    if x is None or y is None:
        return f"{width}x{height}"
    x = max(0, min(x, root.winfo_screenwidth() - 100))
    y = max(0, min(y, root.winfo_screenheight() - 100))
    return f"{width}x{height}+{x}+{y}"


def _save_window_geometry(root: tk.Tk, settings: dict) -> None:
    match = _GEOMETRY_RE.match(root.geometry())
    if not match:
        return
    width, height, x, y = match.groups()
    settings["window_width"] = int(width)
    settings["window_height"] = int(height)
    settings["window_x"] = int(x)
    settings["window_y"] = int(y)


def run() -> int:
    """Create the window and run until it closes."""
    theme.enable_dpi_awareness()

    settings = load_settings()

    root = tk.Tk()
    root.title(f"ISSControl {__version__}")
    root.geometry(_initial_geometry(root, settings))
    root.minsize(520, 440)
    theme.apply(root)
    theme.apply_dark_title_bar(root)
    theme.apply_icon(root)

    App(root, settings)

    def _on_close() -> None:
        _save_window_geometry(root, settings)
        save_settings(settings)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()
    return 0
