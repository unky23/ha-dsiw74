"""Shared entity helpers for CANAL+ decoders."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import DSIW74RuntimeData
from .const import DOMAIN


class DSIW74Entity(Entity):
    """Base CANAL+ decoder entity."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        runtime: DSIW74RuntimeData = entry.runtime_data
        self._runtime = runtime
        self._client = runtime.client
        self._info = runtime.info

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device registry information."""
        sw_version = self._info.external_version or self._info.internal_version or None
        return DeviceInfo(
            identifiers={(DOMAIN, self._info.serial)},
            name=self._entry.title,
            manufacturer=self._info.manufacturer or "CANAL+",
            model=self._info.model or "CANAL+ decoder",
            serial_number=self._info.serial,
            sw_version=sw_version,
            configuration_url=self._client.base_url,
        )
