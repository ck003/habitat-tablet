"""Low-frequency screen state polling."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, CommandFailed, InvalidAuth, TabletApi
from .const import CONF_TOKEN, CONF_URL, DOMAIN

LOGGER = logging.getLogger(__name__)


class ScreenCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One coordinator and one screen switch per tablet."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.api = TabletApi(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN])
        self.device_id = entry.unique_id
        super().__init__(
            hass, LOGGER, config_entry=entry, name=DOMAIN,
            update_interval=timedelta(seconds=30), always_update=False,
        )

    def _check_identity(self, data: dict[str, Any]) -> None:
        if data["device_id"] != self.device_id:
            raise CannotConnect("A different tablet is using this address; reconfigure the integration")

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.api.get_screen()
            self._check_identity(data)
            return data
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("Pairing key rejected") from err
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_screen(self, on: bool) -> None:
        try:
            data = await self.api.set_screen(on)
            self._check_identity(data)
        except InvalidAuth as err:
            self.async_set_update_error(ConfigEntryAuthFailed("Pairing key rejected"))
            raise HomeAssistantError("Pairing key rejected; reconfigure Habitat Tablet") from err
        except CannotConnect as err:
            self.async_set_update_error(UpdateFailed(str(err)))
            raise HomeAssistantError(str(err)) from err
        except CommandFailed as err:
            # Permission failure must not optimistically flip the switch.
            raise HomeAssistantError(str(err)) from err
        self.async_set_updated_data(data)
