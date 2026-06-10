"""Sensor platform for Clever Caravan: Power."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import (
    AGG_SOLAR_ENERGY,
    AGG_SOLAR_POWER,
    DEV_SOLAR,
    DOMAIN,
    SIGNAL_NEW_ENTITY,
    VSensorDef,
)
from .entity import CcpEntity

_LOGGER = logging.getLogger(__name__)


def _ttg_text(value) -> str:
    """Format Venus TimeToGo seconds the Clever Caravan way."""
    if value is None:
        return "For Ever and Ever!"
    total = int(value)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''} {hours} hour{'s' if hours != 1 else ''}"
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


TRANSFORMS = {
    "ttg_text": _ttg_text,
    "m3_to_l": lambda v: round(float(v) * 1000, 1) if v is not None else None,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    aggregates_added = False

    @callback
    def _async_new_entity(platform: str, vdef, instance: str, extra) -> None:
        nonlocal aggregates_added
        if platform != "sensor":
            return
        entities = [CcpSensor(data, vdef, instance, f"{vdef.key}_{instance}")]
        # First solar charger seen -> create the fleet aggregates.
        if not aggregates_added and vdef.service == "solarcharger":
            aggregates_added = True
            entities.append(CcpSolarAggregate(data, AGG_SOLAR_POWER))
            entities.append(CcpSolarAggregate(data, AGG_SOLAR_ENERGY))
        async_add_entities(entities)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, SIGNAL_NEW_ENTITY.format(entry.entry_id), _async_new_entity
        )
    )


class CcpSensor(CcpEntity, SensorEntity):
    """A sensor mapped from a Venus dbus path."""

    def __init__(self, data, vdef: VSensorDef, instance: str, value_key: str) -> None:
        super().__init__(data, vdef, instance, value_key)
        if vdef.unit:
            self._attr_native_unit_of_measurement = vdef.unit
        if vdef.device_class:
            self._attr_device_class = vdef.device_class
        if vdef.state_class:
            self._attr_state_class = vdef.state_class
        if vdef.suggested_precision is not None:
            self._attr_suggested_display_precision = vdef.suggested_precision
        self._expire_unsub = None
        self._apply_value(self._hub.get(vdef.service, instance, vdef.path))

    @callback
    def _apply_value(self, value) -> None:
        vdef = self._def
        if vdef.options_map is not None:
            try:
                value = vdef.options_map.get(int(value), "Unknown")
            except (TypeError, ValueError):
                value = None
        elif vdef.transform:
            try:
                value = TRANSFORMS[vdef.transform](value)
            except (TypeError, ValueError):
                value = None
        self._attr_native_value = value
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
            self._attr_native_value = None
            self.async_write_ha_state()

        self._expire_unsub = async_call_later(self.hass, self._def.expire, _expire)

    async def async_will_remove_from_hass(self) -> None:
        if self._expire_unsub:
            self._expire_unsub()
            self._expire_unsub = None


_AGG_META = {
    AGG_SOLAR_POWER: VSensorDef(
        AGG_SOLAR_POWER, "solarcharger", "Yield/Power", "Total Solar Power",
        DEV_SOLAR, "W", "power", "measurement", "mdi:solar-power",
        suggested_precision=0,
    ),
    AGG_SOLAR_ENERGY: VSensorDef(
        AGG_SOLAR_ENERGY, "solarcharger", "Yield/User", "Total Solar Energy",
        DEV_SOLAR, "kWh", "energy", "total_increasing", "mdi:solar-power",
        suggested_precision=2,
    ),
}


class CcpSolarAggregate(CcpEntity, SensorEntity):
    """Sum of a value across every discovered solar charger."""

    def __init__(self, data, agg_key: str) -> None:
        vdef = _AGG_META[agg_key]
        super().__init__(data, vdef, "all", agg_key)
        self._attr_unique_id = f"{self._hub.portal_id}_{agg_key}"
        self._attr_native_unit_of_measurement = vdef.unit
        self._attr_device_class = vdef.device_class
        self._attr_state_class = vdef.state_class
        self._attr_suggested_display_precision = vdef.suggested_precision
        self._recompute()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Also recompute when any individual charger updates.
        from .const import SIGNAL_VALUE  # local import avoids cycle at module load

        eid = self._data.entry.entry_id
        per_charger_key = "sc_power" if self._def.key == AGG_SOLAR_POWER else "sc_energy"
        for instance in self._hub.instances_of("solarcharger"):
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass,
                    SIGNAL_VALUE.format(eid, f"{per_charger_key}_{instance}"),
                    self._handle_update,
                )
            )

    @callback
    def _handle_update(self, _value) -> None:
        self._recompute()
        self.async_write_ha_state()

    @callback
    def _apply_value(self, value) -> None:
        self._recompute()

    @callback
    def _recompute(self) -> None:
        total = 0.0
        seen = False
        for instance in self._hub.instances_of("solarcharger"):
            value = self._hub.get("solarcharger", instance, self._def.path)
            if value is None:
                continue
            try:
                total += float(value)
                seen = True
            except (TypeError, ValueError):
                continue
        self._attr_native_value = round(total, 3) if seen else None
