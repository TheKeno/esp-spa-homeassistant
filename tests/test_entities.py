"""Entities: states from the status, and the commands they send."""

from __future__ import annotations

from typing import Any

import pytest

from homeassistant.components.button import DOMAIN as BUTTON, SERVICE_PRESS
from homeassistant.components.climate import (
    ATTR_HVAC_ACTION,
    DOMAIN as CLIMATE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.fan import ATTR_PERCENTAGE, DOMAIN as FAN, SERVICE_SET_PERCENTAGE
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.select import DOMAIN as SELECT, SERVICE_SELECT_OPTION
from homeassistant.components.switch import DOMAIN as SWITCH
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import TOKEN, URL, calls


def toggles(module: AiohttpClientMocker) -> list[str]:
    """Items pressed, in order."""
    return [c[1].query["item"] for c in calls(module, "/api/toggle")]


async def call(hass: HomeAssistant, domain: str, service: str, entity_id: str, **data: Any) -> None:
    await hass.services.async_call(domain, service, {ATTR_ENTITY_ID: entity_id, **data}, blocking=True)


async def refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_states(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    climate = hass.states.get("climate.spa")
    assert climate.state == "heat"
    assert climate.attributes["current_temperature"] == 37.5
    assert climate.attributes["temperature"] == 38.0
    assert climate.attributes["min_temp"] == 26.5
    assert climate.attributes["max_temp"] == 40.0
    assert climate.attributes[ATTR_HVAC_ACTION] == "heating"

    # Equipment from the spa's configuration: pumps 1-2 two-speed, pump 3 one-speed, blower, light 1
    assert hass.states.get("fan.spa_jets_1").state == "off"
    jets2 = hass.states.get("fan.spa_jets_2")
    assert jets2.state == "on"
    assert jets2.attributes[ATTR_PERCENTAGE] == 100
    assert hass.states.get("fan.spa_jets_3").state == "on"
    assert hass.states.get("fan.spa_jets_4") is None
    assert hass.states.get("fan.spa_blower").state == "off"
    assert hass.states.get("light.spa_light_1").state == "on"
    assert hass.states.get("light.spa_light_2") is None
    assert hass.states.get("switch.spa_mister") is None

    assert hass.states.get("switch.spa_pause").state == "off"
    assert hass.states.get("select.spa_heat_mode").state == "ready"
    assert hass.states.get("select.spa_temperature_range").state == "high"
    assert hass.states.get("sensor.spa_reminder").state == "none"
    error = hass.states.get("sensor.spa_error")
    assert error.state == "none"
    assert error.attributes["last_logged_error"] == "low_flow"
    assert hass.states.get("sensor.spa_clock").state == "16:58"
    assert hass.states.get("binary_sensor.spa_connection").state == "on"
    assert hass.states.get("binary_sensor.spa_heating").state == "on"
    assert hass.states.get("binary_sensor.spa_filter_cycle").state == "on"
    assert hass.states.get("binary_sensor.spa_circulation_pump").state == "on"
    assert hass.states.get("event.spa_reminder").state == STATE_UNKNOWN
    assert hass.states.get("button.spa_reminder_done") is not None
    assert hass.states.get("button.spa_sync_clock") is not None


async def test_set_temperature(hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker) -> None:
    await call(hass, CLIMATE, SERVICE_SET_TEMPERATURE, "climate.spa", **{ATTR_TEMPERATURE: 38.5})
    (sent,) = calls(module, "/api/temp")
    assert sent[1].query["value"] == "38.5"
    assert sent[3]["X-Spa-Client"] == "home-assistant"
    assert sent[3]["Authorization"] == f"Bearer {TOKEN}"

    with pytest.raises(ServiceValidationError):
        await call(hass, CLIMATE, SERVICE_SET_TEMPERATURE, "climate.spa", **{ATTR_TEMPERATURE: 45})


@pytest.mark.parametrize(
    ("entity", "service", "data", "expected"),
    [
        # Jets 1 is off, two speeds: Off -> Low -> High
        ("fan.spa_jets_1", SERVICE_TURN_ON, {}, ["pump1"]),
        ("fan.spa_jets_1", SERVICE_SET_PERCENTAGE, {ATTR_PERCENTAGE: 50}, ["pump1"]),
        ("fan.spa_jets_1", SERVICE_SET_PERCENTAGE, {ATTR_PERCENTAGE: 100}, ["pump1", "pump1"]),
        ("fan.spa_jets_1", SERVICE_TURN_OFF, {}, []),
        # Jets 2 is on High: High -> Off is one press, High -> Low two
        ("fan.spa_jets_2", SERVICE_TURN_OFF, {}, ["pump2"]),
        ("fan.spa_jets_2", SERVICE_SET_PERCENTAGE, {ATTR_PERCENTAGE: 50}, ["pump2", "pump2"]),
        ("fan.spa_jets_2", SERVICE_TURN_ON, {}, []),
        # Jets 3 is a one-speed pump that is on
        ("fan.spa_jets_3", SERVICE_TURN_OFF, {}, ["pump3"]),
        ("fan.spa_blower", SERVICE_TURN_ON, {}, ["blower"]),
    ],
)
async def test_fans(
    hass: HomeAssistant,
    loaded: MockConfigEntry,
    module: AiohttpClientMocker,
    entity: str,
    service: str,
    data: dict,
    expected: list[str],
) -> None:
    await call(hass, FAN, service, entity, **data)
    assert toggles(module) == expected


async def test_light_switch_select(
    hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker
) -> None:
    await call(hass, LIGHT, SERVICE_TURN_ON, "light.spa_light_1")  # already on
    await call(hass, LIGHT, SERVICE_TURN_OFF, "light.spa_light_1")
    await call(hass, SWITCH, SERVICE_TURN_OFF, "switch.spa_pause")  # already off
    await call(hass, SWITCH, SERVICE_TURN_ON, "switch.spa_pause")
    await call(hass, SELECT, SERVICE_SELECT_OPTION, "select.spa_heat_mode", option="ready")  # already
    await call(hass, SELECT, SERVICE_SELECT_OPTION, "select.spa_heat_mode", option="rest")
    await call(hass, SELECT, SERVICE_SELECT_OPTION, "select.spa_temperature_range", option="low")
    assert toggles(module) == ["light1", "pause", "heatmode", "range"]


async def test_paused(hass: HomeAssistant, loaded: MockConfigEntry, status: dict) -> None:
    status.update(paused=1, pauseMin=42)
    await refresh(hass, loaded)
    pause = hass.states.get("switch.spa_pause")
    assert pause.state == "on"
    assert pause.attributes["minutes_left"] == 42
    assert hass.states.get("climate.spa").attributes[ATTR_HVAC_ACTION] == "off"


async def test_reminder_sensor_event_and_button(
    hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker, status: dict
) -> None:
    with pytest.raises(ServiceValidationError):
        await call(hass, BUTTON, SERVICE_PRESS, "button.spa_reminder_done")

    status["reminder"] = 10
    await refresh(hass, loaded)
    assert hass.states.get("sensor.spa_reminder").state == "check_ph"
    event = hass.states.get("event.spa_reminder")
    assert event.state != STATE_UNKNOWN
    assert event.attributes["event_type"] == "check_ph"

    await call(hass, BUTTON, SERVICE_PRESS, "button.spa_reminder_done")
    assert toggles(module) == ["reminder"]

    # Still showing on the next poll: no second event
    fired_at = event.state
    await refresh(hass, loaded)
    assert hass.states.get("event.spa_reminder").state == fired_at

    # 0x1E is "see error", not a reminder
    status["reminder"] = 0x1E
    await refresh(hass, loaded)
    assert hass.states.get("sensor.spa_reminder").state == "none"


async def test_reminder_at_startup_does_not_fire(
    hass: HomeAssistant, entry: MockConfigEntry, module: AiohttpClientMocker, status: dict
) -> None:
    status["reminder"] = 4
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.spa_reminder").state == "clean_filter"
    assert hass.states.get("event.spa_reminder").state == STATE_UNKNOWN


async def test_error_sensor_and_event(hass: HomeAssistant, loaded: MockConfigEntry, status: dict) -> None:
    status["fault"] = 1
    status["faultLog"]["code"] = 27
    await refresh(hass, loaded)
    assert hass.states.get("sensor.spa_error").state == "heater_dry"
    event = hass.states.get("event.spa_error")
    assert event.attributes["event_type"] == "error"
    assert event.attributes["error"] == "heater_dry"
    assert event.attributes["code"] == 27

    # Unknown code, or no log entry
    status["faultLog"]["code"] = 99
    await refresh(hass, loaded)
    assert hass.states.get("sensor.spa_error").state == "unknown"

    status["fault"] = 0
    await refresh(hass, loaded)
    assert hass.states.get("sensor.spa_error").state == "none"


async def test_sync_clock_uses_token(
    hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker
) -> None:
    await call(hass, BUTTON, SERVICE_PRESS, "button.spa_sync_clock")
    (sent,) = calls(module, "/api/clock")
    now = dt_util.now()
    minutes = int(sent[1].query["time"])
    assert abs(minutes - (now.hour * 60 + now.minute)) <= 1
    assert sent[3]["Authorization"] == f"Bearer {TOKEN}"
    assert sent[3]["X-Spa-Client"] == "home-assistant"


async def test_sync_clock_rejected_token_starts_reauth(
    hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker, status: dict
) -> None:
    module.clear_requests()
    module.get(f"{URL}/api/status", json=status)
    module.post(f"{URL}/api/clock", status=401, json={"ok": False, "error": "Wrong password"})
    with pytest.raises(HomeAssistantError):
        await call(hass, BUTTON, SERVICE_PRESS, "button.spa_sync_clock")
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_command_refused(
    hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker, status: dict
) -> None:
    module.clear_requests()
    module.get(f"{URL}/api/status", json=status)
    module.post(f"{URL}/api/toggle", status=503, json={"ok": False, "error": "Not connected to the spa yet"})
    with pytest.raises(HomeAssistantError, match="Not connected"):
        await call(hass, LIGHT, SERVICE_TURN_OFF, "light.spa_light_1")


async def test_equipment_added_when_spa_reports_it(
    hass: HomeAssistant, entry: MockConfigEntry, module: AiohttpClientMocker, status: dict
) -> None:
    """Spa off at start-up: the equipment appears once its configuration arrives."""
    status["cfg"]["valid"] = 0
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("fan.spa_jets_1") is None
    assert hass.states.get("climate.spa") is not None

    status["cfg"]["valid"] = 1
    status["cfg"]["mister"] = 1
    status["cfg"]["aux"] = [1, 0]
    await refresh(hass, entry)
    assert hass.states.get("fan.spa_jets_1") is not None
    assert hass.states.get("light.spa_light_1") is not None
    assert hass.states.get("switch.spa_mister") is not None
    assert hass.states.get("button.spa_aux_1") is not None

    # Not added twice
    await refresh(hass, entry)
    assert len(hass.states.async_entity_ids("fan")) == 4
