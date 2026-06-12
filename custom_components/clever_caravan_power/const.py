"""Constants and entity definitions for Clever Caravan: Power."""
from __future__ import annotations

from dataclasses import dataclass, field

DOMAIN = "clever_caravan_power"
MANUFACTURER = "Victron Energy"

CONF_PORTAL_ID = "portal_id"
CONF_USE_SSL = "use_ssl"
CONF_CURRENT_LIMIT_MIN = "current_limit_min"
CONF_CURRENT_LIMIT_MAX = "current_limit_max"
CONF_SSH_KEY = "ssh_key_path"
CONF_RELAY_NAME = "relay_{}_name"  # .format(relay_index)
DEFAULT_SSH_KEY = "/config/.ssh/id_rsa"

DEFAULT_PORT = 1883
DEFAULT_HOST = "venus.local"
DEFAULT_CURRENT_LIMIT_MIN = 3.0
DEFAULT_CURRENT_LIMIT_MAX = 32.0

KEEPALIVE_INTERVAL = 30  # seconds — Venus OS drops publishing without this
HEARTBEAT_TIMEOUT = 90  # seconds without heartbeat -> unavailable

SIGNAL_NEW_ENTITY = "ccp_new_entity_{}"  # entry_id
SIGNAL_VALUE = "ccp_value_{}_{}"  # entry_id, datapoint key
SIGNAL_CONNECTION = "ccp_connection_{}"  # entry_id

# ---------------------------------------------------------------------------
# Device grouping (mirrors Sam's YAML layout)
# ---------------------------------------------------------------------------
DEV_GX = "gx"
DEV_BATTERY = "battery"
DEV_SOLAR = "solar"
DEV_ALTERNATOR = "alternator"
DEV_TANKS = "tanks"

DEVICE_NAMES = {
    DEV_GX: "Cerbo GX",
    DEV_BATTERY: "Cerbo GX Batteries",
    DEV_SOLAR: "Cerbo GX Solar",
    DEV_ALTERNATOR: "Cerbo GX Alternator",
    DEV_TANKS: "Cerbo GX Tanks",
}

# ---------------------------------------------------------------------------
# Value maps
# ---------------------------------------------------------------------------
VEBUS_STATE_MAP = {
    0: "Off", 1: "Low Power", 2: "Fault", 3: "Bulk", 4: "Absorption",
    5: "Float", 6: "Storage", 7: "Equalize", 8: "Passthrough", 9: "Inverting",
    10: "Power Assist", 11: "Power Supply", 244: "Sustain", 252: "External Control",
}

ALARM_MAP = {0: "No Alarm", 1: "Warning", 2: "Alarm"}

FLUID_TYPE_MAP = {
    0: "Fuel", 1: "Fresh Water", 2: "Waste Water", 3: "Live Well",
    4: "Oil", 5: "Black Water", 6: "Gasoline", 7: "Diesel",
    8: "LPG", 9: "LNG", 10: "Hydraulic Oil", 11: "Raw Water",
}

INVERTER_MODE_MAP = {1: "Charger Only", 2: "Inverter Only", 3: "On", 4: "Off"}

RELAY_NAMES = {0: "Relay 1", 1: "Relay 2"}

BATT_STATE_MAP = {0: "Idle", 1: "Charging", 2: "Discharging"}
GPS_FIX_MAP = {0: "No Fix", 1: "Fix"}


# ---------------------------------------------------------------------------
# Entity definitions
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VSensorDef:
    """A Venus OS dbus path mapped to an HA sensor."""

    key: str
    service: str
    path: str
    name: str
    device: str = DEV_GX
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    icon: str | None = None
    transform: str | None = None
    options_map: dict | None = field(default=None, hash=False)
    expire: int | None = None
    entity_category: str | None = None
    enabled_default: bool = True
    suggested_precision: int | None = None
    none_as_zero: bool = False
    custom_name: str | None = None


SENSOR_DEFS: tuple[VSensorDef, ...] = (
    # ------------------------------------------------------------------ system
    VSensorDef("dc_consumption", "system", "Dc/System/Power", "DC Consumption",
               DEV_GX, "W", "power", "measurement", "mdi:lightning-bolt", suggested_precision=0),
    VSensorDef("ac_consumption", "system", "Ac/Consumption/L1/Power", "AC Consumption",
               DEV_GX, "W", "power", "measurement", suggested_precision=0, none_as_zero=True),
    VSensorDef("shore_power", "system", "Ac/Grid/L1/Power", "Shore Power",
               DEV_GX, "W", "power", "measurement", "mdi:power-socket-au", suggested_precision=0, none_as_zero=True),
    VSensorDef("battery_soc", "system", "Dc/Battery/Soc", "Battery SoC",
               DEV_BATTERY, "%", "battery", "measurement", suggested_precision=0),
    VSensorDef("battery_voltage", "system", "Dc/Battery/Voltage", "Battery Voltage",
               DEV_BATTERY, "V", "voltage", "measurement", "mdi:flash-triangle", suggested_precision=1),
    VSensorDef("battery_current", "system", "Dc/Battery/Current", "Battery Current",
               DEV_BATTERY, "A", "current", "measurement", "mdi:current-dc", suggested_precision=1),
    VSensorDef("battery_power", "system", "Dc/Battery/Power", "Battery Power",
               DEV_BATTERY, "W", "power", "measurement", "mdi:sine-wave", suggested_precision=0),
    VSensorDef("battery_state", "system", "Dc/Battery/State", "Battery State",
               DEV_BATTERY, icon="mdi:battery-sync", options_map=BATT_STATE_MAP),
    VSensorDef("battery_temperature", "system", "Dc/Battery/Temperature", "Battery Temperature",
               DEV_BATTERY, "°C", "temperature", "measurement"),
    VSensorDef("battery_ttg", "system", "Dc/Battery/TimeToGo", "Battery Time to Go",
               DEV_BATTERY, "s", "duration", None, "mdi:timer", enabled_default=False),
    VSensorDef("battery_ttg_text", "system", "Dc/Battery/TimeToGo", "Time to Go",
               DEV_BATTERY, icon="mdi:timer", transform="ttg_text"),
    VSensorDef("pv_power", "system", "Dc/Pv/Power", "Solar Power",
               DEV_SOLAR, "W", "power", "measurement", "mdi:solar-power", suggested_precision=0),
    VSensorDef("pv_current", "system", "Dc/Pv/Current", "Solar Current",
               DEV_SOLAR, "A", "current", "measurement", "mdi:current-dc", suggested_precision=0),

    # ------------------------------------------------------------- temperature & digital inputs
    VSensorDef("temp", "temperature", "Temperature", "Temperature {instance}",
               DEV_GX, "°C", "temperature", "measurement", custom_name="{custom} Temperature"),
    VSensorDef("temp_humidity", "temperature", "Humidity", "Humidity {instance}",
               DEV_GX, "%", "humidity", "measurement", enabled_default=False, custom_name="{custom} Humidity"),
    VSensorDef("temp_pressure", "temperature", "Pressure", "Pressure {instance}",
               DEV_GX, "hPa", "atmospheric_pressure", "measurement", enabled_default=False, custom_name="{custom} Pressure"),
    VSensorDef("temp_battery", "temperature", "BatteryVoltage", "Sensor {instance} Battery",
               DEV_GX, "V", "voltage", "measurement", entity_category="diagnostic", enabled_default=False, custom_name="{custom} Battery"),
    VSensorDef("digital_input", "digitalinput", "State", "Digital Input {instance}",
               DEV_GX, icon="mdi:import", entity_category="diagnostic", enabled_default=False, custom_name="{custom} State"),

    # ------------------------------------------------------------------- vebus
    VSensorDef("inverter_state", "vebus", "State", "Inverter State",
               DEV_GX, icon="mdi:lightning-bolt", options_map=VEBUS_STATE_MAP),
    VSensorDef("inverter_alarm_overload", "vebus", "Alarms/Overload", "Inverter Overload Alarm",
               DEV_GX, icon="mdi:alert", options_map=ALARM_MAP),
    VSensorDef("inverter_alarm_temp", "vebus", "Alarms/HighTemperature", "Inverter High Temperature Alarm",
               DEV_GX, icon="mdi:alert", options_map=ALARM_MAP, enabled_default=False),
    VSensorDef("inverter_alarm_lowbatt", "vebus", "Alarms/LowBattery", "Inverter Low Battery Alarm",
               DEV_GX, icon="mdi:alert", options_map=ALARM_MAP, enabled_default=False),

    # VE.Bus AC Diagnostics
    VSensorDef("vebus_out_l1_v", "vebus", "Ac/Out/L1/V", "Inverter AC Out Voltage",
               DEV_GX, "V", "voltage", "measurement", "mdi:sine-wave", entity_category="diagnostic", enabled_default=False, suggested_precision=1),
    VSensorDef("vebus_out_l1_i", "vebus", "Ac/Out/L1/I", "Inverter AC Out Current",
               DEV_GX, "A", "current", "measurement", "mdi:sine-wave", entity_category="diagnostic", enabled_default=False, suggested_precision=1),
    VSensorDef("vebus_in_l1_v", "vebus", "Ac/ActiveIn/L1/V", "Inverter AC In Voltage",
               DEV_GX, "V", "voltage", "measurement", "mdi:sine-wave", entity_category="diagnostic", enabled_default=False, suggested_precision=1),
    VSensorDef("vebus_in_l1_i", "vebus", "Ac/ActiveIn/L1/I", "Inverter AC In Current",
               DEV_GX, "A", "current", "measurement", "mdi:sine-wave", entity_category="diagnostic", enabled_default=False, suggested_precision=1),
    VSensorDef("vebus_in_l1_f", "vebus", "Ac/ActiveIn/L1/F", "Inverter AC In Frequency",
               DEV_GX, "Hz", "frequency", "measurement", "mdi:sine-wave", entity_category="diagnostic", enabled_default=False, suggested_precision=1),

    # ------------------------------------------------------------ solarcharger
    VSensorDef("sc_power", "solarcharger", "Yield/Power", "Solar Charger {instance} Power",
               DEV_SOLAR, "W", "power", "measurement", "mdi:lightning-bolt", suggested_precision=0),
    VSensorDef("sc_energy", "solarcharger", "Yield/User", "Solar Charger {instance} Energy",
               DEV_SOLAR, "kWh", "energy", "total_increasing", "mdi:solar-power", suggested_precision=2),
    VSensorDef("sc_pv_voltage", "solarcharger", "Pv/V", "Solar Charger {instance} PV Voltage",
               DEV_SOLAR, "V", "voltage", "measurement", enabled_default=False, suggested_precision=1),
    VSensorDef("sc_batt_voltage", "solarcharger", "Dc/0/Voltage", "Solar Charger {instance} Battery Voltage",
               DEV_SOLAR, "V", "voltage", "measurement", enabled_default=False, suggested_precision=1),
    VSensorDef("sc_batt_current", "solarcharger", "Dc/0/Current", "Solar Charger {instance} Battery Current",
               DEV_SOLAR, "A", "current", "measurement", enabled_default=False, suggested_precision=1),
    VSensorDef("sc_state", "solarcharger", "State", "Solar Charger {instance} State",
               DEV_SOLAR, icon="mdi:solar-power", options_map=VEBUS_STATE_MAP, enabled_default=False),

    # Solar Charger History (Diagnostics)
    VSensorDef("sc_yield_today", "solarcharger", "History/Daily/0/Yield", "Solar Charger {instance} Yield Today",
               DEV_SOLAR, "kWh", "energy", "total_increasing", "mdi:solar-power", entity_category="diagnostic", enabled_default=False, suggested_precision=2),
    VSensorDef("sc_yield_yesterday", "solarcharger", "History/Daily/1/Yield", "Solar Charger {instance} Yield Yesterday",
               DEV_SOLAR, "kWh", "energy", "measurement", "mdi:solar-power", entity_category="diagnostic", enabled_default=False, suggested_precision=2),
    VSensorDef("sc_max_power_today", "solarcharger", "History/Daily/0/MaxPower", "Solar Charger {instance} Max Power Today",
               DEV_SOLAR, "W", "power", "measurement", "mdi:white-balance-sunny", entity_category="diagnostic", enabled_default=False, suggested_precision=0),
    VSensorDef("sc_error", "solarcharger", "ErrorCode", "Solar Charger {instance} Error Code",
               DEV_SOLAR, icon="mdi:alert-circle", entity_category="diagnostic", enabled_default=False),

    # -------------------------------------------------------------- alternator
    VSensorDef("alt_current", "alternator", "Dc/0/Current", "Alternator {instance} Current",
               DEV_ALTERNATOR, "A", "current", "measurement", "mdi:current-dc", expire=10, suggested_precision=0),
    VSensorDef("alt_voltage", "alternator", "Dc/0/Voltage", "Alternator {instance} Voltage",
               DEV_ALTERNATOR, "V", "voltage", "measurement", "mdi:sine-wave", expire=10, suggested_precision=1),
    VSensorDef("alt_power", "alternator", "Dc/0/Power", "Alternator {instance} Power",
               DEV_ALTERNATOR, "W", "power", "measurement", "mdi:sine-wave", expire=10, suggested_precision=0),
    VSensorDef("alt_in_voltage", "alternator", "Dc/In/V", "Alternator {instance} Input Voltage",
               DEV_ALTERNATOR, "V", "voltage", "measurement", "mdi:sine-wave", expire=10, suggested_precision=1),
    VSensorDef("alt_state", "alternator", "State", "Alternator {instance} State",
               DEV_ALTERNATOR, icon="mdi:car-battery", options_map=VEBUS_STATE_MAP, enabled_default=False),
    VSensorDef("alt_error", "alternator", "ErrorCode", "Alternator {instance} Error Code",
               DEV_ALTERNATOR, icon="mdi:alert", entity_category="diagnostic", enabled_default=False),

    # -------------------------------------------------------------------- tank
    VSensorDef("tank_level", "tank", "Level", "Tank {instance} Level",
               DEV_TANKS, "%", None, "measurement", "mdi:water-percent", suggested_precision=0, custom_name="{custom} Level"),
    VSensorDef("tank_remaining", "tank", "Remaining", "Tank {instance} Remaining",
               DEV_TANKS, "L", "volume_storage", "measurement", "mdi:car-coolant-level", transform="m3_to_l", suggested_precision=1, custom_name="{custom} Remaining"),
    VSensorDef("tank_capacity", "tank", "Capacity", "Tank {instance} Capacity",
               DEV_TANKS, "L", "volume_storage", None, "mdi:car-coolant-level", transform="m3_to_l", entity_category="diagnostic", enabled_default=False, custom_name="{custom} Capacity"),
    VSensorDef("tank_fluid", "tank", "FluidType", "Tank {instance} Fluid Type",
               DEV_TANKS, icon="mdi:water", options_map=FLUID_TYPE_MAP, entity_category="diagnostic", enabled_default=False, custom_name="{custom} Fluid Type"),

    # ----------------------------------------------------- battery monitor svc
    VSensorDef("bm_voltage", "battery", "Dc/0/Voltage", "Battery Monitor {instance} Voltage",
               DEV_BATTERY, "V", "voltage", "measurement", enabled_default=False, suggested_precision=2),
    VSensorDef("bm_current", "battery", "Dc/0/Current", "Battery Monitor {instance} Current",
               DEV_BATTERY, "A", "current", "measurement", enabled_default=False, suggested_precision=1),
    VSensorDef("bm_consumed", "battery", "ConsumedAmphours", "Battery Monitor {instance} Consumed Ah",
               DEV_BATTERY, "Ah", None, "measurement", "mdi:battery-minus", enabled_default=False, suggested_precision=1),

    # Battery Monitor History & Diagnostics
    VSensorDef("bm_aux_voltage", "battery", "Dc/1/Voltage", "Battery Monitor {instance} Starter Voltage",
               DEV_BATTERY, "V", "voltage", "measurement", "mdi:car-battery", enabled_default=False, suggested_precision=2),
    VSensorDef("bm_hist_deepest", "battery", "History/DeepestDischarge", "Battery Monitor {instance} Deepest Discharge",
               DEV_BATTERY, "Ah", None, "measurement", "mdi:battery-arrow-down", entity_category="diagnostic", enabled_default=False, suggested_precision=1),
    VSensorDef("bm_hist_cycles", "battery", "History/ChargeCycles", "Battery Monitor {instance} Charge Cycles",
               DEV_BATTERY, None, None, "total_increasing", "mdi:battery-sync", entity_category="diagnostic", enabled_default=False),
    VSensorDef("bm_hist_last_full", "battery", "History/TimeSinceLastFullCharge", "Battery Monitor {instance} Time Since Full",
               DEV_BATTERY, "s", "duration", "measurement", "mdi:timer-sand", transform="ttg_text", entity_category="diagnostic", enabled_default=False),

    # -------------------------------------------------------------------- gps
    VSensorDef("gps_lat", "gps", "Position/Latitude", "GPS Latitude",
               DEV_GX, "°", None, "measurement", "mdi:latitude", entity_category="diagnostic", enabled_default=False, suggested_precision=5),
    VSensorDef("gps_lon", "gps", "Position/Longitude", "GPS Longitude",
               DEV_GX, "°", None, "measurement", "mdi:longitude", entity_category="diagnostic", enabled_default=False, suggested_precision=5),
    VSensorDef("gps_speed", "gps", "Speed", "GPS Speed",
               DEV_GX, "m/s", "speed", "measurement", "mdi:speedometer", entity_category="diagnostic", enabled_default=False, suggested_precision=1),
    VSensorDef("gps_alt", "gps", "Altitude", "GPS Altitude",
               DEV_GX, "m", "distance", "measurement", "mdi:elevation-rise", entity_category="diagnostic", enabled_default=False, suggested_precision=1),
    VSensorDef("gps_sats", "gps", "Satellites", "GPS Satellites",
               DEV_GX, None, None, "measurement", "mdi:satellite-uplink", entity_category="diagnostic", enabled_default=False, suggested_precision=0),
    VSensorDef("gps_fix", "gps", "Fix", "GPS Fix",
               DEV_GX, icon="mdi:crosshairs-gps", options_map=GPS_FIX_MAP, entity_category="diagnostic", enabled_default=False),
)

# Aggregates computed by the integration (sum across discovered solar chargers)
AGG_SOLAR_POWER = "agg_solar_power"
AGG_SOLAR_ENERGY = "agg_solar_energy"

@dataclass(frozen=True)
class VSwitchDef:
    key: str
    service: str
    path: str
    name: str
    device: str = DEV_GX
    icon: str | None = None

SWITCH_DEFS: tuple[VSwitchDef, ...] = (
    VSwitchDef("relay", "system", "Relay/{relay}/State", "Relay {relay_name}", DEV_GX, "mdi:electric-switch"),
)

@dataclass(frozen=True)
class VSelectDef:
    key: str
    service: str
    path: str
    name: str
    options_map: dict = field(hash=False, default=None)
    device: str = DEV_GX
    icon: str | None = None

SELECT_DEFS: tuple[VSelectDef, ...] = (
    VSelectDef("inverter_mode", "vebus", "Mode", "Inverter Mode", INVERTER_MODE_MAP, DEV_GX, "mdi:power-settings"),
)

@dataclass(frozen=True)
class VBinarySensorDef:
    key: str
    service: str
    path: str
    name: str
    predicate: str
    device: str = DEV_GX
    device_class: str | None = None
    icon: str | None = None
    expire: int | None = None
    enabled_default: bool = True
    none_as_zero: bool = False

BINARY_SENSOR_DEFS: tuple[VBinarySensorDef, ...] = (
    VBinarySensorDef("shore_connected", "vebus", "Ac/ActiveIn/Connected", "Shore Power Connected", "eq:1", DEV_GX, "plug", none_as_zero=True),
    VBinarySensorDef("shore_active", "system", "Ac/Grid/L1/Power", "Shore Power Active", "gt:0", DEV_GX, "power", none_as_zero=True),
    VBinarySensorDef("alt_charging", "alternator", "Dc/0/Power", "Alternator {instance} Charging", "gt:0", DEV_ALTERNATOR, "battery_charging", expire=10, enabled_default=False),
    VBinarySensorDef("inverter_inverting", "vebus", "State", "Inverter Inverting", "eq:9", DEV_GX, "running", enabled_default=False),

    # BMS / Alarm states
    VBinarySensorDef("bm_alarm_low_voltage", "battery", "Alarms/LowVoltage", "Battery Low Voltage Alarm", "eq:2", DEV_BATTERY, "problem", "mdi:alert", enabled_default=False),
    VBinarySensorDef("bm_alarm_high_voltage", "battery", "Alarms/HighVoltage", "Battery High Voltage Alarm", "eq:2", DEV_BATTERY, "problem", "mdi:alert", enabled_default=False),
    VBinarySensorDef("bm_alarm_low_soc", "battery", "Alarms/LowSoc", "Battery Low SoC Alarm", "eq:2", DEV_BATTERY, "problem", "mdi:alert", enabled_default=False),
    VBinarySensorDef("digital_input_alarm", "digitalinput", "Alarm", "Digital Input {instance} Alarm", "gt:0", DEV_GX, "problem", "mdi:alert", enabled_default=False),
)

@dataclass(frozen=True)
class VNumberDef:
    key: str
    service: str
    path: str
    name: str
    unit: str | None = None
    device: str = DEV_GX
    icon: str | None = None
    step: float = 0.5
    mode: str = "box"

NUMBER_DEFS: tuple[VNumberDef, ...] = (
    VNumberDef("input_current_limit", "vebus", "Ac/ActiveIn/CurrentLimit", "Input Current Limit", "A", DEV_GX, "mdi:current-ac"),
)
