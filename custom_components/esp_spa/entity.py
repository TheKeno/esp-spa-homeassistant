"""Base entity for ESP Spa."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import EspSpaConfigEntry, EspSpaCoordinator


class EspSpaEntity(CoordinatorEntity[EspSpaCoordinator]):
    """An entity of the spa device."""

    _attr_has_entity_name = True
    # Most entities need the spa itself; the module being reachable is not enough
    _needs_spa = True

    def __init__(self, coordinator: EspSpaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._key = key
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name=entry.title or DEFAULT_NAME,
            manufacturer="ESP Spa",
            model="Balboa spa module",
            configuration_url=coordinator.client.base_url,
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.live if self._needs_spa else True


def add_equipment_entities(
    coordinator: EspSpaCoordinator,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    make: Callable[[str, int], Iterable[Entity]],
) -> None:
    """Add entities for the spa's equipment, once the spa has told us what it has.

    The equipment list comes from the spa's configuration, which can arrive after
    set-up (for example when the spa was off), so this keeps checking.
    """
    added: set[str] = set()

    @callback
    def check() -> None:
        equipment = coordinator.equipment()
        if equipment is None:
            return
        new = []
        for item, speeds in equipment.items():
            if item in added:
                continue
            entities = list(make(item, speeds))
            if entities:
                added.add(item)
                new.extend(entities)
        if new:
            async_add_entities(new)

    check()
    entry.async_on_unload(coordinator.async_add_listener(check))
