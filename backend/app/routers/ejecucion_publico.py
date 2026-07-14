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
    rubro: str | None = None,
    generica: str | None = None,
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
        rubro=rubro,
        generica=generica,
        categoria_gasto=categoria_gasto,
        limit=size,
        offset=offset,
        sort=sort,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(max(1, (total + size - 1) // size))
    _agregar_header_frescura(response, db)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/jerarquia")
def jerarquia(
    response: Response,
    ano: int | None = None,
    nivel: str = Query("funcion", pattern="^(funcion|producto|meta)$"),
    padre_funcion: str | None = None,
    padre_producto: str | None = None,
    filtro_rubro: str | None = None,
    filtro_generica: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Drill-down ciudadano: Funcion -> Producto/Proyecto -> Meta.

    Rubro y generica NO son niveles (son transversales, N:N con la meta).
    Se aplican como filtros opcionales que refinan el drill.

    Cada fila: codigo, nombre, tipo, pim, devengado, girado, certificado,
    porcentaje_ejecucion, participacion_pim, tiene_hijos.
    """
    _agregar_header_frescura(response, db)
    return ejecucion_service.jerarquia(
        db,
        ano=ano,
        nivel=nivel,
        padre_funcion=padre_funcion,
        padre_producto=padre_producto,
        filtro_rubro=filtro_rubro,
        filtro_generica=filtro_generica,
    )


@router.get("/por-rubro")
def por_rubro(
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Distribucion por rubro (¿de donde viene el dinero?)."""
    _agregar_header_frescura(response, db)
    return ejecucion_service.por_rubro(db, ano=ano)


@router.get("/por-generica")
def por_generica(
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Distribucion por generica (¿en que tipo de gasto?)."""
    _agregar_header_frescura(response, db)
    return ejecucion_service.por_generica(db, ano=ano)


@router.get("/mensual-acumulado")
def mensual_acumulado(
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Evolucion mensual con acumulado calculado en backend.

    Cada fila trae flujo del mes + acumulado del anio (SUM OVER).
    Ver Docs/hallazgos-granularidad-siaf.md.
    """
    _agregar_header_frescura(response, db)
    return ejecucion_service.mensual_acumulado(db, ano=ano)


@router.get("/meta/{sec_func}/desglose")
def meta_desglose(
    sec_func: int,
    response: Response,
    ano: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Desglose N:N de una meta: filas por combinacion (rubro, generica).

    Response:
      { cabecera: {sec_func, meta_nombre, funcion_nombre, producto_proyecto_nombre,
                   pim, devengado, ...},
        filas: [{ rubro_codigo, rubro_nombre, generica_codigo, generica_nombre,
                  pim, devengado, ... }] }
    """
    _agregar_header_frescura(response, db)
    return ejecucion_service.desglose_meta(db, sec_func=sec_func, ano=ano)
