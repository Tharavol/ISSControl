# ISSControl

A start/stop control panel for [iShareScreen](https://github.com/renegadelink/iShareScreen),
with status on whether your local install is behind upstream.

`iss` has no PATH-friendly launcher and no documented way to stop a running
session short of killing it. ISSControl manages it as a subprocess instead of
requiring a terminal: Start, Stop, and a status line for whether your install
is behind the upstream repo.

## Status

- **Working**: Start/Stop launch and cleanly terminate `iss` as a managed
  subprocess, resolving its launcher even when it isn't on PATH. The
  install-status card shows whether your local `iss` install is behind
  upstream (by comparing its installed commit against upstream's current
  HEAD) with a one-click Update button. See [CHANGELOG.md](CHANGELOG.md)
  for what shipped in each version.
- **Not yet built**: settings persistence and packaging (v1.0.0), default
  connection parameters and secure password storage (v1.1.0).

See the [issue tracker](https://github.com/Tharavol/ISSControl/issues) and
[milestones](https://github.com/Tharavol/ISSControl/milestones) for details.
Full usage docs (with a screenshot) land with the v1.0.0 milestone.

## Running it

```sh
pip install -e .
isscontrol
# or: python -m isscontrol
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

iShareScreen itself is AGPL-3.0-or-later; ISSControl only launches it as a
subprocess and does not link against its code.
