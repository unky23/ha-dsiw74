# Changelog

## 0.6.1

- Fix remote entity setup after adding HDMI encoder power-state polling.
- Use the shared runtime object correctly when reading encoder state.

## 0.6.0

- Added real ON/standby detection through the configured HDMI encoder `/get_status` endpoint.
- Added HTTP Digest authentication support for the encoder.
- `remote.turn_on` and `remote.turn_off` are now idempotent: `KeyStandBy` is sent only when the HDMI-derived state shows it is required.
- The raw `remote.toggle` behavior remains available.
- Added remote diagnostic attributes for encoder availability and HDMI input frame rate.

## 0.5.1

- Replace the integration icon with the C+ logo.

## 0.5.0

- Add automatic DSIW74 channel synchronization from a selected Home Assistant `media_player`.
- Match `media_channel`, `media_title`, or `source` against configurable preset names.
- Avoid duplicate retunes when unrelated media player attributes change.
- Serialize rapid preset changes so digits from different channel numbers cannot interleave.
- Keep the preset `select` entity synchronized with automatic and manual preset changes.

## 0.4.0

- Make channel presets editable from the integration options.
- Support arbitrary numeric channel numbers and preset names.

## 0.3.0

- Add channel preset buttons and a channel preset `select` entity.
- Support multi-digit channel numbers.

## 0.2.0

- Add HDMI encoder URL, username and password settings for planned HDMI signal based power-state detection.

## 0.1.0

- Initial release.
- Local DSIW74 HTTP API support on port 3030.
- Remote entity and individual remote-control buttons.
