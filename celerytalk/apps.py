from django.apps import AppConfig
from celerytalk import settings


class CelerytalkConfig(AppConfig):
    name = "celerytalk"
    verbose_name = "ReelTalk Celery"

    def ready(self) -> None:
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT or settings.OTEL_EXPORTER_CONSOLE:
            from reeltalk.telemetry import open_telemetry

            open_telemetry.instrumentCelery()
            open_telemetry.instrumentPostgres()
