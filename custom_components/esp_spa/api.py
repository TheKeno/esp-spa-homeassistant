"""Small client for the ESP Spa module's local JSON API (see docs/API.md)."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

import aiohttp

from .const import CLIENT_NAME

TIMEOUT = aiohttp.ClientTimeout(total=10)


class EspSpaError(Exception):
    """Base error."""


class CannotConnect(EspSpaError):
    """The module did not answer."""


class InvalidAuth(EspSpaError):
    """Password or token rejected (401)."""


class NotEspSpa(EspSpaError):
    """The host answered, but it is not an ESP Spa module."""


class CommandFailed(EspSpaError):
    """The module answered a command with an error."""


class EspSpaClient:
    """Talks to one module."""

    def __init__(
        self, session: aiohttp.ClientSession, host: str, token: str | None = None
    ) -> None:
        self._session = session
        self.host = host
        self.token = token

    @property
    def base_url(self) -> str:
        host = self.host
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"  # IPv6 literal
        return f"http://{host}"

    def _headers(self, password: str | None = None) -> dict[str, str]:
        headers = {"X-Spa-Client": CLIENT_NAME}
        if password is not None:
            # Basic auth; the module ignores the user name
            basic = base64.b64encode(f"{CLIENT_NAME}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        headers = self._headers(password)
        try:
            async with self._session.request(
                method,
                self.base_url + path,
                params=params,
                headers=headers,
                timeout=TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    raise InvalidAuth
                try:
                    data = await resp.json(content_type=None)
                except (ValueError, aiohttp.ContentTypeError) as err:
                    # The module always answers JSON; anything else is another device
                    raise NotEspSpa from err
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise CannotConnect(str(err) or type(err).__name__) from err
        if not isinstance(data, dict):
            raise NotEspSpa
        if resp.status >= 400 or data.get("ok") is False:
            raise CommandFailed(str(data.get("error") or f"HTTP {resp.status}"))
        return data

    async def get_status(self) -> dict[str, Any]:
        """Everything the module knows about the spa."""
        data = await self._request("GET", "/api/status")
        if "cfg" not in data or "pumps" not in data or "age" not in data:
            raise NotEspSpa
        return data

    async def get_token(self, password: str) -> str:
        """Use the settings password once to get a token (replaces any earlier token)."""
        data = await self._request("POST", "/api/token", password=password)
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise CommandFailed("No token in the answer")
        return token

    async def check_auth(self) -> None:
        """Raise InvalidAuth if the stored token is no longer accepted."""
        await self._request("GET", "/api/auth")

    async def toggle(self, item: str) -> None:
        """Press a panel button."""
        await self._request("POST", "/api/toggle", {"item": item})

    async def set_temperature(self, value: float) -> None:
        """Set temperature, in the spa's unit."""
        await self._request("POST", "/api/temp", {"value": f"{value:g}"})

    async def set_clock(self, hour: int, minute: int) -> None:
        """Set the spa clock (needs the token)."""
        await self._request("POST", "/api/clock", {"time": str(hour * 60 + minute)})
