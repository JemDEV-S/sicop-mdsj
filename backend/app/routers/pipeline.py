"""Endpoints internos del pipeline (HU-09, HU-10, HU-11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.repositories import pipeline_repo
from app.schemas.pipeline import (
    KanbanResponse,
    PedidoCard,
    PedidoDetalleResponse,
)
from app.security.deps import CurrentUser, get_current_user
from app.services import pipeline_service

pipeline_router = APIRouter(prefix="/interno/pipeline", tags=["interno-pipeline"])
pedidos_router = APIRouter(prefix="/interno/pedidos", tags=["interno-pedidos"])
alertas_router = APIRouter(prefix="/interno/alertas", tags=["interno-alertas"])


@pipeline_router.get("/kanban", response_model=KanbanResponse)
def kanban(
    ano: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KanbanResponse:
    kb = pipeline_service.kanban(
        db,
        ano=ano or settings.ANO_VIGENTE,
        centros=user.centros_permitidos,
    )
    return KanbanResponse(
        solicitado=[PedidoCard.model_validate(f) for f in kb["solicitado"]],
        con_orden=[PedidoCard.model_validate(f) for f in kb["con_orden"]],
        conformidad=[PedidoCard.model_validate(f) for f in kb["conformidad"]],
        devengado=[PedidoCard.model_validate(f) for f in kb["devengado"]],
        cerrado=[PedidoCard.model_validate(f) for f in kb["cerrado"]],
    )


@pedidos_router.get("", response_model=list[PedidoCard])
def listar_pedidos(
    ano: int | None = None,
    etapa: str | None = Query(None, pattern="^(solicitado|con_orden|conformidad|devengado|cerrado)$"),
    q: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PedidoCard]:
    kb = pipeline_service.kanban(
        db, ano=ano or settings.ANO_VIGENTE, centros=user.centros_permitidos
    )
    if etapa:
        filas = kb.get(etapa, [])
    else:
        filas = [f for lst in kb.values() for f in lst]

    if q:
        ql = q.lower()
        filas = [
            f for f in filas
            if (f.get("motivo") or "").lower().find(ql) >= 0
            or (f.get("solicitante") or "").lower().find(ql) >= 0
            or str(f.get("nro_pedido")) == q
        ]

    offset = (page - 1) * size
    return [PedidoCard.model_validate(f) for f in filas[offset : offset + size]]


@pedidos_router.get(
    "/{nro_pedido}/{tipo_bien}", response_model=PedidoDetalleResponse
)
def detalle_pedido(
    nro_pedido: int,
    tipo_bien: str,
    ano: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PedidoDetalleResponse:
    if tipo_bien not in ("B", "S"):
        raise HTTPException(
            status_code=400, detail="tipo_bien debe ser B (Bien) o S (Servicio)"
        )
    ficha = pipeline_repo.obtener_pedido(
        ano or settings.ANO_VIGENTE, nro_pedido, tipo_bien
    )
    if ficha is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"pedido {nro_pedido}/{tipo_bien} no encontrado",
        )
    # RN-04: si el usuario no es admin, verifica que el CC del pedido este permitido.
    if user.centros_permitidos is not None:
        cc = (ficha.get("CENTRO_COSTO") or ficha.get("centro_costo") or "").strip()
        if cc and cc not in user.centros_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="pedido fuera del alcance del usuario",
            )
    # Renombrar keys que vienen en mayusculas.
    mapping = {
        "ANO_EJE": "ano_eje", "SEC_EJEC": "sec_ejec",
        "NRO_PEDIDO": "nro_pedido", "TIPO_BIEN": "tipo_bien",
        "TIPO_PEDIDO": "tipo_pedido", "CENTRO_COSTO": "centro_costo",
        "FECHA_PEDIDO": "fecha_pedido", "FECHA_APROB": "fecha_aprob",
        "FECHA_ATENC": "fecha_atenc",
    }
    renombrado = {mapping.get(k, k): v for k, v in ficha.items()}
    # Los items/ordenes/conformidades vienen con keys mayusculas tambien
    renombrado["items"] = [
        {mapping.get(k, k.lower()): v for k, v in it.items()}
        for it in ficha.get("items", [])
    ]
    renombrado["ordenes"] = [
        {mapping.get(k, k.lower()): v for k, v in o.items()}
        for o in ficha.get("ordenes", [])
    ]
    renombrado["conformidades"] = [
        {mapping.get(k, k.lower()): v for k, v in c.items()}
        for c in ficha.get("conformidades", [])
    ]
    return PedidoDetalleResponse.model_validate(renombrado)


@alertas_router.get("/pedidos-estancados", response_model=list[PedidoCard])
def pedidos_estancados(
    ano: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PedidoCard]:
    filas = pipeline_service.estancados(
        db, ano=ano or settings.ANO_VIGENTE, centros=user.centros_permitidos
    )
    return [PedidoCard.model_validate(f) for f in filas]
