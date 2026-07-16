"""Endpoints internos de saldos (HU-15, HU-16, HU-22). Requieren JWT + filtro por CC."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.saldos import (
    MetaRezagadaItem,
    SaldoItem,
    SaldosListadoResponse,
    SaldosResumenResponse,
)
from app.security.deps import CurrentUser, get_current_user
from app.services import permisos_service, saldos_service

router = APIRouter(prefix="/interno/saldos", tags=["interno-saldos"])


@router.get("", response_model=SaldosListadoResponse)
def listar(
    ano: int | None = None,
    sec_func: int | None = None,
    clasificador: str | None = None,
    fuente_financ: str | None = None,
    centro_costo: str | None = Query(
        None,
        description="Restringe el listado a la subrama del CC indicado (dentro del alcance del usuario).",
    ),
    solo_con_pim: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SaldosListadoResponse:
    centros = permisos_service.restringir_a_subrama(
        db, user.centros_permitidos, centro_costo
    )
    offset = (page - 1) * size
    items, total = saldos_service.listar_saldos(
        db,
        ano=ano or settings.ANO_VIGENTE,
        centros=centros,
        sec_func=sec_func,
        clasificador=clasificador,
        fuente_financ=fuente_financ,
        solo_con_pim=solo_con_pim,
        limit=size,
        offset=offset,
    )
    return SaldosListadoResponse(
        items=[SaldoItem.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/resumen", response_model=SaldosResumenResponse)
def resumen(
    ano: int | None = None,
    centro_costo: str | None = Query(
        None,
        description="Restringe el resumen a la subrama del CC indicado.",
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SaldosResumenResponse:
    """Totales agregados (PIM, devengado, saldo, %) + top-3 metas críticas.

    Se usa en el dashboard T-44 para evitar traer el listado completo y sumar
    en el cliente (fuente única de verdad para los KPIs del dashboard).
    """
    centros = permisos_service.restringir_a_subrama(
        db, user.centros_permitidos, centro_costo
    )
    data = saldos_service.resumen_saldos(
        db,
        ano=ano or settings.ANO_VIGENTE,
        centros=centros,
    )
    return SaldosResumenResponse.model_validate(data)


@router.get("/metas-rezagadas", response_model=list[MetaRezagadaItem])
def metas_rezagadas(
    ano: int | None = None,
    umbral_porcentaje: float = Query(50.0, ge=0, le=100),
    centro_costo: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MetaRezagadaItem]:
    centros = permisos_service.restringir_a_subrama(
        db, user.centros_permitidos, centro_costo
    )
    items = saldos_service.metas_rezagadas(
        db,
        ano=ano or settings.ANO_VIGENTE,
        centros=centros,
        umbral_porcentaje=umbral_porcentaje,
        limit=limit,
    )
    return [MetaRezagadaItem.model_validate(i) for i in items]
