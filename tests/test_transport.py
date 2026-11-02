import pytest
import requests

from garmin_connect_plugin.errors import ErrorCode, PluginError, map_error
from garmin_connect_plugin.transport import BoundedSession


def response(status=200, content=b"{}", headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = content
    result._content_consumed = True
    result.headers.update(headers or {})
    result.url = "https://personal.connectapi.garmin.com/test"
    return result


def test_response_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(requests.Session, "send", lambda *a, **kw: response(content=b"123456789"))
    with pytest.raises(PluginError):
        BoundedSession(max_bytes=8).get("https://personal.connectapi.garmin.com/test")


def test_retry_after_is_capped_and_error_body_not_exposed(monkeypatch):
    monkeypatch.setattr(
        requests.Session, "send", lambda *a, **kw: response(429, b"private-secret", {"Retry-After": "999"})
    )
    with pytest.raises(Exception) as caught:
        BoundedSession().get("https://personal.connectapi.garmin.com/test")
    error = map_error(caught.value)
    assert error.code == ErrorCode.RATE_LIMITED
    assert error.retry_after == 5.0
    assert "private-secret" not in str(error)


def test_arbitrary_origins_and_redirects_are_rejected(monkeypatch):
    session = BoundedSession()
    with pytest.raises(PluginError):
        session.get("https://untrusted.example/test")
    monkeypatch.setattr(
        requests.Session,
        "send",
        lambda *a, **kw: response(302, b"", {"Location": "https://untrusted.example/"}),
    )
    with pytest.raises(PluginError):
        session.get("https://personal.connectapi.garmin.com/test")
