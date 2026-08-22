# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.3.0] - 2026-08-22

### Added

- **Standalone `ISSControl.exe`, built and released automatically on tag
  push** (#21). PyInstaller was picked over Nuitka/cx_Freeze for this app:
  mature, wide Tk compatibility, and a light Tk + keyring GUI is exactly
  where PyInstaller's faster/simpler build outweighs Nuitka's
  smaller/faster-starting binary. `ISSControl.spec` builds a onefile,
  windowed exe from `isscontrol.pyw` rather than the package's own
  `__main__.py` -- the former's absolute import and its existing
  try/except-then-messagebox startup-error handling both freeze cleanly,
  where the latter's relative import assumes a package context the frozen
  entry script doesn't have. Verified locally before wiring this into CI:
  the frozen build renders correctly, and -- the one real risk with
  PyInstaller + `keyring`, which discovers its backend via package
  metadata that freezing can break -- a set/get/delete round trip against
  Windows Credential Manager works in a frozen build with no extra
  hidden-import wiring needed.
  `.github/workflows/release.yml` runs the test suite, builds the exe, and
  attaches it to a GitHub Release for the pushed tag.

## [1.2.0] - 2026-08-22

### Added

- **Frontend setting: native window vs. browser tab** (#18). iss's own
  default frontend is the WebTransport "browser" bridge, and it never opens
  a tab itself -- confirmed against iShareScreen's own source
  (`frontend/wt/server.py`), it only logs a connect URL, so Start produced
  log output and nothing visible. ISSControl now defaults to iss's other
  frontend, `--frontend desktop` (native wgpu window(s), opened
  automatically), with Browser tab available in the Settings dialog for
  anyone who wants it -- in which case the main window shows a clickable
  link once iss actually logs the URL, since that frontend still gives no
  window of its own.
- **Connection defaults summary on the main window** (#19). Host, user,
  frontend, resolution, display scale, decoder, audio, and curtain were
  only visible by opening Settings. A "Connection defaults" card now shows
  all of it (never the password) below the install-status card, in the
  same wording the Settings dialog's own dropdowns use, and wraps to the
  card's actual width rather than clipping at the window edge.

### Fixed

- **Settings dialog changes reverted to defaults the next time the app
  launched** (#20), for every field except host/user, which is what made
  it easy to miss. `run()` discarded the `App(root, settings)` return
  value, and `_on_close()`'s closure kept the original `settings` dict from
  `load_settings()` -- `SettingsDialog._save()` writes the new values to
  disk immediately, but `App.open_settings()` reassigns `self._settings` to
  a *new* dict rather than mutating that original one in place, so the
  stale closure never saw what had actually changed. Every window close
  then re-saved that stale snapshot over whatever Settings had just
  written, silently reverting the session's changes. `_on_close()` now
  saves `app._settings` instead.

## [1.1.1] - 2026-08-22

### Fixed

- **Double-clicking `isscontrol.pyw` could silently do nothing** (#16).
  `keyring` becoming a real dependency in v1.1.0 exposed a gap the launcher
  already had: with no shebang, Windows runs it under whichever Python the
  `py` launcher defaults to, which is not necessarily the one ISSControl
  and its dependencies are actually installed into (the same kind of
  environment mismatch `iss_locate.py` works around for `iss` itself, just
  now on ISSControl's own side) -- and under pythonw there's no console for
  the resulting exception to print to, so it just vanished. The launcher
  now catches a failed startup and shows it in a message box instead,
  naming the interpreter it ran under so the fix (installing into that
  specific Python) is obvious.
- **Settings dialog's Resolution/Display scale/Decoder didn't actually
  match iShareScreen's web connect form** (#17), despite pre-filling that
  form being the whole point. Replaced the free-text fields with dropdowns
  sourced directly from the web form's own option lists, labels, and
  defaults (`isharescreen.gui.connect._FORM` / `_DECODER_LABELS`), and
  `iss_launch.build_args()` now reproduces that form's
  resolution-÷-scale-into-one---advertise-flag math instead of passing
  Resolution straight through -- the two aren't independent flags in
  practice. vt-hevc444 is left off the decoder list on purpose: it's
  Darwin-only decode hardware, and ISSControl only ever runs as the
  Windows-side viewer.
- **Settings dialog dropdowns were unreadable -- white text on white**
  (found while fixing #17). `theme.py` styled every other input widget but
  never `TCombobox`; clam's readonly state in particular renders from its
  *select* colors rather than `fieldbackground`/`foreground`, so a plain
  style pass would have left it looking fine closed and still broken once
  opened. Both the closed field and the popdown list (a plain Tk Listbox
  under a ttk combobox, styled through the option database like Text/Menu
  already were) now follow the rest of the dark theme.

## [1.1.0] - 2026-08-22

### Added

- **Settings dialog with connection defaults** (#14). Host, user,
  resolution, display scale, decoder, audio, and curtain now have a real
  editor (extending #11's settings.json), and `iss_launch.build_args()`
  turns them into the same CLI flags iss's own browser connect form
  pre-fills from -- `iss --host mac.local -u me --advertise 1920x1080
  --no-curtain` -- plus whatever's in `iss_args` as an escape hatch for
  anything not exposed by the dialog.
- **Password stored in Windows Credential Manager, not settings.json**
  (#15). Filed as "discuss the approach" rather than a locked-in design;
  keyring + Credential Manager is what got picked, matching what the issue
  itself suggested. `iss_credentials.py` keys the stored password by
  host/user pair; iss has no `--password` flag on purpose (its own --help
  text notes argv is visible in `ps` / Task Manager), so it only ever
  reaches iss over `--password-stdin`, piped through `ManagedProcess`'s new
  `stdin_data` parameter rather than ever touching argv or disk in
  plaintext.

## [1.0.0] - 2026-08-22

### Added

- **Settings persistence** (#11). Window position/size, and a
  settings.json-only `iss_path_override`/`iss_args` pair that extend the
  fallback chain from `find_iss()` (#4), round-trip through a per-user
  `settings.json` under `%LOCALAPPDATA%\ISSControl` -- following AddOnSync's
  convention for a pip-installed package rather than pwgen/AddOnTools' (a
  flat script's own directory isn't a sensible write target once installed
  to site-packages). Every field is validated on its own read, so a
  hand-edited or truncated file costs only the field it broke rather than
  stopping the window from opening. A saved position is clamped to the
  current screen bounds before being applied, since it may have been saved
  on a monitor that is no longer connected.
- **App icon and `.pyw` launcher** (#12). A window/taskbar icon (matching
  the sibling AddOnSync/AddOnTools/pwgen family's dark-badge-plus-bold-glyph
  style) and `isscontrol.pyw`, so the app can be double-clicked without a
  console window flashing up behind it -- the icon path `theme.py` already
  wired up in v0.1.0 just had no file behind it until now.
- **Real usage docs** (#13). A screenshot and an explanation of what
  Start/Stop/Update actually do, plus the PATH problem `find_iss()` works
  around, replacing the "docs land later" placeholder.

## [0.3.0] - 2026-08-22

### Added

- **Install-status card now does something** (#8, #9). `iss_install.py`
  reads the version and, more importantly, the installed commit SHA for
  whichever `iss` install `find_iss()` resolved -- pulled straight from the
  `direct_url.json` pip writes next to the dist-info of a `pip install
  git+...`, since the package's version string is static regardless of
  which commit is actually installed. `iss_update.py` compares that commit
  against upstream's current HEAD via `git ls-remote <url> HEAD`, chosen
  over the GitHub API because it resolves the default branch's symbolic ref
  for us and needs no auth/rate-limit handling -- and because git already
  has to be on PATH for the update action below to do its own clone. The
  check runs in a background thread on startup so a slow or unreachable
  GitHub can't stall the window from appearing.
- **One-click update** (#10). An Update button next to the install-status
  line runs `pip install --upgrade --force-reinstall git+<upstream>`
  against the *same* Python environment `iss` is actually installed in --
  not necessarily the one running ISSControl -- streaming its output into
  the log pane and re-checking install status once it finishes. The
  subprocess runner from #5/#6 (`iss_process.IssProcess`) generalized into
  `managed_process.ManagedProcess` to drive both `iss` and this pip
  invocation rather than duplicating the queue-fed-output/kill-tree
  plumbing a second time.

## [0.2.0] - 2026-08-22

### Added

- **Start and Stop actually control `iss`** (#5, #6). `iss_locate.find_iss()`
  resolves the launcher across the PATH gap discovered while scoping this
  project: pip installs its console scripts to whichever interpreter's
  Scripts directory was active at install time, which is usually not on
  PATH and often a different Python than whatever runs ISSControl.
  `iss_process.IssProcess` owns the subprocess lifecycle -- stdout/stderr
  stream through a queue the Tk loop drains without blocking, and Stop
  takes the whole process tree down with `taskkill /T /F` since iss has no
  shutdown path of its own to ask for nicely.
- **A watchdog notices iss exiting on its own** (#7), whether crashed or
  closed from its own window, and resets the status card and buttons
  instead of leaving the UI showing "Running" for a session that has
  already ended. An intentional Stop is reported distinctly from an
  unexpected exit, since a forced kill always reports a nonzero exit code
  and the two are not the same event.

### Fixed

- **`iss` crashed immediately whenever its output was piped rather than
  shown in a terminal.** Found by actually running it end-to-end rather
  than trusting the traceback would never come up: with stdout redirected,
  Python falls back to the Windows ANSI codepage, and iss's own startup
  banner prints a `→` character that codepage can't encode.
  `PYTHONIOENCODING=utf-8` on the child process fixes it.

## [0.1.0] - 2026-08-22

### Added

- Initial project scaffold: `pyproject.toml`, console-script entry point,
  and package layout.
- Dark theme ported from the sibling AddOnSync project (#2) -- palette,
  `clam`-theme repaint, dark title bar via DWM, DPI awareness, and an icon
  hook, so ISSControl reads as the same family of tool as AddOnSync,
  AddOnTools, and pwgen.
- The main window shell (#3): process-status card, install-status card
  (placeholder pending v0.3.0), Start/Stop buttons, and a log pane.
