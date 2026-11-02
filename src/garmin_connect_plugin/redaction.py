"""Defense in depth for diagnostic text; payload logging is disabled."""

import logging
import re
from collections.abc import Collection


def redact(value, secrets: Collection[str] = ()):
    if isinstance(value, dict):
        return {
            k: "[REDACTED]"
            if re.search(r"authorization|api.?key|token|password", str(k), re.I)
            else redact(v, secrets)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets) for item in value]
    if isinstance(value, BaseException):
        return "[upstream error redacted]"
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return re.sub(r"(?i)(Bearer|ApiKey)\s+[^\s,;]+", r"\1 [REDACTED]", value)
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        return True
