"""Minimize Garmin records and extract only recognizable measured values."""

from datetime import date
from math import isfinite
from typing import Any

from .errors import ErrorCode, PluginError

ACTIVITY_FIELDS = frozenset(
    "activityId activityName activityType startTimeLocal startTimeGMT distance duration elapsedDuration movingDuration averageHR maxHR calories averageSpeed maxSpeed elevationGain elevationLoss averageRunningCadenceInStepsPerMinute averageBikingCadenceInRevPerMinute averagePower maxPower normalizedPower aerobicTrainingEffect anaerobicTrainingEffect trainingEffectLabel vO2MaxValue lapCount splitSummaries lapDTOs".split()
)
PROFILE_FIELDS = frozenset(
    "measurementSystem timeFormat firstDayOfWeek runningTrainingSpeed activityLevel preferredLocale".split()
)
NESTED_FIELDS = frozenset(
    "typeId typeKey sortOrder lapIndex startTimeGMT startTimeLocal distance duration elapsedDuration movingDuration averageHR maxHR averageSpeed maxSpeed calories elevationGain elevationLoss averagePower maxPower".split()
)

# Alias paths are documented Garmin JSON field names; unknown data never becomes a measurement.
ALIASES = {
    "sleep": {
        "sleepTimeSeconds": "sleep_seconds",
        "deepSleepSeconds": "deep_sleep_seconds",
        "lightSleepSeconds": "light_sleep_seconds",
        "remSleepSeconds": "rem_sleep_seconds",
        "awakeSleepSeconds": "awake_sleep_seconds",
        "sleepScore": "sleep_score",
    },
    "hrv": {"lastNightAvg": "hrv_ms", "lastNight5MinHigh": "hrv_5min_high_ms", "weeklyAvg": "hrv_weekly_ms"},
    "heart_rate": {
        "restingHeartRate": "resting_heart_rate_bpm",
        "minHeartRate": "min_heart_rate_bpm",
        "maxHeartRate": "max_heart_rate_bpm",
    },
    "stress": {"overallStressLevel": "stress", "averageStressLevel": "stress", "avgStressLevel": "stress"},
    "steps": {"totalSteps": "steps", "steps": "steps"},
    "body_battery": {
        "charged": "body_battery_charged",
        "drained": "body_battery_drained",
        "highest": "body_battery_highest",
        "lowest": "body_battery_lowest",
    },
    "hydration": {"valueInML": "hydration_ml", "totalIntakeInML": "hydration_ml"},
    "weight": {"weight": "weight_grams", "bmi": "bmi", "bodyFat": "body_fat_percent"},
    "weight_goals": {"value": "weight_goal_grams", "targetValue": "weight_goal_grams"},
    "spo2": {
        "averageSpO2": "spo2_percent",
        "lowestSpO2": "min_spo2_percent",
        "avgSleepSpO2": "sleep_spo2_percent",
    },
    "fitness_age": {"fitnessAge": "fitness_age_years", "chronologicalAge": "chronological_age_years"},
    "daily_summaries": {
        "totalSteps": "steps",
        "restingHeartRate": "resting_heart_rate_bpm",
        "averageStressLevel": "stress",
        "totalKilocalories": "calories_kcal",
    },
}
ALIASES["sleep_summaries"] = ALIASES["sleep"]
ALIASES["hrv_summaries"] = ALIASES["hrv"]
SAFE_DETAIL_FIELDS = frozenset(
    (
        "calendarDate date startDate endDate status hrvStatus "
        "sleepStartTimestampGMT sleepEndTimestampGMT heartRateValues heartRateValueDescriptors "
        "hrvReadings readingTimeGMT hrvValue heartRateZones zoneNumber zoneLowBoundary zoneUpperBoundary "
        "foodName calories protein carbohydrate fat servingSize amount units cycleDay phase cycleLength "
        "periodLength predictedCycleStartDate predictedPeriodStartDate activityType duration distance "
        "sleepScores overall value qualifierKey"
    ).split()
)


def minimize(value: Any, allowed: frozenset[str], depth: int = 0) -> Any:
    if depth > 8:
        raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
    if isinstance(value, dict):
        return {key: minimize(item, allowed, depth + 1) for key, item in value.items() if key in allowed}
    if isinstance(value, list):
        if len(value) > 12000:
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
        return [minimize(item, allowed, depth + 1) for item in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value if isfinite(value) else None
    if value is None or isinstance(value, (str, bool)):
        return value
    raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)


def normalize_activity(payload) -> dict:
    if not isinstance(payload, dict) or "activityId" not in payload:
        raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
    return minimize(payload, ACTIVITY_FIELDS | NESTED_FIELDS)


def _walk(record, depth=0):
    if depth > 8:
        raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
    if isinstance(record, dict):
        yield record
        for value in record.values():
            if isinstance(value, (dict, list)):
                yield from _walk(value, depth + 1)
    elif isinstance(record, list):
        if len(record) > 12000:
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
        for value in record:
            yield from _walk(value, depth + 1)


def normalize_health(metric: str, payload) -> dict:
    aliases = ALIASES.get(metric, {})
    if payload is None or payload == []:
        return {"days": [], "details": [], "empty": True}
    records = payload
    if isinstance(payload, dict):
        records = payload.get("data", [payload])
    if not isinstance(records, list):
        raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
    days, details = [], []
    recognized = False
    nonempty_records = 0
    for record in records:
        if not isinstance(record, dict):
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
        requested = record.get("calendarDate")
        body = record.get("data", record)
        if body is None:
            continue
        nonempty_records += 1
        parts = list(_walk(body))
        dates = {
            part[key]
            for part in parts
            for key in ("calendarDate", "date")
            if isinstance(part.get(key), str) and len(part[key]) == 10
        }
        if requested and dates and dates != {requested}:
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
        day = requested or next(iter(dates), None)
        measured = {}
        for part in parts:
            for key, output in aliases.items():
                if key in part:
                    val = part[key]
                    if val is None or (
                        isinstance(val, (int, float)) and not isinstance(val, bool) and isfinite(val)
                    ):
                        measured[output] = val
            # Garmin daily statistics often return type/value pairs.
            if part.get("type") in aliases and "value" in part:
                value = part["value"]
                if value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)):
                    measured[aliases[part["type"]]] = value
        detail = minimize(body, SAFE_DETAIL_FIELDS | frozenset(aliases)) if isinstance(body, dict) else {}
        # Preserve recognized nested sections without forwarding account identifiers.
        for part in parts:
            detail.update(minimize(part, SAFE_DETAIL_FIELDS | frozenset(aliases)))
        diagnostic_only = {"calendarDate", "date", "startDate", "endDate", "status", "hrvStatus"}
        if measured or (not aliases and set(detail) - diagnostic_only):
            recognized = True
            if day:
                try:
                    date.fromisoformat(day)
                except (ValueError, TypeError):
                    raise PluginError(ErrorCode.UNEXPECTED_RESPONSE) from None
                days.append({"date": day, "metrics": measured})
            details.append({"date": day, "data": detail})
        else:
            raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
    if not recognized and nonempty_records:
        raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
    return {"days": days, "details": details, "empty": not nonempty_records}
