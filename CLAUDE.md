# ESP Spa for Home Assistant

Public Home Assistant custom integration (`custom_components/esp_spa/`, domain `esp_spa`) for the ESP Spa
module. Distributed through the Home Assistant Marketplace (built into HA since 2026.11, formerly HACS)
as a custom repository, so `hacs.json` must stay at the repository root.

**This repository is public: never commit personal details** (owners' names, addresses, WiFi, passwords,
tokens, IP addresses of real homes).

The firmware and the project roadmap live in a separate private repository. The plan for this
integration is decision 9 there. The API contract between module and integration is `docs/API.md`;
keep it in step with the firmware's API section (`API_VERSION` in `const.py` = `"api"` in the status).

## Project facts
- Test command: from the repo folder: `wsl -d Ubuntu -- bash -lc '~/.venvs/esp-spa-ha/bin/python -m pytest -q -p no:cacheprovider'`
  (Linux only; see `notes/testing.md`). CI runs the same plus hacs/action and hassfest.
- Roadmap file: kept in the firmware repository (`ROADMAP.md`, area "Home Assistant")
- Notes folder: `notes/`
- Areas: Home Assistant, Docs
- Repo and account: `TheKeno/esp-spa-homeassistant` (public).
