"""Persist the GitHub OAuth token in the OS keychain via ``keyring``.

If the user's machine has no keyring backend at all, ``keyring`` will
raise on save - we degrade to an in-memory cache that lasts for the
current process and surface a warning so the user knows they'll have
to log in next time.
"""

from __future__ import annotations

import logging

import keyring
import keyring.errors

from gui.config import KEYRING_SERVICE, KEYRING_TOKEN_KEY

log = logging.getLogger(__name__)

# Process-lifetime fallback when the OS keyring is unavailable.
_memory_cache: dict[str, str] = {}


def save_token(token: str) -> None:
    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY, token)
    except keyring.errors.KeyringError as exc:  # pragma: no cover - env-specific
        log.warning("OS keyring unavailable; token will not persist: %s", exc)
        _memory_cache[KEYRING_TOKEN_KEY] = token


def load_token() -> str | None:
    try:
        token = keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)
    except keyring.errors.KeyringError as exc:  # pragma: no cover
        log.warning("OS keyring unavailable; using in-memory token: %s", exc)
        return _memory_cache.get(KEYRING_TOKEN_KEY)
    if token:
        return token
    return _memory_cache.get(KEYRING_TOKEN_KEY)


def clear_token() -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass
    except keyring.errors.KeyringError as exc:  # pragma: no cover
        log.warning("OS keyring unavailable on clear: %s", exc)
    _memory_cache.pop(KEYRING_TOKEN_KEY, None)
