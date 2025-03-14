"""
Regression tests for Ecobee 3.

https://github.com/home-assistant/core/issues/15336
"""

from unittest import mock

from aiohomekit import AccessoryDisconnectedError
from aiohomekit.testing import FakePairing

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_HUMIDITY,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers import entity_registry as er

from tests.components.homekit_controller.common import (
    DeviceTestInfo,
    EntityTestInfo,
    assert_devices_and_entities_created,
    device_config_changed,
    setup_accessories_from_file,
    setup_test_accessories,
    time_changed,
)


async def test_ecobee3_setup(hass):
    """Test that a Ecbobee 3 can be correctly setup in HA."""
    accessories = await setup_accessories_from_file(hass, "ecobee3.json")
    await setup_test_accessories(hass, accessories)

    await assert_devices_and_entities_created(
        hass,
        DeviceTestInfo(
            unique_id="00:00:00:00:00:00",
            name="HomeW",
            model="ecobee3",
            manufacturer="ecobee Inc.",
            sw_version="4.2.394",
            hw_version="",
            serial_number="123456789012",
            devices=[
                DeviceTestInfo(
                    name="Kitchen",
                    model="REMOTE SENSOR",
                    manufacturer="ecobee Inc.",
                    sw_version="1.0.0",
                    hw_version="",
                    serial_number="AB1C",
                    devices=[],
                    entities=[
                        EntityTestInfo(
                            entity_id="binary_sensor.kitchen",
                            friendly_name="Kitchen",
                            unique_id="homekit-AB1C-56",
                            state="off",
                        ),
                    ],
                ),
                DeviceTestInfo(
                    name="Porch",
                    model="REMOTE SENSOR",
                    manufacturer="ecobee Inc.",
                    sw_version="1.0.0",
                    hw_version="",
                    serial_number="AB2C",
                    devices=[],
                    entities=[
                        EntityTestInfo(
                            entity_id="binary_sensor.porch",
                            friendly_name="Porch",
                            unique_id="homekit-AB2C-56",
                            state="off",
                        ),
                    ],
                ),
                DeviceTestInfo(
                    name="Basement",
                    model="REMOTE SENSOR",
                    manufacturer="ecobee Inc.",
                    sw_version="1.0.0",
                    hw_version="",
                    serial_number="AB3C",
                    devices=[],
                    entities=[
                        EntityTestInfo(
                            entity_id="binary_sensor.basement",
                            friendly_name="Basement",
                            unique_id="homekit-AB3C-56",
                            state="off",
                        ),
                    ],
                ),
            ],
            entities=[
                EntityTestInfo(
                    entity_id="climate.homew",
                    friendly_name="HomeW",
                    unique_id="homekit-123456789012-16",
                    supported_features=(
                        SUPPORT_TARGET_TEMPERATURE
                        | SUPPORT_TARGET_TEMPERATURE_RANGE
                        | SUPPORT_TARGET_HUMIDITY
                    ),
                    capabilities={
                        "hvac_modes": ["off", "heat", "cool", "heat_cool"],
                        "min_temp": 7.2,
                        "max_temp": 33.3,
                        "min_humidity": 20,
                        "max_humidity": 50,
                    },
                    state="heat",
                ),
                EntityTestInfo(
                    entity_id="sensor.homew_current_temperature",
                    friendly_name="HomeW - Current Temperature",
                    unique_id="homekit-123456789012-aid:1-sid:16-cid:19",
                    capabilities={"state_class": SensorStateClass.MEASUREMENT},
                    unit_of_measurement=TEMP_CELSIUS,
                    state="21.8",
                ),
            ],
        ),
    )


async def test_ecobee3_setup_from_cache(hass, hass_storage):
    """Test that Ecbobee can be correctly setup from its cached entity map."""
    accessories = await setup_accessories_from_file(hass, "ecobee3.json")

    hass_storage["homekit_controller-entity-map"] = {
        "version": 1,
        "data": {
            "pairings": {
                "00:00:00:00:00:00": {
                    "config_num": 1,
                    "accessories": [
                        a.to_accessory_and_service_list() for a in accessories
                    ],
                }
            }
        },
    }

    await setup_test_accessories(hass, accessories)

    entity_registry = er.async_get(hass)

    climate = entity_registry.async_get("climate.homew")
    assert climate.unique_id == "homekit-123456789012-16"

    occ1 = entity_registry.async_get("binary_sensor.kitchen")
    assert occ1.unique_id == "homekit-AB1C-56"

    occ2 = entity_registry.async_get("binary_sensor.porch")
    assert occ2.unique_id == "homekit-AB2C-56"

    occ3 = entity_registry.async_get("binary_sensor.basement")
    assert occ3.unique_id == "homekit-AB3C-56"


async def test_ecobee3_setup_connection_failure(hass):
    """Test that Ecbobee can be correctly setup from its cached entity map."""
    accessories = await setup_accessories_from_file(hass, "ecobee3.json")

    entity_registry = er.async_get(hass)

    # Test that the connection fails during initial setup.
    # No entities should be created.
    list_accessories = "list_accessories_and_characteristics"
    with mock.patch.object(FakePairing, list_accessories) as laac:
        laac.side_effect = AccessoryDisconnectedError("Connection failed")

        # If there is no cached entity map and the accessory connection is
        # failing then we have to fail the config entry setup.
        config_entry, pairing = await setup_test_accessories(hass, accessories)
        assert config_entry.state is ConfigEntryState.SETUP_RETRY

    climate = entity_registry.async_get("climate.homew")
    assert climate is None

    # When accessory raises ConfigEntryNoteReady HA will retry - lets make
    # sure there is no cruft causing conflicts left behind by now doing
    # a successful setup.

    # We just advance time by 5 minutes so that the retry happens, rather
    # than manually invoking async_setup_entry.
    await time_changed(hass, 5 * 60)

    climate = entity_registry.async_get("climate.homew")
    assert climate.unique_id == "homekit-123456789012-16"

    occ1 = entity_registry.async_get("binary_sensor.kitchen")
    assert occ1.unique_id == "homekit-AB1C-56"

    occ2 = entity_registry.async_get("binary_sensor.porch")
    assert occ2.unique_id == "homekit-AB2C-56"

    occ3 = entity_registry.async_get("binary_sensor.basement")
    assert occ3.unique_id == "homekit-AB3C-56"


async def test_ecobee3_add_sensors_at_runtime(hass):
    """Test that new sensors are automatically added."""
    entity_registry = er.async_get(hass)

    # Set up a base Ecobee 3 with no additional sensors.
    # There shouldn't be any entities but climate visible.
    accessories = await setup_accessories_from_file(hass, "ecobee3_no_sensors.json")
    await setup_test_accessories(hass, accessories)

    climate = entity_registry.async_get("climate.homew")
    assert climate.unique_id == "homekit-123456789012-16"

    occ1 = entity_registry.async_get("binary_sensor.kitchen")
    assert occ1 is None

    occ2 = entity_registry.async_get("binary_sensor.porch")
    assert occ2 is None

    occ3 = entity_registry.async_get("binary_sensor.basement")
    assert occ3 is None

    # Now added 3 new sensors at runtime - sensors should appear and climate
    # shouldn't be duplicated.
    accessories = await setup_accessories_from_file(hass, "ecobee3.json")
    await device_config_changed(hass, accessories)

    occ1 = entity_registry.async_get("binary_sensor.kitchen")
    assert occ1.unique_id == "homekit-AB1C-56"

    occ2 = entity_registry.async_get("binary_sensor.porch")
    assert occ2.unique_id == "homekit-AB2C-56"

    occ3 = entity_registry.async_get("binary_sensor.basement")
    assert occ3.unique_id == "homekit-AB3C-56"
