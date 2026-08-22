# ISSControl

A start/stop control panel for [iShareScreen](https://github.com/renegadelink/iShareScreen),
with status on whether your local install is behind upstream.

`iss` has no PATH-friendly launcher and no documented way to stop a running
session short of killing it. ISSControl manages it as a subprocess instead of
requiring a terminal: Start, Stop, and a status line for whether your install
is behind the upstream repo.

## Status

Early development — see the [issue tracker](https://github.com/Tharavol/ISSControl/issues)
and [milestones](https://github.com/Tharavol/ISSControl/milestones) for what's
built and what's planned. Full usage docs land with the v1.0.0 milestone.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

iShareScreen itself is AGPL-3.0-or-later; ISSControl only launches it as a
subprocess and does not link against its code.
