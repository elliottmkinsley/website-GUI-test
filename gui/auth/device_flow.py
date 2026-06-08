"""GitHub OAuth Device Flow client.

Reference:
    https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow

The Qt UI uses ``DeviceFlowWorker`` (a ``QThread``) so the polling
loop doesn't block the event loop. Pure logic functions are exposed
on this module for unit testing without Qt.
"""

from __future__ import annotations

import dataclasses
import logging
import time
from typing import Any

import requests
from PySide6.QtCore import QThread, Signal

from gui.config import GITHUB_OAUTH_SCOPE, resolve_github_client_id

log = logging.getLogger(__name__)

DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
DEFAULT_TIMEOUT = 10  # seconds, per HTTP request


@dataclasses.dataclass
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DeviceCode":
        return cls(
            device_code=payload["device_code"],
            user_code=payload["user_code"],
            verification_uri=payload.get(
                "verification_uri", "https://github.com/login/device"
            ),
            expires_in=int(payload.get("expires_in", 900)),
            interval=int(payload.get("interval", 5)),
        )


class DeviceFlowError(RuntimeError):
    """Raised when the Device Flow cannot proceed (config missing, denied,
    expired, etc.)."""


def request_device_code(
    client_id: str | None = None,
    scope: str = GITHUB_OAUTH_SCOPE,
) -> DeviceCode:
    if client_id is None:
        client_id = resolve_github_client_id()
    if not client_id or client_id.startswith("Iv1.PLACEHOLDER"):
        raise DeviceFlowError(
            "GitHub OAuth Client ID is not configured. Complete the "
            "Setup screen (or set RADIANT_GUI_GITHUB_CLIENT_ID) - see "
            "gui/README.md."
        )
    response = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": scope},
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return DeviceCode.from_payload(response.json())


def _poll_once(
    device_code: str,
    client_id: str | None = None,
) -> tuple[str | None, str | None]:
    if client_id is None:
        client_id = resolve_github_client_id()
    """Single token-poll round-trip.

    Returns ``(token, error)`` where exactly one of the two is set.
    ``error`` may be one of the documented strings:
    ``authorization_pending``, ``slow_down``, ``expired_token``,
    ``access_denied``, or any unexpected payload error.
    """
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        },
        headers={"Accept": "application/json"},
        timeout=DEFAULT_TIMEOUT,
    )
    if not response.ok:
        return None, f"http_{response.status_code}"
    payload = response.json()
    if "access_token" in payload:
        return payload["access_token"], None
    return None, payload.get("error", "unknown_error")


class DeviceFlowWorker(QThread):
    """Polls GitHub until a token is issued or the request expires.

    Signals:
        codeIssued(DeviceCode): emitted once when GitHub returns the
            user code.
        succeeded(str): emitted with the access token when the user
            completes authorization.
        failed(str): emitted with a human-readable error message.
    """

    codeIssued = Signal(object)  # DeviceCode
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: D401 - QThread API
        try:
            code = request_device_code()
        except DeviceFlowError as exc:
            self.failed.emit(str(exc))
            return
        except requests.RequestException as exc:
            self.failed.emit(f"Could not reach GitHub: {exc}")
            return

        self.codeIssued.emit(code)
        deadline = time.monotonic() + code.expires_in
        interval = code.interval

        while not self._cancel and time.monotonic() < deadline:
            time.sleep(interval)
            if self._cancel:
                return
            try:
                token, error = _poll_once(code.device_code)
            except requests.RequestException as exc:
                self.failed.emit(f"Network error while polling GitHub: {exc}")
                return
            if token:
                self.succeeded.emit(token)
                return
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval += 5
                continue
            if error == "expired_token":
                self.failed.emit(
                    "The login code expired before you authorized it. "
                    "Click Try Again to start over."
                )
                return
            if error == "access_denied":
                self.failed.emit(
                    "You denied access. Click Try Again to start over."
                )
                return
            self.failed.emit(f"GitHub returned an unexpected error: {error}")
            return

        if not self._cancel:
            self.failed.emit(
                "Login timed out. Click Try Again to request a new code."
            )
