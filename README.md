# ESP Spa for Home Assistant

A Home Assistant integration for **ESP Spa**: an ESP8266 module that connects to a Balboa spa controller
over RS485 and serves a local web page and JSON API. Everything stays on the local network: no cloud,
no MQTT broker.

- Found automatically on the network, set up with the module's settings password
- Thermostat: water temperature, set temperature, heating
- Jets (with Low / High for two-speed pumps), blower, light, pause
- Heat mode (Ready / Rest) and temperature range (Low / High)
- Spa reminders (clean the filter, check the sanitizer, check the pH) and errors, as sensors and events
- "Reminder done" and "Sync clock" buttons

## Requirements

- Home Assistant **2026.11 or newer**
- An ESP Spa module with firmware that has API version 1 (the module's status shows `"api": 1`) and a
  settings password (chosen when the module was set up)
- Home Assistant and the module on the same network

## Install

The integration is installed from the Home Assistant **Marketplace** as a custom repository.

1. In Home Assistant, go to **Settings → Marketplace**. (Admins only. Accept the notice the first time.)
2. In the upper-right corner, select **Add from link**.
3. Under **GitHub link**, enter `https://github.com/TheKeno/esp-spa-homeassistant` and select **Add**.
   If Home Assistant asks you to connect a GitHub account, follow its steps (a code and a GitHub link).
   If it asks for a **Type**, choose **Integration** and select **Add** again.
4. Open **ESP Spa** in the list and select **Install**, then **Install** again in the dialog.
5. Restart Home Assistant (**Settings → System → Restart**).

Updates show up in the Marketplace like any other.

## Set up

1. After the restart, Home Assistant normally finds the module by itself: **Settings → Devices &
   services** shows **ESP Spa** under *Discovered*. Select **Add**.
   If it is not found, select **Add integration**, search for **ESP Spa** and enter `spa.local` or the
   module's IP address.
2. Enter the module's **settings password**. Home Assistant uses it once to get its own token from the
   module and does not store the password.

Good to know:

- Each module has **one** Home Assistant token. Setting the module up in a second Home Assistant (or
  again) replaces the token, and the first one asks for the password again (*Re-authenticate*).
  A factory reset of the module also removes the token.
- The module is polled every 5 seconds. A change made in Home Assistant shows up after a second or two.
- Give the module a fixed IP address in your router if you can. If it moves, Home Assistant usually
  finds it again by itself.

## Entities

The device is called **Spa**; rename it under the device if you like. Equipment appears as the spa
reports it (if the spa was off during set-up, the jets and lights appear once it is on).

| Entity | What it does |
| --- | --- |
| `climate.spa` | Water temperature and set temperature. Heating shows as the action; *Off* while paused. The allowed range follows the temperature range |
| `fan.spa_jets_1` … | Jets. Two-speed pumps have Low (50 %) and High (100 %). The spa steps Off → Low → High, so a change can take two presses (about a second) |
| `fan.spa_blower` | Blower |
| `light.spa_light_1` | Spa light |
| `switch.spa_pause` | Pause: jets and heating off for a while (`minutes_left` attribute) |
| `switch.spa_mister`, `button.spa_aux_1` | Only if the spa has them |
| `select.spa_heat_mode` | *Ready* (heats when needed) or *Rest* (heats only during filter cycles) |
| `select.spa_temperature_range` | *Low* or *High*; each has its own set temperature |
| `sensor.spa_reminder` | Reminder shown on the spa panel: *None*, *Clean the filter*, *Check the sanitizer*, *Check the pH* |
| `sensor.spa_error` | Error the spa shows now (*No error* otherwise). Attributes: the most recent error in the spa's log |
| `event.spa_reminder`, `event.spa_error` | Fire when a reminder or error appears, for notifications |
| `button.spa_reminder_done` | Dismiss the reminder, like on the spa panel |
| `button.spa_sync_clock` | Set the spa clock to Home Assistant's time (also switches the panel to 24 h) |
| `binary_sensor.spa_heating`, `…_filter_cycle`, `…_circulation_pump` | What the spa is doing |
| `binary_sensor.spa_connection`, `…_panel_lock`, `sensor.spa_clock`, `sensor.spa_wifi_signal` | Diagnostics (WiFi signal is off by default) |

When the module does not hear the spa, the spa entities become *unavailable*; **Connection** stays
available and shows *Disconnected*.

## Notifications for reminders and errors

The event entities fire once when a reminder or an error appears. This automation puts them in Home
Assistant's notification panel (the bell) and on your phone. Create it under **Settings → Automations →
Create automation → ⋮ → Edit in YAML**; replace `notify.mobile_app_your_phone` with your own phone, or
remove that action.

```yaml
alias: Spa reminders and errors
triggers:
  - trigger: state
    entity_id: event.spa_reminder
    not_from: unavailable
  - trigger: state
    entity_id: event.spa_error
    not_from: unavailable
actions:
  - variables:
      message: >-
        {% if trigger.entity_id == 'event.spa_error' %}
          Spa error: {{ states('sensor.spa_error') | replace('_', ' ') }}
        {% else %}
          Spa: {{ state_translated('sensor.spa_reminder') }}
        {% endif %}
  - action: persistent_notification.create
    data:
      title: Spa
      message: "{{ message }}"
      notification_id: "spa_{{ trigger.entity_id.split('.')[1] }}"
  - action: notify.mobile_app_your_phone
    data:
      title: Spa
      message: "{{ message }}"
mode: queued
```

`sensor.spa_reminder` and `sensor.spa_error` also work in conditions and dashboards, for example a
conditional card that only shows while `sensor.spa_reminder` is not *None*.

## API version

The module reports an API version. This integration is written for **API version 1** (see
[docs/API.md](docs/API.md)). If the module reports another version, Home Assistant shows a repair issue
under **Settings → System → Repairs**: update the integration (Marketplace) or the module's firmware so
they match. Until then the integration keeps working as far as it can.

## Troubleshooting

- **Not discovered:** add it by hand with the module's IP address. mDNS does not cross VLANs or guest
  networks.
- **"Cannot reach the module":** check that the module's web page opens in a browser at the same address.
- **Asks to re-authenticate:** the token was replaced or the module was factory reset. Enter the
  settings password again.
- **Diagnostics:** on the device page, ⋮ → *Download diagnostics* gives the latest status (token and
  address hidden), useful for an issue report.

## Development

Tests use [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
against a mocked module (Linux or WSL; Home Assistant does not run its tests on Windows):

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
```

The API contract between module and integration is [docs/API.md](docs/API.md).
