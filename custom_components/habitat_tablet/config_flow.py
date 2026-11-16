"""Pair using the address and secret copied from the tablet."""

from typing import Any

import probatio

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, TabletApi, normalize_url
from .const import CONF_TOKEN, CONF_URL, DOMAIN


class HabitatTabletConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure one tablet; its stable ID prevents duplicate entities."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._step("user", user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._step("reconfigure", user_input)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._step("reauth_confirm", user_input)

    async def _step(self, step_id: str, user_input: dict[str, Any] | None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
                token = user_input[CONF_TOKEN].strip()
                if not token:
                    raise ValueError
                data = {CONF_URL: url, CONF_TOKEN: token}
                api = TabletApi(async_get_clientsession(self.hass), url, token)
                snapshot = await api.get_screen()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_address"
            else:
                if step_id != "user":
                    entry = self._get_reauth_entry() if step_id == "reauth_confirm" else self._get_reconfigure_entry()
                    if entry.unique_id != snapshot["device_id"]:
                        return self.async_abort(reason="wrong_device")
                    return self.async_update_reload_and_abort(entry, data_updates=data)
                await self.async_set_unique_id(snapshot["device_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=snapshot["name"], data=data)
        return self.async_show_form(
            step_id=step_id,
            data_schema=probatio.Schema({
                probatio.Required(CONF_URL): str,
                probatio.Required(probatio.Secret(CONF_TOKEN)): str,
            }),
            errors=errors,
        )
