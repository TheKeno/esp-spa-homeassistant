"""Events when a reminder or an error appears, for notifications and automations."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EVENT_ERROR, FAULT_NONE, FAULTS, REMINDER_NONE, REMINDER_OTHER, REMINDERS
from .coordinator import EspSpaConfigEntry, EspSpaCoordinator
from .entity import EspSpaEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([ReminderEvent(coordinator), ErrorEvent(coordinator)])


class _ChangeEvent(EspSpaEntity, EventEntity):
    """Fires when the watched value turns from 'none' to something else (or changes).

    What is already showing when Home Assistant starts does not fire; the sensors show it.
    """

    _none: str

    def __init__(self, coordinator: EspSpaCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._last: str | None = None

    def _current(self) -> str:
        raise NotImplementedError

    def _fire(self, value: str) -> None:
        raise NotImplementedError

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self.coordinator.live:
            self._last = self._current()

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.live:
            value = self._current()
            if self._last is not None and value != self._last and value != self._none:
                self._fire(value)
            self._last = value
        super()._handle_coordinator_update()


class ReminderEvent(_ChangeEvent):
    """The spa shows a new reminder."""

    _attr_translation_key = "reminder"
    _attr_event_types = [*REMINDERS.values(), REMINDER_OTHER]
    _none = REMINDER_NONE

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "reminder_event")

    def _current(self) -> str:
        return self.coordinator.reminder

    def _fire(self, value: str) -> None:
        self._trigger_event(value, {"code": self.coordinator.data.get("reminder")})


class ErrorEvent(_ChangeEvent):
    """The spa shows an error."""

    _attr_translation_key = "error"
    _attr_event_types = [EVENT_ERROR]
    _none = FAULT_NONE

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "error_event")

    def _current(self) -> str:
        return self.coordinator.fault

    def _fire(self, value: str) -> None:
        code = self.coordinator.fault_code
        self._trigger_event(EVENT_ERROR, {"error": value, "code": code})
