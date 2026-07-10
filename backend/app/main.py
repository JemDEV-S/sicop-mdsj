"""Punto de entrada FastAPI del backend SICOP-MDSJ.

- Base URL API: `/api/v1/`
- Swagger UI: `/api/v1/docs`
- OpenAPI JSON: `/api/v1/openapi.json`
- Liveness: `/health` (fuera del prefix, para orquestadores)

Ver `Docs/actividad-3-arquitectura-tecnica.md` §4.1 (convenciones), §4.7
(CORS), §10.3 (métricas).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    app = FastAPI(
        title="SICOP-MDSJ API",
        description=(
            "Sistema Integrado de Consulta Presupuestal — Municipalidad "
            "Distrital de San Jerónimo (Cusco)."
        ),
        version="0.1.0",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Total-Pages", "X-Sincronizado-En"],
    )

    # Liveness accesible desde la raíz — para probes de Docker/K8s.
    app.include_router(health.router)
    # También bajo el prefijo API para consistencia con Swagger.
    app.include_router(health.router, prefix=API_PREFIX)

    return app


app = create_app()
