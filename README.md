# ESP Spa for Home Assistant

A Home Assistant integration for **ESP Spa**: an ESP8266 module that connects to a Balboa spa controller
over RS485 and exposes a local JSON API.

> **Status: not built yet.** This repository is a placeholder. The integration is planned, and this
> README will cover installation through the Home Assistant Marketplace once version 1 exists.

## Planned features

- Discovered automatically on the local network, set up with the module's settings password
- Thermostat (water temperature, set temperature, heating)
- Jets, blower, light, pause
- Heat mode and temperature range
- Spa reminders (clean filter, check pH, check sanitizer) and errors as sensors and events
- "Reminder done" and "Sync spa clock" buttons

Everything stays on the local network. No cloud, no MQTT broker.

## Requirements

- Home Assistant 2026.11 or newer (installed through the built-in Marketplace as a custom repository)
- An ESP Spa module running compatible firmware
