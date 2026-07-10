"""Endpoints admin de trigger manual del sync SIAF/Invierte.

Requieren rol `admin` (Depends require_role). Ver `Docs/actividad-3-arquitectura-tecnica.md`
§6.3 (trigger manual) y §4.5 (endpoints admin).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.jobs import scheduler as sched
from app.models.enums import CodigoRol
from app.security.deps import CurrentUser, require_role
from app.services import auditoria_service

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])


class TriggerResponse(BaseModel):
    job_id: str
    nombre: str
    estado: str


class RunEstadoResponse(BaseModel):
    job_id: str
    nombre: str
    inicio: datetime
    fin: datetime | None
    estado: str
    resultado: dict | None = None
    error: str | None = None


@router.post(
    "/sincronizar-siaf",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_sync_siaf(
    request: Request,
    ano: int | None = None,
    user: CurrentUser = Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> TriggerResponse:
    job_id = sched.trigger_sync_siaf(ano=ano)
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="trigger_sync_siaf",
        usuario_id=user.id,
        detalle={"job_id": job_id, "ano": ano},
    )
    db.commit()
    return TriggerResponse(job_id=job_id, nombre="sync_siaf", estado="en_curso")


@router.post(
    "/sincronizar-invierte",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_sync_invierte(
    request: Request,
    user: CurrentUser = Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> TriggerResponse:
    job_id = sched.trigger_sync_invierte()
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="trigger_sync_invierte",
        usuario_id=user.id,
        detalle={"job_id": job_id},
    )
    db.commit()
    return TriggerResponse(job_id=job_id, nombre="sync_invierte", estado="en_curso")


@router.get("/{job_id}", response_model=RunEstadoResponse)
def estado_run(
    job_id: str,
    _: CurrentUser = Depends(require_role(CodigoRol.admin)),
) -> RunEstadoResponse:
    run = sched.obtener_run(job_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="job_id no encontrado"
        )
    return RunEstadoResponse(
        job_id=run.job_id,
        nombre=run.nombre,
        inicio=run.inicio,
        fin=run.fin,
        estado=run.estado,
        resultado=run.resultado or None,
        error=run.error,
    )


@router.get("", response_model=list[RunEstadoResponse])
def listar(
    _: CurrentUser = Depends(require_role(CodigoRol.admin)),
) -> list[RunEstadoResponse]:
    return [
        RunEstadoResponse(
            job_id=r.job_id,
            nombre=r.nombre,
            inicio=r.inicio,
            fin=r.fin,
            estado=r.estado,
            resultado=r.resultado or None,
            error=r.error,
        )
        for r in sched.listar_runs()
    ]
