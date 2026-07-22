"""Servicio pipeline: clasifica cada pedido a su etapa maxima alcanzada,
agrupa por macrofase, marca estancados y arma el timeline del detalle.

Reglas RN-02 (estancado):
    Un pedido se marca estancado si lleva > umbral dias sin cambio de etapa,
    y su etapa no es final (cierre). El umbral se lee de
    `sistema.umbrales_alertas` (codigo_alerta='pedido_estancado').
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.repositories import pipeline_repo, resolucion_ccmn_repo
from app.schemas.pipeline import (
    CONFIANZA_A_ESTADO,
    CONFIANZA_A_LABEL,
    ESTADOS_ALCANZADOS,
    ETAPA_A_LABEL,
    ETAPA_A_MACROFASE,
    ETAPA_A_NUMERO,
    ETAPA_CCMN,
    ETAPA_CERTIFICACION,
    ETAPA_CIERRE,
    ETAPA_COMPROMISO_SIAF,
    ETAPA_COTIZACION,
    ETAPA_CUADRO_ADQUISICION,
    ETAPA_CUADRO_NECESIDAD,
    ETAPA_DESPACHO_PECOSA,
    ETAPA_DEVENGADO,
    ETAPA_EJECUCION,
    ETAPA_ORDEN_EMITIDA,
    ETAPA_PEDIDO_APROBADO,
    ETAPA_PEDIDO_INTERNO,
    ETAPA_PEDIDO_REGISTRADO,
    ETAPA_PUENTE_PAAC,
    ETAPA_RECEPCION_KARDEX,
    ETAPAS_ORDEN,
    MACROFASE_A_LABEL,
    MACROFASES,
    Macrofase,
)

logger = logging.getLogger(__name__)

DEFAULT_DIAS = 15
ETAPAS_FINALES = {ETAPA_CIERRE}

# Umbrales por defecto por macrofase (usados si sistema.umbrales_alertas no
# los define). Calibrado con el diagnóstico 2026-07-16:
#   - solicitud/programacion: días bajos porque son etapas administrativas.
#   - ejecucion: alto porque un servicio/obra puede durar meses legítimamente.
#   - cierre: None → nunca estancado (es etapa terminal).
DEFAULT_DIAS_POR_MACROFASE: dict[str, int | None] = {
    "solicitud":     15,
    "programacion":  30,
    "certificacion": 30,
    "contratacion":  45,
    "ejecucion":     180,
    "cierre":        None,
}


def _cargar_umbrales(db: Session) -> tuple[int, dict[str, int | None]]:
    """Devuelve (dias_fallback, dias_por_macrofase) desde `sistema.umbrales_alertas`.

    El JSON puede tener las llaves:
      - "dias": entero de fallback si la macrofase no está en el mapping.
      - "dias_por_macrofase": mapping macrofase → días o null. `null` desactiva
        la alerta para esa macrofase.
    """
    row = db.execute(
        text(
            """
            SELECT parametros
              FROM sistema.umbrales_alertas
             WHERE codigo_alerta = 'pedido_estancado'
            """
        )
    ).first()
    if row is None:
        return DEFAULT_DIAS, dict(DEFAULT_DIAS_POR_MACROFASE)
    params = row[0]
    if isinstance(params, str):
        params = json.loads(params)
    dias = int(params.get("dias", DEFAULT_DIAS))
    por_macrofase = dict(DEFAULT_DIAS_POR_MACROFASE)
    if isinstance(params.get("dias_por_macrofase"), dict):
        for k, v in params["dias_por_macrofase"].items():
            por_macrofase[k] = None if v is None else int(v)
    return dias, por_macrofase


def _umbral_para(macrofase: str, dias_fallback: int,
                 por_macrofase: dict[str, int | None]) -> int | None:
    """Devuelve el umbral en días para una macrofase, o None si está desactivada."""
    if macrofase in por_macrofase:
        return por_macrofase[macrofase]
    return dias_fallback


# ─── Cascada de confianza del match pedido <-> CCMN ──────────────────────


def confianza_match(fila: dict[str, Any]) -> str:
    """Nivel de confianza del CCMN atribuido al pedido.

    Resuelve en cascada y declara el nivel; nunca elige un ganador por
    parecido. Las etapas 4-7 (programacion) dependen de esto: si el nivel
    no esta en CONFIANZA_RESUELTA, el avance observado puede pertenecer al
    CCMN de OTRO pedido de la misma bolsa.

    Ref: doc de refactorizacion §4.
    """
    n_cand = fila.get("n_candidatos_ccmn") or 0

    if fila.get("ccmn_manual"):
        return "resuelto_manual"

    if n_cand == 0:
        return "sin_ccmn"

    if n_cand == 1:
        return "unico"

    # Con N candidatos solo una fuente declarativa desambigua. Si declara un
    # CCMN que no esta entre los candidatos es un typo o un desfase: se marca
    # visible en vez de aceptarlo.
    for nivel, declarado in (
        ("declarado",      fila.get("ccmn_declarado_orden")),
        ("declarado_cert", fila.get("ccmn_declarado_cert")),
    ):
        if not declarado:
            continue
        candidatos = fila.get("ccmn_candidatos") or ()
        if not candidatos or declarado in candidatos:
            return nivel
        return "conflicto"

    return "ambiguo"


def estado_etapa_programacion(fila: dict[str, Any]) -> str:
    """Estado de las etapas 4-7, que solo son observables a traves del CCMN."""
    return CONFIANZA_A_ESTADO.get(confianza_match(fila), "sin_dato")


# ─── Clasificacion pedido -> etapa maxima alcanzada ───────────────────────
#
# Se recorre en orden inverso (de la ultima hacia la primera) y se toma la
# etapa mas avanzada cuyo flag este en 1. Si ninguna, cae a pedido_registrado.

def _etapa_maxima(fila: dict[str, Any]) -> str:
    tipo_bien = fila.get("TIPO_BIEN") or fila.get("tipo_bien")
    # Etapas 4-7: solo cuentan si el CCMN es atribuible a ESTE pedido. Con
    # nivel `ambiguo`/`conflicto` el avance es del grupo (otros pedidos de la
    # bolsa) y marcarlo aqui es el bug que pintaba verdes ajenos.
    prog_atribuible = estado_etapa_programacion(fila) in ESTADOS_ALCANZADOS

    # [16] Cierre
    if fila.get("tiene_cierre"):
        return ETAPA_CIERRE

    # [15] Devengado (solo cuando SIGA lo marca — no cae en 0 para servicios
    # porque el devengado real vendra de SIAF via Fix #2).
    if fila.get("tiene_devengado"):
        return ETAPA_DEVENGADO

    # Bienes: [14] Despacho pecosa · [13] Pedido interno · [12] Kardex.
    if tipo_bien == "B":
        if fila.get("tiene_pecosa"):
            return ETAPA_DESPACHO_PECOSA
        if fila.get("tiene_pedido_interno"):
            return ETAPA_PEDIDO_INTERNO
        if fila.get("tiene_kardex"):
            return ETAPA_RECEPCION_KARDEX

    # [11] Ejecucion (S: conformidades · B: entrada almacen I,1)
    if fila.get("tiene_ejecucion"):
        return ETAPA_EJECUCION

    # [10] Compromiso / envio SIAF
    if fila.get("tiene_compromiso"):
        return ETAPA_COMPROMISO_SIAF

    # [9] Orden emitida
    if fila.get("tiene_orden"):
        return ETAPA_ORDEN_EMITIDA

    # [8] Certificacion (CCP)
    if fila.get("tiene_certificacion") or fila.get("tiene_ccp_siaf"):
        return ETAPA_CERTIFICACION

    # [7] Cuadro adquisicion
    if fila.get("tiene_cuadro_adq") and prog_atribuible:
        return ETAPA_CUADRO_ADQUISICION

    # [6] Cotizacion
    if fila.get("tiene_cotizacion") and prog_atribuible:
        return ETAPA_COTIZACION

    # [5] CCMN
    if fila.get("tiene_ccmn") and prog_atribuible:
        return ETAPA_CCMN

    # [4] Puente pedido<->PAAC
    if fila.get("tiene_puente_paac") and prog_atribuible:
        return ETAPA_PUENTE_PAAC

    # [3] Cuadro necesidad
    if fila.get("tiene_cuadro_neces"):
        return ETAPA_CUADRO_NECESIDAD

    # [2] Aprobacion pedido
    estado = fila.get("estado_pedido") or fila.get("ESTADO")
    if str(estado).strip() == "1":
        return ETAPA_PEDIDO_APROBADO

    # [1] Pedido registrado
    return ETAPA_PEDIDO_REGISTRADO


def _fecha_etapa(fila: dict[str, Any]) -> date | None:
    """Fecha del evento que llevó al pedido a su etapa actual.

    Antes usaba solo las 3 fechas cabecera del pedido (FECHA_PEDIDO/APROB/ATENC),
    lo que hacía que un pedido en 'certificacion' con solo FECHA_PEDIDO cayera
    a esa fecha e inflara dias_en_etapa a "hace medio año" → ~1700 falsos
    estancados en 2026. El repo ahora expone fecha_ccmn, fecha_certificacion,
    fecha_orden, fecha_compromiso, fecha_ejecucion, fecha_pecosa, fecha_cierre_seg.
    """
    etapa = fila["etapa"]
    if etapa == ETAPA_CIERRE:
        return (fila.get("fecha_cierre_seg")
                or fila.get("FECHA_ATENC")
                or fila.get("fecha_ejecucion")
                or fila.get("FECHA_APROB")
                or fila.get("FECHA_PEDIDO"))
    if etapa == ETAPA_DEVENGADO:
        return (fila.get("fecha_ejecucion")
                or fila.get("fecha_compromiso")
                or fila.get("FECHA_ATENC")
                or fila.get("FECHA_APROB")
                or fila.get("FECHA_PEDIDO"))
    if etapa == ETAPA_DESPACHO_PECOSA:
        return fila.get("fecha_pecosa") or fila.get("fecha_ejecucion") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if etapa in (ETAPA_EJECUCION, ETAPA_RECEPCION_KARDEX, ETAPA_PEDIDO_INTERNO):
        return fila.get("fecha_ejecucion") or fila.get("fecha_compromiso") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if etapa == ETAPA_COMPROMISO_SIAF:
        return fila.get("fecha_compromiso") or fila.get("fecha_orden") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if etapa == ETAPA_ORDEN_EMITIDA:
        return fila.get("fecha_orden") or fila.get("fecha_certificacion") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if etapa == ETAPA_CERTIFICACION:
        return fila.get("fecha_certificacion") or fila.get("fecha_ccmn") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if etapa == ETAPA_CUADRO_ADQUISICION:
        return fila.get("fecha_cuadro_adq") or fila.get("fecha_ccmn") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if etapa in (ETAPA_COTIZACION, ETAPA_CCMN, ETAPA_PUENTE_PAAC, ETAPA_CUADRO_NECESIDAD):
        return fila.get("fecha_ccmn") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if etapa == ETAPA_PEDIDO_APROBADO:
        return fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    return fila.get("FECHA_PEDIDO")


def _enriquecer(
    fila: dict[str, Any],
    hoy: date,
    dias_fallback: int,
    dias_por_macrofase: dict[str, int | None],
) -> dict[str, Any]:
    # Se resuelve ANTES de clasificar: las etapas 4-7 dependen del nivel.
    confianza = confianza_match(fila)
    fila["confianza_ccmn"] = confianza
    fila["confianza_ccmn_label"] = CONFIANZA_A_LABEL.get(confianza, confianza)
    fila["estado_programacion"] = CONFIANZA_A_ESTADO.get(confianza, "sin_dato")
    # El CCMN atribuido solo se expone cuando la cascada lo resolvio; con
    # `ambiguo`/`conflicto` no hay un CCMN de ESTE pedido que mostrar.
    fila["ccmn_atribuido"] = (
        fila.get("ccmn_manual")
        or fila.get("ccmn_declarado_orden")
        or fila.get("ccmn_declarado_cert")
        or (fila.get("nro_consolid_muestra") if confianza == "unico" else None)
    )

    etapa = _etapa_maxima(fila)
    macrofase = ETAPA_A_MACROFASE[etapa]
    fila["etapa"] = etapa
    fila["etapa_numero"] = ETAPA_A_NUMERO[etapa]
    fila["etapa_label"] = ETAPA_A_LABEL[etapa]
    fila["macrofase"] = macrofase
    fila["macrofase_label"] = MACROFASE_A_LABEL[macrofase]

    umbral_macro = _umbral_para(macrofase, dias_fallback, dias_por_macrofase)

    f = _fecha_etapa(fila)
    if f is not None:
        if isinstance(f, datetime):
            f = f.date()
        dias = (hoy - f).days
        fila["dias_en_etapa"] = dias
        # Estancado sólo si (1) hay umbral definido para la macrofase, (2) la
        # etapa no es terminal, y (3) los días superan el umbral.
        fila["estancado"] = (
            umbral_macro is not None
            and dias > umbral_macro
            and etapa not in ETAPAS_FINALES
        )
    else:
        fila["dias_en_etapa"] = None
        fila["estancado"] = False
    return fila


def _renombrar(fila: dict[str, Any]) -> dict[str, Any]:
    """SQL Server -> snake_case Pydantic + coerce tipos."""
    mapping = {
        "ANO_EJE": "ano_eje",
        "SEC_EJEC": "sec_ejec",
        "NRO_PEDIDO": "nro_pedido",
        "TIPO_BIEN": "tipo_bien",
        "TIPO_PEDIDO": "tipo_pedido",
        "CENTRO_COSTO": "centro_costo",
        "FECHA_PEDIDO": "fecha_pedido",
        "FECHA_APROB": "fecha_aprob",
        "FECHA_ATENC": "fecha_atenc",
    }
    # Campos de trabajo de la cascada: ya se consumieron en _enriquecer y no
    # son serializables (frozenset). `confianza_ccmn` es lo que sale al API.
    internos = {"ccmn_candidatos", "ccmn_declarado_orden",
                "ccmn_declarado_cert", "ccmn_manual", "ccmn_manual_todos"}

    out: dict[str, Any] = {}
    for k, v in fila.items():
        if k in internos:
            continue
        nk = mapping.get(k, k)
        if isinstance(v, datetime):
            v = v.date()
        elif nk == "sec_ejec" and v is not None:
            v = str(v)
        elif nk == "monto_total" and v is not None:
            v = float(v)
        out[nk] = v
    cc = out.get("centro_costo")
    if isinstance(cc, str):
        out["centro_costo"] = cc.strip()
    return out


# ─── Resoluciones manuales (Postgres) sobre las filas de SIGA ────────────


def _aplicar_resoluciones_manuales(
    db: Session, filas: list[dict[str, Any]], *, ano: int
) -> None:
    """Inyecta `ccmn_manual` en las filas que vienen de SIGA.

    El pedido y el CCMN viven en SIGA; la asociacion manual vive en Postgres
    (regla 2: jamas se escribe en SIGA). Por eso el cruce se hace aqui y no
    en el repo del pipeline.

    La resolucion manual es **referencial y opcional** (§5): si esta consulta
    falla, el pipeline sigue funcionando con la cascada automatica y solo
    pierde precision en los `ambiguo`. No se propaga el error.
    """
    try:
        activas = resolucion_ccmn_repo.resoluciones_activas(
            db, ano=ano, sec_ejec=int(settings.SEC_EJEC)
        )
    except Exception:  # noqa: BLE001 — degradar, no romper el pipeline
        logger.warning(
            "No se pudieron leer las resoluciones manuales pedido<->CCMN; "
            "el pipeline continua solo con la cascada automatica",
            exc_info=True,
        )
        return

    if not activas:
        return

    for fila in filas:
        clave = (
            str(fila.get("TIPO_BIEN") or "").strip(),
            str(fila.get("TIPO_PEDIDO") or "").strip(),
            int(fila["NRO_PEDIDO"]),
        )
        ccmns = activas.get(clave)
        if not ccmns:
            continue
        # N:M: un pedido puede tener varios CCMN asociados. Para la cascada
        # basta uno (el nivel es `resuelto_manual` igual); la lista completa
        # se expone aparte para el panel de trazabilidad.
        fila["ccmn_manual"] = ccmns[0]
        fila["ccmn_manual_todos"] = list(ccmns)


# ─── API publica del servicio ─────────────────────────────────────────────


def clasificar_pedidos(
    db: Session, *, ano: int, centros: list[str] | None
) -> list[dict[str, Any]]:
    """Devuelve la lista plana de pedidos clasificados a etapa + macrofase,
    ya enriquecidos con dias_en_etapa y estancado, y renombrados a snake_case.
    """
    raw = pipeline_repo.pipeline_pedidos_raw(ano, centros)
    _aplicar_resoluciones_manuales(db, raw, ano=ano)
    dias_fallback, por_macrofase = _cargar_umbrales(db)
    hoy = date.today()
    return [
        _renombrar(_enriquecer(f, hoy, dias_fallback, por_macrofase))
        for f in raw
    ]


def kanban(
    db: Session, *, ano: int, centros: list[str] | None
) -> dict[str, Any]:
    """Vista jerarquica del kanban: macrofases + drill-down por etapa.

    Retorna:
        {
            "ano": int,
            "macrofases": [
                {"macrofase": "solicitud", "conteo": N, "monto": M,
                 "etapas": [{"etapa": "pedido_registrado", "conteo": ...}, ...]},
                ...
            ],
            "pedidos_por_etapa": { "pedido_registrado": [PedidoCard, ...], ... },
        }
    """
    pedidos = clasificar_pedidos(db, ano=ano, centros=centros)

    pedidos_por_etapa: dict[str, list[dict[str, Any]]] = {
        e: [] for e in ETAPAS_ORDEN
    }
    for p in pedidos:
        pedidos_por_etapa.setdefault(p["etapa"], []).append(p)

    macrofases_out: list[dict[str, Any]] = []
    for macro in MACROFASES:
        etapas_macro = [e for e in ETAPAS_ORDEN if ETAPA_A_MACROFASE[e] == macro]
        etapas_out: list[dict[str, Any]] = []
        conteo_macro = 0
        monto_macro = 0.0
        for etapa in etapas_macro:
            filas = pedidos_por_etapa.get(etapa, [])
            conteo = len(filas)
            monto = sum(float(f.get("monto_total") or 0) for f in filas)
            etapas_out.append({
                "etapa": etapa,
                "etapa_numero": ETAPA_A_NUMERO[etapa],
                "etapa_label": ETAPA_A_LABEL[etapa],
                "conteo": conteo,
                "monto": monto,
            })
            conteo_macro += conteo
            monto_macro += monto
        macrofases_out.append({
            "macrofase": macro,
            "macrofase_label": MACROFASE_A_LABEL[macro],  # type: ignore[index]
            "conteo": conteo_macro,
            "monto": monto_macro,
            "etapas": etapas_out,
        })

    return {
        "ano": ano,
        "macrofases": macrofases_out,
        "pedidos_por_etapa": pedidos_por_etapa,
    }


def estancados(
    db: Session, *, ano: int, centros: list[str] | None
) -> list[dict[str, Any]]:
    pedidos = clasificar_pedidos(db, ano=ano, centros=centros)
    return sorted(
        [p for p in pedidos if p.get("estancado")],
        key=lambda p: p.get("dias_en_etapa") or 0,
        reverse=True,
    )


# ─── Timeline del detalle del pedido ──────────────────────────────────────


def _to_dt(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    return None


def construir_timeline(ficha: dict[str, Any]) -> list[dict[str, Any]]:
    """A partir de la ficha detallada devuelve un timeline con las 13/16 etapas
    posibles, marcando cuales fueron alcanzadas y con que fecha aproximada.
    """
    tipo_bien = (ficha.get("TIPO_BIEN") or ficha.get("tipo_bien") or "").strip()
    es_bien = tipo_bien == "B"

    fecha_pedido = _to_dt(ficha.get("FECHA_PEDIDO") or ficha.get("fecha_pedido"))
    fecha_aprob = _to_dt(ficha.get("FECHA_APROB") or ficha.get("fecha_aprob"))
    fecha_atenc = _to_dt(ficha.get("FECHA_ATENC") or ficha.get("fecha_atenc"))
    estado_pedido = str(ficha.get("estado_pedido") or ficha.get("ESTADO") or "").strip()

    ordenes = ficha.get("ordenes", []) or []
    cuadros = ficha.get("cuadros", []) or []
    certificaciones = ficha.get("certificaciones", []) or []
    expedientes = ficha.get("expedientes", []) or []
    conformidades = ficha.get("conformidades", []) or []
    movimientos = ficha.get("movimientos_almacen", []) or []
    items = ficha.get("items", []) or []

    fecha_orden = min(
        (o.get("FECHA_ORDEN") or o.get("fecha_orden") for o in ordenes
         if o.get("FECHA_ORDEN") or o.get("fecha_orden")),
        default=None,
    )
    fecha_orden = _to_dt(fecha_orden) if fecha_orden else None

    fecha_certif = min(
        (c.get("FECHA") or c.get("fecha") for c in certificaciones
         if c.get("FECHA") or c.get("fecha")),
        default=None,
    )
    fecha_certif = _to_dt(fecha_certif) if fecha_certif else None

    fecha_cuadro = min(
        (c.get("FECHA_CUADRO") or c.get("fecha_cuadro") for c in cuadros
         if c.get("FECHA_CUADRO") or c.get("fecha_cuadro")),
        default=None,
    )
    fecha_cuadro = _to_dt(fecha_cuadro) if fecha_cuadro else None

    fecha_exp = min(
        (e.get("FECHA_EXP_SIGA") or e.get("fecha_exp_siga") for e in expedientes
         if e.get("FECHA_EXP_SIGA") or e.get("fecha_exp_siga")),
        default=None,
    )
    fecha_exp = _to_dt(fecha_exp) if fecha_exp else None

    fecha_ingreso = None
    fecha_kardex = None
    fecha_despacho = None
    if es_bien and movimientos:
        for m in movimientos:
            tm = (m.get("TIPO_MOVIMTO") or m.get("tipo_movimto") or "").strip()
            fm = _to_dt(m.get("FECHA_MOVIMTO") or m.get("fecha_movimto"))
            if not fm:
                continue
            if tm == "I":
                fecha_ingreso = min(filter(None, [fecha_ingreso, fm]))
            elif tm == "R":
                fecha_kardex = min(filter(None, [fecha_kardex, fm]))
            elif tm == "S":
                fecha_despacho = min(filter(None, [fecha_despacho, fm]))

    fecha_confor = None
    if conformidades:
        fechas = [_to_dt(c.get("FECHA_MOVIMTO") or c.get("fecha_movimto"))
                  for c in conformidades]
        fechas = [f for f in fechas if f is not None]
        if fechas:
            fecha_confor = min(fechas)

    tiene_cuadro_neces = any(
        (i.get("SEC_CUA_MOD_SAL") or i.get("sec_cua_mod_sal"))
        for i in items
    )
    tiene_orden = bool(ordenes)
    tiene_certif = bool(certificaciones)
    tiene_cuadro_adq = bool(cuadros)
    tiene_compromiso = any(
        _to_dt(e.get("FECHA_SIAF") or e.get("fecha_siaf")) for e in expedientes
    )
    tiene_ejecucion = bool(conformidades) if not es_bien else bool(fecha_ingreso)
    tiene_cierre = estado_pedido == "7"

    hitos: list[dict[str, Any]] = []

    def _add(etapa: str, fecha: datetime | None, alcanzada: bool, detalle: str | None = None):
        hitos.append({
            "etapa": etapa,
            "etapa_numero": ETAPA_A_NUMERO[etapa],
            "etapa_label": ETAPA_A_LABEL[etapa],
            "macrofase": ETAPA_A_MACROFASE[etapa],
            "fecha": fecha,
            "detalle": detalle,
            "alcanzada": alcanzada,
        })

    _add(ETAPA_PEDIDO_REGISTRADO, fecha_pedido, fecha_pedido is not None,
         "Pedido registrado en SIG_PEDIDOS")
    _add(ETAPA_PEDIDO_APROBADO, fecha_aprob,
         fecha_aprob is not None or estado_pedido in ("1", "7"),
         "SIG_PEDIDOS.ESTADO='1' + FECHA_APROB")
    _add(ETAPA_CUADRO_NECESIDAD, None, tiene_cuadro_neces,
         "SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL presente")
    _add(ETAPA_PUENTE_PAAC, None, tiene_cuadro_adq or tiene_certif,
         "SIG_CUADRO_MODIFICADO_CMN")
    _add(ETAPA_CCMN, None, tiene_cuadro_adq or tiene_certif,
         "SIG_PAAC_CONSOLIDADO")
    _add(ETAPA_COTIZACION, None, tiene_cuadro_adq,
         "SIG_SOLICITUD_COTIZACION")
    _add(ETAPA_CUADRO_ADQUISICION, fecha_cuadro, tiene_cuadro_adq,
         "SIG_CUADRO_ADQUISICION")
    _add(ETAPA_CERTIFICACION, fecha_certif, tiene_certif,
         "SIG_CERTIFICACION (CCP SIAF)")
    _add(ETAPA_ORDEN_EMITIDA, fecha_orden, tiene_orden,
         "SIG_ORDEN_ADQUISICION")
    _add(ETAPA_COMPROMISO_SIAF, fecha_exp, tiene_compromiso,
         "SIG_EXP_SIGA_DOCU.FECHA_INTERFASE")
    _add(ETAPA_EJECUCION, fecha_confor or fecha_ingreso, tiene_ejecucion,
         "Servicios: SIG_MOVIM_CONFOR_SERVICIO · Bienes: SIG_MOVIM_ALMACEN (I,1)")

    if es_bien:
        _add(ETAPA_RECEPCION_KARDEX, fecha_kardex, fecha_kardex is not None,
             "SIG_MOVIM_ALMACEN (R,1)")
        _add(ETAPA_PEDIDO_INTERNO, None, False,
             "Pedido TIPO=1 posterior con misma meta+CC (por composite)")
        _add(ETAPA_DESPACHO_PECOSA, fecha_despacho, fecha_despacho is not None,
             "SIG_MOVIM_ALMACEN (S,1) + NRO_PECOSA")

    _add(ETAPA_DEVENGADO, None, False,
         "Devengado consolidado — proviene de SIAF (Fix #2 pendiente)")
    _add(ETAPA_CIERRE, fecha_atenc if tiene_cierre else None, tiene_cierre,
         "SIG_PEDIDOS.ESTADO='7' o SIG_SEGUIMIENTO tipo=19")

    return hitos
