"""The ESP Spa integration: a Balboa spa through an ESP8266 module on the local network."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EspSpaClient
from .const import CONF_TOKEN
from .coordinator import EspSpaConfigEntry, EspSpaCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.EVENT,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: EspSpaConfigEntry) -> bool:
    """Set up a spa module."""
    client = EspSpaClient(
        async_get_clientsession(hass), entry.data[CONF_HOST], entry.data[CONF_TOKEN]
    )
    coordinator = EspSpaCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EspSpaConfigEntry) -> bool:
    """Unload a spa module."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
