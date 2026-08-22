# ISSControl

A start/stop control panel for [iShareScreen](https://github.com/renegadelink/iShareScreen),
with status on whether your local install is behind upstream.

`iss` has no PATH-friendly launcher and no documented way to stop a running
session short of killing it. ISSControl manages it as a subprocess instead of
requiring a terminal: Start, Stop, and a status line for whether your install
is behind the upstream repo.

![ISSControl main window](docs/screenshot.png)

## The PATH problem this works around

`pip install`ing iShareScreen drops its `iss` console script into whichever
Python's `Scripts` directory was active at install time -- a venv, or (very
often on Windows) the per-user install under `%APPDATA%\Python\PythonXY`.
Neither is reliably on PATH, so a plain `iss` typed at a shell often does
nothing. ISSControl resolves the launcher itself: the interpreter it's
running under, PATH, then the well-known per-user install locations pip
uses -- so Start works whether or not `iss` itself is reachable from a
terminal. If none of that finds it, set the `ISSCONTROL_ISS_PATH`
environment variable to the full path, or add it as `iss_path_override` in
`settings.json` (see below).

## Using it

- **Start** launches `iss` as a managed subprocess and streams its output
  into the log pane below. **Stop** takes down the whole process tree --
  `iss` has no shutdown path of its own to ask for nicely, so this is the
  only way to end a session short of closing its browser tab and hoping. If
  `iss` crashes or is closed some other way, the status card notices on its
  own and resets the buttons rather than sitting on "Running" forever.
- The **iShareScreen install** card checks, in the background on startup,
  whether your installed commit matches upstream's current HEAD (`git
  ls-remote`, since that resolves the default branch for you without
  needing an API key). If you're behind, **Update** runs `pip install
  --upgrade --force-reinstall` against the same Python environment `iss` is
  actually installed in -- not necessarily the one running ISSControl --
  and streams that into the log pane too.
- Window position/size persist between sessions in a per-user
  `settings.json` (`%LOCALAPPDATA%\ISSControl` on Windows). There's no
  settings dialog yet ([#14](https://github.com/Tharavol/ISSControl/issues/14)
  covers that), but `iss_path_override` and `iss_args` in that file are
  already read and applied if you want to hand-edit them in the meantime.

## Running it

```sh
pip install -e .
isscontrol
# or: python -m isscontrol
```

On Windows, double-clicking `isscontrol.pyw` runs the same app without a
console window flashing up behind it.

## Status

- **Working**: Start/Stop/Update as a managed subprocess, install-vs-upstream
  status, settings persistence, and a console-free launcher. See
  [CHANGELOG.md](CHANGELOG.md) for what shipped in each version.
- **Not yet built**: default connection parameters and secure password
  storage (v1.1.0).

See the [issue tracker](https://github.com/Tharavol/ISSControl/issues) and
[milestones](https://github.com/Tharavol/ISSControl/milestones) for details.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

iShareScreen itself is AGPL-3.0-or-later; ISSControl only launches it as a
subprocess and does not link against its code.
