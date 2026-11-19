"""Fixtures: a mocked ESP Spa module on 192.0.2.10 (a documentation address)."""

from __future__ import annotations

import copy
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.esp_spa.const import CONF_TOKEN, DOMAIN

HOST = "192.0.2.10"
URL = f"http://{HOST}"
TOKEN = "0123456789abcdef0123456789abcdef"

STATUS: dict[str, Any] = {
    "api": 1,
    "name": "Test spa",
    "tagline": "Test line",
    "age": 180,
    "unit": "C",
    "temp": 37.5,
    "set": 38.0,
    "lo": 26.5,
    "hi": 40.0,
    "time": "16:58",
    "clock24": 1,
    "heatMode": 0,
    "highRange": 1,
    "heating": 1,
    "filter": 1,
    "locked": 0,
    "spaState": 0,
    "paused": 0,
    "pauseMin": 0,
    "reminder": 0,
    "fault": 0,
    "filters": {"valid": 1, "s1": 1200, "d1": 120, "on2": 1, "s2": 480, "d2": 60},
    "faultLog": {"valid": 1, "entries": 3, "code": 16, "daysAgo": 2, "hour": 7, "minute": 15},
    "pumps": [0, 2, 1, 0, 0, 0],
    "lights": [1, 0],
    "blower": 0,
    "circ": 1,
    "mister": 0,
    "cfg": {
        "valid": 1,
        "pumps": [2, 2, 1, 0, 0, 0],
        "lights": [1, 0],
        "blower": 1,
        "aux": [0, 0],
        "mister": 0,
    },
    "bus": {"channel": 16, "frames": 1000, "crc": 0, "framing": 0, "late": 0, "sent": 4, "queued": 0},
    "rssi": -61,
    "uptime": 86400,
    "heap": 21000,
}

OK = {"ok": True}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in every test."""


@pytest.fixture(autouse=True)
def no_delays() -> Generator[None]:
    """No pauses between button presses or before the extra poll."""
    with (
        patch("custom_components.esp_spa.coordinator.PRESS_DELAY", 0),
        patch("custom_components.esp_spa.coordinator.REFRESH_DELAY", 0),
    ):
        yield


@pytest.fixture
def status() -> dict[str, Any]:
    """The status the mocked module returns (change it in a test, then refresh)."""
    return copy.deepcopy(STATUS)


@pytest.fixture
def module(aioclient_mock: AiohttpClientMocker, status: dict[str, Any]) -> AiohttpClientMocker:
    """A module that answers every call."""

    async def get_status(method, url, data):  # noqa: ANN001
        return AiohttpClientMockResponse(method, url, json=status)

    aioclient_mock.get(f"{URL}/api/status", side_effect=get_status)
    aioclient_mock.get(f"{URL}/api/auth", json=OK)
    aioclient_mock.post(f"{URL}/api/token", json={"ok": True, "token": TOKEN})
    aioclient_mock.post(f"{URL}/api/toggle", json=OK)
    aioclient_mock.post(f"{URL}/api/temp", json=OK)
    aioclient_mock.post(f"{URL}/api/clock", json=OK)
    return aioclient_mock


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """A set-up spa module."""
    e = MockConfigEntry(
        domain=DOMAIN,
        title="Spa",
        unique_id="spa",
        data={CONF_HOST: HOST, CONF_TOKEN: TOKEN},
    )
    e.add_to_hass(hass)
    return e


@pytest.fixture
async def loaded(hass: HomeAssistant, entry: MockConfigEntry, module: AiohttpClientMocker) -> MockConfigEntry:
    """The integration set up against the mocked module."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def calls(mock: AiohttpClientMocker, path: str) -> list[tuple[str, Any, Any, Any]]:
    """Recorded calls to one path."""
    return [c for c in mock.mock_calls if c[1].path == path]
