"""A dark theme for ttk, plus the Windows call that darkens the title bar.

ttk's built-in themes on Windows delegate to the native renderer, which ignores
most color settings -- a dark window ends up with light gray buttons and a
white entry field. The 'clam' theme is drawn by Tk itself, so it is the only one
that actually honors these colors, and everything below is built on it.

The title bar is not Tk's to draw at all. Without the DWM call the window keeps
a white caption bar above a dark client area, which looks broken.

Ported from the sibling AddOnSync project's theme.py so ISSControl matches the
rest of the Tharavol tools -- same palette, same DWM/DPI/icon handling.
"""

from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# Palette. Backgrounds step from the window up through raised surfaces, so
# panels read as layered without needing borders.
BG = "#1b1d21"
BG_RAISED = "#24272c"
BG_INPUT = "#15171a"
BG_HOVER = "#2f333a"
BG_ACTIVE = "#3a3f47"

FG = "#e4e6ea"
FG_MUTED = "#9aa0a8"
FG_DIM = "#6b7178"

ACCENT = "#4a8cff"
ACCENT_HOVER = "#5f9bff"
ACCENT_TEXT = "#ffffff"

BORDER = "#33373d"

OK = "#4cc38a"
WARN = "#e5a44b"
DANGER = "#f0616d"
INFO = "#6ba6ff"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI Semibold", 15)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO = ("Cascadia Mono", 9)

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19


def apply_dark_title_bar(window: tk.Misc) -> None:
    """Ask the desktop window manager to draw this window's caption dark.

    Supported from Windows 10 build 18985 onward; the attribute id changed
    during that period, so both are attempted. Failure is not worth reporting --
    the window merely keeps a light title bar.
    """
    if sys.platform != "win32":
        return
    try:
        # A full update, not just update_idletasks: the native frame does not
        # exist until Tk has handled the map event.
        #
        # wm_frame() is the only reliable way to reach the window that actually
        # draws the caption. winfo_id() returns the widget window, which for the
        # main window is a child of the frame -- but for a Toplevel is an
        # unrelated handle that GetParent and GetAncestor cannot navigate from,
        # which is why the dialogs kept a light title bar.
        toplevel = window.winfo_toplevel()
        toplevel.update()
        hwnd = int(toplevel.wm_frame(), 16)
        if not hwnd:
            return
        enabled = ctypes.c_int(1)
        for attribute in (
            _DWMWA_USE_IMMERSIVE_DARK_MODE,
            _DWMWA_USE_IMMERSIVE_DARK_MODE_OLD,
        ):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled)
            )
            if result == 0:
                _redraw_frame(hwnd)
                return
    except (OSError, AttributeError, ValueError, tk.TclError):
        pass  # a light title bar is not worth surfacing an error over


def _redraw_frame(hwnd: int) -> None:
    """Force the non-client area to repaint.

    The main window is styled before it is first painted, so it picks the dark
    caption up for free. Dialogs are already on screen by the time we get their
    handle, and DWM will not repaint the frame on its own -- without this they
    keep a light title bar above dark content.
    """
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_FRAMECHANGED = 0x0020
    ctypes.windll.user32.SetWindowPos(
        hwnd,
        0,
        0,
        0,
        0,
        0,
        SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
    )


ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.ico"


def apply_icon(root: tk.Tk) -> None:
    """Set the window and taskbar icon, and the default for its Toplevels."""
    if not ICON_PATH.exists():
        return
    try:
        root.iconbitmap(default=str(ICON_PATH))
    except tk.TclError:
        pass  # .ico support is Windows-only; nothing to fall back to elsewhere.


def enable_dpi_awareness() -> None:
    """Stop Windows bitmap-scaling the window into a blurry mess on high DPI."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (OSError, AttributeError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (OSError, AttributeError):
            pass


def apply(root: tk.Tk) -> ttk.Style:
    """Install the dark theme and return the configured style object."""
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(background=BG)
    # Classic Tk widgets (Text, Listbox, Menu) are not styled by ttk, so their
    # defaults are set through the option database instead.
    root.option_add("*Font", FONT)
    root.option_add("*Text.background", BG_INPUT)
    root.option_add("*Text.foreground", FG)
    root.option_add("*Text.insertBackground", FG)
    root.option_add("*Text.selectBackground", ACCENT)
    root.option_add("*Text.selectForeground", ACCENT_TEXT)
    root.option_add("*Menu.background", BG_RAISED)
    root.option_add("*Menu.foreground", FG)
    root.option_add("*Menu.activeBackground", ACCENT)
    root.option_add("*Menu.activeForeground", ACCENT_TEXT)
    # A Combobox's popdown list is a plain Tk Listbox too, so it needs the
    # same treatment -- without it, the dropdown itself stays light even
    # once the closed field below is styled to match everything else.
    root.option_add("*TCombobox*Listbox.background", BG_INPUT)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", ACCENT_TEXT)

    style.configure(".", background=BG, foreground=FG, font=FONT, borderwidth=0)

    # ---- Frames and labels --------------------------------------------------
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=BG_RAISED, relief="flat")
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Card.TLabel", background=BG_RAISED, foreground=FG)
    style.configure("Title.TLabel", background=BG, foreground=FG, font=FONT_TITLE)
    style.configure("Muted.TLabel", background=BG, foreground=FG_MUTED, font=FONT_SMALL)
    style.configure(
        "CardMuted.TLabel", background=BG_RAISED, foreground=FG_MUTED, font=FONT_SMALL
    )
    style.configure("CardHeading.TLabel", background=BG_RAISED, foreground=FG, font=FONT_BOLD)
    for name, color in (("Ok", OK), ("Warn", WARN), ("Danger", DANGER), ("Info", INFO)):
        style.configure(
            f"{name}.TLabel", background=BG_RAISED, foreground=color, font=FONT_BOLD
        )

    # ---- Buttons ------------------------------------------------------------
    style.configure(
        "TButton",
        background=BG_RAISED,
        foreground=FG,
        bordercolor=BORDER,
        borderwidth=1,
        focuscolor=BG_RAISED,
        relief="flat",
        padding=(14, 8),
    )
    style.map(
        "TButton",
        background=[("disabled", BG), ("pressed", BG_ACTIVE), ("active", BG_HOVER)],
        foreground=[("disabled", FG_DIM)],
        bordercolor=[("focus", ACCENT)],
    )

    style.configure(
        "Accent.TButton",
        background=ACCENT,
        foreground=ACCENT_TEXT,
        bordercolor=ACCENT,
        focuscolor=ACCENT,
        font=FONT_BOLD,
    )
    style.map(
        "Accent.TButton",
        background=[("disabled", "#2c3f63"), ("pressed", ACCENT), ("active", ACCENT_HOVER)],
        foreground=[("disabled", "#7f8894")],
    )

    style.configure(
        "Danger.TButton",
        background=DANGER,
        foreground=ACCENT_TEXT,
        bordercolor=DANGER,
        focuscolor=DANGER,
        font=FONT_BOLD,
    )
    style.map(
        "Danger.TButton",
        background=[("disabled", "#5c2c30"), ("pressed", DANGER), ("active", "#f37d87")],
        foreground=[("disabled", "#8a8f94")],
    )

    style.configure("Link.TButton", background=BG, borderwidth=0, padding=(6, 4))
    style.map("Link.TButton", background=[("active", BG_HOVER)])

    # ---- Inputs -------------------------------------------------------------
    style.configure(
        "TEntry",
        fieldbackground=BG_INPUT,
        foreground=FG,
        insertcolor=FG,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        padding=6,
    )
    style.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])

    style.configure(
        "TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_RAISED,
        foreground=FG,
        arrowcolor=FG_MUTED,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        borderwidth=1,
        padding=6,
    )
    style.map(
        "TCombobox",
        # clam renders a readonly Combobox's field using the *select*
        # colors, not fieldbackground/foreground -- without overriding
        # these too, a readonly box stays the theme's stock light blue
        # regardless of the colors set above.
        fieldbackground=[("readonly", BG_INPUT)],
        selectbackground=[("readonly", BG_INPUT)],
        selectforeground=[("readonly", FG)],
        foreground=[("disabled", FG_DIM)],
        bordercolor=[("focus", ACCENT)],
        lightcolor=[("focus", ACCENT)],
        arrowcolor=[("active", FG)],
    )

    # ---- Progress and separators -------------------------------------------
    style.configure(
        "TProgressbar",
        background=ACCENT,
        troughcolor=BG_INPUT,
        bordercolor=BG_INPUT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        borderwidth=0,
        thickness=6,
    )
    style.configure("TSeparator", background=BORDER)

    # ---- Scrollbars ---------------------------------------------------------
    style.configure(
        "Vertical.TScrollbar",
        background=BG_RAISED,
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=FG_MUTED,
        borderwidth=0,
        width=12,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("pressed", BG_ACTIVE), ("active", BG_HOVER)],
        arrowcolor=[("active", FG)],
    )

    return style


# Colors used for log lines, keyed by the levels the log pane emits.
LOG_COLORS = {
    "info": FG,
    "step": ACCENT,
    "warning": WARN,
    "error": DANGER,
    "success": OK,
    "muted": FG_MUTED,
}
