"""Endpoints publicos de obras (HU-01, HU-02, HU-04).

Sin autenticacion. Solo lectura sobre snapshots MEF (`siaf.inversiones` + `siaf.ejecucion_presupuestal`).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import obras_repo
from app.schemas.obras import (
    ObraDetalleResponse,
    ObraListadoResponse,
    ObrasMapaResponse,
)
from app.services import obras_service

router = APIRouter(prefix="/publico/obras", tags=["publico-obras"])


def _agregar_header_frescura(response: Response, db: Session) -> None:
    """Setea X-Sincronizado-En con el ultimo sync exitoso del SIAF/Invierte."""
    ts = db.execute(
        text(
            """
            SELECT MAX(fin) AS ts
              FROM logs.sincronizacion
             WHERE estado = 'exito'
               AND job LIKE 'siaf%%'
            """
        )
    ).scalar()
    if ts is not None:
        response.headers["X-Sincronizado-En"] = (
            ts.isoformat() if isinstance(ts, datetime) else str(ts)
        )


@router.get("", response_model=ObraListadoResponse)
def listar_obras(
    response: Response,
    db: Session = Depends(get_db),
    ano: int | None = Query(None, description="Ano fiscal, por defecto vigente"),
    funcion: str | None = None,
    tipologia: str | None = None,
    modalidad: str | None = None,
    q: str | None = Query(None, description="Busqueda por nombre o codigo"),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    sort: str = Query("pim_desc"),
) -> ObraListadoResponse:
    offset = (page - 1) * size
    items, total = obras_service.listar_obras(
        db,
        ano=ano,
        funcion=funcion,
        tipologia=tipologia,
        modalidad=modalidad,
        q=q,
        limit=size,
        offset=offset,
        sort=sort,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(max(1, (total + size - 1) // size))
    _agregar_header_frescura(response, db)
    return ObraListadoResponse(items=items, total=total, page=page, size=size)


@router.get("/mapa", response_model=ObrasMapaResponse)
def obras_mapa(
    response: Response,
    db: Session = Depends(get_db),
    ano: int | None = None,
    funcion: str | None = None,
) -> ObrasMapaResponse:
    data = obras_service.obras_para_mapa(db, ano=ano, funcion=funcion)
    _agregar_header_frescura(response, db)
    return ObrasMapaResponse(**data)


@router.get("/funciones", response_model=list[str])
def funciones(db: Session = Depends(get_db)) -> list[str]:
    return obras_repo.funciones_disponibles(db)


@router.get("/tipologias", response_model=list[str])
def tipologias(db: Session = Depends(get_db)) -> list[str]:
    return obras_repo.tipologias_disponibles(db)


@router.get("/{codigo_unico}", response_model=ObraDetalleResponse)
def obtener_obra(
    codigo_unico: str,
    response: Response,
    db: Session = Depends(get_db),
    ano: int | None = None,
) -> ObraDetalleResponse:
    ficha = obras_service.obtener_obra(db, codigo_unico=codigo_unico, ano=ano)
    if ficha is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"obra {codigo_unico} no encontrada",
        )
    _agregar_header_frescura(response, db)
    return ObraDetalleResponse.model_validate(ficha)
