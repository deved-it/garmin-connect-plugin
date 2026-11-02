"""Opaque, session-scoped ZIP resources. No client-supplied filesystem paths."""

import atexit
import io
import tempfile
import uuid
import zipfile
from pathlib import Path

from .errors import ErrorCode, PluginError


class ActivityResourceStore:
    def __init__(self):
        self._directory = tempfile.TemporaryDirectory(prefix="garmin-activity-")
        self._files: dict[str, Path] = {}
        atexit.register(self.cleanup)

    def create(self, activity_id: str, content: bytes) -> dict:
        if not isinstance(content, bytes) or len(content) > 50 * 1024 * 1024:
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if (
                    not archive.namelist()
                    or sum(item.file_size for item in archive.infolist()) > 200 * 1024 * 1024
                ):
                    raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
        except (zipfile.BadZipFile, ValueError):
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE) from None
        nonce = uuid.uuid4().hex
        uri = f"garmin-activity://{activity_id}/{nonce}"
        path = Path(self._directory.name) / nonce
        with path.open("xb") as stream:
            stream.write(content)
        path.chmod(0o600)
        self._files[uri] = path
        return {
            "uri": uri,
            "activity_id": activity_id,
            "mime_type": "application/zip",
            "size_bytes": len(content),
            "lifetime": "server_session",
        }

    def read(self, uri: str) -> bytes:
        if uri not in self._files:
            raise PluginError(ErrorCode.INVALID_INPUT)
        return self._files[uri].read_bytes()

    def cleanup(self) -> None:
        self._files.clear()
        self._directory.cleanup()
