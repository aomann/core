"""The tests for the WebOS TV notify platform."""
from unittest.mock import Mock, call

from aiowebostv import WebOsTvPairError
import pytest

from homeassistant.components.notify import ATTR_MESSAGE, DOMAIN as NOTIFY_DOMAIN
from homeassistant.components.webostv import DOMAIN
from homeassistant.const import CONF_ICON, CONF_SERVICE_DATA
from homeassistant.setup import async_setup_component

from . import TV_NAME, setup_webostv

ICON_PATH = "/some/path"
MESSAGE = "one, two, testing, testing"


async def test_notify(hass, client):
    """Test sending a message."""
    await setup_webostv(hass, "fake-uuid")
    assert hass.services.has_service(NOTIFY_DOMAIN, TV_NAME)

    await hass.services.async_call(
        NOTIFY_DOMAIN,
        TV_NAME,
        {
            ATTR_MESSAGE: MESSAGE,
            CONF_SERVICE_DATA: {
                CONF_ICON: ICON_PATH,
            },
        },
        blocking=True,
    )
    assert client.mock_calls[0] == call.connect()
    assert client.connect.call_count == 1
    client.send_message.assert_called_with(MESSAGE, icon_path=ICON_PATH)


async def test_notify_not_connected(hass, client, monkeypatch):
    """Test sending a message when client is not connected."""
    await setup_webostv(hass, "fake-uuid")
    assert hass.services.has_service(NOTIFY_DOMAIN, TV_NAME)

    monkeypatch.setattr(client, "is_connected", Mock(return_value=False))
    await hass.services.async_call(
        NOTIFY_DOMAIN,
        TV_NAME,
        {
            ATTR_MESSAGE: MESSAGE,
            CONF_SERVICE_DATA: {
                CONF_ICON: ICON_PATH,
            },
        },
        blocking=True,
    )
    assert client.mock_calls[0] == call.connect()
    assert client.connect.call_count == 2
    client.send_message.assert_called_with(MESSAGE, icon_path=ICON_PATH)


async def test_icon_not_found(hass, caplog, client, monkeypatch):
    """Test notify icon not found error."""
    await setup_webostv(hass, "fake-uuid")
    assert hass.services.has_service(NOTIFY_DOMAIN, TV_NAME)

    monkeypatch.setattr(client, "send_message", Mock(side_effect=FileNotFoundError))
    await hass.services.async_call(
        NOTIFY_DOMAIN,
        TV_NAME,
        {
            ATTR_MESSAGE: MESSAGE,
            CONF_SERVICE_DATA: {
                CONF_ICON: ICON_PATH,
            },
        },
        blocking=True,
    )
    assert client.mock_calls[0] == call.connect()
    assert client.connect.call_count == 1
    client.send_message.assert_called_with(MESSAGE, icon_path=ICON_PATH)
    assert f"Icon {ICON_PATH} not found" in caplog.text


@pytest.mark.parametrize(
    "side_effect,error",
    [
        (WebOsTvPairError, "Pairing with TV failed"),
        (ConnectionRefusedError, "TV unreachable"),
    ],
)
async def test_connection_errors(hass, caplog, client, monkeypatch, side_effect, error):
    """Test connection errors scenarios."""
    await setup_webostv(hass, "fake-uuid")
    assert hass.services.has_service("notify", TV_NAME)

    monkeypatch.setattr(client, "is_connected", Mock(return_value=False))
    monkeypatch.setattr(client, "connect", Mock(side_effect=side_effect))
    await hass.services.async_call(
        NOTIFY_DOMAIN,
        TV_NAME,
        {
            ATTR_MESSAGE: MESSAGE,
            CONF_SERVICE_DATA: {
                CONF_ICON: ICON_PATH,
            },
        },
        blocking=True,
    )
    assert client.mock_calls[0] == call.connect()
    assert client.connect.call_count == 1
    client.send_message.assert_not_called()
    assert error in caplog.text


async def test_no_discovery_info(hass, caplog):
    """Test setup without discovery info."""
    assert NOTIFY_DOMAIN not in hass.config.components
    assert await async_setup_component(
        hass,
        NOTIFY_DOMAIN,
        {"notify": {"platform": DOMAIN}},
    )
    await hass.async_block_till_done()
    assert NOTIFY_DOMAIN in hass.config.components
    assert f"Failed to initialize notification service {DOMAIN}" in caplog.text
    assert not hass.services.has_service("notify", TV_NAME)
