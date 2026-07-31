"""Servicio v2 del pipeline: clasifica desde el snapshot siga.* (vista
materializada) con etapas por FECHA CIERTA y alertas honestas.

Guia Pipeline v2 §02. Diferencias con el modelo anterior:
    - Etapa = ultima con FECHA (principio 7: sin fecha, la etapa no se alcanzo).
    - El avance del expediente/bolsa se muestra SIEMPRE (§02.1), aunque el
      puente pedido<->CCMN no este resuelto. Un pedido `ambiguo` con orden en
      su bolsa no esta "sin avance": tiene `puente_pendiente`, no `estancado`.
    - Alertas con evidencia y fecha (§02.4). Rojo solo `estancado_real`.

La cascada de confianza se reutiliza de pipeline_service (misma logica, sin
duplicar). Este modulo se testea sin BD: recibe filas dict y devuelve cards.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.config import settings
from app.schemas.pipeline import (
    ALERTA_SEVERIDAD,
    CONFIANZA_A_LABEL,
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
    ETAPA_PEDIDO_REGISTRADO,
    ETAPA_RECEPCION_KARDEX,
    MACROFASE_A_LABEL,
)

logger = logging.getLogger(__name__)

# Niveles del puente en los que el CCMN identificado es de ESTE pedido: su
# avance de bolsa se atribuye al pedido (etapa "directa").
CONFIANZA_RESUELTA = frozenset({"unico", "declarado", "resuelto_manual"})


def _d(v: Any) -> date | None:
    if v is None:
        return None
    return v.date() if isinstance(v, datetime) else v


# ─── Avance de la bolsa: hasta donde llego la cadena dura ─────────────────
#
# Orden de las etapas de bolsa por fecha, de la mas avanzada a la mas temprana.
# La bolsa "alcanzo" la etapa mas avanzada que tenga fecha.
_ETAPAS_BOLSA: tuple[tuple[str, str], ...] = (
    # Cierre real: la orden recibio todos sus items (FLAG_RECEP='3'). Es la
    # etapa mas avanzada; si la bolsa/CCMN atribuido cerro, el pedido cerro.
    ("bolsa_fecha_cierre", ETAPA_CIERRE),
    ("bolsa_fecha_devengado", ETAPA_DEVENGADO),
    ("bolsa_fecha_despacho", ETAPA_DESPACHO_PECOSA),
    ("bolsa_fecha_ejecucion", ETAPA_EJECUCION),
    ("bolsa_fecha_compromiso", ETAPA_COMPROMISO_SIAF),
    ("bolsa_fecha_orden", ETAPA_ORDEN_EMITIDA),
    ("bolsa_fecha_certificacion", ETAPA_CERTIFICACION),
    ("bolsa_fecha_cuadro", ETAPA_CUADRO_ADQUISICION),
    ("bolsa_fecha_cotizacion", ETAPA_COTIZACION),
    # Cuadro consolidado / estudio de mercado (etapa 5): sin esta entrada un
    # pedido cuyo CCMN existe pero aun no cotiza se quedaba en "cuadro de
    # necesidades" en el kanban mientras el detalle mostraba la etapa 5.
    ("bolsa_fecha_consolid", ETAPA_CCMN),
)


def max_etapa_bolsa(fila: dict[str, Any]) -> tuple[str | None, date | None]:
    """Etapa mas avanzada de la bolsa (con su fecha), o (None, None)."""
    for col, etapa in _ETAPAS_BOLSA:
        f = _d(fila.get(col))
        if f is not None:
            return etapa, f
    return None, None


def aplicar_avance_ccmn(fila: dict[str, Any], avance: dict[str, Any]) -> None:
    """Sobrescribe el avance de bolsa de la fila con el del CCMN resuelto.

    En una bolsa compartida las columnas `bolsa_*` agregan sobre TODOS los
    candidatos; si el puente resuelve hacia un CCMN concreto, atribuirle al
    pedido el avance agregado es heredar hitos de OTRO candidato (caso 286/B:
    asociado al 2530 sin orden, aparecia en "orden emitida" por la O/C del
    3472). `avance` es una fila de `siga.v_ccmn_avance`.
    """
    fila["bolsa_n_ordenes"] = int(avance.get("n_ordenes") or 0)
    fila["bolsa_n_ordenes_anuladas"] = int(avance.get("n_ordenes_anuladas") or 0)
    fila["bolsa_ordenes_csv"] = avance.get("ordenes_csv")
    for hito in ("consolid", "cotizacion", "cuadro", "certificacion", "orden",
                 "compromiso", "ejecucion", "despacho", "devengado", "cierre"):
        fila[f"bolsa_fecha_{hito}"] = avance.get(f"fecha_{hito}")


def avance_bolsa(fila: dict[str, Any]) -> dict[str, Any]:
    """Dict serializable con el avance duro de la bolsa (§02.1, §02.3)."""
    etapa, _fecha = max_etapa_bolsa(fila)
    csv = fila.get("bolsa_ordenes_csv")
    fecha_orden = _d(fila.get("bolsa_fecha_orden"))
    ordenes = [
        {"nro_orden": int(x), "fecha": fecha_orden}
        for x in (csv.split(",") if csv else [])
        if x.strip()
    ]
    return {
        "n_ordenes": int(fila.get("bolsa_n_ordenes") or 0),
        "ordenes": ordenes,
        "max_etapa": etapa,
        "max_etapa_label": ETAPA_A_LABEL.get(etapa) if etapa else None,
    }


# ─── Clasificacion de la etapa del pedido (por fecha cierta) ──────────────
#
# El pedido tiene etapas PROPIAS (registro, aprobacion, cuadro de necesidad,
# pecosa/almacen para bienes) y hereda el avance de su bolsa SOLO si el puente
# esta resuelto (§02.1). Con puente sin resolver, la etapa del pedido no pasa
# de "cuadro de necesidad": el avance existe pero es de la bolsa, no atribuible.


def clasificar_etapa(fila: dict[str, Any], confianza: str) -> tuple[str, date | None]:
    """Etapa maxima del pedido + su fecha. Devuelve (etapa, fecha_de_la_etapa)."""
    tipo_bien = (fila.get("tipo_bien") or "").strip()
    estado = str(fila.get("estado") or "").strip()
    atribuible = confianza in CONFIANZA_RESUELTA

    # Cierre propio del pedido (ESTADO='7'). Casi nunca ocurre en compras (el
    # cierre real llega por recepcion completa de la orden, abajo), pero si
    # SIGA lo marca es terminal.
    if estado == "7":
        f = _d(fila.get("fecha_atenc")) or _d(fila.get("fecha_pedido"))
        return ETAPA_CIERRE, f

    # Avance heredado de la bolsa: solo si el puente atribuye la bolsa a ESTE
    # pedido. Si no, el pedido se queda en su etapa propia (cuadro de necesidad)
    # y el avance de la bolsa se muestra aparte (avance_bolsa), no como etapa.
    # Va ANTES que la pecosa de bienes: el cierre por recepcion completa
    # (bolsa_fecha_cierre) es un hito mas avanzado que el despacho.
    if atribuible:
        etapa_b, fecha_b = max_etapa_bolsa(fila)
        if etapa_b is not None:
            return etapa_b, fecha_b

    # Bienes: pecosa / almacen son etapas PROPIAS del pedido (llave dura via
    # su NRO_PECOSA), no dependen del puente. Solo se llega aqui si la bolsa
    # atribuida no dio una etapa mas avanzada (o el puente no resuelve).
    if tipo_bien == "B":
        if fila.get("tiene_pecosa"):
            return ETAPA_DESPACHO_PECOSA, _d(fila.get("fecha_pecosa"))
        if fila.get("tiene_ingreso"):
            return ETAPA_EJECUCION, _d(fila.get("fecha_ingreso"))

    # Etapas propias tempranas.
    if fila.get("tiene_cuadro_neces"):
        f = _d(fila.get("fecha_aprob")) or _d(fila.get("fecha_pedido"))
        return ETAPA_CUADRO_NECESIDAD, f
    if estado == "1" or fila.get("fecha_aprob"):
        return ETAPA_PEDIDO_APROBADO, _d(fila.get("fecha_aprob")) or _d(fila.get("fecha_pedido"))
    return ETAPA_PEDIDO_REGISTRADO, _d(fila.get("fecha_pedido"))


# ─── Fechas de todas las etapas alcanzadas (§02.3) ───────────────────────


def fechas_alcanzadas(fila: dict[str, Any], confianza: str) -> dict[str, date]:
    """Mapping etapa -> fecha para todas las etapas con fecha cierta.

    Incluye las propias del pedido y, si el puente esta resuelto, las de la
    bolsa. La UI las usa para el timeline y el "en X desde <fecha>".
    """
    out: dict[str, date] = {}

    def _set(etapa: str, f: Any) -> None:
        d = _d(f)
        if d is not None:
            out.setdefault(etapa, d)

    _set(ETAPA_PEDIDO_REGISTRADO, fila.get("fecha_pedido"))
    _set(ETAPA_PEDIDO_APROBADO, fila.get("fecha_aprob"))
    if fila.get("tiene_cuadro_neces"):
        _set(ETAPA_CUADRO_NECESIDAD, fila.get("fecha_aprob") or fila.get("fecha_pedido"))

    if confianza in CONFIANZA_RESUELTA:
        _set(ETAPA_CCMN, fila.get("bolsa_fecha_consolid"))
        _set(ETAPA_COTIZACION, fila.get("bolsa_fecha_cotizacion"))
        _set(ETAPA_CUADRO_ADQUISICION, fila.get("bolsa_fecha_cuadro"))
        _set(ETAPA_CERTIFICACION, fila.get("bolsa_fecha_certificacion"))
        _set(ETAPA_ORDEN_EMITIDA, fila.get("bolsa_fecha_orden"))
        _set(ETAPA_COMPROMISO_SIAF, fila.get("bolsa_fecha_compromiso"))
        _set(ETAPA_EJECUCION, fila.get("bolsa_fecha_ejecucion"))
        _set(ETAPA_DESPACHO_PECOSA, fila.get("bolsa_fecha_despacho"))
        _set(ETAPA_DEVENGADO, fila.get("bolsa_fecha_devengado"))
        _set(ETAPA_CIERRE, fila.get("bolsa_fecha_cierre"))

    tipo_bien = (fila.get("tipo_bien") or "").strip()
    if tipo_bien == "B":
        _set(ETAPA_EJECUCION, fila.get("fecha_ingreso"))
        _set(ETAPA_DESPACHO_PECOSA, fila.get("fecha_pecosa"))
    return out


# ─── Identificadores (§00 principio 2) ───────────────────────────────────


def identificadores(fila: dict[str, Any], confianza: str) -> dict[str, Any]:
    tipo_bien = (fila.get("tipo_bien") or "").strip()
    ano = fila.get("ano_eje")
    nro = fila.get("nro_pedido")
    ped = f"{nro}-{ano}/{tipo_bien}"

    # Orden/EXP/CCP solo se atribuyen al pedido si el puente resuelve; si no,
    # la UI muestra "O/S de bolsa: ..." desde avance_bolsa (no aqui).
    orden = exp_siaf = ccp = None
    if confianza in CONFIANZA_RESUELTA:
        csv = fila.get("bolsa_ordenes_csv")
        if csv:
            primera = csv.split(",")[0].strip()
            prefijo = "O/S" if tipo_bien == "S" else "O/C"
            orden = f"{prefijo} {primera}"
    return {"pedido": ped, "orden": orden, "exp_siaf": exp_siaf, "ccp_siaf": ccp}


# ─── Alertas v2 (§02.4) ──────────────────────────────────────────────────


def calcular_alerta(
    fila: dict[str, Any],
    etapa: str,
    fecha_etapa: date | None,
    confianza: str,
    hoy: date,
    umbral: int | None,
) -> dict[str, Any] | None:
    """Devuelve la alerta v2 (dict) o None. Con evidencia y fecha siempre.

    Reglas anti-alarma (§02.4):
      1. Antes de `estancado_real`, comprobar el avance de la bolsa: si la bolsa
         ya tiene orden/conformidad, el pedido esta `puente_pendiente`, no
         estancado.
      2. El reloj corre desde la fecha de la etapa, no desde el registro.
      3. Etapas terminales nunca alertan.
    """
    # 3) Terminal: cierre nunca alerta.
    if etapa == ETAPA_CIERRE:
        return None

    n_ordenes = int(fila.get("bolsa_n_ordenes") or 0)
    n_anuladas = int(fila.get("bolsa_n_ordenes_anuladas") or 0)
    tiene_avance_bolsa = n_ordenes > 0
    n_cand = int(fila.get("n_candidatos_ccmn") or 0)

    # cerrado_negativo (gris, terminal): la(s) orden(es) atribuida(s) al pedido
    # estan anuladas y no hay ninguna orden viva. Solo con puente resuelto, para
    # no atribuir una anulacion ajena; sale del flujo activo (no estancado).
    if (
        confianza in CONFIANZA_RESUELTA
        and n_anuladas > 0
        and n_anuladas >= n_ordenes
    ):
        return _alerta("cerrado_negativo",
                       f"la orden atribuida al pedido esta anulada en SIGA",
                       _d(fila.get("bolsa_fecha_orden")))

    # conflicto_puente: una fuente declara un CCMN fuera de los candidatos.
    if confianza == "conflicto":
        return _alerta("conflicto_puente",
                       "una fuente declara un CCMN que no es candidato de la bolsa",
                       _d(fila.get("bolsa_fecha_orden")))

    # puente_pendiente: la bolsa avanzo pero el puente no se resolvio. Ambar,
    # NO rojo. Es el caso 232/S: servicio concluido, puente por confirmar.
    if confianza not in CONFIANZA_RESUELTA and n_cand > 1 and tiene_avance_bolsa:
        etapa_b, fecha_b = max_etapa_bolsa(fila)
        label_b = ETAPA_A_LABEL.get(etapa_b, "avance") if etapa_b else "avance"
        return _alerta(
            "puente_pendiente",
            f"tu bolsa ya tiene {fila.get('bolsa_n_ordenes')} orden(es) "
            f"({label_b.lower()}) — confirma cual corresponde a tu pedido",
            fecha_b,
        )

    # sin_consolidar: aprobado hace > umbral y sin bolsa.
    if (
        not fila.get("tiene_cuadro_neces")
        and etapa in (ETAPA_PEDIDO_APROBADO, ETAPA_PEDIDO_REGISTRADO)
        and umbral is not None
        and fecha_etapa is not None
        and (hoy - fecha_etapa).days > umbral
    ):
        return _alerta("sin_consolidar",
                       f"aprobado hace {(hoy - fecha_etapa).days} dias sin entrar a un cuadro",
                       fecha_etapa)

    # desfase_devengado: el gasto se comprometio hace > umbral pero la meta no
    # tiene devengado MEF. Solo con puente resuelto (si no, el compromiso es de
    # la bolsa, no atribuible a ESTE pedido). Ambar: es un desfase, no un bloqueo.
    fecha_comp = _d(fila.get("bolsa_fecha_compromiso"))
    if (
        confianza in CONFIANZA_RESUELTA
        and fecha_comp is not None
        and umbral is not None
        and (hoy - fecha_comp).days > umbral
        and float(fila.get("devengado_mef") or 0) == 0
        and etapa in (ETAPA_COMPROMISO_SIAF, ETAPA_ORDEN_EMITIDA)
    ):
        return _alerta("desfase_devengado",
                       f"comprometido hace {(hoy - fecha_comp).days} dias y la "
                       f"meta aun no registra devengado en el MEF",
                       fecha_comp)

    # estancado_real: etapa con fecha > umbral Y ninguna posterior (ni del
    # pedido ni de su bolsa). Si la bolsa avanzo, NO es estancado (regla 1).
    if (
        umbral is not None
        and fecha_etapa is not None
        and (hoy - fecha_etapa).days > umbral
        and not tiene_avance_bolsa
    ):
        return _alerta("estancado_real",
                       f"en {ETAPA_A_LABEL.get(etapa, etapa).lower()} desde "
                       f"{fecha_etapa.isoformat()} ({(hoy - fecha_etapa).days} dias), "
                       f"sin avance posterior",
                       fecha_etapa)

    return None


def _alerta(tipo: str, evidencia: str, desde: date | None) -> dict[str, Any]:
    return {
        "tipo": tipo,
        "severidad": ALERTA_SEVERIDAD[tipo],
        "evidencia": evidencia,
        "desde": desde,
    }


# ─── Ensamblado de la card v2 ────────────────────────────────────────────


def construir_card(
    fila: dict[str, Any],
    confianza: str,
    hoy: date,
    umbral: int | None,
    sincronizado_hasta: datetime | None,
) -> dict[str, Any]:
    """A partir de una fila de la vista + su nivel de puente, arma la card v2."""
    etapa, fecha_etapa = clasificar_etapa(fila, confianza)
    macrofase = ETAPA_A_MACROFASE[etapa]
    ab = avance_bolsa(fila)
    alerta = calcular_alerta(fila, etapa, fecha_etapa, confianza, hoy, umbral)

    csv = fila.get("ccmn_candidatos_csv")
    candidatos = sorted(int(x) for x in (csv.split(",") if csv else []) if x.strip())
    ccmn_atribuido = fila.get("ccmn_manual") or fila.get("ccmn_declarado_orden")
    if ccmn_atribuido is None and confianza == "unico" and candidatos:
        ccmn_atribuido = candidatos[0]

    dias = (hoy - fecha_etapa).days if fecha_etapa is not None else None

    return {
        "ano_eje": fila.get("ano_eje"),
        "sec_ejec": str(fila.get("sec_ejec")),
        "nro_pedido": fila.get("nro_pedido"),
        "tipo_bien": fila.get("tipo_bien"),
        "tipo_pedido": fila.get("tipo_pedido"),
        "centro_costo": (fila.get("centro_costo") or "").strip() or None,
        "sec_func": fila.get("sec_func"),
        "estado_pedido": fila.get("estado"),
        "fecha_pedido": _d(fila.get("fecha_pedido")),
        "fecha_aprob": _d(fila.get("fecha_aprob")),
        "fecha_atenc": _d(fila.get("fecha_atenc")),
        "motivo": fila.get("motivo"),
        "solicitante": fila.get("solicitante"),
        "fuente_financ": fila.get("fuente_financ"),
        "monto_total": float(fila.get("monto_total") or 0),
        "items": int(fila.get("items") or 0),
        "etapa": etapa,
        "etapa_numero": ETAPA_A_NUMERO[etapa],
        "etapa_label": ETAPA_A_LABEL[etapa],
        "macrofase": macrofase,
        "macrofase_label": MACROFASE_A_LABEL[macrofase],
        "identificadores": identificadores(fila, confianza),
        "fechas": fechas_alcanzadas(fila, confianza),
        "puente": {
            "nivel": confianza,
            "nivel_label": CONFIANZA_A_LABEL.get(confianza, confianza),
            "bolsa": fila.get("sec_cua_mod_sal"),
            "candidatos": candidatos,
            "ccmn_atribuido": ccmn_atribuido,
            "avance_bolsa": ab,
        },
        "alerta": alerta,
        "sincronizado_hasta": sincronizado_hasta,
        "n_candidatos_ccmn": int(fila.get("n_candidatos_ccmn") or 0),
        "confianza_ccmn": confianza,
        "confianza_ccmn_label": CONFIANZA_A_LABEL.get(confianza, confianza),
        "ccmn_atribuido": ccmn_atribuido,
        "dias_en_etapa": dias,
        "estancado": bool(alerta and alerta["tipo"] == "estancado_real"),
    }
