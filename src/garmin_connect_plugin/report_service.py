"""Measured baselines only: no fabricated recovery scores or medical advice."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .errors import ErrorCode, PluginError, map_error
from .models import ActivityQuery, HealthQuery, ReportRequest


class ReportService:
    def __init__(self, health, activities, clock=None):
        self.health = health
        self.activities = activities
        self.clock = clock or (lambda: datetime.now(UTC))

    def build(self, request: ReportRequest) -> dict:
        now = self.clock()
        local = now.astimezone(ZoneInfo(request.timezone)) if request.timezone else now.astimezone()
        if request.reference_date > local.date():
            raise PluginError(ErrorCode.INVALID_INPUT)
        end = request.reference_date
        # At most 90 calendar dates per source call; default is previous 28 days plus reference date.
        start = end - timedelta(days=request.history_days)
        sources, days, activities = {}, {}, []
        for section in dict.fromkeys(request.sections):
            try:
                if section == "activities":
                    # Date queries are bounded to 90 days. Split the 91-date maximum-history case.
                    cursor, pages, next_start = start, 0, None
                    while cursor <= end and pages < 10:
                        chunk_end = min(end, cursor + timedelta(days=89))
                        offset = 0
                        while pages < 10:
                            page = self.activities.list(
                                ActivityQuery(start_date=cursor, end_date=chunk_end, start=offset, limit=100)
                            )
                            activities.extend(page["activities"])
                            pages += 1
                            next_start = page.get("next_start")
                            if next_start is None:
                                break
                            if next_start <= offset:
                                raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
                            offset = next_start
                        if next_start is not None:
                            break
                        cursor = chunk_end + timedelta(days=1)
                    sources[section] = {
                        "status": "partial" if next_start is not None or cursor <= end else "ok",
                        "samples": len(activities),
                        "next_start": next_start,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                        "pages": pages,
                    }
                    continue
                cursor = start
                while cursor <= end:
                    chunk_end = min(end, cursor + timedelta(days=89))
                    result = self.health.get(
                        HealthQuery(metrics=[section], start_date=cursor, end_date=chunk_end)
                    )
                    status = result["sources"][section]
                    previous = sources.get(section)
                    sources[section] = (
                        status
                        if not previous
                        else {
                            "status": "partial"
                            if previous["status"] != status["status"]
                            else status["status"],
                            "samples": previous.get("samples", 0) + status.get("samples", 0),
                            "chunks": [previous, status],
                        }
                    )
                    for record in result["days"]:
                        if start.isoformat() <= record["date"] <= end.isoformat():
                            days.setdefault(record["date"], {}).update(record["metrics"])
                    cursor = chunk_end + timedelta(days=1)
            except Exception as exc:
                sources[section] = {"status": "unavailable", "error": map_error(exc).as_dict()}
        baselines = {}
        for window in (7, 28):
            samples = {}
            cutoff = (end - timedelta(days=window)).isoformat()
            for day, measured in days.items():
                if cutoff <= day < end.isoformat():
                    for key, value in measured.items():
                        if isinstance(value, (int, float)) and not isinstance(value, bool):
                            samples.setdefault(key, []).append(value)
            baselines[f"{window}_days"] = {
                key: {"mean": sum(values) / len(values), "samples": len(values)}
                for key, values in samples.items()
            }
        successes = sum(source["status"] in ("ok", "empty") for source in sources.values())
        return {
            "status": "ok"
            if successes == len(sources)
            else "partial"
            if successes or days or activities
            else "unavailable",
            "fetched_at": now.isoformat(),
            "range": {"start_date": start.isoformat(), "end_date": end.isoformat()},
            "partial_day": end == local.date(),
            "timezone": str(local.tzinfo),
            "sources": sources,
            "days": [{"date": day, "metrics": measured} for day, measured in sorted(days.items())],
            "baselines": baselines,
            "activities": activities,
        }
