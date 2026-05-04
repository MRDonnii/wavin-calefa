"""Sensors for Wavin Calefa."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfEnergy,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_LANGUAGE,
    DEFAULT_LANGUAGE,
    DOMAIN,
    LANGUAGE_AUTO,
    LANGUAGE_DA,
    LANGUAGE_EN,
)
from .coordinator import WavinCalefaCoordinator


UNSUPPORTED_SENSOR_KEYS_BY_DEVICE_TYPE: dict[int, set[str]] = {
    3: {
        "ch_desired_inlet_temperature",
        "hc_supply_temperature",
        "hc_return_temperature",
        "hc_delta_temperature",
    }
}


STATE_MAPS = {
    "dhw_state": {
        0: "Standby",
        1: "Opvarmning",
        2: "Bypass",
        3: "Rensning",
        4: "Suspenderet",
    },
    "dhw_blocking_source": {
        0: "Ingen",
        1: "Varmekreds",
        2: "Standby",
        3: "Ferie",
    },
    "circulation_state": {0: "Standby", 1: "Til"},
    "dhw_boost_state": {0: "Standby", 1: "Til"},
    "dhw_control_mode": {
        0: "Opstart",
        1: "Diagnose",
        2: "Fejl",
        3: "Automatisk",
        4: "Manuel",
        5: "Fjernstyring",
        6: "HEX søgning",
    },
    "dhw_regulator_state": {
        0: "Standby",
        1: "Panik",
        2: "Kold",
        3: "Varm",
        4: "Bypass cirkulation",
        5: "Frostbeskyttelse",
        6: "Afsluttet",
    },
    "ch_state": {0: "Standby", 1: "Opvarmning"},
    "ch_regulator_state": {
        0: "Opstart",
        1: "Diagnose",
        2: "Fejl",
        3: "Automatisk",
        4: "Manuel",
        5: "Fjernstyring",
        6: "Blokeret af DHW",
    },
    "boost_pump_mode": {0: "Fra", 1: "Lav", 2: "Høj"},
    "flow_sensor_type": {0: "H210 DN8", 1: "H210 DN10"},
    "dhw_mode": {0: "Tidsplan", 1: "Adaptiv tidsplan", 2: "Eco", 3: "Comfort"},
    "dhw_block_request": {0: "Ingen", 1: "Blokeret"},
    "device_type": {2: "DHW-201 Calefa", 3: "Sentio"},
    "on_off": {0: "Fra", 1: "Til"},
}

SENSOR_NAMES_DA: dict[str, str] = {
    "dhw_state": "BVV status",
    "dhw_bypass_active": "BVV bypass",
    "dhw_blocking_source": "BVV blokeret af",
    "dhw_out_temperature": "Varmt vand ud (BV)",
    "dcw_sensor_temperature": "Koldt vand ind (KV)",
    "domestic_cold_water_flow": "Varmtvandsflow (FLW)",
    "outdoor_temperature": "Udetemperatur (UT)",
    "source_inlet_temperature": "Fjernvarme fremlob (FJF)",
    "source_return_temperature": "Fjernvarme retur (FJR)",
    "source_delta_temperature": "Fjernvarme afkoling",
    "cvv_supply_temperature": "CVV fremlob",
    "cvv_desired_supply_temperature": "CVV onsket fremlob",
    "cvv_return_temperature": "CVV retur",
    "cvv_delta_temperature": "CVV afkoling",
    "itc_pump_demand": "CVV pumpe kald",
    "itc_pump_status": "CVV pumpe status",
    "dhw_control_mode": "BVV styre-mode",
    "dhw_regulator_state": "BVV regulator tilstand",
    "dhw_motor_stall_level": "BVV motor stall niveau",
    "ch_state": "Varmekreds status (CH)",
    "ch_blocking_source": "Varmekreds blokeret af (CH)",
    "ch_regulator_state": "Varme regulator tilstand (CH)",
    "ch_desired_inlet_temperature": "Varme onsket indlob (CH)",
    "hc_supply_temperature": "Varme fremlob (HC)",
    "hc_return_temperature": "Varme retur (HC)",
    "hc_delta_temperature": "Radiator frem/retur delta (HC)",
    "system_pressure": "Anlaegstryk",
    "itc_max_outdoor_temp": "ITC max udetemperatur",
    "documented_secondary_pressure": "Dokumenteret sekundartryk",
    "valve_position": "Varmtvandsventil (BVV)",
    "cvv_valve_position": "Radiatorventil (CVV)",
    "dhw_power_estimate": "Varmtvand effekt estimat",
    "dhw_energy_estimate": "Varmtvand energi estimat",
    "dhw_temperature_setpoint": "BVV temperatur setpunkt",
    "dhw_bypass_temperature": "BVV bypass temperatur",
    "circulation_temperature": "Cirkulation temperatur",
    "circulation_state": "Cirkulation status",
    "dhw_boost_state": "Boostpumpe status",
    "boost_pump_mode": "Boostpumpe tilstand",
    "flow_sensor_type": "Flowmaler type",
    "dhw_mode": "BVV mode",
    "device_type": "Enhedstype",
    "hardware_version": "Hardwareversion",
    "software_version": "Softwareversion",
}


def _selected_language(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Resolve language mode for this integration entry."""
    choice = entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    if choice == LANGUAGE_AUTO:
        hass_lang = str(getattr(hass.config, "language", "en")).lower()
        return LANGUAGE_DA if hass_lang.startswith("da") else LANGUAGE_EN
    return LANGUAGE_DA if choice == LANGUAGE_DA else LANGUAGE_EN


def _device_model(coordinator: WavinCalefaCoordinator) -> str:
    """Return a generic model name based on the reported device type."""
    device_type = coordinator.data.get("device_type")
    return STATE_MAPS["device_type"].get(device_type, "Calefa / Sentio")


def _supported_sensors(coordinator: WavinCalefaCoordinator) -> tuple[WavinCalefaSensorDescription, ...]:
    """Return only sensors supported by the detected device type."""
    device_type = coordinator.data.get("device_type")
    unsupported_keys = UNSUPPORTED_SENSOR_KEYS_BY_DEVICE_TYPE.get(device_type, set())
    return tuple(
        description for description in SENSORS if description.key not in unsupported_keys
    )


@dataclass(frozen=True, kw_only=True)
class WavinCalefaSensorDescription(SensorEntityDescription):
    """Wavin Calefa sensor description."""

    source_key: str
    enum_map: dict[int, str] | None = None
    raw_attribute: bool = False
    description_text: str | None = None


SENSORS: tuple[WavinCalefaSensorDescription, ...] = (
    WavinCalefaSensorDescription(
        key="dhw_state",
        source_key="dhw_state",
        name="DHW status",
        icon="mdi:water-boiler",
        enum_map=STATE_MAPS["dhw_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_bypass_active",
        source_key="dhw_bypass_active",
        name="DHW bypass",
        icon="mdi:pipe-valve",
        enum_map=STATE_MAPS["on_off"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_blocking_source",
        source_key="dhw_blocking_source",
        name="DHW blocked by",
        icon="mdi:block-helper",
        enum_map=STATE_MAPS["dhw_blocking_source"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_out_temperature",
        source_key="dhw_out_temperature",
        name="Hot water outlet (HW)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="dcw_sensor_temperature",
        source_key="dcw_sensor_temperature",
        name="Cold water inlet (CW)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="domestic_cold_water_flow",
        source_key="domestic_cold_water_flow",
        name="Hot water flow (FLW)",
        icon="mdi:waves-arrow-right",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L/h",
        suggested_display_precision=0,
    ),
    WavinCalefaSensorDescription(
        key="outdoor_temperature",
        source_key="outdoor_temperature",
        name="Outdoor temperature (OT)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="source_inlet_temperature",
        source_key="source_inlet_temperature",
        name="District heating supply (DHS)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="source_return_temperature",
        source_key="source_return_temperature",
        name="District heating return (DHR)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="source_delta_temperature",
        source_key="source_delta_temperature",
        name="District heating cooling",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="cvv_supply_temperature",
        source_key="cvv_supply_temperature",
        name="Heating supply (ITC)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="cvv_desired_supply_temperature",
        source_key="cvv_desired_supply_temperature",
        name="Heating desired supply (ITC)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="cvv_return_temperature",
        source_key="cvv_return_temperature",
        name="Heating return (ITC)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="cvv_delta_temperature",
        source_key="cvv_delta_temperature",
        name="Heating delta (ITC)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="itc_pump_demand",
        source_key="itc_pump_demand",
        name="Heating pump demand (ITC)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
        enum_map=STATE_MAPS["on_off"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="itc_pump_status",
        source_key="itc_pump_status",
        name="Heating pump status (ITC)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
        enum_map=STATE_MAPS["on_off"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_control_mode",
        source_key="dhw_control_mode",
        name="DHW control mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cog",
        enum_map=STATE_MAPS["dhw_control_mode"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_regulator_state",
        source_key="dhw_regulator_state",
        name="DHW regulator state",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
        enum_map=STATE_MAPS["dhw_regulator_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_motor_stall_level",
        source_key="dhw_motor_stall_level",
        name="DHW motor stall level",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mV",
        suggested_display_precision=0,
    ),
    WavinCalefaSensorDescription(
        key="ch_state",
        source_key="ch_state",
        name="Heating state (CH)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:heat-wave",
        enum_map=STATE_MAPS["ch_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="ch_blocking_source",
        source_key="ch_blocking_source",
        name="Heating blocked by (CH)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:block-helper",
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="ch_regulator_state",
        source_key="ch_regulator_state",
        name="Heating regulator state (CH)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:state-machine",
        enum_map=STATE_MAPS["ch_regulator_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="ch_desired_inlet_temperature",
        source_key="ch_desired_inlet_temperature",
        name="Heating desired inlet (CH)",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="hc_supply_temperature",
        source_key="hc_supply_temperature",
        name="Heating supply (HC)",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="hc_return_temperature",
        source_key="hc_return_temperature",
        name="Heating return (HC)",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="hc_delta_temperature",
        source_key="hc_delta_temperature",
        name="Heating delta (HC)",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="system_pressure",
        source_key="system_pressure",
        name="System pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
    ),
    WavinCalefaSensorDescription(
        key="itc_max_outdoor_temp",
        source_key="itc_max_outdoor_temp",
        name="ITC max outdoor temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="documented_secondary_pressure",
        source_key="documented_secondary_pressure",
        name="Documented secondary pressure",
        device_class=SensorDeviceClass.PRESSURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
    ),
    WavinCalefaSensorDescription(
        key="valve_position",
        source_key="valve_position",
        name="DHW valve position (DHW)",
        icon="mdi:valve",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    WavinCalefaSensorDescription(
        key="cvv_valve_position",
        source_key="cvv_valve_position",
        name="Heating valve position (CH)",
        icon="mdi:valve",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    WavinCalefaSensorDescription(
        key="dhw_power_estimate",
        source_key="dhw_power_estimate",
        name="Hot water power estimate (DHW)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=3,
    ),
    WavinCalefaSensorDescription(
        key="dhw_energy_estimate",
        source_key="dhw_energy_estimate",
        name="Hot water energy estimate (DHW)",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    WavinCalefaSensorDescription(
        key="dhw_temperature_setpoint",
        source_key="dhw_temperature_setpoint",
        name="DHW temperature setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="dhw_bypass_temperature",
        source_key="dhw_bypass_temperature",
        name="DHW bypass temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="circulation_temperature",
        source_key="circulation_temperature",
        name="Circulation temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="circulation_state",
        source_key="circulation_state",
        name="Circulation status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
        enum_map=STATE_MAPS["circulation_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_boost_state",
        source_key="dhw_boost_state",
        name="Boost pump status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
        enum_map=STATE_MAPS["dhw_boost_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="boost_pump_mode",
        source_key="boost_pump_mode",
        name="Boost pump mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune-variant",
        enum_map=STATE_MAPS["boost_pump_mode"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="flow_sensor_type",
        source_key="flow_sensor_type",
        name="Flow sensor type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:gauge",
        enum_map=STATE_MAPS["flow_sensor_type"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_mode",
        source_key="dhw_mode",
        name="DHW mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune-variant",
        enum_map=STATE_MAPS["dhw_mode"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="device_type",
        source_key="device_type",
        name="Device type",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
        enum_map=STATE_MAPS["device_type"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="hardware_version",
        source_key="hardware_version",
        name="Hardware version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    WavinCalefaSensorDescription(
        key="software_version",
        source_key="software_version",
        name="Software version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:source-branch",
    ),
)


# ---------------------------------------------------------------------------
# Legacy block removed in v0.2.0 – sensors below were superseded by the
# rewritten SENSORS tuple above.
# ---------------------------------------------------------------------------
(  # legacy content - ignored
    WavinCalefaSensorDescription(
        key="dhw_bypass_active",
        source_key="dhw_bypass_active",
        name="BVV bypass status",
        icon="mdi:pipe-valve",
        enum_map=STATE_MAPS["on_off"],
        raw_attribute=True,
        description_text=(
            "Viser om BVV-bypass er aktiv. Den er udledt af BVV status, hvor "
            "status 'Bypass' betyder bypass til."
        ),
    ),
    WavinCalefaSensorDescription(
        key="dhw_blocking_source",
        source_key="dhw_blocking_source",
        name="BVV blokeret af",
        icon="mdi:block-helper",
        enum_map=STATE_MAPS["dhw_blocking_source"],
        raw_attribute=True,
        description_text=(
            "Matcher feltet 'Blokeret af' på Calefa-displayets varmtvandsside. "
            "Værdien 0 betyder Ingen."
        ),
    ),
    WavinCalefaSensorDescription(
        key="dhw_out_temperature",
        source_key="dhw_out_temperature",
        name="Varmt vand ud (BV)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "BV på Calefa-displayet. Temperaturen på det varme brugsvand ud "
            "fra varmtvandsveksleren."
        ),
    ),
    WavinCalefaSensorDescription(
        key="dcw_sensor_temperature",
        source_key="dcw_sensor_temperature",
        name="Koldt vand ind (KV)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "KV på Calefa-displayet. Føleren sidder ved varmtvandsveksleren og "
            "kan blive varmet op, når der ikke tappes vand."
        ),
    ),
    WavinCalefaSensorDescription(
        key="domestic_cold_water_flow",
        source_key="domestic_cold_water_flow",
        name="Varmtvandsflow (FLW)",
        icon="mdi:waves-arrow-right",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L/h",
        suggested_display_precision=0,
        description_text=(
            "FLW på Calefa-displayets varmtvandsside. Dette er flowet gennem "
            "varmtvandsdelen/BVV-kredsen og læses fra inputregister 6510."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_flow",
        source_key="cvv_flow",
        name="Radiator flow (CVV, uverificeret)",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:waves-arrow-right",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L/h",
        suggested_display_precision=0,
        description_text=(
            "Uverificeret kandidatværdi for flow på radiator-/CVV-kredsen. "
            "Den er ikke matchet mod en flowværdi i Calefa-displayet og kan "
            "på nogle units være en intern reguleringsværdi."
        ),
    ),
    WavinCalefaSensorDescription(
        key="source_flow",
        source_key="source_flow",
        name="Fjernvarme flow (uverificeret)",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:waves-arrow-right",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L/h",
        suggested_display_precision=0,
        description_text=(
            "Uverificeret kandidatværdi for flow på primærsiden. Den er ikke "
            "matchet mod en flowværdi i Calefa-displayet og bør ikke bruges "
            "som afregnings- eller forbrugsmåler."
        ),
    ),
    WavinCalefaSensorDescription(
        key="outdoor_temperature",
        source_key="outdoor_temperature",
        name="Udetemperatur (UT)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "UT på Calefa-displayets følermenu. Udetemperaturen læses fra "
            "inputregister 20."
        ),
    ),
    WavinCalefaSensorDescription(
        key="source_inlet_temperature",
        source_key="source_inlet_temperature",
        name="Fjernvarme fremløb (FJF)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "FJF på Calefa-displayet. Fjernvarmefremløb ind i unitten."
        ),
    ),
    WavinCalefaSensorDescription(
        key="source_return_temperature",
        source_key="source_return_temperature",
        name="Fjernvarme retur (FJR)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "FJR på Calefa-displayet. Fjernvarmeretur ud fra unitten."
        ),
    ),
    WavinCalefaSensorDescription(
        key="source_delta_temperature",
        source_key="source_delta_temperature",
        name="Fjernvarme afkøling",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="source_power",
        source_key="source_power",
        name="Fjernvarme effekt (uverificeret)",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=3,
        description_text=(
            "Eksperimentelt estimat baseret på den uverificerede fjernvarmeflow-kandidat "
            "og afkøling: L/h × °C × 1,163 / 1000. Ikke officiel afregningsmåler."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_supply_temperature",
        source_key="cvv_supply_temperature",
        name="Radiator fremløb (CVV)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "VF på Calefa-displayets følermenu. Dette er det målte fremløb "
            "til radiator-/CVV-kredsen og læses fra inputregister 7701."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_desired_supply_temperature",
        source_key="cvv_desired_supply_temperature",
        name="Radiator ønsket fremløb (ØVF)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "ØVF på Calefa-displayets følermenu. Dette er ønsket/beregnet "
            "fremløbstemperatur til CVV-kredsen og læses fra inputregister 7703."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_return_temperature",
        source_key="cvv_return_temperature",
        name="Radiator retur (CVV)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "VR på Calefa-displayets følermenu. Dette er returtemperaturen "
            "fra radiator-/CVV-kredsen og læses fra inputregister 7702."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_delta_temperature",
        source_key="cvv_delta_temperature",
        name="Radiator delta (CVV)",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "Beregnet som radiator-/CVV-fremløb minus radiator-/CVV-retur "
            "baseret på inputregister 7701 og 7702."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_pump_state",
        source_key="cvv_pump_state",
        name="Radiatorpumpe status (CVV)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
        enum_map=STATE_MAPS["on_off"],
        raw_attribute=True,
        description_text=(
            "Status for radiatorpumpen i CVV-kredsen. Matcher PUM-linjen "
            "på radiator-statussiden."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_heat_request",
        source_key="cvv_heat_request",
        name="Radiator varmekald (CVV)",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:heat-wave",
        enum_map=STATE_MAPS["on_off"],
        raw_attribute=True,
        description_text=(
            "Indikerer om radiator-/CVV-kredsen kalder på varme. Bruges til "
            "at validere radiator-statussiden i Calefa-displayet."
        ),
    ),
    WavinCalefaSensorDescription(
        key="system_pressure",
        source_key="system_pressure",
        name="Anlægstryk",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        description_text=(
            "PRE på Calefa-displayets følermenu. Matcher anlægstrykket på "
            "displayet og læses fra inputregister 7310."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_room_setpoint",
        source_key="cvv_room_setpoint",
        name="Radiator setpunkt (SÆT)",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        description_text=(
            "SÆT på Calefa-displayets følermenu. Setpunktet læses fra "
            "holdingregister 38."
        ),
    ),
    WavinCalefaSensorDescription(
        key="documented_secondary_pressure",
        source_key="documented_secondary_pressure",
        name="Dokumenteret sekundærtryk",
        device_class=SensorDeviceClass.PRESSURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
    ),
    WavinCalefaSensorDescription(
        key="valve_position",
        source_key="valve_position",
        name="Varmtvandsventil (BVV)",
        icon="mdi:valve",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        description_text=(
            "BVV er brugsvandsventilen til varmt brugsvand. Den viser hvor "
            "meget ventilen mod varmtvandsveksleren er åben."
        ),
    ),
    WavinCalefaSensorDescription(
        key="cvv_valve_position",
        source_key="cvv_valve_position",
        name="Radiatorventil (CVV)",
        icon="mdi:valve",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
        description_text=(
            "CVV er centralvarmeventilen til varmekredsen/radiatorvarmen. "
            "Den viser hvor meget varmeventilen er åben."
        ),
    ),
    WavinCalefaSensorDescription(
        key="dhw_power_estimate",
        source_key="dhw_power_estimate",
        name="Varmtvand effekt estimat (BVV)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=3,
    ),
    WavinCalefaSensorDescription(
        key="dhw_energy_estimate",
        source_key="dhw_energy_estimate",
        name="Varmtvand energi estimat (BVV)",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    WavinCalefaSensorDescription(
        key="dhw_temperature_setpoint",
        source_key="dhw_temperature_setpoint",
        name="BVV temperatur setpunkt",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="dhw_bypass_temperature",
        source_key="dhw_bypass_temperature",
        name="BVV bypass temperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="circulation_inlet_temperature",
        source_key="circulation_inlet_temperature",
        name="Cirkulation indløbstemperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    WavinCalefaSensorDescription(
        key="circulation_state",
        source_key="circulation_state",
        name="Cirkulation status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
        enum_map=STATE_MAPS["circulation_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="boost_pump_state",
        source_key="boost_pump_state",
        name="Boostpumpe status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
        enum_map=STATE_MAPS["dhw_boost_state"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="dhw_mode",
        source_key="dhw_mode",
        name="BVV mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tune-variant",
        enum_map=STATE_MAPS["dhw_mode"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="device_type",
        source_key="device_type",
        name="Enhedstype",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
        enum_map=STATE_MAPS["device_type"],
        raw_attribute=True,
    ),
    WavinCalefaSensorDescription(
        key="hardware_version",
        source_key="hardware_version",
        name="Hardwareversion",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    WavinCalefaSensorDescription(
        key="software_version",
        source_key="software_version",
        name="Softwareversion",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:source-branch",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Wavin Calefa sensors."""
    coordinator: WavinCalefaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WavinCalefaSensor(coordinator, entry, description)
        for description in _supported_sensors(coordinator)
    )


class WavinCalefaSensor(
    CoordinatorEntity[WavinCalefaCoordinator], SensorEntity, RestoreEntity
):
    """Wavin Calefa sensor."""

    entity_description: WavinCalefaSensorDescription
    _attr_has_entity_name = True
    _energy_kwh: float | None = None
    _last_energy_update: datetime | None = None

    def __init__(
        self,
        coordinator: WavinCalefaCoordinator,
        entry: ConfigEntry,
        description: WavinCalefaSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        selected_language = _selected_language(coordinator.hass, entry)
        if selected_language == LANGUAGE_DA:
            self._attr_name = SENSOR_NAMES_DA.get(description.key, description.name)
        else:
            self._attr_name = description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Wavin",
            model=_device_model(coordinator),
        )

    async def async_added_to_hass(self) -> None:
        """Restore state for cumulative estimate sensors."""
        await super().async_added_to_hass()
        if self.entity_description.key != "dhw_energy_estimate":
            return

        last_state = await self.async_get_last_state()
        if last_state is not None:
            try:
                self._energy_kwh = max(0.0, float(last_state.state))
            except (TypeError, ValueError):
                self._energy_kwh = 0.0
        else:
            self._energy_kwh = 0.0
        self._last_energy_update = datetime.now(timezone.utc)
        self._integrate_energy_estimate()

    def _handle_coordinator_update(self) -> None:
        """Update cumulative values before Home Assistant writes state."""
        if self.entity_description.key == "dhw_energy_estimate":
            self._integrate_energy_estimate()
        super()._handle_coordinator_update()

    def _integrate_energy_estimate(self) -> None:
        """Integrate current DHW power estimate into kWh."""
        now = datetime.now(timezone.utc)
        if self._energy_kwh is None:
            self._energy_kwh = 0.0

        power = self.coordinator.data.get("dhw_power_estimate")
        if (
            self._last_energy_update is not None
            and isinstance(power, (int, float))
            and power >= 0
        ):
            hours = (now - self._last_energy_update).total_seconds() / 3600
            if 0 <= hours <= 1:
                self._energy_kwh += power * hours

        self._last_energy_update = now

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.entity_description.key == "dhw_energy_estimate":
            if self._energy_kwh is None:
                return None
            return round(self._energy_kwh, 3)

        value = self.coordinator.data.get(self.entity_description.source_key)
        if self.entity_description.enum_map is not None:
            return self.entity_description.enum_map.get(value, str(value))
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        attrs: dict[str, Any] = {}
        description = self.entity_description
        raw_key = f"{description.source_key}_raw"
        if description.description_text:
            attrs["description"] = description.description_text
        if description.raw_attribute and raw_key in self.coordinator.data:
            attrs["raw_value"] = self.coordinator.data[raw_key]
        if description.key == "dhw_power_estimate":
            attrs["cold_water_temperature_for_calculation"] = self.coordinator.data.get(
                "dcw_temperature_for_calculation"
            )
            attrs["note"] = (
                "Estimat for varmt brugsvand. Ikke officiel fjernvarmeafregning."
            )
        if description.key == "dhw_energy_estimate":
            attrs["note"] = (
                "Akkumuleret estimat fra Varmtvand effekt estimat. "
                "Ikke officiel fjernvarmeafregning."
            )
        return attrs or None
