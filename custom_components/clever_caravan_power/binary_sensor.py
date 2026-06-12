"""Binary sensor platform for Clever Caravan: Power."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, VBinarySensorDef
from .entity import CcpEntity, async_setup_discovery


def _evaluate(predicate: str, value) -> bool | None:
    """Evaluate "gt:<n>" / "eq:<n>" predicates against a Venus value."""
    if value is None:
        return None
    op, _, threshold = predicate.partition(":")
    try:
        number = float(value)
        limit = float(threshold)
    except (TypeError, ValueError):
        return None
    if op == "gt":
        return number > limit
    if op == "eq":
        return number == limit
    return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]

    @callback
    def _factory(vdef, instance: str, extra) -> None:
        async_add_entities([CcpBinarySensor(data, vdef, instance)])

    async_setup_discovery(hass, entry, data, "binary_sensor", _factory)


class CcpBinarySensor(CcpEntity, BinarySensorEntity):
    """A boolean condition derived from a Venus dbus value."""

    def __init__(self, data, vdef: VBinarySensorDef, instance: str) -> None:
        super().__init__(data, vdef, instance, f"{vdef.key}_{instance}")
        if vdef.device_class:
            self._attr_device_class = vdef.device_class
        self._expire_unsub = None
        self._apply_value(self._hub.get(vdef.service, instance, vdef.path))

    @callback
    def _apply_value(self, value) -> None:
        if value is None and self._def.none_as_zero:
            value = 0
        self._attr_is_on = _evaluate(self._def.predicate, value)
        self._schedule_expiry()

    @callback
    def _schedule_expiry(self) -> None:
        if not self._def.expire or not self.hass:
            return
        if self._expire_unsub:
            self._expire_unsub()

        @callback
        def _expire(_now) -> None:
            self._expire_unsub = None
            self._attr_is_on = None
            self.async_write_ha_state()

        self._expire_unsub = async_call_later(self.hass, self._def.expire, _expire)

    async def async_will_remove_from_hass(self) -> None:
        if self._expire_unsub:
            self._expire_unsub()
            self._expire_unsub = None
