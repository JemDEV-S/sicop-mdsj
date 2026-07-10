"""Configuración de logging estructurado con structlog (T-11).

Objetivos (Docs/actividad-3-arquitectura-tecnica.md §10.1):
- Salida JSON a stdout (Docker/K8s captura stdout).
- Un solo pipeline que unifica el stdlib `logging` y structlog. Cualquier
  librería que use `logging.getLogger(...)` (SQLAlchemy, uvicorn, fastapi)
  termina como JSON estructurado.
- Nivel INFO por defecto, DEBUG activable vía env.
- Formato humano en desarrollo (console renderer con colores) para
  legibilidad rápida, JSON en producción para ingest de un colector.
- Suprimir warnings ruidosos (SQL echo, httpx, etc.) sin perder trazas útiles.

Ejemplo de log de request (RequestLoggingMiddleware, T-11):
    {"ts": "2026-07-09T14:23:45.123Z", "level": "info", "service": "backend",
     "event": "request", "method": "GET", "path": "/api/v1/publico/obras",
     "status": 200, "duration_ms": 42, "usuario_id": null}
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.config import settings

SERVICE_NAME = "backend"


def _es_produccion() -> bool:
    return settings.APP_ENV.lower() in {"production", "prod", "staging"}


def _nivel_root() -> int:
    """Nivel INFO por defecto; DEBUG si APP_ENV=development y LOG_DEBUG=1 en env."""
    import os

    if os.getenv("LOG_DEBUG") == "1":
        return logging.DEBUG
    return logging.INFO


def _agregar_service(_logger: Any, _method_name: str, event_dict: dict) -> dict:
    """Añade `service: "backend"` a todo evento — util al agregar logs."""
    event_dict.setdefault("service", SERVICE_NAME)
    return event_dict


def configurar_logging() -> None:
    """Configura structlog + stdlib logging. Idempotente."""
    nivel = _nivel_root()

    # ── Processors comunes (aplicados a todo evento) ──
    processors_comunes: list[Any] = [
        structlog.contextvars.merge_contextvars,   # inyecta contexto request-scoped
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
        _agregar_service,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Renderer final: JSON en prod, consola con colores en dev.
    if _es_produccion():
        renderer_final: Any = structlog.processors.JSONRenderer()
    else:
        renderer_final = structlog.dev.ConsoleRenderer(colors=True)

    # ── structlog nativo (loggers vía structlog.get_logger) ──
    structlog.configure(
        processors=[
            *processors_comunes,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(nivel),
        cache_logger_on_first_use=True,
    )

    # ── stdlib logging → mismo pipeline (uvicorn, sqlalchemy, etc.) ──
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=processors_comunes,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer_final,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(nivel)

    # Ruido de librerías — bajar a WARNING para que no llenen stdout en prod.
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # uvicorn envia sus propios logs; permitimos INFO (arranque/errores).
    logging.getLogger("uvicorn").setLevel(nivel)
    logging.getLogger("uvicorn.error").setLevel(nivel)


def get_logger(nombre: str | None = None) -> structlog.stdlib.BoundLogger:
    """Fábrica única de loggers estructurados. Usar en toda la app."""
    return structlog.get_logger(nombre)
