"""Verify the actual HA entity, config flow and failure behavior."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.exceptions import HomeAssistantError

from custom_components.habitat_tablet.api import CannotConnect, CommandFailed, InvalidAuth
from custom_components.habitat_tablet.const import DOMAIN


async def test_config_flow_and_duplicate(hass, snapshot):
    data = {"url": "http://192.168.1.50:8765", "token": "pairing-key"}
    with patch("custom_components.habitat_tablet.config_flow.TabletApi.get_screen", return_value=snapshot), patch("custom_components.habitat_tablet.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        assert result["type"] == "form"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
        assert result["type"] == "create_entry"
        assert result["result"].unique_id == snapshot["device_id"]
        await hass.async_block_till_done()
        duplicate = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data=data)
        assert duplicate["type"] == "abort"
        assert duplicate["reason"] == "already_configured"


@pytest.mark.parametrize("error,reason", [(InvalidAuth(), "invalid_auth"), (CannotConnect(), "cannot_connect")])
async def test_config_errors(hass, error, reason):
    with patch("custom_components.habitat_tablet.config_flow.TabletApi.get_screen", side_effect=error):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER}, data={"url": "192.168.1.50", "token": "key"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": reason}


async def test_one_switch_real_state_errors_and_offline(hass, snapshot):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=snapshot["device_id"], title="Living tablet", data={"url": "http://192.168.1.50:8765", "token": "key"})
    entry.add_to_hass(hass)
    async def set_state(on):
        return {**snapshot, "screen_on": on}

    with patch("custom_components.habitat_tablet.api.TabletApi.get_screen", return_value=snapshot), patch("custom_components.habitat_tablet.api.TabletApi.set_screen", side_effect=set_state) as setter:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        switches = hass.states.async_all("switch")
        assert len(switches) == 1
        entity_id = switches[0].entity_id
        assert hass.states.get(entity_id).state == "on"
        await hass.services.async_call("switch", "turn_off", {"entity_id": entity_id}, blocking=True)
        assert hass.states.get(entity_id).state == "off"
        setter.side_effect = CommandFailed("permission required")
        with pytest.raises(HomeAssistantError, match="permission required"):
            await hass.services.async_call("switch", "turn_on", {"entity_id": entity_id}, blocking=True)
        assert hass.states.get(entity_id).state == "off"
        setter.side_effect = set_state
        await hass.services.async_call("switch", "turn_on", {"entity_id": entity_id}, blocking=True)
        assert hass.states.get(entity_id).state == "on"
        setter.side_effect = CannotConnect("offline")
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call("switch", "turn_off", {"entity_id": entity_id}, blocking=True)
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)
