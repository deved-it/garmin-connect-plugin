"""Health queries report independent source failures and preserve successful data."""

from datetime import UTC, datetime

from .errors import map_error
from .models import HealthQuery
from .normalize import normalize_health


class HealthService:
    def __init__(self, gateway):
        self.gateway = gateway

    def get(self, query: HealthQuery) -> dict:
        sources, days, details = {}, {}, {}
        for metric in query.metrics:
            try:
                normalized = normalize_health(metric, self.gateway.health(metric, query))
                for record in normalized["days"]:
                    key = record["date"]
                    if not query.start_date.isoformat() <= key <= query.end_date.isoformat():
                        from .errors import ErrorCode, PluginError

                        raise PluginError(ErrorCode.UNEXPECTED_RESPONSE)
                # Commit only after every returned date is validated.
                for record in normalized["days"]:
                    days.setdefault(record["date"], {}).update(record["metrics"])
                details[metric] = normalized["details"]
                sources[metric] = {
                    "status": "empty" if normalized["empty"] else "ok",
                    "samples": len(normalized["days"]),
                }
            except Exception as exc:
                sources[metric] = {"status": "unavailable", "error": map_error(exc).as_dict()}
        success = sum(source["status"] != "unavailable" for source in sources.values())
        return {
            "status": "ok" if success == len(sources) else "partial" if success else "unavailable",
            "fetched_at": datetime.now(UTC).isoformat(),
            "sources": sources,
            "days": [{"date": key, "metrics": value} for key, value in sorted(days.items())],
            "details": details,
        }
