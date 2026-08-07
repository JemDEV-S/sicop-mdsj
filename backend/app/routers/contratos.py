"""Endpoints internos de contratos (HU-19, HU-20)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.config import settings
from app.repositories import contratos_repo
from app.schemas.proveedores import (
    ContratoItem,
    ContratoPorVencerItem,
    ContratosListado,
)
from app.security.deps import CurrentUser, get_current_user


def _norm(d: dict) -> dict:
    """Renombra keys MAYUSCULAS a snake_case y limpia TIPO_CONTRATO."""
    mapa = {
        "ANO_EJE": "ano_eje", "SEC_EJEC": "sec_ejec",
        "TIPO_CONTRATO": "tipo_contrato",
        "NRO_CONTRATO": "nro_contrato", "SEC_CONTRATO": "sec_contrato",
        "TIPO_BIEN": "tipo_bien",
        "FECHA_INICIAL": "fecha_inicial",
        "FECHA_FINAL": "fecha_final",
        "FECHA_CESE": "fecha_cese",
        "VALOR_SOLES": "valor_soles",
        "NRO_MESES": "nro_meses", "MONTO_SUELDO_SOLES": "monto_sueldo_soles",
    }
    out = {mapa.get(k, k): v for k, v in d.items()}
    # tipo_contrato viene como CHAR con padding en SQL Server
    tc = out.get("tipo_contrato")
    if isinstance(tc, str):
        out["tipo_contrato"] = tc.strip()
    return out


router = APIRouter(prefix="/interno/contratos", tags=["interno-contratos"])

# NOTA DE ALCANCE — contratos transversales (no filtrados por CC).
# En la municipalidad los contratos los administra de forma central Logistica /
# Abastecimiento, no la sub-gerencia usuaria. Ademas SIGA no amarra el contrato
# a un centro de costo directamente (SIG_CONTRATOS no tiene CENTRO_COSTO); el
# unico vinculo posible seria via las ordenes derivadas, con costo alto y poco
# retorno para el MVP. Por eso estos endpoints devuelven contratos de toda la
# entidad (SEC_EJEC=300687) para cualquier rol autenticado. Es intencional y se
# rotula como tal en la UI. Amarre CC<->contrato via ordenes: mejora futura.
# Ver Docs/guia-frontend-interno.md §5.2 y §6 (decision T-53).


@router.get("", response_model=ContratosListado)
def listar_contratos(
    response: Response,
    ano: int | None = None,
    proveedor_ruc: str | None = None,
    estado: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    _: CurrentUser = Depends(get_current_user),
) -> ContratosListado:
    offset = (page - 1) * size
    items = contratos_repo.listar_contratos(
        ano=ano, proveedor_ruc=proveedor_ruc, estado=estado,
        limit=size, offset=offset,
    )
    total = contratos_repo.contar_contratos(
        ano=ano, proveedor_ruc=proveedor_ruc, estado=estado
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(max(1, (total + size - 1) // size))
    return ContratosListado(
        items=[ContratoItem.model_validate(_norm(i)) for i in items],
        total=total, page=page, size=size,
    )


@router.get(
    "/{tipo_contrato}/{ano}/{nro_contrato}/{sec_contrato}",
    response_model=ContratoItem,
)
def obtener_contrato(
    tipo_contrato: str,
    ano: int,
    nro_contrato: int,
    sec_contrato: int,
    _: CurrentUser = Depends(get_current_user),
) -> ContratoItem:
    c = contratos_repo.obtener_contrato(
        ano, nro_contrato, sec_contrato, tipo_contrato
    )
    if c is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="contrato no encontrado",
        )
    return ContratoItem.model_validate(_norm(c))


alertas_router = APIRouter(prefix="/interno/alertas", tags=["interno-alertas"])


@alertas_router.get(
    "/contratos-por-vencer", response_model=list[ContratoPorVencerItem]
)
def contratos_por_vencer(
    dias: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    fecha_referencia: date | None = Query(
        None,
        description=(
            "Fecha 'hoy' contra la que se mide el vencimiento. Por defecto la "
            "actual del servidor. En desarrollo sobre el backup del SIGA se "
            "puede fijar una fecha del corte para que la ventana tenga sentido."
        ),
    ),
    _: CurrentUser = Depends(get_current_user),
) -> list[ContratoPorVencerItem]:
    _ = settings  # keep import
    filas = contratos_repo.contratos_por_vencer(
        dias=dias, limit=limit, fecha_referencia=fecha_referencia
    )
    return [ContratoPorVencerItem.model_validate(_norm(f)) for f in filas]
