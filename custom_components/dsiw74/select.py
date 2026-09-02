"""Channel-preset select entity for Sagemcom DSIW74."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DSIW74ConnectionError
from .entity import DSIW74Entity
from .presets import ChannelPreset


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the channel-preset selector."""
    async_add_entities([DSIW74PresetSelect(entry)])


class DSIW74PresetSelect(DSIW74Entity, SelectEntity):
    """Select a named channel preset and send its numeric channel number."""

    _attr_name = "Preset kanału"
    _attr_icon = "mdi:format-list-numbered"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._presets: tuple[ChannelPreset, ...] = entry.runtime_data.presets
        self._presets_by_name = {preset.name: preset for preset in self._presets}
        self._attr_options = [preset.name for preset in self._presets]
        self._attr_unique_id = f"{self._info.serial}_channel_preset"

    @property
    def current_option(self) -> str | None:
        """Return the last preset tuned by the integration."""
        value = self._runtime.last_preset_name
        return value if value in self._presets_by_name else None

    async def async_select_option(self, option: str) -> None:
        """Tune the channel associated with a preset name."""
        preset = self._presets_by_name.get(option)
        if preset is None:
            raise HomeAssistantError(f"Unknown DSIW74 preset: {option}")
        try:
            await self._runtime.async_tune_preset(preset)
        except DSIW74ConnectionError as err:
            raise HomeAssistantError(f"DSIW74 communication error: {err}") from err

    async def async_added_to_hass(self) -> None:
        """Subscribe to preset changes made by buttons or media-player sync."""
        await super().async_added_to_hass()
        self._runtime.preset_state_listeners.append(self._handle_preset_change)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from shared preset state updates."""
        if self._handle_preset_change in self._runtime.preset_state_listeners:
            self._runtime.preset_state_listeners.remove(self._handle_preset_change)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_preset_change(self) -> None:
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Expose the numeric channel for the last selected preset."""
        current = self.current_option
        if current is None:
            return None
        preset = self._presets_by_name[current]
        return {"channel_number": preset.channel}
