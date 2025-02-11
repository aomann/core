"""Adds config flow for Yale Smart Alarm integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from yalesmartalarmclient.client import YaleSmartAlarmClient
from yalesmartalarmclient.exceptions import AuthenticationError, UnknownError

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_CODE, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_AREA_ID,
    CONF_LOCK_CODE_DIGITS,
    DEFAULT_AREA_ID,
    DEFAULT_LOCK_CODE_DIGITS,
    DEFAULT_NAME,
    DOMAIN,
    LOGGER,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_AREA_ID, default=DEFAULT_AREA_ID): cv.string,
    }
)

DATA_SCHEMA_AUTH = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


class YaleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yale integration."""

    VERSION = 1

    entry: ConfigEntry

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> YaleOptionsFlowHandler:
        """Get the options flow for this handler."""
        return YaleOptionsFlowHandler(config_entry)

    async def async_step_import(self, config: dict):
        """Import a configuration from config.yaml."""

        self.context.update(
            {"title_placeholders": {CONF_NAME: f"YAML import {DOMAIN}"}}
        )
        return await self.async_step_user(user_input=config)

    async def async_step_reauth(self, user_input=None):
        """Handle initiation of re-authentication with Yale."""
        self.entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                await self.hass.async_add_executor_job(
                    YaleSmartAlarmClient, username, password
                )
            except AuthenticationError as error:
                LOGGER.error("Authentication failed. Check credentials %s", error)
                errors = {"base": "invalid_auth"}
            except (ConnectionError, TimeoutError, UnknownError) as error:
                LOGGER.error("Connection to API failed %s", error)
                errors = {"base": "cannot_connect"}

            if not errors:
                existing_entry = await self.async_set_unique_id(username)
                if existing_entry:
                    self.hass.config_entries.async_update_entry(
                        existing_entry,
                        data={
                            **self.entry.data,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                        },
                    )
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=DATA_SCHEMA_AUTH,
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            name = user_input.get(CONF_NAME, DEFAULT_NAME)
            area = user_input.get(CONF_AREA_ID, DEFAULT_AREA_ID)

            try:
                await self.hass.async_add_executor_job(
                    YaleSmartAlarmClient, username, password
                )
            except AuthenticationError as error:
                LOGGER.error("Authentication failed. Check credentials %s", error)
                errors = {"base": "invalid_auth"}
            except (ConnectionError, TimeoutError, UnknownError) as error:
                LOGGER.error("Connection to API failed %s", error)
                errors = {"base": "cannot_connect"}

            if not errors:
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_NAME: name,
                        CONF_AREA_ID: area,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class YaleOptionsFlowHandler(OptionsFlow):
    """Handle Yale options."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize Yale options flow."""
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Yale options."""
        errors = {}

        if user_input:
            if len(user_input[CONF_CODE]) not in [0, user_input[CONF_LOCK_CODE_DIGITS]]:
                errors["base"] = "code_format_mismatch"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CODE, default=self.entry.options.get(CONF_CODE)
                    ): str,
                    vol.Optional(
                        CONF_LOCK_CODE_DIGITS,
                        default=self.entry.options.get(
                            CONF_LOCK_CODE_DIGITS, DEFAULT_LOCK_CODE_DIGITS
                        ),
                    ): int,
                }
            ),
            errors=errors,
        )
