"""Activity workflows with explicit pagination and bounded output."""

import re

from .errors import ErrorCode, PluginError
from .models import ActivityQuery
from .normalize import ACTIVITY_FIELDS, NESTED_FIELDS, minimize, normalize_activity


def valid_activity_id(value: str) -> str:
    if not re.fullmatch(r"[0-9]{1,24}", value):
        raise PluginError(ErrorCode.INVALID_INPUT)
    return value


class ActivityService:
    def __init__(self, gateway, resources=None):
        from .resources import ActivityResourceStore

        self.gateway = gateway
        self.resources = resources if resources is not None else ActivityResourceStore()

    def list(self, query: ActivityQuery) -> dict:
        records = self.gateway.activities(query)
        if not isinstance(records, list) or len(records) > query.limit:
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
        return {
            "status": "ok",
            "activities": [normalize_activity(item) for item in records],
            "start": query.start,
            "limit": query.limit,
            "next_start": query.start + len(records) if len(records) == query.limit else None,
        }

    def get(self, activity_id: str, include_workout: bool = False) -> dict:
        activity_id = valid_activity_id(activity_id)
        result = {"status": "ok", "activity": normalize_activity(self.gateway.activity(activity_id))}
        if include_workout:
            result["workout"] = minimize(
                self.gateway.activity_workouts(activity_id),
                ACTIVITY_FIELDS
                | NESTED_FIELDS
                | frozenset(
                    "workoutId workoutName workoutSegments workoutSteps stepOrder stepType endCondition endConditionValue targetType targetValueOne targetValueTwo iterations".split()
                ),
            )
        return result

    def file(self, activity_id: str) -> dict:
        activity_id = valid_activity_id(activity_id)
        return {"status": "ok", **self.resources.create(activity_id, self.gateway.activity_file(activity_id))}
