"""Config flow for Prosegur Alarm integration."""
from collections.abc import Mapping
import logging
from typing import Any, cast

from pyprosegur.auth import COUNTRY, Auth
from pyprosegur.installation import Installation
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client, selector

from .const import CONF_CONTRACT, CONF_COUNTRY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_COUNTRY): vol.In(COUNTRY.keys()),
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""
    session = aiohttp_client.async_get_clientsession(hass)
    auth = Auth(session, data[CONF_USERNAME], data[CONF_PASSWORD], data[CONF_COUNTRY])
    try:
        await Installation.list(auth)
        return auth
    except ConnectionRefusedError:
        raise InvalidAuth from ConnectionRefusedError
    except ConnectionError:
        raise CannotConnect from ConnectionError


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Prosegur Alarm."""

    VERSION = 1
    entry: ConfigEntry
    auth: Auth
    user_input: dict

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input:
            try:
                self.auth = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as exception:  # pylint: disable=broad-except
                _LOGGER.exception(exception)
                errors["base"] = "unknown"
            else:
                self.user_input = user_input
                return await self.async_step_choose_contract()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_choose_contract(self, user_input=None):
        """Let user decide which contract is being setup."""

        if user_input:
            await self.async_set_unique_id(user_input[CONF_CONTRACT])
            self._abort_if_unique_id_configured()

            self.user_input["contract"] = user_input[CONF_CONTRACT]

            return self.async_create_entry(
                title=f"Contract {user_input[CONF_CONTRACT]}", data=self.user_input
            )

        try:
            list_contracts = await Installation.list(self.auth)
        except ConnectionRefusedError:
            raise InvalidAuth from ConnectionRefusedError
        except ConnectionError:
            raise CannotConnect from ConnectionError

        return self.async_show_form(
            step_id="choose_contract",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONTRACT): selector.selector(
                        {
                            "select": {
                                "options": [
                                    {
                                        "value": c["contractId"],
                                        "label": c["description"],
                                    }
                                    for c in list_contracts
                                ]
                            }
                        }
                    ),
                }
            ),
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Handle initiation of re-authentication with Prosegur."""
        self.entry = cast(
            ConfigEntry,
            self.hass.config_entries.async_get_entry(self.context["entry_id"]),
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Handle re-authentication with Prosegur."""
        errors = {}

        if user_input:
            try:
                user_input[CONF_COUNTRY] = self.entry.data[CONF_COUNTRY]
                self.auth = await validate_input(self.hass, user_input)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    data={
                        **self.entry.data,
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self.entry.entry_id)
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME, default=self.entry.data[CONF_USERNAME]
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
