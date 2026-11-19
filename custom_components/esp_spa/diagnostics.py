"""Diagnostics download: the config entry (token hidden) and the latest status."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN
from .coordinator import EspSpaConfigEntry

TO_REDACT = {CONF_TOKEN, CONF_HOST, "name", "tagline"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EspSpaConfigEntry
) -> dict[str, Any]:
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "status": async_redact_data(entry.runtime_data.data or {}, TO_REDACT),
    }
