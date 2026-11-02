"""Application composition; nothing accesses Garmin during construction."""

from dataclasses import dataclass

from .activity_service import ActivityService
from .auth import TokenManager
from .config import Settings
from .credentials import CredentialResolver
from .gateway import GarminGateway
from .health_service import HealthService
from .report_service import ReportService
from .resources import ActivityResourceStore
from .status_service import StatusService


@dataclass
class ServiceContainer:
    settings: Settings
    status: StatusService
    activities: ActivityService
    health: HealthService
    reports: ReportService
    resources: ActivityResourceStore

    @classmethod
    def build(cls, settings: Settings | None = None) -> "ServiceContainer":
        settings = settings or Settings.load()
        resolver = CredentialResolver(settings)
        tokens = TokenManager(settings, resolver)
        gateway = GarminGateway(tokens)
        resources = ActivityResourceStore()
        activities, health = ActivityService(gateway, resources), HealthService(gateway)
        return cls(
            settings,
            StatusService(resolver, tokens, gateway),
            activities,
            health,
            ReportService(health, activities),
            resources,
        )
