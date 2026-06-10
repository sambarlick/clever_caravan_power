"""Number platform for Clever Caravan: Power (input current limit)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CURRENT_LIMIT_MAX,
    CONF_CURRENT_LIMIT_MIN,
    DEFAULT_CURRENT_LIMIT_MAX,
    DEFAULT_CURRENT_LIMIT_MIN,
    DOMAIN,
    SIGNAL_NEW_ENTITY,
)
from .entity import CcpEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]

    @callback
    def _async_new_entity(platform: str, vdef, instance: str, extra) -> None:
        if platform != "number":
            return
        async_add_entities([CcpNumber(data, vdef, instance)])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_NEW_ENTITY.format(entry.entry_id), _async_new_entity
        )
    )


class CcpNumber(CcpEntity, NumberEntity):
    """A writable Venus value exposed as a number."""

    _attr_mode = NumberMode.BOX

    def __init__(self, data, vdef, instance: str) -> None:
        super().__init__(data, vdef, instance, f"{vdef.key}_{instance}")
        options = data.entry.options
        self._attr_native_min_value = options.get(
            CONF_CURRENT_LIMIT_MIN, DEFAULT_CURRENT_LIMIT_MIN
        )
        self._attr_native_max_value = options.get(
            CONF_CURRENT_LIMIT_MAX, DEFAULT_CURRENT_LIMIT_MAX
        )
        self._attr_native_step = vdef.step
        if vdef.unit:
            self._attr_native_unit_of_measurement = vdef.unit
        self._apply_value(self._hub.get(vdef.service, instance, vdef.path))

    @callback
    def _apply_value(self, value) -> None:
        try:
            self._attr_native_value = float(value)
        except (TypeError, ValueError):
            self._attr_native_value = None

    async def async_set_native_value(self, value: float) -> None:
        self._hub.set_value(self._def.service, self._instance, self._def.path, value)
