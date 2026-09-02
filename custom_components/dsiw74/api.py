"""HTTP client for Sagemcom DSIW74 local API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import COMMAND_ALIASES, DEFAULT_TIMEOUT, RAW_COMMANDS


class DSIW74Error(Exception):
    """Base DSIW74 error."""


class DSIW74ConnectionError(DSIW74Error):
    """Raised when the decoder cannot be reached."""


class DSIW74InvalidCommand(DSIW74Error):
    """Raised for an unsupported remote command."""


class DSIW74UnsupportedDevice(DSIW74Error):
    """Raised when the endpoint is not a DSIW74."""


@dataclass(slots=True)
class DSIW74DeviceInfo:
    """Static information returned by /system/version."""

    serial: str
    manufacturer: str
    model: str
    friendly_name: str
    internal_version: str
    external_version: str
    release: str


class DSIW74Client:
    """Client for the DSIW74 web service."""

    def __init__(self, host: str, port: int, session: ClientSession) -> None:
        self.host = host
        self.port = port
        self._session = session
        self._channel_lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def async_get_info(self) -> DSIW74DeviceInfo:
        """Read decoder information."""
        try:
            async with self._session.get(
                f"{self.base_url}/system/version",
                timeout=ClientTimeout(total=DEFAULT_TIMEOUT),
                headers={"Accept": "*/*"},
            ) as response:
                if response.status != 200:
                    raise DSIW74ConnectionError(
                        f"/system/version returned HTTP {response.status}"
                    )
                serial = response.headers.get("Serial", "").strip()
                text = await response.text()
        except (ClientError, TimeoutError) as err:
            raise DSIW74ConnectionError(str(err)) from err

        try:
            data = json.loads(text)
        except (TypeError, ValueError) as err:
            raise DSIW74ConnectionError("Invalid JSON from /system/version") from err

        model = str(data.get("model", "")).strip()
        manufacturer = str(data.get("manufacturer", "")).strip()
        if model.upper() != "DSIW74":
            raise DSIW74UnsupportedDevice(
                f"Expected DSIW74, got {manufacturer} {model}".strip()
            )
        if not serial:
            raise DSIW74ConnectionError("Decoder did not return Serial header")

        return DSIW74DeviceInfo(
            serial=serial,
            manufacturer=manufacturer or "Sagemcom",
            model=model,
            friendly_name=str(data.get("friendly_name", "DEKODER CANAL+")).strip(),
            internal_version=str(data.get("internal_version", "")).strip(),
            external_version=str(data.get("external_version", "")).strip(),
            release=str(data.get("release", "")).strip(),
        )

    @staticmethod
    def normalize_command(command: str) -> str:
        """Convert a friendly alias to the native Key... command."""
        command = command.strip()
        if command in RAW_COMMANDS:
            return command

        alias = COMMAND_ALIASES.get(command.lower())
        if alias is not None:
            return alias

        raise DSIW74InvalidCommand(f"Unsupported DSIW74 command: {command}")

    async def async_send_key(self, command: str) -> None:
        """Send one remote-control key."""
        native_command = self.normalize_command(command)
        try:
            async with self._session.post(
                f"{self.base_url}/control/rcu",
                data={"Keypress": native_command},
                timeout=ClientTimeout(total=DEFAULT_TIMEOUT),
                headers={"Accept": "*/*"},
            ) as response:
                await response.read()
                if response.status < 200 or response.status >= 300:
                    raise DSIW74ConnectionError(
                        f"/control/rcu returned HTTP {response.status}"
                    )
        except (ClientError, TimeoutError) as err:
            raise DSIW74ConnectionError(str(err)) from err
    async def async_send_channel_number(
        self, channel: int, inter_key_delay: float = 0.25
    ) -> None:
        """Tune a numeric channel by dispatching digit key presses.

        Multi-digit numbers are dispatched 250 ms apart without waiting for the
        previous HTTP response. Channel-tune operations themselves are serialized
        so rapid media-player changes cannot interleave digits from two channels.
        """
        if channel < 0:
            raise DSIW74InvalidCommand(f"Invalid channel number: {channel}")

        digit_commands = {
            "0": "KeyZero",
            "1": "KeyOne",
            "2": "KeyTwo",
            "3": "KeyThree",
            "4": "KeyFour",
            "5": "KeyFive",
            "6": "KeySix",
            "7": "KeySeven",
            "8": "KeyEight",
            "9": "KeyNine",
        }

        async with self._channel_lock:
            tasks: list[asyncio.Task[None]] = []
            for index, digit in enumerate(str(channel)):
                if index and inter_key_delay > 0:
                    await asyncio.sleep(inter_key_delay)
                tasks.append(
                    asyncio.create_task(self.async_send_key(digit_commands[digit]))
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException):
                    if isinstance(result, DSIW74Error):
                        raise result
                    raise DSIW74ConnectionError(str(result)) from result
