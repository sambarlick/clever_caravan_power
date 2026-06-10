"""Base entity for Clever Caravan: Power."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity, EntityCategory

from .const import DEV_GX, DEVICE_NAMES, DOMAIN, MANUFACTURER, SIGNAL_CONNECTION, SIGNAL_VALUE


class CcpEntity(Entity):
    """Common behaviour: device grouping, availability, value updates."""

    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, data, vdef, instance: str, value_key: str) -> None:
        self._data = data
        self._hub = data.hub
        self._def = vdef
        self._instance = instance
        self._value_key = value_key
        portal = self._hub.portal_id
        self._attr_unique_id = f"{portal}_{vdef.key}_{instance}"
        self._attr_name = vdef.name.format(instance=instance)
        if getattr(vdef, "icon", None):
            self._attr_icon = vdef.icon
        if getattr(vdef, "entity_category", None) == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if getattr(vdef, "enabled_default", True) is False:
            self._attr_entity_registry_enabled_default = False

        device = getattr(vdef, "device", DEV_GX)
        dev_id = f"{portal}_{device}"
        info = DeviceInfo(
            identifiers={(DOMAIN, dev_id)},
            name=DEVICE_NAMES[device],
            manufacturer=MANUFACTURER,
            model="Cerbo GX",
        )
        if device != DEV_GX:
            info["via_device"] = (DOMAIN, f"{portal}_{DEV_GX}")
        self._attr_device_info = info

    @property
    def available(self) -> bool:
        return self._hub.connected and self._hub.heartbeat_ok

    async def async_added_to_hass(self) -> None:
        eid = self._data.entry.entry_id
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_VALUE.format(eid, self._value_key), self._handle_update
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONNECTION.format(eid), self._handle_connection
            )
        )

    @callback
    def _handle_connection(self, _connected: bool) -> None:
        self.async_write_ha_state()

    @callback
    def _handle_update(self, value) -> None:
        self._apply_value(value)
        self.async_write_ha_state()

    @callback
    def _apply_value(self, value) -> None:
        """Override in platform classes."""
        raise NotImplementedError
