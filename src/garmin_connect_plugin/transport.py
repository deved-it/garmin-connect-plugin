"""Origin-pinned, bounded HTTP transport for the official Garmin client."""

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests
from garmin_personal_api.errors import HttpError

from .errors import ErrorCode, PluginError

GARMIN_ORIGIN = "https://personal.connectapi.garmin.com"


def retry_delay(value: str) -> float:
    try:
        delay = float(value)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 1.0
    return max(0.0, min(delay, 5.0))


class TimedHttpError(HttpError):
    retry_after: float = 1.0


class BoundedSession(requests.Session):
    def __init__(self, max_bytes: int = 8 * 1024 * 1024):
        super().__init__()
        self.max_bytes = max_bytes

    def request(self, method, url, *args, **kwargs):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "personal.connectapi.garmin.com":
            raise PluginError(ErrorCode.INVALID_INPUT)
        kwargs["allow_redirects"] = False
        kwargs["stream"] = True
        response = super().request(method, url, *args, **kwargs)
        try:
            if 300 <= response.status_code < 400:
                raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
            if response.status_code >= 400:
                error = TimedHttpError(
                    status_code=response.status_code, method=method, url=GARMIN_ORIGIN, response_text=""
                )
                error.retry_after = retry_delay(response.headers.get("Retry-After", "1"))
                raise error
            content = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                if len(content) + len(chunk) > self.max_bytes:
                    raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
                content.extend(chunk)
            response._content = bytes(content)
            response._content_consumed = True
            return response
        finally:
            response.close()
