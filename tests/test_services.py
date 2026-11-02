from datetime import UTC, date, datetime

import pytest

from garmin_connect_plugin.errors import ErrorCode, PluginError
from garmin_connect_plugin.models import HealthQuery, ReportRequest
from garmin_connect_plugin.normalize import normalize_activity, normalize_health
from garmin_connect_plugin.report_service import ReportService


def test_activity_allowlist_drops_private_fields():
    result = normalize_activity(
        {
            "activityId": 42,
            "distance": 0,
            "duration": 600,
            "ownerFullName": "private",
            "email": "private@example.test",
        }
    )
    assert result["activityId"] == 42
    assert result["distance"] == 0
    assert "private" not in str(result)


def test_sleep_extracts_known_metrics_and_preserves_null():
    result = normalize_health(
        "sleep",
        [
            {
                "calendarDate": "2026-03-28",
                "data": {
                    "dailySleepDTO": {
                        "calendarDate": "2026-03-28",
                        "sleepTimeSeconds": 0,
                        "deepSleepSeconds": None,
                        "userProfilePK": 123,
                        "email": "private@example.test",
                    }
                },
            }
        ],
    )
    assert result["days"][0]["metrics"]["sleep_seconds"] == 0
    assert result["days"][0]["metrics"]["deep_sleep_seconds"] is None
    assert "private" not in str(result)


def test_unknown_shape_is_not_successful_empty_data():
    with pytest.raises(PluginError) as caught:
        normalize_health("sleep", {"surprise": "unknown"})
    assert caught.value.code == ErrorCode.UNEXPECTED_RESPONSE


def test_date_without_measurements_is_not_success():
    with pytest.raises(PluginError):
        normalize_health("sleep", {"calendarDate": "2026-03-28", "unknown": 42})


def test_nested_stat_values_are_extracted():
    result = normalize_health(
        "steps", [{"calendarDate": "2026-03-28", "values": [{"type": "totalSteps", "value": 0}]}]
    )
    assert result["days"] == [{"date": "2026-03-28", "metrics": {"steps": 0}}]


def test_wrapped_missing_daily_record_is_empty():
    result = normalize_health("sleep", [{"calendarDate": "2026-03-28", "data": None}])
    assert result["empty"] is True
    assert result["days"] == []


def test_wrong_day_is_not_attributed_to_requested_day():
    with pytest.raises(PluginError):
        normalize_health(
            "sleep",
            [
                {
                    "calendarDate": "2026-03-28",
                    "data": {"dailySleepDTO": {"calendarDate": "2026-03-27", "sleepTimeSeconds": 22000}},
                }
            ],
        )


def test_report_baseline_zero_partial_failure_and_dst():
    class Health:
        def get(self, query: HealthQuery):
            if query.metrics == ["hrv"]:
                return {
                    "status": "unavailable",
                    "sources": {"hrv": {"status": "unavailable", "error": {"code": "FORBIDDEN"}}},
                    "days": [],
                }
            return {
                "status": "ok",
                "sources": {"steps": {"status": "ok"}},
                "days": [
                    {"date": "2026-03-28", "metrics": {"steps": 0}},
                    {"date": "2026-03-29", "metrics": {"steps": 100}},
                    {"date": "2026-03-30", "metrics": {"steps": 999}},
                ],
            }

    class Activities:
        def list(self, query):
            raise PluginError(ErrorCode.FORBIDDEN)

    report = ReportService(Health(), Activities(), clock=lambda: datetime(2026, 3, 30, 10, tzinfo=UTC)).build(
        ReportRequest(
            reference_date=date(2026, 3, 30), sections=["steps", "hrv", "activities"], timezone="Europe/Rome"
        )
    )
    assert report["status"] == "partial"
    assert report["partial_day"] is True
    assert report["baselines"]["7_days"]["steps"] == {"mean": 50.0, "samples": 2}
    assert report["sources"]["activities"]["status"] == "unavailable"
    assert report["days"][0]["date"] == "2026-03-28"


def test_resource_cannot_read_arbitrary_file(tmp_path):
    import io
    import zipfile

    from garmin_connect_plugin.resources import ActivityResourceStore

    content = io.BytesIO()
    with zipfile.ZipFile(content, "w") as archive:
        archive.writestr("activity.fit", b"example")
    store = ActivityResourceStore()
    result = store.create("123", content.getvalue())
    assert store.read(result["uri"]) == content.getvalue()
    with pytest.raises(PluginError):
        store.read("file:///etc/passwd")
    with pytest.raises(PluginError):
        store.create("123", b"not-a-zip")
    store.cleanup()
    with pytest.raises(PluginError):
        store.read(result["uri"])


def test_report_includes_oldest_day_and_paginates():
    class Activities:
        def list(self, query):
            if query.start_date == date(2026, 3, 28):
                return {"activities": [{"activityId": 1}], "next_start": None}
            if query.start == 0:
                return {"activities": [{"activityId": 2}], "next_start": 100}
            return {"activities": [{"activityId": 3}], "next_start": None}

    report = ReportService(None, Activities(), clock=lambda: datetime(2026, 7, 1, tzinfo=UTC)).build(
        ReportRequest(reference_date=date(2026, 6, 26), history_days=90, sections=["activities"])
    )
    assert {a["activityId"] for a in report["activities"]} == {1, 2, 3}
    assert report["sources"]["activities"]["start_date"] == "2026-03-28"


def test_failed_health_source_does_not_leave_uncommitted_records():
    from garmin_connect_plugin.health_service import HealthService

    class Gateway:
        def health(self, metric, query):
            return [
                {"calendarDate": "2026-03-28", "totalSteps": 100},
                {"calendarDate": "2026-03-27", "totalSteps": 200},
            ]

    result = HealthService(Gateway()).get(
        HealthQuery(metrics=["steps"], start_date=date(2026, 3, 28), end_date=date(2026, 3, 28))
    )
    assert result["status"] == "unavailable"
    assert result["days"] == []


def test_mixed_valid_and_unknown_health_records_are_not_silent_success():
    with pytest.raises(PluginError):
        normalize_health(
            "steps",
            [
                {"calendarDate": "2026-03-28", "totalSteps": 100},
                {"calendarDate": "2026-03-29", "unknown": 42},
            ],
        )


def test_activities_only_report_at_cap_is_partial_not_unavailable():
    class Activities:
        def list(self, query):
            return {"activities": [{"activityId": query.start + 1}], "next_start": query.start + 100}

    result = ReportService(None, Activities(), clock=lambda: datetime(2026, 7, 1, tzinfo=UTC)).build(
        ReportRequest(reference_date=date(2026, 6, 30), sections=["activities"])
    )
    assert result["status"] == "partial"
    assert result["sources"]["activities"]["pages"] == 10
    assert len(result["activities"]) == 10
