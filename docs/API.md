# ESP Spa module API (version 1)

This is the contract between the ESP Spa module (ESP8266 firmware) and this integration. The module serves
plain HTTP on port 80 on the local network and announces itself over mDNS as `spa.local`
(`_http._tcp`, instance name `spa`).

`GET /api/status` returns `"api": 1`. The module raises that number when the API changes in a way clients
must know about. The integration expects version **1**; on any other value (or none) it raises a repair
issue in Home Assistant and keeps working as far as it can.

## Rules

- Every `POST` needs the header `X-Spa-Client` (any value; the integration sends `home-assistant`).
  Without it the module answers `403`.
- Calls marked 🔒 also need either the settings password as HTTP basic auth (any user name) or the token
  from `POST /api/token`: `Authorization: Bearer <token>`. Wrong or missing: `401`.
- Arguments go in the query string. Answers are JSON with `"ok": true` or `"ok": false, "error": "..."`.
- A command the module cannot queue because it is not talking to the spa yet answers `503`
  (`"error": "Not connected to the spa yet"`).
- Commands are queued and reach the spa within about a second. `GET /api/status` shows the result once
  the spa reports it.

## Status

`GET /api/status` (no auth). Example:

```json
{
  "api": 1,
  "name": "My spa", "tagline": "Control panel",
  "age": 180,
  "unit": "C", "temp": 37.5, "set": 38.0, "lo": 26.5, "hi": 40.0,
  "time": "16:58", "clock24": 1,
  "heatMode": 0, "highRange": 1, "heating": 1, "filter": 1, "locked": 0,
  "spaState": 0, "paused": 0, "pauseMin": 0,
  "reminder": 0, "fault": 0,
  "filters": {"valid": 1, "s1": 1200, "d1": 120, "on2": 1, "s2": 480, "d2": 60},
  "faultLog": {"valid": 1, "entries": 3, "code": 16, "daysAgo": 2, "hour": 7, "minute": 15},
  "pumps": [0, 2, 1, 0, 0, 0], "lights": [1, 0], "blower": 0, "circ": 1, "mister": 0,
  "cfg": {"valid": 1, "pumps": [2, 2, 1, 0, 0, 0], "lights": [1, 0], "blower": 1, "aux": [0, 0], "mister": 0},
  "bus": {"channel": 16, "frames": 123456, "crc": 0, "framing": 0, "late": 0, "sent": 42, "queued": 0},
  "rssi": -61, "uptime": 86400, "heap": 21000
}
```

| Key | Meaning |
| --- | --- |
| `api` | API version (this document: 1) |
| `name`, `tagline` | Page name and second line, set by the owner |
| `age` | Milliseconds since the last status from the spa; `-1` = no status yet. Older than 15000 = spa not responding |
| `unit` | `"C"` or `"F"`: the unit of every temperature |
| `temp` | Water temperature, `null` until the spa has measured it |
| `set` | Set temperature |
| `lo`, `hi` | Allowed set-temperature range for the current temperature range |
| `time`, `clock24` | Spa clock `"HH:MM"` (24 h), and whether the spa panel shows 24 h time |
| `heatMode` | `0` Ready, `1` Rest, `3` Ready-in-Rest |
| `highRange` | `1` = high temperature range, `0` = low |
| `heating` | `0` off, `1` heating, `2` waiting to heat |
| `filter` | Filter cycles running now: bit 0 = cycle 1, bit 1 = cycle 2 |
| `locked` | `1` = the spa's own panel is locked |
| `spaState` | `0` running, `1` initialising, `5` hold, `0x17` test |
| `paused`, `pauseMin` | Pause (hold mode) on, and minutes left |
| `reminder` | Reminder shown on the panel: `0` none, `4` clean the filter, `9` check the sanitizer, `10` check the pH. `30` (`0x1E`) means "see error" and is not a reminder |
| `fault` | `1` = the spa shows an error |
| `filters` | Filter cycle settings: start (minutes since midnight) and length (minutes); `valid` = read from the spa |
| `faultLog` | Most recent error log entry: `entries` (0 = empty log), `code`, `daysAgo`, `hour`, `minute`; `valid` = read from the spa |
| `pumps` | Pump 1–6 state: `0` off, `1` low, `2` high |
| `lights` | Light 1–2: `1` on |
| `blower` | Blower speed, `0` off |
| `circ` | Circulation pump running |
| `mister` | Mister on |
| `cfg` | What the spa has (`valid` = read from the spa). `pumps`: `0` none, `1` one speed, `2` two speeds. `lights`: `1` present. `blower`: number of speeds (`0` none). `aux`, `mister`: present |
| `bus` | RS485 statistics. `channel` = the module's address on the spa bus, `0` = not joined yet |
| `rssi`, `uptime`, `heap` | WiFi signal (dBm), seconds since start, free memory (bytes) |

Error codes (`faultLog.code`): 15 sensors out of sync, 16 low water flow, 17 water flow failed,
18 settings reset, 19 priming mode, 20 clock failed, 21 settings reset, 22 program memory failure,
26 sensors out of sync (call for service), 27 heater is dry, 28 heater may be dry, 29 water too hot,
30 heater too hot, 31 sensor A fault, 32 sensor B fault, 34 a pump may be stuck on, 35 hot fault,
36 GFCI test failed, 37 standby (paused).

## Commands

| Call | Auth | Effect |
| --- | --- | --- |
| `POST /api/toggle?item=<item>` | header | Press a panel button. Items: `pump1`–`pump6`, `light1`, `light2`, `blower`, `mister`, `aux1`, `aux2`, `heatmode`, `range`, `pause`, `reminder` (dismiss the current reminder). Two-speed pumps cycle Off → Low → High → Off |
| `POST /api/temp?value=38.5` | header | Set temperature, in the spa's unit |
| `POST /api/clock?time=1018` | 🔒 | Set the spa clock to minutes since midnight (here 16:58); also switches the panel to 24 h |
| `POST /api/filters?s1=1200&d1=120&on2=1&s2=480&d2=60` | 🔒 | Filter cycles |
| `POST /api/lock?on=1` | 🔒 | Lock (`1`) or unlock (`0`) the spa panel |
| `POST /api/units` | 🔒 | Switch the spa to °C and 24 h time |
| `GET /api/auth` | 🔒 | `200` if the password or token is right, else `401` |
| `POST /api/token` | 🔒 | `{"ok": true, "token": "..."}`: a new token. Replaces the previous one; a factory reset removes it |

The module has more calls for its own web page (page layout, page name, firmware upload, factory reset).
The integration does not use them.

## How the integration uses the API

1. Setup: `GET /api/status` to check the host is an ESP Spa module, then `POST /api/token` once with the
   settings password as basic auth. Only the token is stored; the password is not.
2. Start-up: `GET /api/auth` with the token. `401` starts re-authentication in Home Assistant.
3. Polling: `GET /api/status` every 5 seconds.
4. Commands: `POST` with `X-Spa-Client: home-assistant` and the token.
