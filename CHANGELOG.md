# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
