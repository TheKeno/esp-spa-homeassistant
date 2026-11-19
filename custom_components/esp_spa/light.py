"""Spa lights."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EspSpaConfigEntry, EspSpaCoordinator
from .entity import EspSpaEntity, add_equipment_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    def make(item: str, speeds: int) -> list[EspSpaLight]:
        return [EspSpaLight(coordinator, item)] if item.startswith("light") else []

    add_equipment_entities(coordinator, entry, async_add_entities, make)


class EspSpaLight(EspSpaEntity, LightEntity):
    """An on/off spa light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_translation_key = "light"

    def __init__(self, coordinator: EspSpaCoordinator, item: str) -> None:
        super().__init__(coordinator, item)
        self._item = item
        self._index = int(item.removeprefix("light")) - 1
        self._attr_translation_placeholders = {"number": str(self._index + 1)}

    @property
    def is_on(self) -> bool:
        lights = self.coordinator.data.get("lights", [])
        return bool(lights[self._index]) if self._index < len(lights) else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            await self.coordinator.async_press(self._item)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.is_on:
            await self.coordinator.async_press(self._item)
