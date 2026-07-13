"""Endpoint publico de exportacion (T-42.5).

Provee capacidad de exportacion Excel sin autenticacion,
pero con rate limiting estricto y auditoria anonima.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.exportar import excel as excel_gen
from app.exportar.reportes import obtener_reporte
from app.routers.exportar import _nombre_archivo
from app.security.deps import get_client_ip
from app.services import auditoria_service, rate_limit

router = APIRouter(prefix="/publico/exportar", tags=["publico-exportar"])

_MAX_HITS = 2
_VENTANA = 60


class ExportPublicoRequest(BaseModel):
    reporte: str = Field(..., description="codigo del reporte")
    filtros: dict[str, Any] = Field(default_factory=dict)


@router.post("/excel")
def exportar_excel_publico(
    payload: ExportPublicoRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    # 1. Rate limiting estricto por IP
    ip = get_client_ip(request) or "sin-ip"
    if not rate_limit.permitir(f"export_pub:{ip}", max_hits=_MAX_HITS, ventana_seg=_VENTANA):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="demasiadas solicitudes de exportacion desde esta IP, intente en 1 minuto",
        )

    # 2. Solo permitimos reportes publicos autorizados
    if payload.reporte != "ejecucion_detalle":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="este reporte no esta habilitado para exportacion publica",
        )

    rep = obtener_reporte(payload.reporte)
    if rep is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"reporte desconocido: {payload.reporte}",
        )

    # 3. Forzamos hard-cap en los filtros (5001) para detectar desbordamiento
    filtros_seguros = payload.filtros.copy()
    filtros_seguros["limit"] = 5001

    # 4. Generamos sin CurrentUser (user=None)
    datos = rep.obtener_datos(db, filtros_seguros, user=None)
    
    if len(datos) > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La consulta supera el límite de 5000 registros para exportación pública. "
                "Por favor, refine sus filtros (por ejemplo, seleccionando una Función o Fuente específica)."
            ),
        )

    binario = excel_gen.generar(
        rep, datos, filtros=filtros_seguros, usuario_nombre="Visitante Publico"
    )

    # 5. Auditoria anonima (usuario_id=None)
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="exportacion_reporte",
        usuario_id=None,
        detalle={
            "reporte": payload.reporte,
            "formato": "excel",
            "filas": len(datos),
            "filtros_originales": payload.filtros,
            "contexto": "publico",
        },
    )
    db.commit()

    nombre = _nombre_archivo(payload.reporte, "xlsx")
    return Response(
        content=binario,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
