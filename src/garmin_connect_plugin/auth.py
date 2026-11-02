"""Official Garmin token exchange with one retry after an unauthorized response."""

import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from garmin_personal_api import PersonalApiAuthenticator
from garmin_personal_api.errors import HttpError

from .config import Settings
from .credentials import CredentialResolver
from .errors import map_error
from .transport import GARMIN_ORIGIN, BoundedSession

T = TypeVar("T")


class TokenManager:
    def __init__(self, settings: Settings, resolver: CredentialResolver):
        self.settings = settings
        self.resolver = resolver
        self.auth_factory: Callable[[], Any] = self._authenticator

    def _authenticator(self):
        self.settings.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.settings.token_file.is_symlink():
            from .errors import ErrorCode, PluginError

            raise PluginError(ErrorCode.INVALID_INPUT)
        if self.settings.token_file.exists():
            self.settings.token_file.chmod(0o600)
        auth = PersonalApiAuthenticator(
            timeout=self.settings.timeout,
            bearer_token_cache_file=self.settings.token_file,
            session=BoundedSession(max_bytes=65536),
        )
        # Never permit upstream environment overrides to receive a personal credential.
        auth.base_url = GARMIN_ORIGIN
        logging.getLogger("garmin_personal_api").disabled = True
        return auth

    def get_token(self, force_refresh: bool = False):
        auth = self.auth_factory()
        try:
            return auth.obtain_token(self.resolver.resolve().value, force_refresh=force_refresh)
        except Exception as exc:
            raise map_error(exc) from None
        finally:
            auth.close()

    def run_with_refresh(self, operation: Callable[[str], T]) -> T:
        token = self.get_token()
        try:
            return operation(token.access_token)
        except HttpError as exc:
            if exc.status_code != 401:
                raise map_error(exc) from None
        except Exception as exc:
            raise map_error(exc) from None
        token = self.get_token(force_refresh=True)
        try:
            return operation(token.access_token)
        except Exception as exc:
            raise map_error(exc) from None

    def cache_status(self) -> dict:
        try:
            if self.settings.token_file.is_symlink():
                return {"cached": False}
            data = json.loads(self.settings.token_file.read_text(encoding="utf-8"))
            expiry = float(data["expires_at"])
            return {"cached": True, "expires_at": expiry}
        except (OSError, ValueError, TypeError, KeyError):
            return {"cached": False}
