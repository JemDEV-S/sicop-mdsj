"""Middleware que registra cada request con duración (T-11).

Emite un evento `request` en JSON:
    {"ts": "...", "level": "info", "service": "backend", "event": "request",
     "method": "GET", "path": "/api/v1/publico/obras", "status": 200,
     "duration_ms": 42, "request_id": "9f...", "client_ip": "...", "usuario_id": null}

Detalles:
- Genera un `request_id` (UUID4 hex) y lo inyecta en el contextvars de structlog
  para que TODOS los logs emitidos durante ese request lo hereden. También se
  devuelve como header `X-Request-ID` para trazar del cliente al backend.
- La duración se mide con `time.perf_counter()` para evitar el jitter del reloj
  del sistema.
- No hay `usuario_id` a este nivel — el middleware corre antes que las
  dependencies de auth. Los endpoints pueden enriquecer el contexto llamando
  `structlog.contextvars.bind_contextvars(usuario_id=...)`.
- Los healthchecks se registran a DEBUG (evitan ruido en prod).
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.logging_config import get_logger

logger = get_logger(__name__)

_PATHS_SILENCIOSOS = frozenset({"/health", "/api/v1/health"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Registra cada request HTTP en formato estructurado."""

    def __init__(self, app: ASGIApp, header_request_id: str = "X-Request-ID") -> None:
        super().__init__(app)
        self._header = header_request_id

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self._header) or uuid.uuid4().hex

        # contextvars — cualquier log emitido en handlers hereda estos campos.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        inicio = time.perf_counter()
        status_code = 500  # fallback si algo revienta antes del response
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[self._header] = request_id
            return response
        except Exception:
            logger.exception("request_error")
            raise
        finally:
            duration_ms = int((time.perf_counter() - inicio) * 1000)
            evento = {
                "event": "request",
                "status": status_code,
                "duration_ms": duration_ms,
                "client_ip": _client_ip(request),
            }
            # Healthchecks a DEBUG, resto a INFO. Errores 5xx elevados a error.
            if status_code >= 500:
                logger.error(**evento)
            elif request.url.path in _PATHS_SILENCIOSOS:
                logger.debug(**evento)
            else:
                logger.info(**evento)
            # Limpiar contextvars para no filtrar entre requests.
            structlog.contextvars.clear_contextvars()


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
