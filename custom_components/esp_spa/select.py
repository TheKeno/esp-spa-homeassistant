"""Heat mode (Ready / Rest) and temperature range (Low / High)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EspSpaConfigEntry, EspSpaCoordinator
from .entity import EspSpaEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([HeatModeSelect(coordinator), TempRangeSelect(coordinator)])


class _ToggleSelect(EspSpaEntity, SelectEntity):
    """Two options, switched with one panel button."""

    _item: str

    def __init__(self, coordinator: EspSpaCoordinator) -> None:
        super().__init__(coordinator, self._attr_translation_key)

    async def async_select_option(self, option: str) -> None:
        if option != self.current_option:
            await self.coordinator.async_press(self._item)


class HeatModeSelect(_ToggleSelect):
    """Ready heats whenever needed; Rest only heats during filter cycles."""

    _attr_translation_key = "heat_mode"
    _attr_options = ["ready", "rest"]
    _item = "heatmode"

    @property
    def current_option(self) -> str:
        # 3 = Ready-in-Rest: Rest mode that is heating now; the spa panel shows Rest
        return "ready" if self.coordinator.data.get("heatMode") == 0 else "rest"


class TempRangeSelect(_ToggleSelect):
    """Each range has its own set temperature and limits."""

    _attr_translation_key = "temp_range"
    _attr_options = ["low", "high"]
    _item = "range"

    @property
    def current_option(self) -> str:
        return "high" if self.coordinator.data.get("highRange") else "low"
