"""Connection, heating, filtering and circulation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EspSpaConfigEntry, EspSpaCoordinator
from .entity import EspSpaEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class EspSpaBinaryDescription(BinarySensorEntityDescription):
    """How to read one binary sensor."""

    value: Callable[[EspSpaCoordinator, dict[str, Any]], bool]
    needs_spa: bool = True


DESCRIPTIONS = (
    EspSpaBinaryDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda c, d: c.ready,
        needs_spa=False,
    ),
    EspSpaBinaryDescription(
        key="heating",
        translation_key="heating",
        device_class=BinarySensorDeviceClass.HEAT,
        value=lambda c, d: d.get("heating") == 1,
    ),
    EspSpaBinaryDescription(
        key="filtering",
        translation_key="filtering",
        device_class=BinarySensorDeviceClass.RUNNING,
        value=lambda c, d: bool(d.get("filter")),
    ),
    EspSpaBinaryDescription(
        key="circulation",
        translation_key="circulation",
        device_class=BinarySensorDeviceClass.RUNNING,
        value=lambda c, d: bool(d.get("circ")),
    ),
    EspSpaBinaryDescription(
        key="panel_locked",
        translation_key="panel_locked",
        device_class=BinarySensorDeviceClass.LOCK,
        entity_category=EntityCategory.DIAGNOSTIC,
        # The lock device class is "on" when unlocked
        value=lambda c, d: not d.get("locked"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(EspSpaBinarySensor(coordinator, d) for d in DESCRIPTIONS)


class EspSpaBinarySensor(EspSpaEntity, BinarySensorEntity):
    """A yes/no value from the status."""

    entity_description: EspSpaBinaryDescription

    def __init__(self, coordinator: EspSpaCoordinator, description: EspSpaBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._needs_spa = description.needs_spa

    @property
    def is_on(self) -> bool:
        return self.entity_description.value(self.coordinator, self.coordinator.data)
