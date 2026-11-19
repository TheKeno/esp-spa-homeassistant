"""Polls the module and sends commands."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, CommandFailed, EspSpaClient, EspSpaError, InvalidAuth, NotEspSpa
from .const import (
    API_VERSION,
    DOMAIN,
    FAULT_NONE,
    FAULT_UNKNOWN,
    FAULTS,
    MAX_STATUS_AGE_MS,
    PRESS_DELAY,
    REFRESH_DELAY,
    REMINDER_FAULT,
    REMINDER_NONE,
    REMINDER_OTHER,
    REMINDERS,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type EspSpaConfigEntry = ConfigEntry[EspSpaCoordinator]


class EspSpaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Keeps the latest /api/status."""

    config_entry: EspSpaConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: EspSpaConfigEntry, client: EspSpaClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self._api_warned: Any = None
        self._lock = asyncio.Lock()

    async def _async_setup(self) -> None:
        """Check the token once at start-up."""
        try:
            await self.client.check_auth()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("The module no longer accepts the token") from err
        except EspSpaError as err:
            raise UpdateFailed(f"Cannot reach the spa module: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.get_status()
        except NotEspSpa as err:
            raise UpdateFailed("The host no longer answers like an ESP Spa module") from err
        except EspSpaError as err:
            raise UpdateFailed(f"Cannot reach the spa module: {err}") from err
        self._check_api_version(data.get("api"))
        return data

    def _check_api_version(self, version: Any) -> None:
        if version == self._api_warned:
            return
        self._api_warned = version
        issue_id = f"api_version_{self.config_entry.entry_id}"
        if version == API_VERSION:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return
        _LOGGER.warning(
            "The spa module at %s uses API version %s, this integration expects %s. "
            "Update the integration or the module firmware",
            self.client.host,
            version,
            API_VERSION,
        )
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="api_version",
            translation_placeholders={
                "found": str(version) if version is not None else "none",
                "expected": str(API_VERSION),
                "host": self.client.host,
            },
        )

    # --- Reading the status ------------------------------------------------

    @property
    def live(self) -> bool:
        """The module hears the spa."""
        if not self.data:
            return False
        age = self.data.get("age", -1)
        return isinstance(age, int) and 0 <= age < MAX_STATUS_AGE_MS

    @property
    def ready(self) -> bool:
        """The module hears the spa and may send commands."""
        return self.live and bool(self.data.get("bus", {}).get("channel"))

    @property
    def reminder(self) -> str:
        """Key of the reminder shown on the panel."""
        code = self.data.get("reminder", 0) if self.live else 0
        if not code or code == REMINDER_FAULT:
            return REMINDER_NONE
        return REMINDERS.get(code, REMINDER_OTHER)

    @property
    def fault(self) -> str:
        """Key of the error the spa shows now."""
        if not self.live or not self.data.get("fault"):
            return FAULT_NONE
        log = self.data.get("faultLog", {})
        if log.get("valid") and log.get("entries"):
            return FAULTS.get(log.get("code"), FAULT_UNKNOWN)
        return FAULT_UNKNOWN

    @property
    def fault_code(self) -> int | None:
        """Code of the most recent logged error, if the log has one."""
        log = self.data.get("faultLog", {}) if self.data else {}
        if log.get("valid") and log.get("entries"):
            return log.get("code")
        return None

    def equipment(self) -> dict[str, int] | None:
        """What the spa has: item -> number of speeds (1 for on/off items), None if unknown."""
        cfg = self.data.get("cfg", {}) if self.data else {}
        if not cfg.get("valid"):
            return None
        out: dict[str, int] = {}
        for i, speeds in enumerate(cfg.get("pumps", [])):
            if speeds:
                out[f"pump{i + 1}"] = speeds
        for i, has in enumerate(cfg.get("lights", [])):
            if has:
                out[f"light{i + 1}"] = 1
        if cfg.get("blower"):
            out["blower"] = cfg["blower"]
        if cfg.get("mister"):
            out["mister"] = 1
        for i, has in enumerate(cfg.get("aux", [])):
            if has:
                out[f"aux{i + 1}"] = 1
        return out

    # --- Commands ------------------------------------------------------------

    async def async_command(self, call: Callable[[], Awaitable[None]]) -> None:
        """Send one command, then poll again soon."""
        await self.async_commands([call])

    async def async_commands(self, calls: list[Callable[[], Awaitable[None]]]) -> None:
        """Send several commands with a pause between them, then poll again soon."""
        async with self._lock:
            for i, call in enumerate(calls):
                if i:
                    await asyncio.sleep(PRESS_DELAY)
                try:
                    await call()
                except InvalidAuth as err:
                    self.config_entry.async_start_reauth(self.hass)
                    raise HomeAssistantError(
                        "The spa module rejected the token; re-authenticate the integration"
                    ) from err
                except CommandFailed as err:
                    raise HomeAssistantError(f"The spa module refused: {err}") from err
                except CannotConnect as err:
                    raise HomeAssistantError(f"Cannot reach the spa module: {err}") from err
                except EspSpaError as err:
                    raise HomeAssistantError(str(err)) from err
        async_call_later(self.hass, REFRESH_DELAY, self._refresh_later)

    async def _refresh_later(self, _now: Any) -> None:
        await self.async_request_refresh()

    async def async_press(self, item: str, times: int = 1) -> None:
        """Press a panel button one or more times."""
        await self.async_commands([lambda: self.client.toggle(item)] * times)
