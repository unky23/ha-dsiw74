"""Config flow for compatible CANAL+ decoders."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DSIW74Client, DSIW74ConnectionError, DSIW74UnsupportedDevice
from .const import (
    CONF_AUTO_SYNC_CHANNEL,
    CONF_CHANNEL_PRESETS,
    CONF_ENCODER_URL,
    CONF_MEDIA_PLAYER_ENTITY,
    DEFAULT_AUTO_SYNC_CHANNEL,
    DEFAULT_ENCODER_URL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
)
from .presets import DEFAULT_PRESETS_TEXT, parse_presets

_LOGGER = logging.getLogger(__name__)


def _password_selector() -> selector.TextSelector:
    return selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
    )


def _presets_selector() -> selector.TextSelector:
    return selector.TextSelector(selector.TextSelectorConfig(multiline=True))


def _media_player_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="media_player")
    )


def _normalize_presets(value: str) -> str:
    """Validate and normalize editable channel preset text."""
    value = value.strip()
    parse_presets(value)
    return value


class DSIW74ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a CANAL+ decoder."""

    VERSION = 3
    MINOR_VERSION = 0

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DSIW74OptionsFlow:
        """Return the options flow handler."""
        return DSIW74OptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle manual configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            name = user_input[CONF_NAME].strip() or DEFAULT_NAME
            encoder_url = user_input.get(CONF_ENCODER_URL, "").strip().rstrip("/")
            encoder_username = user_input.get(CONF_USERNAME, "").strip()
            encoder_password = user_input.get(CONF_PASSWORD, "")
            presets_text = user_input.get(CONF_CHANNEL_PRESETS, DEFAULT_PRESETS_TEXT)
            media_player_entity = user_input.get(CONF_MEDIA_PLAYER_ENTITY, "")
            auto_sync_channel = user_input.get(
                CONF_AUTO_SYNC_CHANNEL, DEFAULT_AUTO_SYNC_CHANNEL
            )

            try:
                presets_text = _normalize_presets(presets_text)
            except ValueError:
                errors[CONF_CHANNEL_PRESETS] = "invalid_presets"

            if not errors:
                client = DSIW74Client(host, port, async_get_clientsession(self.hass))
                try:
                    info = await client.async_get_info()
                except DSIW74UnsupportedDevice:
                    errors["base"] = "unsupported_device"
                except DSIW74ConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("Unexpected error while connecting to CANAL+ decoder")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(info.serial)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_NAME: name,
                            CONF_ENCODER_URL: encoder_url,
                            CONF_USERNAME: encoder_username,
                            CONF_PASSWORD: encoder_password,
                            CONF_CHANNEL_PRESETS: presets_text,
                            CONF_MEDIA_PLAYER_ENTITY: media_player_entity,
                            CONF_AUTO_SYNC_CHANNEL: auto_sync_channel,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="192.168.0.100"): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_ENCODER_URL, default=DEFAULT_ENCODER_URL): str,
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): _password_selector(),
                vol.Optional(CONF_MEDIA_PLAYER_ENTITY): _media_player_selector(),
                vol.Required(
                    CONF_AUTO_SYNC_CHANNEL, default=DEFAULT_AUTO_SYNC_CHANNEL
                ): bool,
                vol.Required(
                    CONF_CHANNEL_PRESETS,
                    default=(
                        user_input.get(CONF_CHANNEL_PRESETS, DEFAULT_PRESETS_TEXT)
                        if user_input
                        else DEFAULT_PRESETS_TEXT
                    ),
                ): _presets_selector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class DSIW74OptionsFlow(OptionsFlowWithReload):
    """Allow editing HDMI encoder, media-player sync and channel presets."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage CANAL+ decoder options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_ENCODER_URL] = (
                user_input.get(CONF_ENCODER_URL, "").strip().rstrip("/")
            )
            user_input[CONF_USERNAME] = user_input.get(CONF_USERNAME, "").strip()
            user_input[CONF_MEDIA_PLAYER_ENTITY] = user_input.get(
                CONF_MEDIA_PLAYER_ENTITY, ""
            )
            user_input[CONF_AUTO_SYNC_CHANNEL] = user_input.get(
                CONF_AUTO_SYNC_CHANNEL, DEFAULT_AUTO_SYNC_CHANNEL
            )
            try:
                user_input[CONF_CHANNEL_PRESETS] = _normalize_presets(
                    user_input.get(CONF_CHANNEL_PRESETS, DEFAULT_PRESETS_TEXT)
                )
            except ValueError:
                errors[CONF_CHANNEL_PRESETS] = "invalid_presets"

            if not errors:
                return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        data = self.config_entry.data
        preset_default = current.get(
            CONF_CHANNEL_PRESETS,
            data.get(CONF_CHANNEL_PRESETS, DEFAULT_PRESETS_TEXT),
        )
        if user_input is not None:
            preset_default = user_input.get(CONF_CHANNEL_PRESETS, preset_default)

        media_player_default = current.get(
            CONF_MEDIA_PLAYER_ENTITY, data.get(CONF_MEDIA_PLAYER_ENTITY, "")
        )

        schema_dict: dict[Any, Any] = {
            vol.Required(
                CONF_ENCODER_URL,
                default=current.get(
                    CONF_ENCODER_URL,
                    data.get(CONF_ENCODER_URL, DEFAULT_ENCODER_URL),
                ),
            ): str,
            vol.Optional(
                CONF_USERNAME,
                default=current.get(CONF_USERNAME, data.get(CONF_USERNAME, "")),
            ): str,
            vol.Optional(
                CONF_PASSWORD,
                default=current.get(CONF_PASSWORD, data.get(CONF_PASSWORD, "")),
            ): _password_selector(),
            vol.Required(
                CONF_AUTO_SYNC_CHANNEL,
                default=current.get(
                    CONF_AUTO_SYNC_CHANNEL,
                    data.get(CONF_AUTO_SYNC_CHANNEL, DEFAULT_AUTO_SYNC_CHANNEL),
                ),
            ): bool,
            vol.Required(
                CONF_CHANNEL_PRESETS,
                default=preset_default,
            ): _presets_selector(),
        }

        if media_player_default:
            schema_dict[
                vol.Optional(CONF_MEDIA_PLAYER_ENTITY, default=media_player_default)
            ] = _media_player_selector()
        else:
            schema_dict[vol.Optional(CONF_MEDIA_PLAYER_ENTITY)] = _media_player_selector()

        schema = vol.Schema(schema_dict)
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
