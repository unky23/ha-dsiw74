"""HDMI encoder client used to determine CANAL+ decoder power state."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import DEFAULT_TIMEOUT


class EncoderError(Exception):
    """Base HDMI encoder error."""


class EncoderConnectionError(EncoderError):
    """Raised when the HDMI encoder cannot be reached or parsed."""


@dataclass(slots=True)
class EncoderInputStatus:
    """Current HDMI input state returned by /get_status."""

    video_ok: bool
    framerate: int
    width: int
    height: int
    int_cnt: int

    @property
    def decoder_on(self) -> bool:
        """Return True when a live HDMI signal is present."""
        return self.video_ok and self.framerate > 0


def _parse_digest_challenge(header: str) -> dict[str, str]:
    """Parse the key/value portion of a Digest WWW-Authenticate header."""
    if not header.lower().startswith("digest "):
        raise EncoderConnectionError("Encoder did not offer Digest authentication")

    params: dict[str, str] = {}
    payload = header[7:]
    for match in re.finditer(r'(\w+)=(?:"([^"]*)"|([^,\s]+))', payload):
        params[match.group(1).lower()] = match.group(2) or match.group(3) or ""
    return params


def _md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


def _digest_authorization(
    *,
    method: str,
    uri: str,
    username: str,
    password: str,
    challenge: dict[str, str],
) -> str:
    """Build a Digest Authorization header for qop=auth / MD5 devices."""
    realm = challenge.get("realm", "")
    nonce = challenge.get("nonce", "")
    algorithm = challenge.get("algorithm", "MD5").upper()
    qop_options = [item.strip() for item in challenge.get("qop", "").split(",") if item.strip()]
    qop = "auth" if "auth" in qop_options else (qop_options[0] if qop_options else "")

    if not realm or not nonce:
        raise EncoderConnectionError("Incomplete Digest authentication challenge")
    if algorithm not in ("MD5", "MD5-SESS"):
        raise EncoderConnectionError(f"Unsupported Digest algorithm: {algorithm}")

    cnonce = os.urandom(8).hex()
    nc = "00000001"
    ha1 = _md5(f"{username}:{realm}:{password}")
    if algorithm == "MD5-SESS":
        ha1 = _md5(f"{ha1}:{nonce}:{cnonce}")
    ha2 = _md5(f"{method}:{uri}")

    if qop:
        response = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    else:
        response = _md5(f"{ha1}:{nonce}:{ha2}")

    parts = [
        f'username="{username}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
        f'response="{response}"',
        f"algorithm={algorithm}",
    ]
    if qop:
        parts.extend([f"qop={qop}", f"nc={nc}", f'cnonce="{cnonce}"'])
    opaque = challenge.get("opaque")
    if opaque:
        parts.append(f'opaque="{opaque}"')
    return "Digest " + ", ".join(parts)


class HDMIEncoderClient:
    """Client for the HiSilicon-based encoder /get_status endpoint."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        session: ClientSession,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._session = session

    @property
    def status_url(self) -> str:
        """Return the status endpoint URL."""
        if self.base_url.endswith("/get_status"):
            return self.base_url
        return f"{self.base_url}/get_status"

    async def _async_get_status_xml(self) -> str:
        """Fetch /get_status, handling the encoder's HTTP Digest auth."""
        timeout = ClientTimeout(total=DEFAULT_TIMEOUT)
        try:
            async with self._session.get(self.status_url, timeout=timeout) as response:
                if response.status == 200:
                    return await response.text()
                if response.status != 401:
                    raise EncoderConnectionError(
                        f"/get_status returned HTTP {response.status}"
                    )
                challenge_header = response.headers.get("WWW-Authenticate", "")
                await response.read()

            if not self.username:
                raise EncoderConnectionError("Encoder requires authentication")

            challenge = _parse_digest_challenge(challenge_header)
            split = urlsplit(self.status_url)
            uri = split.path or "/"
            if split.query:
                uri += f"?{split.query}"
            authorization = _digest_authorization(
                method="GET",
                uri=uri,
                username=self.username,
                password=self.password,
                challenge=challenge,
            )
            async with self._session.get(
                self.status_url,
                timeout=timeout,
                headers={"Authorization": authorization},
            ) as response:
                if response.status != 200:
                    raise EncoderConnectionError(
                        f"Authenticated /get_status returned HTTP {response.status}"
                    )
                return await response.text()
        except (ClientError, TimeoutError) as err:
            raise EncoderConnectionError(str(err)) from err

    async def async_get_input_status(self) -> EncoderInputStatus:
        """Read the HDMI input status from vi id=0."""
        text = await self._async_get_status_xml()
        try:
            root = ET.fromstring(text)
        except ET.ParseError as err:
            raise EncoderConnectionError("Invalid XML from /get_status") from err

        vi = next((item for item in root.findall("vi") if item.get("id") == "0"), None)
        if vi is None:
            raise EncoderConnectionError("/get_status has no vi id=0 section")

        def _int(tag: str) -> int:
            value = vi.findtext(tag, default="0").strip()
            try:
                return int(value)
            except ValueError:
                return 0

        return EncoderInputStatus(
            video_ok=_int("video_ok") == 1,
            framerate=_int("framerate"),
            width=_int("width"),
            height=_int("height"),
            int_cnt=_int("int_cnt"),
        )
