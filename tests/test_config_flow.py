"""Config flow: manual host, mDNS discovery, password -> token, re-authentication."""

from __future__ import annotations

from ipaddress import ip_address

import aiohttp

from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.esp_spa.const import CONF_TOKEN, DOMAIN

from .conftest import HOST, TOKEN, URL, calls

DISCOVERY = ZeroconfServiceInfo(
    ip_address=ip_address(HOST),
    ip_addresses=[ip_address(HOST)],
    port=80,
    hostname="spa.local.",
    type="_http._tcp.local.",
    name="spa._http._tcp.local.",
    properties={},
)


async def test_user_flow(hass: HomeAssistant, module: AiohttpClientMocker) -> None:
    """Host, then password; only the token is stored."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "secret"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_TOKEN: TOKEN}
    assert "secret" not in str(result["data"])

    (token_call,) = calls(module, "/api/token")
    assert token_call[3]["X-Spa-Client"] == "home-assistant"
    assert token_call[3]["Authorization"] == "Basic aG9tZS1hc3Npc3RhbnQ6c2VjcmV0"  # home-assistant:secret


async def test_user_flow_cannot_connect(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/status", exc=aiohttp.ClientError)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_not_esp_spa(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/status", text="<html>printer</html>")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["errors"] == {"base": "not_esp_spa"}


async def test_user_flow_wrong_password(
    hass: HomeAssistant, module: AiohttpClientMocker, status: dict
) -> None:
    module.clear_requests()
    module.get(f"{URL}/api/status", json=status)
    module.post(f"{URL}/api/token", status=401, json={"ok": False, "error": "Wrong password"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "nope"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    # Right password after a wrong one
    module.clear_requests()
    module.post(f"{URL}/api/token", json={"ok": True, "token": TOKEN})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "secret"})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, module: AiohttpClientMocker, entry: MockConfigEntry
) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_module_id_used_when_reported(
    hass: HomeAssistant, module: AiohttpClientMocker, status: dict
) -> None:
    """Newer firmware may report its own id; it becomes the unique id."""
    status["id"] = "A0B1C2"
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "secret"})
    assert result["result"].unique_id == "a0b1c2"


async def test_zeroconf_flow(hass: HomeAssistant, module: AiohttpClientMocker) -> None:
    """Found on the network: only the password is asked."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=DISCOVERY
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "secret"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST, CONF_TOKEN: TOKEN}
    assert result["result"].unique_id == "spa"


async def test_zeroconf_updates_host(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: dict) -> None:
    """A known module found at a new address: the entry follows it."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="spa", data={CONF_HOST: "192.0.2.99", CONF_TOKEN: TOKEN}
    )
    entry.add_to_hass(hass)
    aioclient_mock.get(f"{URL}/api/status", json=status)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=DISCOVERY
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == HOST


async def test_zeroconf_not_esp_spa(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Another device whose mDNS name starts with 'spa' is ignored."""
    aioclient_mock.get(f"{URL}/api/status", status=404, text="Not found")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=DISCOVERY
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_esp_spa"


async def test_reauth(hass: HomeAssistant, module: AiohttpClientMocker, entry: MockConfigEntry) -> None:
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    module.clear_requests()
    module.post(f"{URL}/api/token", json={"ok": True, "token": "new-token"})
    module.get(f"{URL}/api/status", json={})  # reload after the abort may poll
    module.get(f"{URL}/api/auth", json={"ok": True})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "secret"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "new-token"
