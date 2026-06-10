"""Config flow for Clever Caravan: Power."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback

from .const import (
    CONF_CURRENT_LIMIT_MAX,
    CONF_CURRENT_LIMIT_MIN,
    CONF_PORTAL_ID,
    CONF_SSH_KEY,
    CONF_USE_SSL,
    DEFAULT_CURRENT_LIMIT_MAX,
    DEFAULT_CURRENT_LIMIT_MIN,
    DEFAULT_HOST,
    DEFAULT_SSH_KEY,
    DEFAULT_PORT,
    DOMAIN,
)
from .hub import VenusHub

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_USERNAME, default=""): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_USE_SSL, default=False): bool,
    }
)


def _probe(user_input: dict[str, Any]) -> str | None:
    """Connect briefly and return the detected portal ID (runs in executor)."""
    hub = VenusHub(
        host=user_input[CONF_HOST],
        port=user_input[CONF_PORT],
        username=user_input.get(CONF_USERNAME) or None,
        password=user_input.get(CONF_PASSWORD) or None,
        use_ssl=user_input.get(CONF_USE_SSL, False),
    )
    try:
        hub.start()
        return hub.wait_for_portal(12.0)
    finally:
        hub.stop()


class CcpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                portal_id = await self.hass.async_add_executor_job(_probe, user_input)
            except OSError:
                portal_id = None
                errors["base"] = "cannot_connect"
            if portal_id:
                await self.async_set_unique_id(portal_id)
                self._abort_if_unique_id_configured()
                user_input[CONF_PORTAL_ID] = portal_id
                return self.async_create_entry(
                    title=f"Cerbo GX ({portal_id})", data=user_input
                )
            errors.setdefault("base", "no_portal")

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CcpOptionsFlow()


class CcpOptionsFlow(config_entries.OptionsFlow):
    """Per-install tuning (shore breaker limits etc.)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CURRENT_LIMIT_MIN,
                    default=options.get(CONF_CURRENT_LIMIT_MIN, DEFAULT_CURRENT_LIMIT_MIN),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_CURRENT_LIMIT_MAX,
                    default=options.get(CONF_CURRENT_LIMIT_MAX, DEFAULT_CURRENT_LIMIT_MAX),
                ): vol.Coerce(float),
                vol.Required(
                    CONF_SSH_KEY,
                    default=options.get(CONF_SSH_KEY, DEFAULT_SSH_KEY),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
