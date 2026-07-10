"""Endpoints publicos de ejecucion presupuestal (HU-05, HU-06)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import ejecucion_service

router = APIRouter(prefix="/publico/ejecucion", tags=["publico-ejecucion"])


def _agregar_header_frescura(response: Response, db: Session) -> None:
    ts = db.execute(
        text(
            """
            SELECT MAX(fin) FROM logs.sincronizacion
             WHERE estado = 'exito' AND job LIKE 'siaf%%'
            """
        )
    ).scalar()
    if ts is not None:
        response.headers["X-Sincronizado-En"] = (
            ts.isoformat() if isinstance(ts, datetime) else str(ts)
        )


@router.get("/resumen")
def resumen(
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    _agregar_header_frescura(response, db)
    return ejecucion_service.resumen(db, ano=ano)


@router.get("/por-funcion")
def por_funcion(
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    _agregar_header_frescura(response, db)
    return ejecucion_service.por_funcion(db, ano=ano)


@router.get("/por-fuente")
def por_fuente(
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    _agregar_header_frescura(response, db)
    return ejecucion_service.por_fuente(db, ano=ano)


@router.get("/mensual")
def mensual(
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    _agregar_header_frescura(response, db)
    return ejecucion_service.mensual(db, ano=ano)


@router.get("/detalle")
def detalle(
    response: Response,
    ano: int | None = None,
    funcion: str | None = None,
    fuente: str | None = None,
    categoria_gasto: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    sort: str = Query("pim_desc"),
    db: Session = Depends(get_db),
) -> dict:
    offset = (page - 1) * size
    items, total = ejecucion_service.detalle(
        db,
        ano=ano,
        funcion=funcion,
        fuente=fuente,
        categoria_gasto=categoria_gasto,
        limit=size,
        offset=offset,
        sort=sort,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(max(1, (total + size - 1) // size))
    _agregar_header_frescura(response, db)
    return {"items": items, "total": total, "page": page, "size": size}
