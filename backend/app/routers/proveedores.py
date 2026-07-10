"""Endpoints de proveedores (HU-07 publico, HU-19 interno)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.config import settings
from app.repositories import proveedores_repo
from app.schemas.proveedores import (
    OrdenProveedor,
    ProveedoresListado,
    ProveedoresListadoInterno,
    ProveedorInternoItem,
    ProveedorPublicoItem,
)
from app.security.deps import CurrentUser, get_current_user


def _norm(d: dict) -> dict:
    """Uppercase SQL Server keys → snake_case Pydantic."""
    mapa = {
        "ANO_EJE": "ano_eje", "NRO_ORDEN": "nro_orden",
        "TIPO_BIEN": "tipo_bien", "EXP_SIAF": "exp_siaf",
        "ESTADO": "estado", "ESTADO_SIAF": "estado_siaf",
        "TOTAL_FACT_SOLES": "total_fact_soles",
        "FECHA_ORDEN": "fecha_orden",
    }
    return {mapa.get(k, k): v for k, v in d.items()}


publico_router = APIRouter(prefix="/publico/proveedores", tags=["publico-proveedores"])


@publico_router.get("", response_model=ProveedoresListado)
def listar_publico(
    response: Response,
    ano: int | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
) -> ProveedoresListado:
    offset = (page - 1) * size
    items = proveedores_repo.listar_proveedores(
        ano=ano or settings.ANO_VIGENTE,
        q=q, limit=size, offset=offset,
        incluir_contacto=False,
    )
    total = proveedores_repo.contar_proveedores(q=q)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(max(1, (total + size - 1) // size))
    return ProveedoresListado(
        items=[ProveedorPublicoItem.model_validate(i) for i in items],
        total=total, page=page, size=size,
    )


@publico_router.get("/{ruc}", response_model=ProveedorPublicoItem)
def obtener_publico(ruc: str) -> ProveedorPublicoItem:
    p = proveedores_repo.obtener_proveedor_por_ruc(ruc, incluir_contacto=False)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="proveedor no encontrado")
    return ProveedorPublicoItem.model_validate(p)


interno_router = APIRouter(prefix="/interno/proveedores", tags=["interno-proveedores"])


@interno_router.get("", response_model=ProveedoresListadoInterno)
def listar_interno(
    response: Response,
    ano: int | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    _: CurrentUser = Depends(get_current_user),
) -> ProveedoresListadoInterno:
    offset = (page - 1) * size
    items = proveedores_repo.listar_proveedores(
        ano=ano or settings.ANO_VIGENTE,
        q=q, limit=size, offset=offset,
        incluir_contacto=True,
    )
    total = proveedores_repo.contar_proveedores(q=q)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(max(1, (total + size - 1) // size))
    return ProveedoresListadoInterno(
        items=[ProveedorInternoItem.model_validate(i) for i in items],
        total=total, page=page, size=size,
    )


@interno_router.get("/{ruc}", response_model=ProveedorInternoItem)
def obtener_interno(
    ruc: str,
    _: CurrentUser = Depends(get_current_user),
) -> ProveedorInternoItem:
    p = proveedores_repo.obtener_proveedor_por_ruc(ruc, incluir_contacto=True)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="proveedor no encontrado")
    return ProveedorInternoItem.model_validate(p)


@interno_router.get("/{ruc}/ordenes", response_model=list[OrdenProveedor])
def ordenes_de_proveedor(
    ruc: str,
    ano: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    _: CurrentUser = Depends(get_current_user),
) -> list[OrdenProveedor]:
    ordenes = proveedores_repo.ordenes_por_proveedor(ruc, ano=ano, limit=limit)
    return [OrdenProveedor.model_validate(_norm(o)) for o in ordenes]
