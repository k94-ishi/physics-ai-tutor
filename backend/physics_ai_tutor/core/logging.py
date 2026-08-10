import logging
import logging.config
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from physics_ai_tutor.core.config import settings

access_logger = logging.getLogger("physics_ai_tutor.access")


def configure_logging(environment: str | None = None) -> None:
    environment = environment or settings.environment
    level = "DEBUG" if environment == "development" else "INFO"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-8s %(name)s %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": level,
            },
            "loggers": {
                "uvicorn": {"level": level, "propagate": True},
                "uvicorn.error": {"level": level, "propagate": True},
                "openai": {"level": "WARNING", "propagate": True},
                "httpx": {"level": "WARNING", "propagate": True},
                "httpcore": {"level": "WARNING", "propagate": True},
                "sqlalchemy.engine": {
                    "level": "INFO" if environment == "development" else "WARNING",
                    "propagate": True,
                },
            },
        }
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        access_logger.info("Request: %s %s", request.method, request.url.path)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            access_logger.error(
                "Unhandled exception: %s %s (%.2fms)",
                request.method,
                request.url.path,
                duration_ms,
                exc_info=True,
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        access_logger.info(
            "Response: %s %s %d %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
