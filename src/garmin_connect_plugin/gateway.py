"""Bounded official API calls; no arbitrary endpoint or destination URLs."""

import time
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from garmin_personal_api import GarminPersonalApiClient

from .auth import GARMIN_ORIGIN, TokenManager
from .errors import ErrorCode, PluginError
from .models import ActivityQuery, HealthQuery
from .transport import BoundedSession

METRICS = {
    "sleep": ("get_daily_sleep", "date"),
    "sleep_summaries": ("get_daily_sleep_summaries", "range"),
    "hrv": ("get_daily_hrv", "date"),
    "hrv_summaries": ("get_daily_hrv_summaries", "range"),
    "heart_rate": ("get_daily_heart_rate", "date"),
    "heart_rate_zones": ("get_heart_rate_zones", "none"),
    "stress": ("get_daily_stress", "range"),
    "body_battery": ("get_daily_body_battery", "range"),
    "daily_summaries": ("get_daily_summaries", "range"),
    "steps": ("get_daily_steps", "range"),
    "hydration": ("get_daily_hydration", "range"),
    "weight": ("get_weight_measurements", "range"),
    "weight_goals": ("get_effective_weight_goals", "range"),
    "spo2": ("get_daily_spo2", "date"),
    "fitness_age": ("get_fitness_age", "date"),
    "wellness_activities": ("get_wellness_activity_summaries", "range"),
    "food_logs": ("get_daily_food_logs", "date"),
    "menstrual_cycle_summary": ("get_menstrual_cycle_summary", "date"),
    "menstrual_cycle_day_view": ("get_menstrual_cycle_day_view", "date_today"),
}


class GarminGateway:
    def __init__(
        self,
        tokens: TokenManager,
        client_factory: Callable[[str], Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.tokens = tokens
        self.client_factory = client_factory or self._client
        self.sleep = sleep

    def _client(self, token):
        client = GarminPersonalApiClient(
            token, timeout=self.tokens.settings.timeout, session=BoundedSession(max_bytes=50 * 1024 * 1024)
        )
        client.base_url = GARMIN_ORIGIN
        return client

    def call(self, method: str, *args, **kwargs):
        def operation(token):
            client = self.client_factory(token)
            try:
                return getattr(client, method)(*args, **kwargs)
            finally:
                client.close()

        for attempt in range(3):
            try:
                return self.tokens.run_with_refresh(operation)
            except PluginError as exc:
                if not exc.retryable or attempt == 2:
                    raise
                self.sleep(min(5.0, max(float(2**attempt), exc.retry_after)))
        raise PluginError(ErrorCode.GARMIN_UNAVAILABLE)

    def profile(self):
        return self.call("get_user_profile_settings")

    def activities(self, query: ActivityQuery):
        return self.call("search_activities", **query.model_dump(mode="json", exclude_none=True))

    def activity(self, activity_id: str):
        return self.call("get_activity", activity_id)

    def activity_workouts(self, activity_id: str):
        return self.call("get_activity_workouts", activity_id)

    def activity_file(self, activity_id: str):
        return self.call("download_activity", activity_id)

    def health(self, metric: str, query: HealthQuery):
        method, kind = METRICS[metric]
        start, end = query.start_date.isoformat(), query.end_date.isoformat()
        if kind == "none":
            return self.call(method)
        if kind == "range":
            return self.call(method, start, end)
        records = []
        day = query.start_date
        while day <= query.end_date:
            args = (day.isoformat(),)
            if kind == "date_today":
                args += (query.end_date.isoformat(),)
            records.append({"calendarDate": day.isoformat(), "data": self.call(method, *args)})
            day += timedelta(days=1)
        return records
