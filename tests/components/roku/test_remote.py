"""The tests for the Roku remote platform."""
from unittest.mock import patch

from homeassistant.components.remote import (
    ATTR_COMMAND,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry
from tests.components.roku import UPNP_SERIAL

MAIN_ENTITY_ID = f"{REMOTE_DOMAIN}.my_roku_3"

# pylint: disable=redefined-outer-name


async def test_setup(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test setup with basic config."""
    assert hass.states.get(MAIN_ENTITY_ID)


async def test_unique_id(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test unique id."""
    entity_registry = er.async_get(hass)

    main = entity_registry.async_get(MAIN_ENTITY_ID)
    assert main.unique_id == UPNP_SERIAL


async def test_main_services(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test platform services."""
    with patch("homeassistant.components.roku.coordinator.Roku.remote") as remote_mock:
        await hass.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: MAIN_ENTITY_ID},
            blocking=True,
        )
        remote_mock.assert_called_once_with("poweroff")

    with patch("homeassistant.components.roku.coordinator.Roku.remote") as remote_mock:
        await hass.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: MAIN_ENTITY_ID},
            blocking=True,
        )
        remote_mock.assert_called_once_with("poweron")

    with patch("homeassistant.components.roku.coordinator.Roku.remote") as remote_mock:
        await hass.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {ATTR_ENTITY_ID: MAIN_ENTITY_ID, ATTR_COMMAND: ["home"]},
            blocking=True,
        )
        remote_mock.assert_called_once_with("home")
