# CANAL+ Decoder for Home Assistant

Custom Home Assistant integration for compatible CANAL+ / nc+ satellite decoders exposing the local HTTP remote-control API.

The integration keeps the internal Home Assistant domain `dsiw74` for backward compatibility with existing installations and entity IDs, but the visible integration name is now **CANAL+ Decoder** / **Dekoder CANAL+**.

## Confirmed decoder models

- Sagemcom **DSIW74** (wifiBOX+) — API port `3030`
- ADB **NCP3670SF / NCP-3670SF** (4K UltraBOX+) — API port `8080`
- ADB **NCP4740SF / NCP-4740SF** (WiFi PremiumBOX+) — API port `8080`
- Technicolor **USW4001NCP** (4K UltraBOX+) — compatible model accepted by the integration

The decoder is verified using `GET /system/version`. The `Serial` HTTP header is used as the unique identifier.

## Features

- Local decoder control using `POST /control/rcu`.
- `remote` entity with native `Key...` commands and friendly aliases.
- Individual remote-control buttons.
- Editable numeric channel presets.
- Preset `select` entity.
- Automatic channel synchronization from a selected Home Assistant `media_player`.
- Real ON/standby state from a configured HDMI encoder (`/get_status`, `vi id=0`, `video_ok`).
- Safe `remote.turn_on` / `remote.turn_off`: the standby toggle is sent only when the HDMI-derived state requires it.
- Polish and English UI translations.

## Installation with HACS

1. Open **HACS**.
2. Add custom repository: `https://github.com/unky23/ha-dsiw74` as **Integration**.
3. Install **CANAL+ Decoder**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → CANAL+ Decoder**.

## Manual installation

Copy `custom_components/dsiw74` to `/config/custom_components/dsiw74` and restart Home Assistant.

## Configuration

The integration asks for:

- decoder IP address,
- decoder HTTP API port,
- device name,
- HDMI encoder URL and optional credentials,
- optional `media_player` to follow,
- automatic channel synchronization,
- editable channel presets.

Typical ports are:

```text
wifiBOX+ DSIW74      3030
4K UltraBOX+         8080
WiFi PremiumBOX+     8080
```

## Default channel presets

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

Presets are fully editable. Multi-digit channel numbers are sent as consecutive remote-control digit presses.

## Automatic channel synchronization

When a media player is selected, the integration checks `media_channel`, then `media_title`, then `source`. If the value matches a preset name (case-insensitive), the corresponding numeric channel is sent to the decoder. Duplicate unrelated media-player updates do not repeatedly retune the same preset.

## Automation examples

Select a channel preset:

```yaml
action: select.select_option
target:
  entity_id: select.dsiw74_preset_kanalu
data:
  option: "CANAL+ Sport 1"
```

Send a remote key:

```yaml
action: remote.send_command
target:
  entity_id: remote.dsiw74_pilot
data:
  command: KeyMenu
```

Friendly aliases such as `menu`, `guide`, `ch+`, `ch-`, `1`, `2`, and `power` are also supported.

## Power-state detection

The CANAL+ decoder network API does not expose a reliable ON/standby state on the confirmed models. The integration therefore optionally polls the configured HDMI encoder and uses `video_ok` from input `vi id=0` as the real power-state source.

Without a working HDMI encoder state, `remote.turn_on` and `remote.turn_off` cannot safely distinguish ON from standby. The raw standby toggle remains available through `remote.toggle` / `KeyStandBy`.

## Local API

Device information:

```text
GET http://DECODER_IP:PORT/system/version
```

Remote key:

```text
POST http://DECODER_IP:PORT/control/rcu
Content-Type: application/x-www-form-urlencoded

Keypress=KeyMenu
```

## Backward compatibility

The integration folder, domain, Python class names and existing entity unique IDs remain based on `dsiw74`. This is intentional so upgrading from older versions does not create a second integration or break existing automations.

## License

MIT
