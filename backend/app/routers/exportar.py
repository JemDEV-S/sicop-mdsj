"""Endpoints de exportacion (HU-21).

- `POST /interno/exportar/excel` { reporte, filtros }  -> binario .xlsx
- `POST /interno/exportar/pdf`   { reporte, filtros }  -> binario .pdf
- `GET  /interno/exportar/reportes`                    -> catalogo de reportes

Auditoria: cada exportacion queda en logs.auditoria (RN-05, AC-21.4).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.exportar import excel as excel_gen
from app.exportar import pdf as pdf_gen
from app.exportar.reportes import listar_reportes, obtener_reporte
from app.security.deps import CurrentUser, get_current_user
from app.services import auditoria_service

router = APIRouter(prefix="/interno/exportar", tags=["interno-exportar"])


class ExportRequest(BaseModel):
    reporte: str = Field(..., description="codigo del reporte (ver /reportes)")
    filtros: dict[str, Any] = Field(default_factory=dict)


class ReporteInfo(BaseModel):
    codigo: str
    titulo: str


@router.get("/reportes", response_model=list[ReporteInfo])
def catalogo_reportes(
    _: CurrentUser = Depends(get_current_user),
) -> list[ReporteInfo]:
    return [ReporteInfo.model_validate(r) for r in listar_reportes()]


def _generar_datos(
    codigo: str, filtros: dict[str, Any], user: CurrentUser, db: Session
):
    rep = obtener_reporte(codigo)
    if rep is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"reporte desconocido: {codigo}",
        )
    datos = rep.obtener_datos(db, filtros, user)
    return rep, datos


def _nombre_archivo(codigo: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{codigo}_{ts}.{ext}"


@router.post("/excel")
def exportar_excel(
    payload: ExportRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    rep, datos = _generar_datos(payload.reporte, payload.filtros, user, db)
    binario = excel_gen.generar(
        rep, datos, filtros=payload.filtros, usuario_nombre=user.nombre_completo
    )
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="exportacion_reporte",
        usuario_id=user.id,
        detalle={
            "reporte": payload.reporte,
            "formato": "excel",
            "filas": len(datos),
            "filtros": payload.filtros,
        },
    )
    db.commit()

    nombre = _nombre_archivo(payload.reporte, "xlsx")
    return Response(
        content=binario,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/pdf")
def exportar_pdf(
    payload: ExportRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    rep, datos = _generar_datos(payload.reporte, payload.filtros, user, db)
    binario = pdf_gen.generar(
        rep, datos, filtros=payload.filtros, usuario_nombre=user.nombre_completo
    )
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="exportacion_reporte",
        usuario_id=user.id,
        detalle={
            "reporte": payload.reporte,
            "formato": "pdf",
            "filas": len(datos),
            "filtros": payload.filtros,
        },
    )
    db.commit()

    nombre = _nombre_archivo(payload.reporte, "pdf")
    return Response(
        content=binario,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
