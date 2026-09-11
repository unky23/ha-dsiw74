"""Configurable channel presets for CANAL+ decoders."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class ChannelPreset:
    """A named CANAL+ decoder channel preset."""

    key: str
    name: str
    channel: int
    slot: int


DEFAULT_PRESETS_TEXT = """1 = CANAL+ Sport 1
2 = CANAL+ Sport 2
3 = CANAL+ Sport 3
4 = CANAL+ Sport 4
5 = CANAL+ Sport 5
6 = CANAL+ Sport 6
7 = CANAL+ 360
8 = CANAL+ Extra 1
9 = CANAL+ Extra 2
10 = CANAL+ Extra 3
11 = CANAL+ Extra 4"""


def _slugify(value: str) -> str:
    """Create a predictable key for diagnostics; entity IDs remain HA-managed."""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "preset"


def parse_presets(value: str) -> tuple[ChannelPreset, ...]:
    """Parse editable preset text.

    Accepted line formats:
      1 = CANAL+ Sport 1
      1 | CANAL+ Sport 1
      1 ; CANAL+ Sport 1

    Blank lines and lines beginning with # are ignored. Order is preserved.
    """
    presets: list[ChannelPreset] = []
    used_names: set[str] = set()
    used_channels: set[int] = set()

    for line_no, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        match = re.match(r"^(\d+)\s*(?:=|\||;)\s*(.+?)\s*$", line)
        if match is None:
            raise ValueError(
                f"Line {line_no}: use format 'channel number = preset name'"
            )

        channel = int(match.group(1))
        name = match.group(2).strip()
        if not name:
            raise ValueError(f"Line {line_no}: preset name cannot be empty")
        if channel > 9999:
            raise ValueError(f"Line {line_no}: channel number must be 0..9999")

        normalized_name = name.casefold()
        if normalized_name in used_names:
            raise ValueError(f"Line {line_no}: duplicate preset name '{name}'")
        if channel in used_channels:
            raise ValueError(f"Line {line_no}: duplicate channel number {channel}")

        slot = len(presets) + 1
        presets.append(
            ChannelPreset(
                key=f"slot_{slot}_{_slugify(name)}",
                name=name,
                channel=channel,
                slot=slot,
            )
        )
        used_names.add(normalized_name)
        used_channels.add(channel)

    if not presets:
        raise ValueError("At least one channel preset is required")

    return tuple(presets)
