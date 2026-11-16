"""Only the screen on/off switch is exposed."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ScreenCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([TabletScreen(entry.runtime_data)])


class TabletScreen(CoordinatorEntity[ScreenCoordinator], SwitchEntity):
    """Screen state is confirmed by the tablet, never assumed."""

    _attr_has_entity_name = True
    _attr_translation_key = "screen"
    _attr_icon = "mdi:tablet"

    def __init__(self, coordinator: ScreenCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_screen"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name=coordinator.data["name"],
            model=coordinator.data["model"],
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator.data["screen_on"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_screen(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_screen(False)
