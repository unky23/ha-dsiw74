"""Remote platform for Sagemcom DSIW74."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
import logging
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DSIW74ConnectionError, DSIW74InvalidCommand
from .encoder import EncoderConnectionError
from .entity import DSIW74Entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DSIW74 remote entity."""
    async_add_entities([DSIW74Remote(entry)], update_before_add=True)


class DSIW74Remote(DSIW74Entity, RemoteEntity):
    """Representation of the DSIW74 network remote."""

    _attr_name = "Pilot"
    _attr_icon = "mdi:remote-tv"
    _attr_should_poll = True

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{self._info.serial}_remote"
        self._attr_available = True
        self._decoder_on: bool | None = None
        self._encoder_available = False
        self._input_framerate: int | None = None

    @property
    def is_on(self) -> bool | None:
        """Return real decoder power state based on the HDMI input signal."""
        return self._decoder_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose useful diagnostics for the HDMI-derived power state."""
        return {
            "encoder_available": self._encoder_available,
            "hdmi_input_framerate": self._input_framerate,
            "power_state_source": "hdmi_encoder" if self._encoder_available else None,
        }

    async def _async_read_power_state(self) -> bool | None:
        """Read ON/standby from encoder vi id=0/video_ok."""
        encoder = self._runtime.encoder_client
        if encoder is None:
            self._encoder_available = False
            self._input_framerate = None
            return None
        try:
            status = await encoder.async_get_input_status()
        except EncoderConnectionError as err:
            self._encoder_available = False
            self._input_framerate = None
            _LOGGER.debug("Cannot read HDMI encoder state: %s", err)
            return None

        self._encoder_available = True
        self._input_framerate = status.framerate
        return status.decoder_on

    async def async_update(self) -> None:
        """Update decoder availability and HDMI-derived ON/standby state."""
        try:
            self._info = await self._client.async_get_info()
        except DSIW74ConnectionError:
            self._attr_available = False
        else:
            self._attr_available = True

        self._decoder_on = await self._async_read_power_state()

    async def _async_set_power(self, turn_on: bool) -> None:
        """Set power idempotently even though KeyStandBy itself is a toggle."""
        current = await self._async_read_power_state()
        if current is None:
            raise HomeAssistantError(
                "Cannot determine DSIW74 ON/standby state from the HDMI encoder. "
                "Use remote.toggle if you intentionally want to send the raw standby toggle."
            )
        if current == turn_on:
            self._decoder_on = current
            self.async_write_ha_state()
            return

        try:
            await self._client.async_send_key("KeyStandBy")
        except DSIW74ConnectionError as err:
            raise HomeAssistantError(f"DSIW74 communication error: {err}") from err

        # The HDMI link does not change instantaneously. Poll briefly so the UI
        # reflects the new state without waiting for the next normal HA poll.
        for _ in range(10):
            await asyncio.sleep(0.75)
            new_state = await self._async_read_power_state()
            if new_state == turn_on:
                self._decoder_on = new_state
                self.async_write_ha_state()
                return

        self._decoder_on = await self._async_read_power_state()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the decoder on only if it is currently in standby."""
        await self._async_set_power(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Put the decoder in standby only if it is currently on."""
        await self._async_set_power(False)

    async def async_toggle(self, **kwargs: Any) -> None:
        """Send the raw DSIW74 standby toggle."""
        try:
            await self._client.async_send_key("KeyStandBy")
        except DSIW74ConnectionError as err:
            raise HomeAssistantError(f"DSIW74 communication error: {err}") from err

    async def async_send_command(
        self, command: Iterable[str], **kwargs: Any
    ) -> None:
        """Send one or more DSIW74 remote-control commands."""
        repeats = int(kwargs.get(ATTR_NUM_REPEATS, 1))
        delay = float(kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS))

        try:
            for repeat_index in range(repeats):
                for single_command in command:
                    await self._client.async_send_key(single_command)
                if repeat_index < repeats - 1 and delay > 0:
                    await asyncio.sleep(delay)
        except DSIW74InvalidCommand as err:
            raise HomeAssistantError(str(err)) from err
        except DSIW74ConnectionError as err:
            raise HomeAssistantError(f"DSIW74 communication error: {err}") from err
