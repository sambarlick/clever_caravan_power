"""Switch platform for Clever Caravan: Power (Cerbo GX relays)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RELAY_NAMES, SIGNAL_NEW_ENTITY
from .entity import CcpEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]

    @callback
    def _async_new_entity(platform: str, vdef, instance: str, extra) -> None:
        if platform != "switch":
            return
        async_add_entities([CcpRelaySwitch(data, vdef, instance, extra["relay"])])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_NEW_ENTITY.format(entry.entry_id), _async_new_entity
        )
    )


class CcpRelaySwitch(CcpEntity, SwitchEntity):
    """A Cerbo GX relay."""

    def __init__(self, data, vdef, instance: str, relay: str) -> None:
        super().__init__(data, vdef, instance, f"relay_{relay}")
        self._relay = relay
        relay_name = RELAY_NAMES.get(int(relay), f"Relay {relay}")
        self._attr_name = relay_name
        self._attr_unique_id = f"{self._hub.portal_id}_relay_{relay}"
        self._path = f"Relay/{relay}/State"
        self._apply_value(self._hub.get("system", instance, self._path))

    @callback
    def _apply_value(self, value) -> None:
        try:
            self._attr_is_on = int(value) == 1
        except (TypeError, ValueError):
            self._attr_is_on = None

    async def async_turn_on(self, **kwargs) -> None:
        self._hub.set_value("system", self._instance, self._path, 1)

    async def async_turn_off(self, **kwargs) -> None:
        self._hub.set_value("system", self._instance, self._path, 0)
