"""Set-up, unload, API version check, token check, availability, diagnostics."""

from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.esp_spa.const import DOMAIN
from custom_components.esp_spa.diagnostics import async_get_config_entry_diagnostics

from .conftest import TOKEN, URL, calls


async def test_setup_and_unload(hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker) -> None:
    assert loaded.state is ConfigEntryState.LOADED
    # The token is checked once at start-up
    (auth,) = calls(module, "/api/auth")
    assert auth[3]["Authorization"] == f"Bearer {TOKEN}"

    assert await hass.config_entries.async_unload(loaded.entry_id)
    assert loaded.state is ConfigEntryState.NOT_LOADED


async def test_module_offline_retries(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/auth", exc=aiohttp.ClientError)
    aioclient_mock.get(f"{URL}/api/status", exc=aiohttp.ClientError)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_token_rejected_starts_reauth(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/auth", status=401, json={"ok": False})
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_api_version_mismatch_raises_issue(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    module: AiohttpClientMocker,
    status: dict,
    issue_registry: ir.IssueRegistry,
) -> None:
    status["api"] = 2
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    issue = issue_registry.async_get_issue(DOMAIN, f"api_version_{entry.entry_id}")
    assert issue is not None
    assert issue.translation_placeholders["found"] == "2"
    assert issue.translation_placeholders["expected"] == "1"
    # It keeps working
    assert hass.states.get("climate.spa").state == "heat"

    # Matching again (firmware or integration updated): the issue goes away
    status["api"] = 1
    await entry.runtime_data.async_refresh()
    assert issue_registry.async_get_issue(DOMAIN, f"api_version_{entry.entry_id}") is None


async def test_no_issue_when_version_matches(
    hass: HomeAssistant, loaded: MockConfigEntry, issue_registry: ir.IssueRegistry
) -> None:
    assert issue_registry.async_get_issue(DOMAIN, f"api_version_{loaded.entry_id}") is None


async def test_spa_not_responding_makes_entities_unavailable(
    hass: HomeAssistant, loaded: MockConfigEntry, status: dict
) -> None:
    status["age"] = 60000
    await loaded.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("climate.spa").state == STATE_UNAVAILABLE
    assert hass.states.get("fan.spa_jets_1").state == STATE_UNAVAILABLE
    # The module itself still answers and says so
    assert hass.states.get("binary_sensor.spa_connection").state == "off"


async def test_module_unreachable_makes_everything_unavailable(
    hass: HomeAssistant, loaded: MockConfigEntry, module: AiohttpClientMocker
) -> None:
    module.clear_requests()
    module.get(f"{URL}/api/status", exc=aiohttp.ClientError)
    await loaded.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("climate.spa").state == STATE_UNAVAILABLE
    assert hass.states.get("binary_sensor.spa_connection").state == STATE_UNAVAILABLE


async def test_diagnostics_hide_token(hass: HomeAssistant, loaded: MockConfigEntry) -> None:
    diag = await async_get_config_entry_diagnostics(hass, loaded)
    assert TOKEN not in str(diag)
    assert "Test spa" not in str(diag)
    assert diag["status"]["temp"] == 37.5
