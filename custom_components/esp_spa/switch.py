"""Pause (hold mode) and mister."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    async_add_entities([EspSpaSwitch(coordinator, "pause", "paused")])

    def make(item: str, speeds: int) -> list[EspSpaSwitch]:
        return [EspSpaSwitch(coordinator, item, item)] if item == "mister" else []

    add_equipment_entities(coordinator, entry, async_add_entities, make)


class EspSpaSwitch(EspSpaEntity, SwitchEntity):
    """A spa button with an on/off state."""

    def __init__(self, coordinator: EspSpaCoordinator, item: str, field: str) -> None:
        super().__init__(coordinator, item)
        self._item = item
        self._field = field
        self._attr_translation_key = item

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get(self._field))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._item == "pause":
            return {"minutes_left": self.coordinator.data.get("pauseMin") if self.is_on else None}
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            await self.coordinator.async_press(self._item)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.is_on:
            await self.coordinator.async_press(self._item)
