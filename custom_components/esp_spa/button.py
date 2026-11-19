"""Reminder done, sync the spa clock, and aux buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import REMINDER_NONE
from .coordinator import EspSpaConfigEntry, EspSpaCoordinator
from .entity import EspSpaEntity, add_equipment_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([ReminderDoneButton(coordinator), SyncClockButton(coordinator)])

    def make(item: str, speeds: int) -> list[AuxButton]:
        return [AuxButton(coordinator, item)] if item.startswith("aux") else []

    add_equipment_entities(coordinator, entry, async_add_entities, make)


class ReminderDoneButton(EspSpaEntity, ButtonEntity):
    """Dismiss the reminder the spa shows."""

    _attr_translation_key = "reminder_done"

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "reminder_done")

    async def async_press(self) -> None:
        if self.coordinator.reminder == REMINDER_NONE:
            raise ServiceValidationError("The spa shows no reminder")
        await self.coordinator.async_press("reminder")


class SyncClockButton(EspSpaEntity, ButtonEntity):
    """Set the spa clock to Home Assistant's local time (also switches the panel to 24 h)."""

    _attr_translation_key = "sync_clock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "sync_clock")

    async def async_press(self) -> None:
        now = dt_util.now()
        await self.coordinator.async_command(
            lambda: self.coordinator.client.set_clock(now.hour, now.minute)
        )


class AuxButton(EspSpaEntity, ButtonEntity):
    """Aux outputs: the spa does not report their state, so they are buttons."""

    _attr_translation_key = "aux"

    def __init__(self, coordinator: EspSpaCoordinator, item: str) -> None:
        super().__init__(coordinator, item)
        self._item = item
        self._attr_translation_placeholders = {"number": item.removeprefix("aux")}

    async def async_press(self) -> None:
        await self.coordinator.async_press(self._item)
