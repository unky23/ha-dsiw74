"""Button entities forming a full DSIW74 remote control and channel presets."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DSIW74ConnectionError
from .entity import DSIW74Entity
from .presets import ChannelPreset


@dataclass(frozen=True, slots=True)
class ButtonDef:
    key: str
    name: str
    icon: str


BUTTONS = (
    ButtonDef("KeyStandBy", "Zasilanie / Standby", "mdi:power"),
    ButtonDef("KeyMenu", "Menu", "mdi:menu"),
    ButtonDef("KeyExit", "Exit", "mdi:exit-to-app"),
    ButtonDef("KeyBack", "Wstecz", "mdi:arrow-u-left-top"),
    ButtonDef("KeyGuide", "EPG / Guide", "mdi:television-guide"),
    ButtonDef("KeyInfo", "Info", "mdi:information-outline"),
    ButtonDef("KeyProgramUp", "Kanał +", "mdi:chevron-up-box-outline"),
    ButtonDef("KeyProgramDown", "Kanał -", "mdi:chevron-down-box-outline"),
    ButtonDef("KeyVolumeUp", "Głośność +", "mdi:volume-plus"),
    ButtonDef("KeyVolumeDown", "Głośność -", "mdi:volume-minus"),
    ButtonDef("KeyMute", "Wycisz", "mdi:volume-mute"),
    ButtonDef("KeyUp", "Góra", "mdi:chevron-up"),
    ButtonDef("KeyDown", "Dół", "mdi:chevron-down"),
    ButtonDef("KeyLeft", "Lewo", "mdi:chevron-left"),
    ButtonDef("KeyRight", "Prawo", "mdi:chevron-right"),
    ButtonDef("KeyOK", "OK", "mdi:checkbox-marked-circle-outline"),
    ButtonDef("KeyZero", "0", "mdi:numeric-0-box-outline"),
    ButtonDef("KeyOne", "1", "mdi:numeric-1-box-outline"),
    ButtonDef("KeyTwo", "2", "mdi:numeric-2-box-outline"),
    ButtonDef("KeyThree", "3", "mdi:numeric-3-box-outline"),
    ButtonDef("KeyFour", "4", "mdi:numeric-4-box-outline"),
    ButtonDef("KeyFive", "5", "mdi:numeric-5-box-outline"),
    ButtonDef("KeySix", "6", "mdi:numeric-6-box-outline"),
    ButtonDef("KeySeven", "7", "mdi:numeric-7-box-outline"),
    ButtonDef("KeyEight", "8", "mdi:numeric-8-box-outline"),
    ButtonDef("KeyNine", "9", "mdi:numeric-9-box-outline"),
    ButtonDef("KeyRed", "Czerwony", "mdi:circle"),
    ButtonDef("KeyGreen", "Zielony", "mdi:circle"),
    ButtonDef("KeyYellow", "Żółty", "mdi:circle"),
    ButtonDef("KeyBlue", "Niebieski", "mdi:circle"),
    ButtonDef("KeyPlay", "Play", "mdi:play"),
    ButtonDef("KeyPause", "Pauza", "mdi:pause"),
    ButtonDef("KeyStop", "Stop", "mdi:stop"),
    ButtonDef("KeyRecord", "Nagrywaj", "mdi:record-rec"),
    ButtonDef("KeyRewind", "Przewiń wstecz", "mdi:rewind"),
    ButtonDef("KeyFForward", "Przewiń do przodu", "mdi:fast-forward"),
    ButtonDef("KeyRecList", "Nagrania", "mdi:playlist-play"),
    ButtonDef("KeyVOD", "VOD", "mdi:movie-open-play-outline"),
    ButtonDef("KeyTVRadio", "TV / Radio", "mdi:radio-tower"),
    ButtonDef("KeyLang", "Język", "mdi:translate"),
    ButtonDef("KeyOPTS", "Opcje", "mdi:tune"),
    ButtonDef("KeySetup", "Ustawienia", "mdi:cog-outline"),
    ButtonDef("KeyMode", "Tryb", "mdi:swap-horizontal"),
    ButtonDef("KeyAt", "@", "mdi:at"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up remote-key and channel-preset buttons."""
    entities = [DSIW74Button(entry, definition) for definition in BUTTONS]
    entities.extend(
        DSIW74PresetButton(entry, preset) for preset in entry.runtime_data.presets
    )
    async_add_entities(entities)


class DSIW74Button(DSIW74Entity, ButtonEntity):
    """A single DSIW74 remote key."""

    def __init__(self, entry: ConfigEntry, definition: ButtonDef) -> None:
        super().__init__(entry)
        self._definition = definition
        self._attr_name = definition.name
        self._attr_icon = definition.icon
        self._attr_unique_id = f"{self._info.serial}_{definition.key.lower()}"

    async def async_press(self) -> None:
        """Send the remote-control key."""
        try:
            await self._client.async_send_key(self._definition.key)
        except DSIW74ConnectionError as err:
            raise HomeAssistantError(f"DSIW74 communication error: {err}") from err


class DSIW74PresetButton(DSIW74Entity, ButtonEntity):
    """A named channel preset that sends the preset channel number."""

    _attr_icon = "mdi:television-play"

    def __init__(self, entry: ConfigEntry, preset: ChannelPreset) -> None:
        super().__init__(entry)
        self._preset = preset
        self._attr_name = f"{preset.name} — kanał {preset.channel}"
        # Slot-based ID keeps the entity stable when only the name/number is edited.
        self._attr_unique_id = f"{self._info.serial}_preset_slot_{preset.slot}"

    @property
    def extra_state_attributes(self) -> dict[str, str | int]:
        """Expose preset metadata for dashboards and automations."""
        return {
            "preset": self._preset.name,
            "channel_number": self._preset.channel,
        }

    async def async_press(self) -> None:
        """Tune the configured numeric channel."""
        try:
            await self._runtime.async_tune_preset(self._preset)
        except DSIW74ConnectionError as err:
            raise HomeAssistantError(f"DSIW74 communication error: {err}") from err
