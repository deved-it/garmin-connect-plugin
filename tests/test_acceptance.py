"""User workflows through real services and MCP, with only Garmin HTTP calls replaced."""

import asyncio
import io
import zipfile

import requests
from garmin_personal_api import GarminPersonalApiClient
from garmin_personal_api.auth import BearerToken

from garmin_connect_plugin.config import Settings
from garmin_connect_plugin.container import ServiceContainer
from garmin_connect_plugin.credentials import CredentialResolver, save_key
from garmin_connect_plugin.server import create_server


def test_read_only_user_workflows(tmp_path):
    async def run():
        services = ServiceContainer.build(Settings(config_dir=tmp_path))
        save_key(services.settings.key_file, "synthetic-key")
        services.status.resolver = CredentialResolver(services.settings, environ={})
        tokens = services.status.tokens
        tokens.resolver = services.status.resolver

        class Auth:
            def obtain_token(self, key, force_refresh=False):
                return BearerToken(access_token="synthetic-token", expires_at=9999999999)

            def close(self):
                pass

        tokens.auth_factory = lambda: Auth()

        class Session:
            def get(self, url, headers, params=None, timeout=None):
                assert headers["Authorization"] == "Bearer synthetic-token"
                result = requests.Response()
                result.status_code = 200
                result.url = url
                if "userprofile" in url:
                    data = {"measurementSystem": "metric", "email": "private@example.test"}
                elif "search/activities" in url:
                    data = [{"activityId": 42, "distance": 10000, "duration": 3000}]
                elif "/workouts" in url:
                    data = {"workoutId": 1, "workoutName": "Run"}
                elif "download-service" in url:
                    output = io.BytesIO()
                    with zipfile.ZipFile(output, "w") as archive:
                        archive.writestr("activity.fit", b"synthetic")
                    result._content = output.getvalue()
                    return result
                elif "activity-service/activity" in url:
                    data = {"activityId": 42, "distance": 10000, "duration": 3000}
                elif "dailySleep" in url:
                    data = {"dailySleepDTO": {"calendarDate": params["date"], "sleepTimeSeconds": 27000}}
                elif "hrv-service/hrv/" in url:
                    data = {"hrvSummary": {"calendarDate": url.rsplit("/", 1)[1], "lastNightAvg": 52}}
                elif "dailyHeartRate" in url:
                    data = {"calendarDate": params["date"], "restingHeartRate": 48}
                elif "stats/stress" in url:
                    data = [{"calendarDate": "2026-03-28", "overallStressLevel": 20}]
                elif "bodyBattery" in url:
                    data = [{"calendarDate": "2026-03-28", "charged": 55, "drained": 35}]
                elif "stats/steps" in url:
                    data = [{"calendarDate": "2026-03-28", "totalSteps": 0}]
                else:
                    raise AssertionError(f"Unhandled synthetic endpoint: {url}")
                import json

                result._content = json.dumps(data).encode()
                return result

            def close(self):
                pass

        gateway = services.status.gateway
        gateway.client_factory = lambda token: GarminPersonalApiClient(token, session=Session())
        server = create_server(services)

        async def call(name, arguments):
            result = await server.call_tool(name, arguments)
            # FastMCP returns the protocol object's fields for structured calls.
            if isinstance(result, tuple):
                data = result[1]
            else:
                data = result.structuredContent
            assert data is not None, result
            assert "synthetic-token" not in str(result)
            assert "private@example.test" not in str(result)
            return data

        assert (await call("garmin_status", {"validate_connection": True}))["status"] == "connected"
        assert (await call("garmin_profile", {}))["profile"] == {"measurementSystem": "metric"}
        assert (await call("garmin_activities", {}))["activities"][0]["activityId"] == 42
        assert (await call("garmin_activity", {"activity_id": "42", "include_workout": True}))["workout"][
            "workoutId"
        ] == 1
        health = await call(
            "garmin_health",
            {
                "metrics": ["sleep", "hrv", "heart_rate", "stress", "body_battery", "steps"],
                "start_date": "2026-03-28",
                "end_date": "2026-03-28",
            },
        )
        assert health["status"] == "ok"
        assert health["days"][0]["metrics"]["steps"] == 0
        report = await call(
            "garmin_report",
            {
                "reference_date": "2026-03-29",
                "history_days": 2,
                "sections": ["steps", "activities"],
                "timezone": "Europe/Rome",
            },
        )
        assert report["baselines"]["7_days"]["steps"] == {"mean": 0.0, "samples": 1}
        downloaded = await call("garmin_activity_file", {"activity_id": "42"})
        assert services.resources.read(downloaded["uri"]).startswith(b"PK")
        invalid = await call(
            "garmin_health",
            {"metrics": ["menstrual_cycle_summary"], "start_date": "2026-03-28", "end_date": "2026-03-28"},
        )
        assert invalid["error"]["code"] == "INVALID_INPUT"
        services.resources.cleanup()

    asyncio.run(run())
