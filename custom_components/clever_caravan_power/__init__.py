"""Clever Caravan: Power — Victron GX integration over MQTT."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    BINARY_SENSOR_DEFS,
    CONF_PORTAL_ID,
    CONF_USE_SSL,
    DOMAIN,
    KEEPALIVE_INTERVAL,
    NUMBER_DEFS,
    SELECT_DEFS,
    SENSOR_DEFS,
    SIGNAL_CONNECTION,
    SIGNAL_NEW_ENTITY,
    SIGNAL_VALUE,
    SWITCH_DEFS,
)
from .hub import VenusHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]

# Index definitions by (service, path) for O(1) lookup on every MQTT message.
_DEFS_BY_TOPIC: dict[tuple[str, str], list] = {}
for _def in (*SENSOR_DEFS, *BINARY_SENSOR_DEFS, *SELECT_DEFS, *NUMBER_DEFS):
    _DEFS_BY_TOPIC.setdefault((_def.service, _def.path), []).append(_def)

_PLATFORM_OF = {}
for _d in SENSOR_DEFS:
    _PLATFORM_OF[_d.key] = "sensor"
for _d in BINARY_SENSOR_DEFS:
    _PLATFORM_OF[_d.key] = "binary_sensor"
for _d in SELECT_DEFS:
    _PLATFORM_OF[_d.key] = "select"
for _d in NUMBER_DEFS:
    _PLATFORM_OF[_d.key] = "number"


class CcpData:
    """Runtime data shared with the entity platforms."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, hub: VenusHub) -> None:
        self.hass = hass
        self.entry = entry
        self.hub = hub
        # discovered[(def_key, instance)] = (platform, vdef, instance, extra)
        # Persisted so platforms can REPLAY announcements that arrived before
        # they finished setting up — discovery is not fire-and-forget.
        self.discovered: dict[tuple[str, str], tuple] = {}
        # Claimed (created) entities, guarded so replay + live signals can
        # never double-add: claimed by (platform, def_key, instance).
        self._claimed: set[tuple[str, str, str]] = set()
        self._unsub_keepalive = None

    def claim(self, platform: str, def_key: str, instance: str) -> bool:
        """Return True exactly once per entity — the caller may create it."""
        key = (platform, def_key, instance)
        if key in self._claimed:
            return False
        self._claimed.add(key)
        return True

    # Called from the paho network thread — hop onto the event loop.
    def thread_on_value(self, service: str, instance: str, path: str, value) -> None:
        self.hass.loop.call_soon_threadsafe(self._handle_value, service, instance, path, value)

    def thread_on_connection(self, connected: bool) -> None:
        self.hass.loop.call_soon_threadsafe(
            async_dispatcher_send,
            self.hass,
            SIGNAL_CONNECTION.format(self.entry.entry_id),
            connected,
        )

    @callback
    def _handle_value(self, service: str, instance: str, path: str, value) -> None:
        eid = self.entry.entry_id

        # Relays are dynamic (Relay/<n>/State) — handled as a pattern.
        if service == "system" and path.startswith("Relay/") and path.endswith("/State"):
            relay = path.split("/")[1]
            disc_key = ("relay", relay)
            if disc_key not in self.discovered:
                announcement = ("switch", SWITCH_DEFS[0], instance, {"relay": relay})
                self.discovered[disc_key] = announcement
                async_dispatcher_send(self.hass, SIGNAL_NEW_ENTITY.format(eid), *announcement)
            async_dispatcher_send(
                self.hass, SIGNAL_VALUE.format(eid, f"relay_{relay}"), value
            )
            return

        defs = _DEFS_BY_TOPIC.get((service, path))
        if not defs:
            return
        # Any solar yield update also feeds the Total Solar aggregates.
        if service == "solarcharger" and path in ("Yield/Power", "Yield/User"):
            async_dispatcher_send(self.hass, SIGNAL_VALUE.format(eid, "sc_aggregate"), value)
        for vdef in defs:
            disc_key = (vdef.key, instance)
            if disc_key not in self.discovered:
                announcement = (_PLATFORM_OF[vdef.key], vdef, instance, None)
                self.discovered[disc_key] = announcement
                async_dispatcher_send(self.hass, SIGNAL_NEW_ENTITY.format(eid), *announcement)
            async_dispatcher_send(
                self.hass, SIGNAL_VALUE.format(eid, f"{vdef.key}_{instance}"), value
            )

    async def async_start_keepalive(self) -> None:
        @callback
        def _keepalive(_now) -> None:
            self.hub.publish_keepalive()

        self._unsub_keepalive = async_track_time_interval(
            self.hass, _keepalive, timedelta(seconds=KEEPALIVE_INTERVAL)
        )

    def stop(self) -> None:
        if self._unsub_keepalive:
            self._unsub_keepalive()
        self.hub.stop()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = VenusHub(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, 1883),
        username=entry.data.get(CONF_USERNAME) or None,
        password=entry.data.get(CONF_PASSWORD) or None,
        use_ssl=entry.data.get(CONF_USE_SSL, False),
        portal_id=entry.data.get(CONF_PORTAL_ID) or None,
    )
    data = CcpData(hass, entry, hub)
    hub.on_value = data.thread_on_value
    hub.on_connection = data.thread_on_connection

    await hass.async_add_executor_job(hub.start)
    portal = await hass.async_add_executor_job(hub.wait_for_portal, 15.0)
    if portal is None:
        data.stop()
        raise ConfigEntryNotReady(f"No Venus portal detected at {entry.data[CONF_HOST]}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data

    # Entity platforms subscribe to discovery signals first, then we let the
    # retained/full-publish messages flow into discovery.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await data.async_start_keepalive()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data: CcpData = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(data.stop)
    return unload_ok
