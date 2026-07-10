"""Endpoints internos del cruce SIAF-SIGA (HU-12, HU-13, HU-14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.repositories import cruce_repo
from app.schemas.cruce import (
    AfectacionItem,
    ConformidadItem,
    ConsolidadoMetaResponse,
    CruceExpedienteResponse,
    MetaCabecera,
    OrdenCruceItem,
    PedidoOrigenItem,
    PresupuestoMeta,
    CertificacionItem,
)
from app.security.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/interno/cruce", tags=["interno-cruce"])


def _norm(d: dict) -> dict:
    """Renombra keys de SQL Server (mayusculas) a snake_case."""
    mapa = {
        "ANO_EJE": "ano_eje", "SEC_EJEC": "sec_ejec",
        "NRO_ORDEN": "nro_orden", "TIPO_BIEN": "tipo_bien",
        "EXP_SIAF": "exp_siaf", "EXP_SIGA": "exp_siga",
        "ESTADO": "estado", "ESTADO_SIAF": "estado_siaf",
        "TOTAL_FACT_SOLES": "total_fact_soles",
        "FECHA_ORDEN": "fecha_orden",
        "NRO_CONTRATO": "nro_contrato", "ANO_CONTRATO": "ano_contrato",
        "SEC_CONTRATO": "sec_contrato",
        "SEC_FUNC": "sec_func", "VALOR_SOLES": "valor_soles",
        "NRO_PEDIDO": "nro_pedido", "CENTRO_COSTO": "centro_costo",
        "FECHA_PEDIDO": "fecha_pedido",
        "ANO_ORDEN": "ano_orden", "FECHA_MOVIMTO": "fecha_movimto",
        "ESTADO_DEVENG": "estado_deveng",
        "NRO_CERTIFICA": "nro_certifica", "FECHA_REG": "fecha_reg",
    }
    return {mapa.get(k, k): v for k, v in d.items()}


@router.get(
    "/expediente-siaf/{exp_siaf}",
    response_model=CruceExpedienteResponse,
)
def por_expediente(
    exp_siaf: str,
    ano: int | None = None,
    _: CurrentUser = Depends(get_current_user),
) -> CruceExpedienteResponse:
    resultado = cruce_repo.buscar_por_exp_siaf(
        ano or settings.ANO_VIGENTE, exp_siaf
    )
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"expediente SIAF {exp_siaf} sin cruce SIGA",
        )
    return CruceExpedienteResponse(
        exp_siaf=resultado["exp_siaf"],
        ano=resultado["ano"],
        ordenes=[OrdenCruceItem.model_validate(_norm(o)) for o in resultado["ordenes"]],
        afectacion_presupuestal=[
            AfectacionItem.model_validate(_norm(a))
            for a in resultado["afectacion_presupuestal"]
        ],
        pedidos_origen=[
            PedidoOrigenItem.model_validate(_norm(p))
            for p in resultado["pedidos_origen"]
        ],
        conformidades=[
            ConformidadItem.model_validate(_norm(c))
            for c in resultado["conformidades"]
        ],
    )


@router.get("/expediente-siaf", response_model=list[str])
def sugerir_expedientes(
    prefijo: str = Query("", description="Prefijo a buscar (autocomplete)"),
    ano: int | None = None,
    limit: int = Query(10, ge=1, le=50),
    _: CurrentUser = Depends(get_current_user),
) -> list[str]:
    valores = cruce_repo.sugerir_exp_siaf(
        ano or settings.ANO_VIGENTE, prefijo, limit=limit
    )
    return [str(v) for v in valores]


@router.get(
    "/meta/{sec_func}",
    response_model=ConsolidadoMetaResponse,
)
def consolidado_meta(
    sec_func: int,
    ano: int | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> ConsolidadoMetaResponse:
    resultado = cruce_repo.consolidado_por_meta(
        ano or settings.ANO_VIGENTE,
        sec_func,
        centros=user.centros_permitidos,
    )
    if resultado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"meta {sec_func} no encontrada o fuera de alcance",
        )
    return ConsolidadoMetaResponse(
        meta=MetaCabecera.model_validate(_norm(resultado["meta"])),
        presupuesto=PresupuestoMeta.model_validate(resultado["presupuesto"] or {}),
        ordenes=[OrdenCruceItem.model_validate(_norm(o)) for o in resultado["ordenes"]],
        pedidos=[PedidoOrigenItem.model_validate(_norm(p)) for p in resultado["pedidos"]],
        certificaciones=[
            CertificacionItem.model_validate(_norm(c))
            for c in resultado["certificaciones"]
        ],
    )
