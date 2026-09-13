"""Config flow for HA Smart Dehumidifier."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ABS_HUMIDITY_ENTITY,
    CONF_CURRENT_HUMIDITY_ENTITY,
    CONF_DELTA,
    CONF_DRY_TOLERANCE,
    CONF_FAN_ENTITY,
    CONF_MANUAL_PAUSE,
    CONF_MANUAL_RUNTIME,
    CONF_MAX_HUMIDITY,
    CONF_MIN_HUMIDITY,
    DEFAULT_DELTA,
    DEFAULT_DRY_TOLERANCE,
    DEFAULT_MANUAL_PAUSE,
    DEFAULT_MANUAL_RUNTIME,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
    DOMAIN,
)

CONF_NAME = "name"


def _user_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default="Осушувач"): str,
            vol.Required(CONF_FAN_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch")
            ),
            vol.Optional(CONF_CURRENT_HUMIDITY_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_ABS_HUMIDITY_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        }
    )


class HaSmartDehumidifierConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.pop(CONF_NAME)
            return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_user_schema(), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "HaSmartDehumidifierOptionsFlow":
        return HaSmartDehumidifierOptionsFlow(config_entry)


class HaSmartDehumidifierOptionsFlow(config_entries.OptionsFlow):
    """Handle the tunable numbers (used to be input_number helpers)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DELTA, default=options.get(CONF_DELTA, DEFAULT_DELTA)
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_MIN_HUMIDITY, default=options.get(CONF_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY)
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_MAX_HUMIDITY, default=options.get(CONF_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY)
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_DRY_TOLERANCE,
                    default=options.get(CONF_DRY_TOLERANCE, DEFAULT_DRY_TOLERANCE),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_MANUAL_RUNTIME,
                    default=options.get(CONF_MANUAL_RUNTIME, DEFAULT_MANUAL_RUNTIME),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_MANUAL_PAUSE,
                    default=options.get(CONF_MANUAL_PAUSE, DEFAULT_MANUAL_PAUSE),
                ): vol.Coerce(int),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
