"""Endpoints internos del pipeline (HU-09, HU-10, HU-11)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.enums import CodigoRol
from app.repositories import pipeline_repo, resolucion_ccmn_repo
from app.schemas.pipeline import (
    CONFIANZA_A_ESTADO,
    CONFIANZA_A_LABEL,
    ETAPA_A_LABEL,
    ETAPA_A_MACROFASE,
    ETAPA_A_NUMERO,
    ETAPAS_ORDEN,
    BolsaResponse,
    CandidatoCCMN,
    KanbanResponse,
    MACROFASE_A_LABEL,
    MACROFASES,
    PedidoCard,
    PedidoDetalleResponse,
    PedidoEnBolsa,
    ResolucionCreate,
    ResolucionResponse,
)
from app.jobs.siga_refresh import refrescar_pedido
from app.security.deps import CurrentUser, get_current_user
from app.services import (
    auditoria_service,
    permisos_service,
    pipeline_service,
    rate_limit,
)

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


# SQL Server -> snake_case para la vista de bolsa. Las columnas que no estan
# aqui caen a `k.lower()`, que ya coincide con el schema.
_BOLSA_MAP = {
    "NRO_PEDIDO": "nro_pedido", "TIPO_BIEN": "tipo_bien",
    "TIPO_PEDIDO": "tipo_pedido", "CENTRO_COSTO": "centro_costo",
    "FECHA_PEDIDO": "fecha_pedido", "NRO_CONSOLID": "nro_consolid",
    "TIPO_CONSOLID": "tipo_consolid", "FECHA_CONS": "fecha_cons",
    "VALOR_PLAN": "valor_plan", "NRO_EST_MDO": "nro_est_mdo",
    "NRO_CERTIFICA": "nro_certifica",
    "NRO_CERTIFICA_SIAF": "nro_certifica_siaf",
    "SEC_CUADRO": "sec_cuadro", "NRO_ORDEN": "nro_orden",
    "FECHA_ORDEN": "fecha_orden",
}


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
    # Resolucion manual (Postgres): si existe, la cascada la prioriza y el
    # timeline marca las etapas 4-7 como `manual` en vez de `grupo`.
    tipo_pedido = str(ficha.get("TIPO_PEDIDO") or "").strip()
    manuales = resolucion_ccmn_repo.resoluciones_de_pedido(
        db, ano=ano or settings.ANO_VIGENTE, sec_ejec=int(settings.SEC_EJEC),
        tipo_bien=tipo_bien, tipo_pedido=tipo_pedido, nro_pedido=nro_pedido,
    )
    if manuales:
        ficha["ccmn_manual"] = manuales[0]["nro_consolid"]

    mapping = {
        "ANO_EJE": "ano_eje", "SEC_EJEC": "sec_ejec",
        "NRO_PEDIDO": "nro_pedido", "TIPO_BIEN": "tipo_bien",
        "TIPO_PEDIDO": "tipo_pedido", "CENTRO_COSTO": "centro_costo",
        "FECHA_PEDIDO": "fecha_pedido", "FECHA_APROB": "fecha_aprob",
        "FECHA_ATENC": "fecha_atenc",
    }
    renombrado = _mapear(ficha, mapping)
    # `ccmn_candidatos` es un frozenset (no serializable) y solo sirve dentro
    # de la cascada; se convierte a lista ordenada para la UI.
    renombrado["ccmn_candidatos"] = sorted(ficha.get("ccmn_candidatos") or ())
    if renombrado.get("sec_ejec") is not None:
        renombrado["sec_ejec"] = str(renombrado["sec_ejec"])
    for key in ("items", "ordenes", "conformidades", "cuadros",
                "certificaciones", "expedientes", "movimientos_almacen"):
        renombrado[key] = [_mapear(row, mapping) for row in ficha.get(key, [])]

    # La confianza se resuelve ANTES del timeline: las etapas 4-7 toman su
    # estado de ahi, y `ccmn_atribuido` es el numero que el timeline muestra
    # como identificador de esas etapas.
    confianza = pipeline_service.confianza_match(ficha)
    ficha["ccmn_atribuido"] = (
        ficha.get("ccmn_manual")
        or ficha.get("ccmn_declarado_orden")
        or ficha.get("ccmn_declarado_cert")
        or (sorted(ficha.get("ccmn_candidatos") or ())[0]
            if confianza == "unico" else None)
    )

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

    # Confianza del match pedido<->CCMN, para que la UI explique POR QUE una
    # etapa esta en ambar (§8): el usuario debe poder ver que el avance es del
    # grupo y cuantos candidatos hay.
    renombrado["confianza_ccmn"] = confianza
    renombrado["confianza_ccmn_label"] = CONFIANZA_A_LABEL.get(confianza, confianza)
    renombrado["estado_programacion"] = CONFIANZA_A_ESTADO.get(confianza, "sin_dato")
    renombrado["ccmn_atribuido"] = ficha.get("ccmn_atribuido")

    return PedidoDetalleResponse.model_validate(renombrado)


# ─── Bolsa y resolucion manual pedido <-> CCMN (§5, §8.2) ────────────────
#
# SIGA no registra que CCMN corresponde a que pedido (§1): logistica copia los
# datos y no los vincula. La cascada automatica resuelve el 95.5% de bienes y
# 88.7% de servicios; lo que queda (158 `ambiguo` + 4 `conflicto` en 2026) solo
# lo puede decidir un humano que conozca el caso.
#
# Quien puede asociar (cierra §13 item 6, decidido con el usuario 2026-07-22):
# Operativo sobre sus CC, Decisor sobre su jerarquia, Admin sin filtro --
# exactamente el alcance que RN-04 ya le da a cada rol para *ver* el pedido.
# Revocar sigue la misma regla y no exige ser el autor: una asociacion
# equivocada no debe quedar congelada porque su autor roto o esta de licencia.
# La autoria queda en el historial (`revocado_por`), que es lo que importa.

_ROLES_PUEDEN_ASOCIAR = (
    CodigoRol.admin,
    CodigoRol.decisor,
    CodigoRol.operativo,
)


def _verificar_puede_asociar(user: CurrentUser) -> None:
    if user.rol not in _ROLES_PUEDEN_ASOCIAR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="su rol no permite asociar CCMN a pedidos",
        )


def _flujo_ccmn(c: dict[str, Any]) -> list[dict[str, Any]]:
    """Recorrido propio de un CCMN, con los numeros de cada paso.

    Es lo que permite comparar candidatos entre si: dos CCMN de la misma bolsa
    pueden estar en etapas distintas, y ver cual llego mas lejos (y con que
    orden de compra) es la informacion que el funcionario usa para decidir.

    No dice nada sobre a que pedido pertenece cada uno — eso SIGA no lo
    registra (§1) y es justamente lo que se resuelve manualmente.
    """
    def _n(v: Any) -> str | None:
        return None if v in (None, "", 0) else str(int(v)) if isinstance(
            v, (int, float)
        ) else str(v).strip()

    ccmn = _n(c.get("NRO_CONSOLID"))
    cvr = _n(c.get("NRO_EST_MDO"))
    cuadro = _n(c.get("SEC_CUADRO"))
    ccp = _n(c.get("NRO_CERTIFICA"))
    ccp_siaf = _n(c.get("NRO_CERTIFICA_SIAF"))
    orden = _n(c.get("NRO_ORDEN"))

    return [
        {"codigo": "ccmn", "label": "Cuadro consolidado",
         "numero": ccmn, "alcanzado": ccmn is not None},
        {"codigo": "cvr", "label": "Estudio de mercado",
         "numero": cvr, "alcanzado": cvr is not None},
        {"codigo": "cuadro", "label": "Cuadro de adquisición",
         "numero": cuadro, "alcanzado": cuadro is not None},
        {"codigo": "ccp", "label": "Certificación",
         "numero": ccp_siaf or ccp, "alcanzado": ccp is not None},
        {"codigo": "orden", "label": "Orden de compra",
         "numero": orden, "alcanzado": orden is not None},
    ]


def _verificar_cc_permitido(user: CurrentUser, centro_costo: str | None) -> None:
    """RN-04: el pedido debe estar dentro del alcance de CC del usuario.

    `centros_permitidos is None` = admin (sin filtro). Un pedido sin CC no se
    deja pasar a un usuario restringido: preferimos negar que asumir.
    """
    if user.centros_permitidos is None:
        return
    cc = (centro_costo or "").strip()
    if not cc or cc not in user.centros_permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="pedido fuera del alcance del usuario",
        )


@pedidos_router.get(
    "/{nro_pedido}/{tipo_bien}/{tipo_pedido}/bolsa", response_model=BolsaResponse
)
def ver_bolsa(
    nro_pedido: int,
    tipo_bien: str,
    tipo_pedido: str,
    ano: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BolsaResponse:
    """Pedidos y CCMN candidatos que comparten la bolsa de este pedido.

    Es la pantalla donde el funcionario decide: muestra el contexto completo
    (§8.2) sin sugerir un ganador. El orden es cronologico y neutro.
    """
    if tipo_bien not in ("B", "S"):
        raise HTTPException(status_code=400, detail="tipo_bien debe ser B o S")

    ano_eje = ano or settings.ANO_VIGENTE
    ctx = pipeline_repo.contexto_pedido_bolsa(
        ano_eje, tipo_bien, tipo_pedido, nro_pedido
    )
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"pedido {nro_pedido}/{tipo_bien}/{tipo_pedido} no encontrado",
        )
    _verificar_cc_permitido(user, ctx.get("centro_costo"))

    if not ctx["bolsas"]:
        # El pedido aun no se programo: no hay bolsa que mostrar (`sin_ccmn`).
        return BolsaResponse.model_validate({
            "ano_eje": ano_eje,
            "sec_cua_mod_sal": 0,
            "tipo_bien": tipo_bien,
            "pedidos": [],
            "candidatos": [],
        })

    # Un pedido puede tocar varias bolsas si tiene items heterogeneos; se
    # muestra la primera y el resto queda accesible por el mismo endpoint.
    bolsa = pipeline_repo.obtener_bolsa(ano_eje, ctx["bolsas"][0], tipo_bien)
    if bolsa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="bolsa no encontrada"
        )

    manuales = {
        r["nro_consolid"]
        for r in resolucion_ccmn_repo.resoluciones_de_pedido(
            db, ano=ano_eje, sec_ejec=int(settings.SEC_EJEC),
            tipo_bien=tipo_bien, tipo_pedido=tipo_pedido, nro_pedido=nro_pedido,
        )
    }

    # Confianza de CADA pedido de la bolsa: la UI la muestra al lado de cada
    # uno (§8.2). Todos comparten los mismos candidatos (es la misma bolsa),
    # asi que lo que los diferencia es si alguna fuente los declara.
    n_cand = len(bolsa["candidatos"])
    cands_bolsa = frozenset(
        int(c["NRO_CONSOLID"]) for c in bolsa["candidatos"]
    )
    pedidos = []
    for p in bolsa["pedidos"]:
        nro_p = int(p["NRO_PEDIDO"])
        tp = str(p.get("TIPO_PEDIDO") or "").strip()
        ctx_p = pipeline_repo.contexto_pedido_bolsa(
            ano_eje, tipo_bien, tp, nro_p
        ) or {}
        fila = {
            "n_candidatos_ccmn": n_cand,
            "ccmn_candidatos": cands_bolsa,
            "ccmn_declarado_orden": ctx_p.get("ccmn_declarado_orden"),
            "ccmn_declarado_cert": ctx_p.get("ccmn_declarado_cert"),
            "ccmn_manual": None,
        }
        pedidos.append(
            PedidoEnBolsa.model_validate({
                **_mapear(p, _BOLSA_MAP),
                "confianza_ccmn": pipeline_service.confianza_match(fila),
            })
        )
    candidatos = [
        CandidatoCCMN.model_validate({
            **_mapear(c, _BOLSA_MAP),
            "asociado_manual": int(c["NRO_CONSOLID"]) in manuales,
            "flujo": _flujo_ccmn(c),
        })
        for c in bolsa["candidatos"]
    ]
    return BolsaResponse.model_validate({
        "ano_eje": ano_eje,
        "sec_cua_mod_sal": bolsa["sec_cua_mod_sal"],
        "tipo_bien": tipo_bien,
        "pedidos": pedidos,
        "candidatos": candidatos,
    })


@pedidos_router.get(
    "/{nro_pedido}/{tipo_bien}/{tipo_pedido}/resoluciones",
    response_model=list[ResolucionResponse],
)
def listar_resoluciones(
    nro_pedido: int,
    tipo_bien: str,
    tipo_pedido: str,
    ano: int | None = None,
    incluir_revocadas: bool = Query(
        False, description="Incluye el historial de resoluciones revocadas."
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResolucionResponse]:
    """Resoluciones manuales del pedido, con autoria. Lectura: cualquier rol
    con alcance sobre el CC (ver != asociar)."""
    ano_eje = ano or settings.ANO_VIGENTE
    ctx = pipeline_repo.contexto_pedido_bolsa(
        ano_eje, tipo_bien, tipo_pedido, nro_pedido
    )
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="pedido no encontrado"
        )
    _verificar_cc_permitido(user, ctx.get("centro_costo"))

    filas = resolucion_ccmn_repo.resoluciones_de_pedido(
        db, ano=ano_eje, sec_ejec=int(settings.SEC_EJEC),
        tipo_bien=tipo_bien, tipo_pedido=tipo_pedido, nro_pedido=nro_pedido,
        incluir_revocadas=incluir_revocadas,
    )
    return [ResolucionResponse.model_validate(f) for f in filas]


@pedidos_router.post(
    "/{nro_pedido}/{tipo_bien}/resoluciones",
    response_model=ResolucionResponse,
    status_code=status.HTTP_201_CREATED,
)
def asociar_ccmn(
    nro_pedido: int,
    tipo_bien: str,
    payload: ResolucionCreate,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResolucionResponse:
    """Asocia manualmente un CCMN al pedido (referencial y opcional, §5).

    El CCMN debe estar entre los candidatos de la bolsa del pedido: asociar
    uno de fuera no seria una resolucion sino un dato inventado. La operacion
    es idempotente -- reasociar el mismo par devuelve el registro existente.
    """
    _verificar_puede_asociar(user)
    if tipo_bien not in ("B", "S"):
        raise HTTPException(status_code=400, detail="tipo_bien debe ser B o S")

    ano_eje = payload.ano_eje or settings.ANO_VIGENTE
    ctx = pipeline_repo.contexto_pedido_bolsa(
        ano_eje, tipo_bien, payload.tipo_pedido, nro_pedido
    )
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="pedido no encontrado"
        )
    _verificar_cc_permitido(user, ctx.get("centro_costo"))

    if payload.nro_consolid not in ctx["candidatos"]:
        raise HTTPException(
            status_code=422,
            detail=(
                f"el CCMN {payload.nro_consolid} no es candidato de este pedido; "
                f"candidatos: {ctx['candidatos'] or 'ninguno'}"
            ),
        )

    creada = resolucion_ccmn_repo.crear_resolucion(
        db,
        ano=ano_eje,
        sec_ejec=int(settings.SEC_EJEC),
        tipo_bien=tipo_bien,
        tipo_pedido=payload.tipo_pedido,
        nro_pedido=nro_pedido,
        nro_consolid=payload.nro_consolid,
        sec_cua_mod_sal=ctx["bolsas"][0] if ctx["bolsas"] else 0,
        usuario_id=user.id,
        nota=payload.nota,
        candidatos_al_crear=ctx["candidatos"],
    )
    if not creada:
        raise HTTPException(
            status_code=500, detail="no se pudo registrar la resolucion"
        )

    auditoria_service.registrar_desde_request(
        db, request,
        accion=auditoria_service.Accion.RESOLUCION_CCMN_CREADA,
        usuario_id=user.id,
        detalle={
            "ano_eje": ano_eje,
            "tipo_bien": tipo_bien,
            "tipo_pedido": payload.tipo_pedido,
            "nro_pedido": nro_pedido,
            "nro_consolid": payload.nro_consolid,
            "sec_cua_mod_sal": ctx["bolsas"][0] if ctx["bolsas"] else None,
            "candidatos_al_momento": ctx["candidatos"],
            "nota": payload.nota,
        },
    )
    db.commit()
    return ResolucionResponse.model_validate(creada)


@pedidos_router.delete(
    "/resoluciones/{resolucion_id}", status_code=status.HTTP_204_NO_CONTENT
)
def revocar_ccmn(
    resolucion_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Revoca una resolucion manual. Nunca borra: preserva el historial (§5).

    No exige ser el autor -- mismo alcance de CC que para crear.
    """
    _verificar_puede_asociar(user)

    fila = resolucion_ccmn_repo.obtener_resolucion(db, resolucion_id=resolucion_id)
    if fila is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="resolucion no encontrada"
        )

    # El alcance se valida contra el pedido al que pertenece la resolucion.
    ctx = pipeline_repo.contexto_pedido_bolsa(
        int(fila["ano_eje"]), fila["tipo_bien"].strip(),
        fila["tipo_pedido"].strip(), int(fila["nro_pedido"]),
    )
    _verificar_cc_permitido(user, (ctx or {}).get("centro_costo"))

    if not resolucion_ccmn_repo.revocar_resolucion(
        db, resolucion_id=resolucion_id, usuario_id=user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="la resolucion ya estaba revocada",
        )

    auditoria_service.registrar_desde_request(
        db, request,
        accion=auditoria_service.Accion.RESOLUCION_CCMN_REVOCADA,
        usuario_id=user.id,
        detalle={
            "resolucion_id": str(resolucion_id),
            "ano_eje": fila["ano_eje"],
            "tipo_bien": fila["tipo_bien"],
            "tipo_pedido": fila["tipo_pedido"],
            "nro_pedido": fila["nro_pedido"],
            "nro_consolid": fila["nro_consolid"],
            "autor_original": str(fila["usuario_id"]),
        },
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@pedidos_router.post("/{nro_pedido}/{tipo_bien}/{tipo_pedido}/refrescar")
def refrescar_desde_siga(
    nro_pedido: int,
    tipo_bien: str,
    tipo_pedido: str,
    ano: int | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Refresca UN pedido y su cadena desde SIGA (§01.3), sin esperar al ciclo.

    Rate-limit por usuario (1 cada REFRESH_PUNTUAL_COOLDOWN_SEG). Valida el
    alcance de CC igual que el detalle. Tras refrescar, la vista materializada
    del kanban NO se recalcula aqui (es cara): el detalle ya lee de las tablas
    base, asi que el usuario ve su cambio de inmediato.
    """
    if tipo_bien not in ("B", "S"):
        raise HTTPException(status_code=400, detail="tipo_bien debe ser B o S")

    ano_eje = ano or settings.ANO_VIGENTE
    ctx = pipeline_repo.contexto_pedido_bolsa(
        ano_eje, tipo_bien, tipo_pedido, nro_pedido
    )
    if ctx is None:
        raise HTTPException(status_code=404, detail="pedido no encontrado")
    _verificar_cc_permitido(user, ctx.get("centro_costo"))

    if not rate_limit.permitir(
        f"refresh_siga:{user.id}",
        max_hits=1,
        ventana_seg=settings.REFRESH_PUNTUAL_COOLDOWN_SEG,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"espera {settings.REFRESH_PUNTUAL_COOLDOWN_SEG}s entre refrescos",
        )

    r = refrescar_pedido(ano_eje, tipo_bien, tipo_pedido, nro_pedido)
    return {"refrescado": True, "tablas": r.tablas, "total": r.total}


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
