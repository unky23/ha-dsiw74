"""CANAL+ decoder integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event

from .api import DSIW74Client, DSIW74ConnectionError, DSIW74DeviceInfo
from .encoder import HDMIEncoderClient
from .const import (
    CONF_AUTO_SYNC_CHANNEL,
    CONF_CHANNEL_PRESETS,
    CONF_ENCODER_URL,
    CONF_MEDIA_PLAYER_ENTITY,
    DEFAULT_AUTO_SYNC_CHANNEL,
    DEFAULT_ENCODER_URL,
)
from .presets import ChannelPreset, DEFAULT_PRESETS_TEXT, parse_presets

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.REMOTE, Platform.BUTTON, Platform.SELECT]


@dataclass(slots=True)
class DSIW74RuntimeData:
    """Runtime data shared by entity platforms."""

    client: DSIW74Client
    info: DSIW74DeviceInfo
    encoder_url: str
    encoder_username: str
    encoder_password: str
    encoder_client: HDMIEncoderClient | None
    presets: tuple[ChannelPreset, ...]
    media_player_entity: str
    auto_sync_channel: bool
    last_preset_name: str | None = None
    preset_state_listeners: list[Callable[[], None]] = field(default_factory=list)

    async def async_tune_preset(self, preset: ChannelPreset) -> None:
        """Tune a preset and notify entities that expose the last selected preset."""
        await self.client.async_send_channel_number(preset.channel)
        self.last_preset_name = preset.name
        for listener in tuple(self.preset_state_listeners):
            listener()


def _entry_value(entry: ConfigEntry, key: str, default: str = "") -> str:
    """Read an option first and fall back to config-entry data."""
    return str(entry.options.get(key, entry.data.get(key, default)))


def _entry_bool(entry: ConfigEntry, key: str, default: bool) -> bool:
    """Read a boolean option first and fall back to config-entry data."""
    return bool(entry.options.get(key, entry.data.get(key, default)))


def _matching_preset(
    state: State | None, presets_by_name: dict[str, ChannelPreset]
) -> tuple[ChannelPreset, str] | None:
    """Find a preset whose name matches a media-player channel/title attribute."""
    if state is None:
        return None

    # media_channel is the canonical HA attribute for a TV channel. Some media
    # player integrations expose the channel name as media_title instead, so we
    # support both. source is a harmless final fallback for integrations that
    # model live-TV channel selection as a source.
    for attribute in ("media_channel", "media_title", "source"):
        value = state.attributes.get(attribute)
        if not isinstance(value, str):
            continue
        normalized = value.strip().casefold()
        if not normalized:
            continue
        preset = presets_by_name.get(normalized)
        if preset is not None:
            return preset, attribute
    return None


def _setup_media_player_sync(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Follow channel-name changes on a configured media_player entity."""
    runtime: DSIW74RuntimeData = entry.runtime_data
    if not runtime.auto_sync_channel or not runtime.media_player_entity:
        return

    presets_by_name = {preset.name.casefold(): preset for preset in runtime.presets}

    async def _async_handle_change(event: Event) -> None:
        old_state: State | None = event.data.get("old_state")
        new_state: State | None = event.data.get("new_state")

        new_match = _matching_preset(new_state, presets_by_name)
        if new_match is None:
            return

        new_preset, matched_attribute = new_match
        old_match = _matching_preset(old_state, presets_by_name)
        if old_match is not None and old_match[0].name.casefold() == new_preset.name.casefold():
            # The media_player emitted another state update, but the channel did
            # not actually change. Do not repeatedly type the same channel.
            return

        _LOGGER.debug(
            "Media player %s changed to preset %s via %s; tuning decoder channel %s",
            runtime.media_player_entity,
            new_preset.name,
            matched_attribute,
            new_preset.channel,
        )
        try:
            await runtime.async_tune_preset(new_preset)
        except DSIW74ConnectionError as err:
            _LOGGER.warning(
                "Could not sync CANAL+ decoder to media-player channel %s: %s",
                new_preset.name,
                err,
            )

    @callback
    def _handle_change(event: Event) -> None:
        hass.async_create_task(_async_handle_change(event))

    unsub = async_track_state_change_event(
        hass,
        [runtime.media_player_entity],
        _handle_change,
    )
    entry.async_on_unload(unsub)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a CANAL+ decoder from a config entry."""
    client = DSIW74Client(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        async_get_clientsession(hass),
    )
    try:
        info = await client.async_get_info()
    except DSIW74ConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot connect to CANAL+ decoder: {err}") from err

    presets_text = _entry_value(entry, CONF_CHANNEL_PRESETS, DEFAULT_PRESETS_TEXT)
    try:
        presets = parse_presets(presets_text)
    except ValueError:
        presets = parse_presets(DEFAULT_PRESETS_TEXT)

    encoder_url = _entry_value(entry, CONF_ENCODER_URL, DEFAULT_ENCODER_URL).rstrip("/")
    encoder_username = _entry_value(entry, CONF_USERNAME)
    encoder_password = _entry_value(entry, CONF_PASSWORD)
    encoder_client = (
        HDMIEncoderClient(
            encoder_url,
            encoder_username,
            encoder_password,
            async_get_clientsession(hass),
        )
        if encoder_url
        else None
    )

    entry.runtime_data = DSIW74RuntimeData(
        client=client,
        info=info,
        encoder_url=encoder_url,
        encoder_username=encoder_username,
        encoder_password=encoder_password,
        encoder_client=encoder_client,
        presets=presets,
        media_player_entity=_entry_value(entry, CONF_MEDIA_PLAYER_ENTITY),
        auto_sync_channel=_entry_bool(
            entry, CONF_AUTO_SYNC_CHANNEL, DEFAULT_AUTO_SYNC_CHANNEL
        ),
    )

    _setup_media_player_sync(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a CANAL+ decoder config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
