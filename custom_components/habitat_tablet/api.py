"""Authenticated local screen API; never log pairing keys or request headers."""

import asyncio
import json
from typing import Any
from uuid import UUID

import aiohttp
from yarl import URL

from .const import DEFAULT_PORT


class CannotConnect(Exception):
    """The tablet did not return a valid screen response."""


class InvalidAuth(Exception):
    """The pairing key was rejected."""


class CommandFailed(Exception):
    """The tablet could not execute the requested screen operation."""


def normalize_url(value: str) -> str:
    """Accept a tablet IP or the address copied from Habitat settings."""
    value = value.strip()
    if "://" not in value:
        value = f"http://{value}"
        url = URL(value)
        if url.explicit_port is None:
            value = str(url.with_port(DEFAULT_PORT))
    url = URL(value)
    if (
        url.scheme not in ("http", "https")
        or not url.host
        or url.user is not None
        or url.query_string
        or url.fragment
        or url.path not in ("", "/")
    ):
        raise ValueError("Invalid tablet address")
    return str(url).rstrip("/")


class TabletApi:
    """Only two operations: read the screen and set its on/off state."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self._session = session
        self._url = normalize_url(url)
        self._token = token.strip()

    async def get_screen(self) -> dict[str, Any]:
        return await self._request("GET")

    async def set_screen(self, on: bool) -> dict[str, Any]:
        result = await self._request("POST", {"screen_on": on})
        if result["screen_on"] is not on:
            raise CommandFailed("Tablet did not reach the requested screen state")
        return result

    async def _request(self, method: str, body: dict | None = None) -> dict[str, Any]:
        try:
            async with self._session.request(
                method,
                f"{self._url}/api/screen",
                headers={"Authorization": f"Bearer {self._token}"},
                json=body,
                timeout=aiohttp.ClientTimeout(total=8),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise InvalidAuth
                raw = bytearray()
                while chunk := await response.content.read(min(4096, 8193 - len(raw))):
                    raw.extend(chunk)
                    if len(raw) > 8192:
                        raise CannotConnect("Response too large")
                payload = json.loads(raw)
                if response.status == 409:
                    error = payload.get("error", "Screen operation failed") if isinstance(payload, dict) else "Screen operation failed"
                    raise CommandFailed(str(error)[:200])
                if response.status != 200:
                    raise CannotConnect(f"Tablet returned HTTP {response.status}")
                if (
                    not isinstance(payload, dict)
                    or type(payload.get("protocol")) is not int
                    or payload["protocol"] != 1
                    or type(payload.get("screen_on")) is not bool
                    or not isinstance(payload.get("device_id"), str)
                ):
                    raise CannotConnect("Invalid screen response")
                UUID(payload["device_id"])
                for field in ("name", "model"):
                    if not isinstance(payload.get(field), str) or not 1 <= len(payload[field]) <= 80:
                        raise CannotConnect("Invalid device identity")
                return payload
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, UnicodeError) as err:
            raise CannotConnect("Unable to read tablet screen") from err
