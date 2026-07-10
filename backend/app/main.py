"""Punto de entrada FastAPI del backend SICOP-MDSJ.

- Base URL API: `/api/v1/`
- Swagger UI: `/api/v1/docs`
- OpenAPI JSON: `/api/v1/openapi.json`
- Liveness: `/health` (fuera del prefix, para orquestadores)

Ver `Docs/actividad-3-arquitectura-tecnica.md` §4.1 (convenciones), §4.7
(CORS), §10.1 (logging), §10.3 (métricas).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.jobs import scheduler as sched
from app.logging_config import configurar_logging, get_logger
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers import (
    admin_jobs,
    anotaciones,
    auth,
    contratos,
    cruce,
    ejecucion_publico,
    exportar,
    health,
    obras,
    obras_documentos,
    observaciones,
    pipeline,
    proveedores,
    saldos,
)

# Configurar structlog + stdlib logging antes de crear la app: así los logs
# emitidos durante el include_router / add_middleware ya salen como JSON.
configurar_logging()
logger = get_logger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranca APScheduler al iniciar la app y lo detiene al cerrar.

    Los sync SIAF/Invierte se disparan en el cron configurado. El estado se
    consulta y se dispara manualmente por `/admin/jobs/*`.
    """
    if settings.APP_ENV != "test":
        sched.iniciar_scheduler()
    try:
        yield
    finally:
        sched.detener_scheduler()


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
        lifespan=lifespan,
    )

    # Middlewares — el orden importa: el último añadido es el más externo.
    # CORS envuelve al request-logger para que el pre-flight OPTIONS también
    # se registre (y para que los errores de CORS aparezcan en el log).
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Total-Count",
            "X-Total-Pages",
            "X-Sincronizado-En",
            "X-Request-ID",
        ],
    )

    # Liveness accesible desde la raíz — para probes de Docker/K8s.
    app.include_router(health.router)
    # También bajo el prefijo API para consistencia con Swagger.
    app.include_router(health.router, prefix=API_PREFIX)

    # Auth
    app.include_router(auth.router, prefix=API_PREFIX)

    # Admin — trigger manual de jobs
    app.include_router(admin_jobs.router, prefix=API_PREFIX)

    # Publico — obras y ejecucion presupuestal
    app.include_router(obras.router, prefix=API_PREFIX)
    app.include_router(ejecucion_publico.router, prefix=API_PREFIX)

    # Buzon ciudadano (publico) + gestion admin
    app.include_router(observaciones.publico_router, prefix=API_PREFIX)
    app.include_router(observaciones.admin_router, prefix=API_PREFIX)

    # Interno — saldos, pipeline, cruce, proveedores, contratos, anotaciones
    app.include_router(saldos.router, prefix=API_PREFIX)
    app.include_router(pipeline.pipeline_router, prefix=API_PREFIX)
    app.include_router(pipeline.pedidos_router, prefix=API_PREFIX)
    app.include_router(pipeline.alertas_router, prefix=API_PREFIX)
    app.include_router(anotaciones.router, prefix=API_PREFIX)
    app.include_router(cruce.router, prefix=API_PREFIX)
    app.include_router(proveedores.publico_router, prefix=API_PREFIX)
    app.include_router(proveedores.interno_router, prefix=API_PREFIX)
    app.include_router(contratos.router, prefix=API_PREFIX)
    app.include_router(contratos.alertas_router, prefix=API_PREFIX)

    # Documentos y fotos de obra (publico + interno) + media
    app.include_router(obras_documentos.publico_router, prefix=API_PREFIX)
    app.include_router(obras_documentos.interno_router, prefix=API_PREFIX)
    app.include_router(obras_documentos.media_router)  # sin API_PREFIX (§4.2)

    # Exportacion Excel + PDF (HU-21)
    app.include_router(exportar.router, prefix=API_PREFIX)

    logger.info("app_ready", env=settings.APP_ENV, prefix=API_PREFIX)
    return app


app = create_app()
