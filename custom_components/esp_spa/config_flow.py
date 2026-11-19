"""Config flow for ESP Spa: find the module, then use the settings password once to get a token."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import CannotConnect, EspSpaClient, EspSpaError, InvalidAuth, NotEspSpa
from .const import CONF_TOKEN, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PASSWORD_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


def _unique_id(status: dict[str, Any], hostname: str | None) -> str | None:
    """A stable id for the module: its own id if the firmware reports one, else its mDNS name."""
    if status.get("id"):
        return str(status["id"]).lower()
    return hostname


class EspSpaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ESP Spa."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._title = DEFAULT_NAME

    def _client(self, host: str, token: str | None = None) -> EspSpaClient:
        return EspSpaClient(async_get_clientsession(self.hass), host, token)

    async def _check_host(self, host: str) -> tuple[dict[str, Any] | None, str | None]:
        """Status of the module at host, or the error key."""
        try:
            return await self._client(host).get_status(), None
        except NotEspSpa:
            return None, "not_esp_spa"
        except CannotConnect:
            return None, "cannot_connect"
        except EspSpaError:
            _LOGGER.exception("Unexpected answer from %s", host)
            return None, "unknown"

    async def _get_token(self, password: str) -> tuple[str | None, str | None]:
        """Token from the module, or the error key."""
        assert self._host is not None
        try:
            return await self._client(self._host).get_token(password), None
        except InvalidAuth:
            return None, "invalid_auth"
        except CannotConnect:
            return None, "cannot_connect"
        except EspSpaError:
            _LOGGER.exception("Could not get a token from %s", self._host)
            return None, "unknown"

    # --- Manual set-up -------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the host."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            self._async_abort_entries_match({CONF_HOST: host})
            status, error = await self._check_host(host)
            if error:
                errors["base"] = error
            else:
                assert status is not None
                uid = _unique_id(status, None)
                if uid:
                    await self.async_set_unique_id(uid)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                self._host = host
                return await self.async_step_password()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_HOST): str}), user_input or {CONF_HOST: "spa.local"}
            ),
            errors=errors,
        )

    # --- Found on the network -------------------------------------------------

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """The module announced itself over mDNS."""
        host = discovery_info.host
        hostname = discovery_info.hostname.removesuffix(".").removesuffix(".local").lower()
        self._async_abort_entries_match({CONF_HOST: host})
        status, error = await self._check_host(host)
        if error:
            # Something else answering to the same mDNS name pattern, or not reachable now
            return self.async_abort(reason=error)
        assert status is not None
        await self.async_set_unique_id(_unique_id(status, hostname))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._host = host
        self.context["title_placeholders"] = {"host": hostname}
        return await self.async_step_password()

    # --- Settings password -> token -------------------------------------------

    async def async_step_password(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the settings password and swap it for a token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token, error = await self._get_token(user_input[CONF_PASSWORD])
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=self._title, data={CONF_HOST: self._host, CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="password",
            data_schema=PASSWORD_SCHEMA,
            errors=errors,
            description_placeholders={"host": self._host or ""},
        )

    # --- The module stopped accepting the token ---------------------------------

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start re-authentication."""
        self._host = entry_data[CONF_HOST]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the settings password again."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token, error = await self._get_token(user_input[CONF_PASSWORD])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=PASSWORD_SCHEMA,
            errors=errors,
            description_placeholders={"host": self._host or ""},
        )
