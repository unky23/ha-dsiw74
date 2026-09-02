# Sagemcom DSIW74 for Home Assistant

Custom Home Assistant integration for the CANAL+ / nc+ **Sagemcom DSIW74 (wifiBOX+)** local network remote API.

The integration communicates locally with the decoder over HTTP, creates a Home Assistant remote, individual remote-control buttons, configurable channel presets and can automatically keep the DSIW74 channel synchronized with another `media_player` entity.

## Features

- UI configuration through **Settings → Devices & services**.
- Local decoder API: `GET /system/version` and `POST /control/rcu`.
- Default DSIW74 API port: `3030`.
- `remote` entity supporting native `Key...` commands and friendly aliases.
- Individual Home Assistant buttons for the full remote control.
- Editable numeric channel presets.
- Preset `select` entity for automations.
- Automatic channel synchronization from a chosen `media_player`.
- HDMI encoder URL, username and password stored for planned HDMI-frame based ON/STANDBY detection.
- Polish and English UI translations.

## Installation with HACS

1. Open **HACS**.
2. Open the menu in the upper-right corner and choose **Custom repositories**.
3. Add:

   `https://github.com/unky23/ha-dsiw74`

4. Select category **Integration**.
5. Install **Sagemcom DSIW74**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration → Sagemcom DSIW74**.

## Manual installation

Copy:

`custom_components/dsiw74`

to:

`/config/custom_components/dsiw74`

and restart Home Assistant.

## Initial configuration

The integration asks for:

- DSIW74 IP address,
- DSIW74 HTTP port (default `3030`),
- device name,
- HDMI encoder URL,
- encoder username and password,
- optional `media_player` to follow,
- automatic channel synchronization toggle,
- editable channel presets.

The decoder is verified using `/system/version` and its `Serial` HTTP header is used as the unique identifier.

## Channel presets

Presets are edited under **Configure** using one line per channel:

```text
1 = CANAL+ Sport 1
2 = CANAL+ Sport 2
3 = CANAL+ Sport 3
4 = CANAL+ Sport 4
5 = CANAL+ Sport 5
6 = CANAL+ Sport 6
7 = CANAL+ 360
8 = CANAL+ Extra 1
9 = CANAL+ Extra 2
10 = CANAL+ Extra 3
11 = CANAL+ Extra 4
```

The names and numbers are fully editable. Multi-digit numbers are sent as consecutive remote-control digit presses.

## Automatic channel synchronization

Choose a **media player to follow** and enable automatic synchronization. When the media player changes state, the integration checks, in order:

1. `media_channel`
2. `media_title`
3. `source`

If the value matches a configured preset name (case-insensitive), the numeric preset is sent to the DSIW74.

Example:

```text
media_player channel: CANAL+ Extra 4
preset:               CANAL+ Extra 4 = 11
DSIW74 keys:           KeyOne → KeyOne
```

Unrelated media-player state updates do not cause repeated retunes when the matched channel has not changed.

## Automation example

A preset can also be selected directly:

```yaml
action: select.select_option
target:
  entity_id: select.dsiw74_preset_kanalu
data:
  option: "CANAL+ Sport 1"
```

Native remote commands can be sent through the `remote` entity:

```yaml
action: remote.send_command
target:
  entity_id: remote.dsiw74_pilot
data:
  command: KeyMenu
```

Friendly aliases such as `menu`, `guide`, `ch+`, `ch-`, `1`, `2`, `power` are also supported.

## Known limitations

- The DSIW74 network API does **not** expose a reliable ON/STANDBY state.
- `/system/version`, TCP port 3030 and the nc+ SSDP service remain available while the decoder is in standby.
- Therefore the power button currently behaves like the physical remote: it sends `KeyStandBy` as a toggle.
- HDMI encoder credentials are already configurable, but HDMI-frame based power-state detection is not implemented yet.
- The current channel displayed by the preset `select` represents the last channel sent by this integration, not a channel read back from the decoder.

## DSIW74 local API

Device information:

```text
GET http://DECODER_IP:3030/system/version
```

Remote key:

```text
POST http://DECODER_IP:3030/control/rcu
Content-Type: application/x-www-form-urlencoded

Keypress=KeyMenu
```

## License

MIT
