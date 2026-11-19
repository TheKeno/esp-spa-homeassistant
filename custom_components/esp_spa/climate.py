"""Water temperature and set temperature."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EspSpaConfigEntry
from .entity import EspSpaEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EspSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([EspSpaClimate(entry.runtime_data, "climate")])


class EspSpaClimate(EspSpaEntity, ClimateEntity):
    """The spa as a thermostat. It always heats; pause stops it for a while."""

    _attr_name = None  # the device's own name
    _attr_translation_key = "spa"
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data

    @property
    def temperature_unit(self) -> str:
        return UnitOfTemperature.CELSIUS if self._data.get("unit") == "C" else UnitOfTemperature.FAHRENHEIT

    @property
    def target_temperature_step(self) -> float:
        return 0.5 if self._data.get("unit") == "C" else 1.0

    @property
    def precision(self) -> float:
        return 0.5 if self._data.get("unit") == "C" else 1.0

    @property
    def current_temperature(self) -> float | None:
        return self._data.get("temp")

    @property
    def target_temperature(self) -> float | None:
        return self._data.get("set")

    @property
    def min_temp(self) -> float:
        lo = self._data.get("lo")
        return lo if lo is not None else super().min_temp

    @property
    def max_temp(self) -> float:
        hi = self._data.get("hi")
        return hi if hi is not None else super().max_temp

    @property
    def hvac_action(self) -> HVACAction:
        if self._data.get("paused"):
            return HVACAction.OFF
        return HVACAction.HEATING if self._data.get("heating") == 1 else HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        value = kwargs.get(ATTR_TEMPERATURE)
        if value is None:
            return
        if not self.min_temp <= value <= self.max_temp:
            raise ServiceValidationError(
                f"The spa accepts {self.min_temp}–{self.max_temp} in its current temperature range"
            )
        await self.coordinator.async_command(lambda: self.coordinator.client.set_temperature(value))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """The spa only heats; use the pause switch to stop it."""
        if hvac_mode != HVACMode.HEAT:
            raise ServiceValidationError("The spa only has a heat mode; use the Pause switch")
