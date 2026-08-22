"""Settings dialog: connection defaults (#14) and the stored password (#15).

Modelled on the sibling AddOnSync project's SettingsDialog -- a modal
Toplevel that edits a copy of the settings and only writes anything back on
Save. The password field never round-trips through that dict, though: it's
read from and written straight to Windows Credential Manager via
iss_credentials, keyed by whatever host/user is showing at the time, and is
otherwise left blank on open so a stored password is never redisplayed in
plain text.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import iss_credentials, theme
from .settings import save_settings


class SettingsDialog(tk.Toplevel):
    """Modal editor for the connection defaults. Returns the new settings dict, or None."""

    def __init__(self, parent: tk.Misc, settings: dict) -> None:
        super().__init__(parent)
        self.result: dict | None = None
        self._settings = settings

        self.title("ISSControl Settings")
        self.configure(background=theme.BG)
        self.resizable(False, False)
        self.transient(parent)

        self._host = tk.StringVar(value=settings.get("host", ""))
        self._user = tk.StringVar(value=settings.get("user", ""))
        self._password = tk.StringVar(value="")
        self._advertise = tk.StringVar(value=settings.get("advertise", ""))
        self._hidpi = tk.StringVar(value=settings.get("hidpi", ""))
        self._decoder = tk.StringVar(value=settings.get("decoder", ""))
        self._audio = tk.BooleanVar(value=settings.get("audio", True))
        self._curtain = tk.BooleanVar(value=settings.get("curtain", True))

        self._build()
        theme.apply_dark_title_bar(self)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _event: self._cancel())
        self.grab_set()
        self._center_on(parent)

    # ---- Construction ---------------------------------------------------

    def _build(self) -> None:
        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(outer, text="Connection defaults", style="Title.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1
        ttk.Label(
            outer,
            text="Pre-fills iss's browser connect form on Start -- the password too,\n"
            "if one is stored below.",
            style="Muted.TLabel",
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 14))
        row += 1

        row = self._field_row(outer, row, "Host", self._host, "Mac hostname or IP")
        row = self._field_row(
            outer, row, "User", self._user, "macOS account", track_password=True
        )
        row = self._build_password_row(outer, row)
        row = self._field_row(
            outer, row, "Resolution", self._advertise, "e.g. 1920x1080 -- blank for auto"
        )
        row = self._field_row(
            outer,
            row,
            "Display scale",
            self._hidpi,
            "auto / on / off / a number -- blank for auto",
        )
        row = self._field_row(outer, row, "Decoder", self._decoder, "blank for auto")

        ttk.Checkbutton(outer, text="Audio", variable=self._audio).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        row += 1
        ttk.Checkbutton(
            outer,
            text="Curtain (blank the host's physical screen while sharing)",
            variable=self._curtain,
        ).grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        buttons = ttk.Frame(outer)
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self._save).pack(
            side="left"
        )

    def _field_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        hint: str,
        track_password: bool = False,
    ) -> int:
        ttk.Label(parent, text=label, style="TLabel").grid(
            row=row, column=0, sticky="w", pady=(8, 0)
        )
        entry = ttk.Entry(parent, textvariable=variable, width=32)
        entry.grid(row=row, column=1, sticky="ew", pady=(8, 0), padx=(10, 0))
        # Host and User are the only fields the stored password's status
        # line depends on -- retyping either should reflect what's actually
        # on file for the pair now showing, not the pair the dialog opened
        # with.
        if track_password:
            entry.bind("<KeyRelease>", lambda _event: self._refresh_password_status())
        row += 1
        ttk.Label(parent, text=hint, style="Muted.TLabel").grid(
            row=row, column=1, sticky="w", padx=(10, 0)
        )
        return row + 1

    def _build_password_row(self, parent: ttk.Frame, row: int) -> int:
        ttk.Label(parent, text="Password", style="TLabel").grid(
            row=row, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Entry(parent, textvariable=self._password, width=32, show="*").grid(
            row=row, column=1, sticky="ew", pady=(8, 0), padx=(10, 0)
        )
        row += 1

        self._password_status = ttk.Label(parent, text="", style="Muted.TLabel")
        self._password_status.grid(row=row, column=1, sticky="w", padx=(10, 0))
        row += 1

        ttk.Button(parent, text="Clear stored password", command=self._clear_password).grid(
            row=row, column=1, sticky="w", padx=(10, 0), pady=(4, 0)
        )
        row += 1

        self._refresh_password_status()
        return row

    # ---- Behavior ---------------------------------------------------------

    def _refresh_password_status(self) -> None:
        stored = iss_credentials.get_password(self._host.get().strip(), self._user.get().strip())
        text = (
            "A password is stored for this host/user. Leave the field blank to keep it."
            if stored
            else "No password stored. Leave the field blank to keep asking in the browser form."
        )
        self._password_status.configure(text=text)

    def _clear_password(self) -> None:
        iss_credentials.delete_password(self._host.get().strip(), self._user.get().strip())
        self._password.set("")
        self._refresh_password_status()

    def _save(self) -> None:
        host = self._host.get().strip()
        user = self._user.get().strip()
        password = self._password.get()
        if password:
            iss_credentials.set_password(host, user, password)

        self.result = {
            **self._settings,
            "host": host,
            "user": user,
            "advertise": self._advertise.get().strip(),
            "hidpi": self._hidpi.get().strip(),
            "decoder": self._decoder.get().strip(),
            "audio": self._audio.get(),
            "curtain": self._curtain.get(),
        }
        save_settings(self.result)
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def _center_on(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def edit_settings(parent: tk.Misc, settings: dict) -> dict | None:
    """Show the dialog and wait. Returns the new settings dict, or None if cancelled."""
    dialog = SettingsDialog(parent, settings)
    parent.wait_window(dialog)
    return dialog.result
