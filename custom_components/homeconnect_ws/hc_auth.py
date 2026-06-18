"""Home Connect profile downloader.

Uses the same Authorization Code + PKCE flow, client ID, and redirect URI as
the bruestel/homeconnect-profile-downloader desktop tool. The user signs in
via their browser and pastes the resulting redirect URL back.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import zipfile
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qs

import aiohttp

_LOGGER = logging.getLogger(__name__)

CLIENT_ID = "9B75AC9EC512F36C84256AC47D813E2C1DD0D6520DF774B020E1E6E2EB29B1F3"
REDIRECT_URI = "hcauth://auth/prod"
SCOPE = "Control DeleteAppliance IdentifyAppliance Images Monitor ReadAccount ReadOrigApi Settings WriteAppliance WriteOrigApi"

REGION_MAP = {
    "EU": ("https://api.home-connect.com", "https://eu.services.home-connect.com"),
    "NA": ("https://api-rna.home-connect.com", "https://na.services.home-connect.com"),
    "CN": ("https://api.home-connect.cn", "https://cn.services.home-connect.cn"),
}

URLENCODED = {"Content-Type": "application/x-www-form-urlencoded"}


class HCAuthError(Exception):
    """Raised on authentication failure."""


@dataclass
class HCAppliance:
    """Appliance profile data."""

    ha_id: str
    brand: str
    vib: str
    mac: str
    appliance_type: str
    identifier: str
    connection_type: str
    key: str
    iv: str | None
    feature_mapping_filename: str
    device_description_filename: str
    device_description_xml: bytes = field(default=b"", repr=False)
    feature_mapping_xml: bytes = field(default=b"", repr=False)

    def to_profile_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "haId": self.ha_id,
            "brand": self.brand,
            "vib": self.vib,
            "mac": self.mac,
            "type": self.appliance_type,
            "identifier": self.identifier,
            "connectionType": self.connection_type,
            "key": self.key,
            "featureMappingFileName": self.feature_mapping_filename,
            "deviceDescriptionFileName": self.device_description_filename,
        }
        if self.iv:
            d["iv"] = self.iv
        return d


def _generate_code_verifier() -> str:
    """Generate a PKCE code verifier."""
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()


def _generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge from verifier."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _generate_nonce(length: int = 16) -> str:
    """Generate a random nonce."""
    return base64.urlsafe_b64encode(os.urandom(length)).rstrip(b"=").decode()


class HCProfileDownloader:
    """Downloads Home Connect appliance profiles using Authorization Code + PKCE flow."""

    def __init__(self, region: str = "EU") -> None:
        self.region = region.upper()
        if self.region not in REGION_MAP:
            raise ValueError(f"Invalid region '{region}'. Use EU, NA, or CN.")
        self.api_base, self.asset_base = REGION_MAP[self.region]
        self._code_verifier = _generate_code_verifier()
        self._state = _generate_nonce()

    def get_authorize_url(self) -> str:
        """Build the authorization URL the user must open in their browser."""
        params = {
            "redirect_url": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "response_type": "code",
            "prompt": "login",
            "code_challenge_method": "S256",
            "code_challenge": _generate_code_challenge(self._code_verifier),
            "state": self._state,
            "nonce": _generate_nonce(),
            "scope": SCOPE,
        }
        return f"{self.api_base}/security/oauth/authorize?{urlencode(params)}"

    def extract_code_from_redirect(self, redirect_url: str) -> str:
        """Extract the authorization code from the redirect URL the user pastes back."""
        try:
            parsed = urlparse(redirect_url)
            params = parse_qs(parsed.query)
            if "code" not in params:
                params = parse_qs(parsed.fragment)
            if "code" not in params:
                raise HCAuthError("No authorization code found in the URL. Make sure you copied the full redirect URL.")
            if params.get("state", [None])[0] != self._state:
                raise HCAuthError("State mismatch. Please restart the sign-in process.")
            return params["code"][0]
        except HCAuthError:
            raise
        except Exception as err:
            raise HCAuthError(f"Could not parse redirect URL: {err}") from err

    async def async_get_access_token(self, code: str) -> str:
        """Exchange authorization code for access token."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/security/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "code_verifier": self._code_verifier,
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                },
                headers=URLENCODED,
            ) as resp:
                text = await resp.text()
                if not text.strip():
                    raise HCAuthError("Token endpoint returned empty response.")
                try:
                    data = json.loads(text)
                except json.JSONDecodeError as err:
                    raise HCAuthError(f"Token endpoint returned non-JSON: {text[:200]}") from err
                if resp.status != 200:
                    raise HCAuthError(f"Token request failed ({resp.status}): {data}")
                token = data.get("access_token")
                if not token:
                    raise HCAuthError(f"No access_token in response: {data}")
                return token

    async def async_get_appliances(self, access_token: str) -> list[HCAppliance]:
        """Fetch appliance profiles using the access token."""
        async with aiohttp.ClientSession() as session:
            payload_b64 = access_token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            hc_id = json.loads(base64.b64decode(payload_b64)).get("sub")
            if not hc_id:
                raise HCAuthError("Could not extract account ID from token")
            _LOGGER.debug("HC: hcId=%s", hc_id)

            auth_headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }

            async with session.get(
                f"{self.asset_base}/api/account/v2/accounts/{hc_id}/paired-appliances",
                headers=auth_headers,
            ) as resp:
                if resp.status == 401:
                    raise HCAuthError("Wrong region. Try a different region.")
                if resp.status != 200:
                    raise HCAuthError(f"paired-appliances failed ({resp.status}): {await resp.text()}")
                data = await resp.json(content_type=None)
                _LOGGER.debug("HC: paired-appliances response: %s", data)

            all_appliances = data.get("appliances", [])
            appliances = [a for a in all_appliances if not a.get("isDemo")]
            if not appliances:
                raise HCAuthError("No appliances found on this account.")
            _LOGGER.debug("HC: found %d appliance(s)", len(appliances))

            results: list[HCAppliance] = []
            for appliance in appliances:
                ha_id: str = appliance.get("haId", "")
                _LOGGER.debug("HC: processing %s", ha_id)

                enc_data: dict[str, Any] = {}
                async with session.get(
                    f"{self.asset_base}/api/appliance/v2/appliances/{ha_id}/encryption-information",
                    headers=auth_headers,
                ) as resp:
                    if resp.status == 200:
                        enc_data = await resp.json(content_type=None)
                        _LOGGER.debug("HC: encryption data: %s", enc_data)
                    else:
                        _LOGGER.warning("No encryption data for %s (%s)", ha_id, resp.status)

                mac = appliance.get("mac", ha_id.split("-")[-1])
                vib = appliance.get("vib", "")
                brand = (appliance.get("brand") or "").upper()
                appliance_type = appliance.get("haType") or appliance.get("type", "")

                if enc_data.get("tls", {}).get("key"):
                    connection_type, key, iv = "TLS", enc_data["tls"]["key"], None
                elif enc_data.get("aes", {}).get("key"):
                    connection_type = "AES"
                    key = enc_data["aes"]["key"]
                    iv = enc_data["aes"].get("iv")
                else:
                    _LOGGER.warning("No encryption key for %s, skipping", ha_id)
                    continue

                desc_xml = b""
                feat_xml = b""
                async with session.get(
                    f"{self.asset_base}/api/iddf/v1/iddf/{ha_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                ) as resp:
                    if resp.status == 200:
                        try:
                            with zipfile.ZipFile(io.BytesIO(await resp.read())) as zf:
                                for name in zf.namelist():
                                    if name.endswith("_DeviceDescription.xml"):
                                        desc_xml = zf.read(name)
                                    elif name.endswith("_FeatureMapping.xml"):
                                        feat_xml = zf.read(name)
                        except zipfile.BadZipFile:
                            _LOGGER.warning("Could not parse IDDF ZIP for %s", ha_id)
                    else:
                        _LOGGER.warning("IDDF fetch failed for %s (%s)", ha_id, resp.status)

                results.append(HCAppliance(
                    ha_id=ha_id,
                    brand=brand,
                    vib=vib,
                    mac=mac,
                    appliance_type=appliance_type,
                    identifier=ha_id,
                    connection_type=connection_type,
                    key=key,
                    iv=iv,
                    feature_mapping_filename=f"{ha_id}_FeatureMapping.xml",
                    device_description_filename=f"{ha_id}_DeviceDescription.xml",
                    device_description_xml=desc_xml,
                    feature_mapping_xml=feat_xml,
                ))

            return results
