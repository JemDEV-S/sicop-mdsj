"""APScheduler embebido en FastAPI.

Registra 2 jobs nocturnos (SIAF + Invierte.pe) que corren secuencialmente
a la hora configurada (por defecto 03:00). Se arranca/para desde el lifespan
de FastAPI (`main.py`) y expone un helper `trigger_manual()` para el endpoint
admin de disparo forzado.

Ver `Docs/actividad-3-arquitectura-tecnica.md` §6.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.jobs.sync_invierte import sync_invierte
from app.jobs.sync_siaf import sync_siaf

logger = logging.getLogger(__name__)


@dataclass
class JobRun:
    """Estado de una ejecucion disparada (para el endpoint /admin/jobs/*)."""

    job_id: str
    nombre: str
    inicio: datetime
    fin: datetime | None = None
    estado: str = "en_curso"   # en_curso | exito | error
    resultado: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


_scheduler: BackgroundScheduler | None = None
_runs: dict[str, JobRun] = {}
_runs_lock = threading.Lock()


def _ejecutar_encadenado_siaf_invierte() -> None:
    """Job nocturno: SIAF primero, Invierte despues (§6.2)."""
    try:
        logger.info("scheduler: iniciando sync_siaf...")
        sync_siaf()
    except Exception:
        logger.exception("scheduler: sync_siaf FALLO")
    try:
        logger.info("scheduler: iniciando sync_invierte...")
        sync_invierte()
    except Exception:
        logger.exception("scheduler: sync_invierte FALLO")


def iniciar_scheduler() -> BackgroundScheduler:
    """Instancia y arranca el scheduler si aun no existe."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="America/Lima")
    _scheduler.add_job(
        _ejecutar_encadenado_siaf_invierte,
        trigger=CronTrigger(
            hour=settings.SYNC_SIAF_HOUR, minute=settings.SYNC_SIAF_MINUTE
        ),
        id="sync_siaf_invierte_nocturno",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "scheduler iniciado (SIAF+Invierte @%02d:%02d America/Lima)",
        settings.SYNC_SIAF_HOUR,
        settings.SYNC_SIAF_MINUTE,
    )
    return _scheduler


def detener_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler detenido")


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler


# ─── Trigger manual (usado por /admin/jobs/*) ────────────────────────────

def _wrap_run(nombre: str, fn: Callable[[], Any]) -> str:
    """Ejecuta `fn` en un thread aparte y registra el estado en `_runs`."""
    job_id = str(uuid.uuid4())
    run = JobRun(job_id=job_id, nombre=nombre, inicio=datetime.utcnow())
    with _runs_lock:
        _runs[job_id] = run

    def _target() -> None:
        try:
            resultado = fn()
            with _runs_lock:
                run.estado = "exito"
                run.fin = datetime.utcnow()
                if resultado is not None and hasattr(resultado, "__dict__"):
                    run.resultado = dict(resultado.__dict__)
        except Exception as exc:
            with _runs_lock:
                run.estado = "error"
                run.fin = datetime.utcnow()
                run.error = f"{type(exc).__name__}: {exc}"
            logger.exception("job %s FALLO", nombre)

    hilo = threading.Thread(target=_target, name=f"job:{nombre}:{job_id[:8]}")
    hilo.daemon = True
    hilo.start()
    return job_id


def trigger_sync_siaf(ano: int | None = None) -> str:
    return _wrap_run("sync_siaf", lambda: sync_siaf(ano=ano))


def trigger_sync_invierte() -> str:
    return _wrap_run("sync_invierte", sync_invierte)


def obtener_run(job_id: str) -> JobRun | None:
    with _runs_lock:
        return _runs.get(job_id)


def listar_runs(limite: int = 20) -> list[JobRun]:
    with _runs_lock:
        runs = sorted(_runs.values(), key=lambda r: r.inicio, reverse=True)
    return runs[:limite]
