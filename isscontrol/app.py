"""The main window.

Layout only for now: a process-status card, an install-status card, the
Start/Stop pair, and a log pane. Nothing here talks to `iss` yet -- that
starts with the executable lookup (#4) and the Start/Stop wiring (#5, #6).
Both buttons are wired to placeholder handlers that just log a line, so the
window is runnable and the wiring point for the real logic is obvious.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import __version__, theme


class App(ttk.Frame):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=18)
        self.root = root
        self.pack(fill="both", expand=True)

        self._build()

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

        self._append_log("muted", "Ready. Start/Stop aren't wired up yet (see issue #5, #6).")

    # ---- Placeholder actions --------------------------------------------------
    # Replaced by real subprocess management in v0.2.0 (#5, #6).

    def start_iss(self) -> None:
        self._append_log("warning", "Start isn't implemented yet -- see issue #5.")

    def stop_iss(self) -> None:
        self._append_log("warning", "Stop isn't implemented yet -- see issue #6.")

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
