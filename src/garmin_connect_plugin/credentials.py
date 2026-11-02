"""Private credential persistence without command-line arguments."""

import getpass
import os
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

from .config import Settings
from .errors import ErrorCode, PluginError


@dataclass(frozen=True)
class ResolvedCredential:
    value: str = field(repr=False)
    source: str


def validate_key(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 8192 or any(c.isspace() for c in value):
        raise PluginError(ErrorCode.NOT_CONFIGURED)
    return value


class CredentialResolver:
    def __init__(self, settings: Settings, environ: Mapping[str, str] | None = None):
        self.settings = settings
        self.environ = os.environ if environ is None else environ

    def resolve(self, app_secret: str | None = None) -> ResolvedCredential:
        if app_secret is not None:
            return ResolvedCredential(validate_key(app_secret), "app")
        sources = [dict(self.environ)]
        if self.settings.plugin_root is not None:
            # No interpolation: a malicious .env cannot resolve arbitrary environment secrets.
            values = dotenv_values(self.settings.plugin_root / ".env", interpolate=False)
            sources.append({k: v or "" for k, v in values.items()})
        for index, env in enumerate(sources):
            for name in ("GARMIN_CONNECT_PERSONAL_API_KEY", "GARMIN_PERSONAL_API_KEY"):
                if name in env:
                    return ResolvedCredential(
                        validate_key(env[name]), "environment" if index == 0 else "dotenv"
                    )
        try:
            if self.settings.key_file.is_symlink():
                raise PluginError(ErrorCode.NOT_CONFIGURED)
            value = self.settings.key_file.read_text(encoding="utf-8")
            return ResolvedCredential(validate_key(value), "private_file")
        except OSError:
            raise PluginError(ErrorCode.NOT_CONFIGURED) from None


def save_key(destination: Path, value: str) -> None:
    value = validate_key(value)
    if destination.is_symlink() or destination.parent.is_symlink():
        raise PluginError(ErrorCode.INVALID_INPUT)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".key-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def configure_key(destination: Path, input_fn: Callable[[str], str] | None = None) -> Path:
    save_key(destination, (input_fn or getpass.getpass)("Garmin Personal API Key (hidden): "))
    return destination
