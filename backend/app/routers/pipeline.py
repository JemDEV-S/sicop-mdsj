"""Endpoints internos del pipeline (HU-09, HU-10, HU-11)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.repositories import pipeline_repo
from app.schemas.pipeline import (
    ETAPA_A_LABEL,
    ETAPA_A_MACROFASE,
    ETAPA_A_NUMERO,
    ETAPAS_ORDEN,
    KanbanResponse,
    MACROFASE_A_LABEL,
    MACROFASES,
    PedidoCard,
    PedidoDetalleResponse,
)
from app.security.deps import CurrentUser, get_current_user
from app.services import permisos_service, pipeline_service

pipeline_router = APIRouter(prefix="/interno/pipeline", tags=["interno-pipeline"])
pedidos_router = APIRouter(prefix="/interno/pedidos", tags=["interno-pedidos"])
alertas_router = APIRouter(prefix="/interno/alertas", tags=["interno-alertas"])

_ETAPA_PATTERN = "^(" + "|".join(ETAPAS_ORDEN) + ")$"
_MACROFASE_PATTERN = "^(" + "|".join(MACROFASES) + ")$"


def _coerce(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.date()
    return v


def _mapear(row: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    return {mapping.get(k, k.lower()): _coerce(v) for k, v in row.items()}


@pipeline_router.get("/kanban", response_model=KanbanResponse)
def kanban(
    ano: int | None = None,
    centro_costo: str | None = Query(
        None,
        description="Restringe el resultado a la subrama del CC indicado (dentro del alcance del usuario).",
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KanbanResponse:
    centros = permisos_service.restringir_a_subrama(
        db, user.centros_permitidos, centro_costo
    )
    kb = pipeline_service.kanban(
        db,
        ano=ano or settings.ANO_VIGENTE,
        centros=centros,
    )
    return KanbanResponse.model_validate({
        "ano": kb["ano"],
        "macrofases": kb["macrofases"],
        "pedidos_por_etapa": {
            etapa: [PedidoCard.model_validate(f) for f in filas]
            for etapa, filas in kb["pedidos_por_etapa"].items()
        },
    })


@pedidos_router.get("", response_model=list[PedidoCard])
def listar_pedidos(
    ano: int | None = None,
    etapa: str | None = Query(None, pattern=_ETAPA_PATTERN),
    macrofase: str | None = Query(None, pattern=_MACROFASE_PATTERN),
    q: str | None = None,
    centro_costo: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PedidoCard]:
    centros = permisos_service.restringir_a_subrama(
        db, user.centros_permitidos, centro_costo
    )
    filas = pipeline_service.clasificar_pedidos(
        db, ano=ano or settings.ANO_VIGENTE, centros=centros
    )

    if etapa:
        filas = [f for f in filas if f.get("etapa") == etapa]
    elif macrofase:
        filas = [f for f in filas if f.get("macrofase") == macrofase]

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
    mapping = {
        "ANO_EJE": "ano_eje", "SEC_EJEC": "sec_ejec",
        "NRO_PEDIDO": "nro_pedido", "TIPO_BIEN": "tipo_bien",
        "TIPO_PEDIDO": "tipo_pedido", "CENTRO_COSTO": "centro_costo",
        "FECHA_PEDIDO": "fecha_pedido", "FECHA_APROB": "fecha_aprob",
        "FECHA_ATENC": "fecha_atenc",
    }
    renombrado = _mapear(ficha, mapping)
    if renombrado.get("sec_ejec") is not None:
        renombrado["sec_ejec"] = str(renombrado["sec_ejec"])
    for key in ("items", "ordenes", "conformidades", "cuadros",
                "certificaciones", "expedientes", "movimientos_almacen"):
        renombrado[key] = [_mapear(row, mapping) for row in ficha.get(key, [])]

    # Timeline con las 13/16 etapas + etapa actual del pedido.
    timeline = pipeline_service.construir_timeline(ficha)
    renombrado["timeline"] = timeline

    # Etapa actual = la ultima alcanzada del timeline (o pedido_registrado).
    alcanzadas = [h for h in timeline if h.get("alcanzada")]
    if alcanzadas:
        # El timeline sale ordenado por numero de etapa; la ultima alcanzada
        # es la etapa maxima verificable.
        actual = max(alcanzadas, key=lambda h: h["etapa_numero"])
        etapa_actual = actual["etapa"]
    else:
        etapa_actual = ETAPAS_ORDEN[0]
    renombrado["etapa_actual"] = etapa_actual
    renombrado["etapa_actual_numero"] = ETAPA_A_NUMERO[etapa_actual]
    renombrado["etapa_actual_label"] = ETAPA_A_LABEL[etapa_actual]
    renombrado["macrofase_actual"] = ETAPA_A_MACROFASE[etapa_actual]
    renombrado["macrofase_actual_label"] = MACROFASE_A_LABEL[ETAPA_A_MACROFASE[etapa_actual]]

    return PedidoDetalleResponse.model_validate(renombrado)


@alertas_router.get("/pedidos-estancados", response_model=list[PedidoCard])
def pedidos_estancados(
    ano: int | None = None,
    centro_costo: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PedidoCard]:
    centros = permisos_service.restringir_a_subrama(
        db, user.centros_permitidos, centro_costo
    )
    filas = pipeline_service.estancados(
        db, ano=ano or settings.ANO_VIGENTE, centros=centros
    )
    return [PedidoCard.model_validate(f) for f in filas]
