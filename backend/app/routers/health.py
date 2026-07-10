"""Endpoints de health check.

- `GET /health`           → sin autenticación, siempre 200 si el proceso vive.
- `GET /health/detallado` → verifica PostgreSQL, Redis y SIGA + edad del
                            snapshot SIAF más reciente.

Ver `Docs/actividad-3-arquitectura-tecnica.md` §10.3.

TODO T-08: `/health/detallado` debe requerir rol admin cuando exista el
middleware de auth. Por ahora queda público para desarrollo.
"""

from __future__ import annotations

import logging
from typing import Any

import redis as redis_lib
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.siga.conexion import get_pyodbc_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness")
def health() -> dict[str, str]:
    """Liveness sin dependencias — 200 si el proceso está vivo."""
    return {"status": "ok"}


@router.get("/health/detallado", summary="Readiness (dependencias externas)")
def health_detallado() -> dict[str, Any]:
    """Readiness — chequea PostgreSQL, Redis, SIGA y edad del snapshot SIAF.

    Devuelve `status=ok` si todos los checks pasan; `status=degraded` si
    alguno falla (con el detalle por servicio). Nunca lanza 500 para no
    romper el chequeo del orquestador.
    """
    resultado: dict[str, Any] = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "siga": _check_siga(),
        "siaf_snapshot": _check_siaf_snapshot(),
    }
    todos_ok = all(r.get("ok") for r in resultado.values())
    resultado["status"] = "ok" if todos_ok else "degraded"
    return resultado


# ─── Checks individuales ─────────────────────────────────────────────────

def _check_postgres() -> dict[str, Any]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as exc:
        logger.exception("Health check PostgreSQL fallo")
        return {"ok": False, "error": _fmt_exc(exc)}


def _check_redis() -> dict[str, Any]:
    try:
        client = redis_lib.from_url(settings.REDIS_URL, socket_timeout=2)
        client.ping()
        return {"ok": True}
    except Exception as exc:
        logger.exception("Health check Redis fallo")
        return {"ok": False, "error": _fmt_exc(exc)}


def _check_siga() -> dict[str, Any]:
    try:
        conn = get_pyodbc_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            conn.close()
        return {"ok": True}
    except Exception as exc:
        logger.exception("Health check SIGA fallo")
        return {"ok": False, "error": _fmt_exc(exc)}


def _check_siaf_snapshot() -> dict[str, Any]:
    """Edad del snapshot SIAF más reciente."""
    try:
        with SessionLocal() as db:
            row = db.execute(
                text(
                    """
                    SELECT MAX(sincronizado_en) AS ultimo
                      FROM siaf.ejecucion_presupuestal
                    """
                )
            ).first()
            ultimo = row.ultimo if row else None
            if ultimo is None:
                return {"ok": True, "estado": "sin_datos"}
            return {"ok": True, "ultimo_sync": ultimo.isoformat()}
    except Exception as exc:
        logger.exception("Health check SIAF snapshot fallo")
        return {"ok": False, "error": _fmt_exc(exc)}


def _fmt_exc(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"
