from datetime import date

import pytest
from garmin_personal_api.errors import HttpError
from pydantic import ValidationError

from garmin_connect_plugin.auth import TokenManager
from garmin_connect_plugin.config import Settings
from garmin_connect_plugin.errors import ErrorCode, PluginError, map_error
from garmin_connect_plugin.models import ActivityQuery, HealthQuery


@pytest.mark.parametrize(
    ("status", "want"),
    [
        (401, ErrorCode.AUTH_EXPIRED_OR_REVOKED),
        (403, ErrorCode.FORBIDDEN),
        (429, ErrorCode.RATE_LIMITED),
        (503, ErrorCode.GARMIN_UNAVAILABLE),
    ],
)
def test_upstream_body_never_leaks(status, want):
    exc = HttpError(
        status_code=status,
        method="GET",
        url="https://garmin.test/private",
        response_text="Bearer very-secret-token",
    )
    result = map_error(exc)
    assert result.code == want
    assert "very-secret-token" not in str(result.as_dict())


def test_only_one_auth_refresh(tmp_path):
    from garmin_connect_plugin.credentials import CredentialResolver, save_key

    settings = Settings(config_dir=tmp_path)
    save_key(settings.key_file, "synthetic-key")
    manager = TokenManager(settings, CredentialResolver(settings, environ={}))
    attempts = []

    class Auth:
        def obtain_token(self, key, force_refresh=False):
            from garmin_personal_api.auth import BearerToken

            return BearerToken(access_token="second" if force_refresh else "first", expires_at=9999999999)

        def close(self):
            pass

    manager.auth_factory = lambda: Auth()

    def operation(token):
        attempts.append(token)
        raise HttpError(status_code=401, method="GET", url="https://example.test", response_text="secret")

    with pytest.raises(PluginError) as caught:
        manager.run_with_refresh(operation)
    assert caught.value.code == ErrorCode.AUTH_EXPIRED_OR_REVOKED
    assert attempts == ["first", "second"]


def test_date_and_count_bounds():
    with pytest.raises(ValidationError):
        ActivityQuery(limit=101)
    with pytest.raises(ValidationError):
        HealthQuery(metrics=["sleep"], start_date=date(2026, 3, 2), end_date=date(2026, 3, 1))
    with pytest.raises(ValidationError):
        HealthQuery(
            metrics=["menstrual_cycle_summary"], start_date=date(2026, 3, 1), end_date=date(2026, 3, 1)
        )


def test_registry_dispatch_preserves_zero_and_empty(tmp_path):
    from garmin_connect_plugin.gateway import GarminGateway

    class Tokens:
        def run_with_refresh(self, operation):
            return operation("synthetic")

    class Client:
        def get_daily_stress(self, start, end):
            assert (start, end) == ("2026-03-01", "2026-03-02")
            return [{"calendarDate": "2026-03-01", "value": 0}]

        def close(self):
            pass

    gateway = GarminGateway(Tokens(), client_factory=lambda _: Client(), sleep=lambda _: None)
    assert (
        gateway.health(
            "stress", HealthQuery(metrics=["stress"], start_date=date(2026, 3, 1), end_date=date(2026, 3, 2))
        )[0]["value"]
        == 0
    )
