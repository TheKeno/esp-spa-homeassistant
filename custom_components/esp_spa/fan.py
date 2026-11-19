"""Jets and blower as fans (two-speed jets get Low and High)."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from .coordinator import EspSpaConfigEntry, EspSpaCoordinator
from .entity import EspSpaEntity, add_equipment_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    def make(item: str, speeds: int) -> list[EspSpaFan]:
        if item.startswith("pump") or item == "blower":
            return [EspSpaFan(coordinator, item, speeds)]
        return []

    add_equipment_entities(coordinator, entry, async_add_entities, make)


class EspSpaFan(EspSpaEntity, FanEntity):
    """A pump (jets) or the blower.

    The spa only has a button per item that steps through the speeds
    (Off -> Low -> High -> Off), so a change can take several presses.
    """

    def __init__(self, coordinator: EspSpaCoordinator, item: str, speeds: int) -> None:
        super().__init__(coordinator, item)
        self._item = item
        self._speeds = max(1, speeds)
        if item == "blower":
            self._attr_translation_key = "blower"
        else:
            self._attr_translation_key = "jets"
            self._attr_translation_placeholders = {"number": item.removeprefix("pump")}
        self._attr_supported_features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self._speeds > 1:
            self._attr_supported_features |= FanEntityFeature.SET_SPEED
        self._attr_speed_count = self._speeds

    @property
    def _level(self) -> int:
        """Current speed: 0 = off, 1..speeds."""
        data = self.coordinator.data
        if self._item == "blower":
            value = data.get("blower", 0)
        else:
            pumps = data.get("pumps", [])
            index = int(self._item.removeprefix("pump")) - 1
            value = pumps[index] if index < len(pumps) else 0
        return min(int(value or 0), self._speeds)

    @property
    def is_on(self) -> bool:
        return self._level > 0

    @property
    def percentage(self) -> int:
        if self._level == 0:
            return 0
        return ranged_value_to_percentage((1, self._speeds), self._level)

    async def _go_to(self, level: int) -> None:
        presses = (level - self._level) % (self._speeds + 1)
        if presses:
            await self.coordinator.async_press(self._item, presses)

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        if percentage is not None:
            await self.async_set_percentage(percentage)
        elif not self.is_on:
            # One press: the speed the spa starts with
            await self.coordinator.async_press(self._item)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._go_to(0)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self._go_to(0)
            return
        await self._go_to(math.ceil(percentage_to_ranged_value((1, self._speeds), percentage)))
