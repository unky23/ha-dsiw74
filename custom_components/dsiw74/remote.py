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

    @property
    def is_on(self) -> None:
        """Power state is not exposed by DSIW74 firmware."""
        return None

    async def async_update(self) -> None:
        """Update network availability without guessing ON/standby."""
        try:
            self._info = await self._client.async_get_info()
        except DSIW74ConnectionError:
            self._attr_available = False
        else:
            self._attr_available = True

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle standby, exactly like the physical power button."""
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
