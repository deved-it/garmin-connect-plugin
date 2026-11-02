"""Safe public errors: never serialize upstream exception strings or bodies."""

from enum import StrEnum

import requests
from garmin_personal_api.errors import HttpError


class ErrorCode(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    AUTH_EXPIRED_OR_REVOKED = "AUTH_EXPIRED_OR_REVOKED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    GARMIN_UNAVAILABLE = "GARMIN_UNAVAILABLE"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    PARTIAL_RESULT = "PARTIAL_RESULT"
    UNEXPECTED_RESPONSE = "UNEXPECTED_RESPONSE"


class PluginError(Exception):
    def __init__(self, code: ErrorCode, message: str = "", retryable: bool = False, retry_after: float = 1.0):
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after
        # Only fixed application-owned messages cross the public boundary.
        super().__init__(code.value)

    def as_dict(self) -> dict:
        return {"code": self.code.value, "retryable": self.retryable}


def map_error(exc: Exception) -> PluginError:
    if isinstance(exc, PluginError):
        return exc
    if isinstance(exc, HttpError):
        status = exc.status_code
        code = {
            400: ErrorCode.INVALID_INPUT,
            401: ErrorCode.AUTH_EXPIRED_OR_REVOKED,
            403: ErrorCode.FORBIDDEN,
            429: ErrorCode.RATE_LIMITED,
        }.get(status, ErrorCode.GARMIN_UNAVAILABLE if status >= 500 else ErrorCode.UNEXPECTED_RESPONSE)
        return PluginError(
            code, retryable=status == 429 or status >= 500, retry_after=getattr(exc, "retry_after", 1.0)
        )
    if isinstance(exc, requests.RequestException):
        return PluginError(ErrorCode.NETWORK_ERROR, retryable=True)
    return PluginError(ErrorCode.UNEXPECTED_RESPONSE)
