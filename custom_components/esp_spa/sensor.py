"""Reminder, error and diagnostic sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FAULT_NONE, FAULT_UNKNOWN, FAULTS, REMINDER_NONE, REMINDER_OTHER, REMINDERS
from .coordinator import EspSpaConfigEntry, EspSpaCoordinator
from .entity import EspSpaEntity

PARALLEL_UPDATES = 0

REMINDER_OPTIONS = [REMINDER_NONE, *REMINDERS.values(), REMINDER_OTHER]
FAULT_OPTIONS = [FAULT_NONE, *dict.fromkeys(FAULTS.values()), FAULT_UNKNOWN]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ReminderSensor(coordinator),
            ErrorSensor(coordinator),
            SpaClockSensor(coordinator),
            SignalSensor(coordinator),
        ]
    )


class ReminderSensor(EspSpaEntity, SensorEntity):
    """The reminder the spa panel shows (clean the filter, check the pH, ...)."""

    _attr_translation_key = "reminder"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = REMINDER_OPTIONS

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "reminder")

    @property
    def native_value(self) -> str:
        return self.coordinator.reminder


class ErrorSensor(EspSpaEntity, SensorEntity):
    """The error the spa shows now, from its error log."""

    _attr_translation_key = "error"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = FAULT_OPTIONS

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "error")

    @property
    def native_value(self) -> str:
        return self.coordinator.fault

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        log = self.coordinator.data.get("faultLog", {})
        if not (log.get("valid") and log.get("entries")):
            return {"last_logged_code": None}
        return {
            "last_logged_code": log.get("code"),
            "last_logged_error": FAULTS.get(log.get("code"), FAULT_UNKNOWN),
            "last_logged_days_ago": log.get("daysAgo"),
            "last_logged_time": f"{log.get('hour', 0):02d}:{log.get('minute', 0):02d}",
        }


class SpaClockSensor(EspSpaEntity, SensorEntity):
    """The spa's own clock (it drifts; the Sync clock button fixes it)."""

    _attr_translation_key = "spa_clock"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "spa_clock")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("time")


class SignalSensor(EspSpaEntity, SensorEntity):
    """WiFi signal of the module."""

    _attr_translation_key = "signal"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _needs_spa = False

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, "signal")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("rssi")
