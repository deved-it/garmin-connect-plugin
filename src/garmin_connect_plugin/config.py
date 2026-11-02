"""Explicit local paths; never discover .env in arbitrary working directories."""

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_config_path


@dataclass(frozen=True)
class Settings:
    config_dir: Path
    plugin_root: Path | None = None
    timeout: float = 20.0

    @classmethod
    def load(cls, plugin_root: Path | None = None) -> "Settings":
        root = plugin_root
        if root is None and os.environ.get("GARMIN_PLUGIN_ROOT"):
            root = Path(os.environ["GARMIN_PLUGIN_ROOT"]).resolve()
        return cls(
            Path(os.environ.get("GARMIN_PLUGIN_CONFIG_DIR", str(user_config_path("garmin-personal")))), root
        )

    @property
    def key_file(self) -> Path:
        return self.config_dir / "api-key"

    @property
    def token_file(self) -> Path:
        return self.config_dir / "bearer-token.json"
