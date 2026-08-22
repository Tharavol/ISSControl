"""Settings dialog: connection defaults (#14) and the stored password (#15).

Modelled on the sibling AddOnSync project's SettingsDialog -- a modal
Toplevel that edits a copy of the settings and only writes anything back on
Save. The password field never round-trips through that dict, though: it's
read from and written straight to Windows Credential Manager via
iss_credentials, keyed by whatever host/user is showing at the time, and is
otherwise left blank on open so a stored password is never redisplayed in
plain text.

Resolution, Display scale, and Decoder are dropdowns rather than free text,
with the same options, labels, and defaults as isharescreen's own web
connect form (isharescreen.gui.connect._FORM) -- pulled from that form's
HTML/_DECODER_LABELS directly, not reinvented, so a value here means the
same thing it would mean typed into that form. vt-hevc444 (VideoToolbox) is
missing on purpose: it's Darwin-only decode hardware, and ISSControl only
ever runs as the Windows-side viewer.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import iss_credentials, theme
from .settings import save_settings

# (display label, underlying value) -- same order and wording as the web
# form's own <option> list.
RESOLUTION_OPTIONS = [
    ("Auto — track window size", "auto"),
    ("3840 x 2160 (4K UHD)", "3840x2160"),
    ("3440 x 1440 (UWQHD)", "3440x1440"),
    ("2560 x 1600 (WQXGA)", "2560x1600"),
    ("2560 x 1440 (QHD)", "2560x1440"),
    ("1920 x 1200 (WUXGA)", "1920x1200"),
    ("1920 x 1080 (FHD)", "1920x1080"),
    ("1680 x 1050 (WSXGA+)", "1680x1050"),
    ("1600 x 900 (HD+)", "1600x900"),
    ("1366 x 768 (WXGA)", "1366x768"),
    ("1280 x 720 (HD)", "1280x720"),
    ("1024 x 768 (XGA)", "1024x768"),
    ("800 x 600 (SVGA)", "800x600"),
]

SCALE_OPTIONS = [
    ("100% — smallest UI, most desktop space", "1.0"),
    ("150%", "1.5"),
    ("200% — Retina (normal UI, crisp)", "2.0"),
    ("250%", "2.5"),
    ("300% — large UI", "3.0"),
    ("350%", "3.5"),
    ("400% — largest UI", "4.0"),
]

# The web form filters this list to decoders actually available on the
# connecting machine; ISSControl doesn't probe iss's internal decoder
# registry to do the same (that's private API, not a CLI/settings surface),
# so this is the static Windows-relevant subset -- everything except
# vt-hevc444, which supported_here() never offers off Darwin anyway.
DECODER_OPTIONS = [
    ("Auto (best available)", "auto"),
    ("HEVC — Generic GPU (d3d11va / vaapi / cuda)", "libav-hevc444"),
    ("HEVC — Intel Quick Sync", "qsv-hevc444"),
    ("HEVC — Software (CPU)", "libav-hevc444-sw"),
    ("H.264", "libav-avc420"),
]


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
        self._advertise = tk.StringVar(value=settings.get("advertise", "auto"))
        self._hidpi = tk.StringVar(value=settings.get("hidpi", "2.0"))
        self._decoder = tk.StringVar(value=settings.get("decoder", "auto"))
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
        row = self._combo_row(
            outer,
            row,
            "Resolution",
            self._advertise,
            RESOLUTION_OPTIONS,
            "The encoded pixel size = bandwidth. Display scale below sets\n"
            "how large the UI is drawn -- independently of this.",
        )
        row = self._combo_row(
            outer,
            row,
            "Display scale",
            self._hidpi,
            SCALE_OPTIONS,
            "How large the host's UI is drawn, like Windows display scaling.\n"
            "Higher = bigger text/UI. Does not change Resolution's bandwidth.",
        )
        row = self._combo_row(
            outer,
            row,
            "Decoder",
            self._decoder,
            DECODER_OPTIONS,
            "Auto picks the best decoder for the negotiated codec. The rest\n"
            "pin a specific path for debugging -- iss falls back to Auto's\n"
            "choice if the one you pick isn't actually available here.",
        )

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
        ttk.Label(parent, text=hint, style="Muted.TLabel", justify="left").grid(
            row=row, column=1, sticky="w", padx=(10, 0)
        )
        return row + 1

    def _combo_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        options: list[tuple[str, str]],
        hint: str,
    ) -> int:
        """A readonly Combobox whose displayed labels differ from the value
        *variable* actually holds -- Tk has no native (label, value) pair
        widget, so a display-only StringVar is kept in sync with it by hand.
        """
        ttk.Label(parent, text=label, style="TLabel").grid(
            row=row, column=0, sticky="w", pady=(8, 0)
        )

        value_by_label = dict(options)
        label_by_value = {value: display for display, value in options}

        display_var = tk.StringVar(value=label_by_value.get(variable.get(), options[0][0]))
        combo = ttk.Combobox(
            parent,
            textvariable=display_var,
            values=[display for display, _value in options],
            state="readonly",
            width=30,
        )
        combo.grid(row=row, column=1, sticky="ew", pady=(8, 0), padx=(10, 0))

        def _sync(*_args: object) -> None:
            variable.set(value_by_label.get(display_var.get(), variable.get()))

        display_var.trace_add("write", _sync)

        row += 1
        ttk.Label(parent, text=hint, style="Muted.TLabel", justify="left").grid(
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
            "advertise": self._advertise.get(),
            "hidpi": self._hidpi.get(),
            "decoder": self._decoder.get(),
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
