"""Button platform for Clever Caravan: Power (Cerbo GX reboot)."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEV_GX, DEVICE_NAMES, DOMAIN, MANUFACTURER


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CcpRebootButton(data)])


class CcpRebootButton(ButtonEntity):
    """Reboots the GX device over MQTT (Venus OS 3.x+)."""

    _attr_should_poll = False
    _attr_name = "Reboot Cerbo GX"
    _attr_icon = "mdi:restart"
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(self, data) -> None:
        self._hub = data.hub
        portal = self._hub.portal_id
        self._attr_unique_id = f"{portal}_reboot"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{portal}_{DEV_GX}")},
            name=DEVICE_NAMES[DEV_GX],
            manufacturer=MANUFACTURER,
            model="Cerbo GX",
        )

    @property
    def available(self) -> bool:
        return self._hub.connected

    async def async_press(self) -> None:
        self._hub.set_value("platform", "0", "Device/Reboot", 1)
