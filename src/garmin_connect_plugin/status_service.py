"""Minimal profile and offline configuration status."""

from . import __version__
from .errors import PluginError
from .normalize import PROFILE_FIELDS, minimize


class StatusService:
    def __init__(self, resolver, tokens, gateway):
        self.resolver, self.tokens, self.gateway = resolver, tokens, gateway

    def status(self, validate_connection: bool = False) -> dict:
        try:
            credential = self.resolver.resolve()
        except PluginError:
            return {"status": "not_configured", "version": __version__, "network_checked": False}
        result = {
            "status": "configured",
            "source": credential.source,
            "version": __version__,
            "token": self.tokens.cache_status(),
            "network_checked": False,
        }
        if validate_connection:
            self.gateway.profile()
            result["network_checked"] = True
            result["status"] = "connected"
        return result

    def profile(self) -> dict:
        return {"status": "ok", "profile": minimize(self.gateway.profile(), PROFILE_FIELDS)}
