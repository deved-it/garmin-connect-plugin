"""Validated, bounded public requests."""

from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HealthMetric = Literal[
    "sleep",
    "sleep_summaries",
    "hrv",
    "hrv_summaries",
    "heart_rate",
    "heart_rate_zones",
    "stress",
    "body_battery",
    "daily_summaries",
    "steps",
    "hydration",
    "weight",
    "weight_goals",
    "spo2",
    "fitness_age",
    "wellness_activities",
    "food_logs",
    "menstrual_cycle_summary",
    "menstrual_cycle_day_view",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DateRange(StrictModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def ordered(self):
        if not 0 <= (self.end_date - self.start_date).days < 90:
            raise ValueError("Date range must contain 1 to 90 days.")
        return self


class ActivityQuery(StrictModel):
    start: int = Field(default=0, ge=0, le=100000)
    limit: int = Field(default=20, ge=1, le=100)
    start_date: date | None = None
    end_date: date | None = None
    activity_type: str | None = Field(default=None, pattern=r"^[a-zA-Z_]+$", max_length=64)

    @model_validator(mode="after")
    def ordered(self):
        if self.start_date and self.end_date:
            DateRange(start_date=self.start_date, end_date=self.end_date)
        return self


class HealthQuery(DateRange):
    metrics: list[HealthMetric] = Field(min_length=1, max_length=19)
    include_sensitive: bool = False

    @model_validator(mode="after")
    def sensitive_opt_in(self):
        if any(metric.startswith("menstrual_") for metric in self.metrics) and not self.include_sensitive:
            raise ValueError("Sensitive metrics require explicit include_sensitive=true.")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("Duplicate metrics are not permitted.")
        return self


class ReportRequest(StrictModel):
    reference_date: date
    history_days: int = Field(default=28, ge=1, le=90)
    sections: list[Literal["sleep", "hrv", "heart_rate", "stress", "body_battery", "steps", "activities"]] = (
        Field(
            default_factory=lambda: [
                "sleep",
                "hrv",
                "heart_rate",
                "stress",
                "body_battery",
                "steps",
                "activities",
            ],
            min_length=1,
        )
    )
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Unknown timezone.") from None
        return value
