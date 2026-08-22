"""The main window.

A process-status card, an install-status card, the Start/Stop pair, and a
log pane. Start/Stop drive an IssProcess (#5, #6); a recurring poll loop
drains its output into the log and notices when it exits on its own --
crashed, or closed from its own window -- so the UI never sits showing
"Running" for a session that has already ended (#7).
"""

from __future__ import annotations

import queue
import re
import tkinter as tk
from tkinter import messagebox, ttk

from . import __version__, theme
from .iss_locate import IssNotFoundError, find_iss
from .iss_process import IssProcess

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
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=18)
        self.root = root
        self.pack(fill="both", expand=True)

        self._iss: IssProcess | None = None
        self._was_running = False
        self._stopping = False

        self._build()
        self._poll_process()

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
        # Real version/commit comparison against upstream lands in v0.3.0 (#8-#10).
        self._install_status = ttk.Label(
            install_card, text="Update status not implemented yet", style="CardMuted.TLabel"
        )
        self._install_status.grid(row=1, column=0, sticky="w", pady=(4, 0))

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

    def start_iss(self) -> None:
        if self._iss is not None and self._iss.is_running():
            return
        try:
            iss_path = find_iss()
        except IssNotFoundError as error:
            self._append_log("error", str(error))
            messagebox.showerror("Can't find iss", str(error), parent=self.root)
            return

        self._append_log("step", f"Starting {iss_path}")
        self._iss = IssProcess(iss_path)
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

    def _poll_process(self) -> None:
        if self._iss is not None:
            self._drain_output()
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
        self.after(POLL_INTERVAL_MS, self._poll_process)

    def _drain_output(self) -> None:
        assert self._iss is not None
        while True:
            try:
                line = self._iss.output.get_nowait()
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


def run() -> int:
    """Create the window and run until it closes."""
    theme.enable_dpi_awareness()

    root = tk.Tk()
    root.title(f"ISSControl {__version__}")
    root.geometry("640x560")
    root.minsize(520, 440)
    theme.apply(root)
    theme.apply_dark_title_bar(root)
    theme.apply_icon(root)

    App(root)
    root.mainloop()
    return 0
