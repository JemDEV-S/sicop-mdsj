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
from app.repositories import pipeline_read_repo, resolucion_ccmn_repo
from app.services import pipeline_v2
from app.schemas.pipeline import (
    CONFIANZA_A_ESTADO,
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
        # Acepta tanto las filas del snapshot (snake_case) como las de SIGA
        # (UPPER) que aun consume el detalle.
        clave = (
            str(fila.get("tipo_bien") or fila.get("TIPO_BIEN") or "").strip(),
            str(fila.get("tipo_pedido") or fila.get("TIPO_PEDIDO") or "").strip(),
            int(fila.get("nro_pedido") or fila["NRO_PEDIDO"]),
        )
        ccmns = activas.get(clave)
        if not ccmns:
            continue
        # N:M: un pedido puede tener varios CCMN asociados. Para la cascada
        # basta uno (el nivel es `resuelto_manual` igual); la lista completa
        # se expone aparte para el panel de trazabilidad.
        fila["ccmn_manual"] = ccmns[0]
        fila["ccmn_manual_todos"] = list(ccmns)


def _acotar_avance_a_ccmn(
    db: Session, filas: list[dict[str, Any]], *, ano: int
) -> None:
    """En bolsas compartidas, acota el avance de los pedidos RESUELTOS a su CCMN.

    Las columnas `bolsa_*` de la vista agregan sobre todos los candidatos;
    para un pedido con puente resuelto (manual o declarado) el avance
    atribuible es el de SU cuadro consolidado. Con candidato unico no hay nada
    que acotar (bolsa == CCMN). Igual que las resoluciones manuales, esto es
    referencial: si la consulta falla se degrada al avance de bolsa.
    """
    objetivo: list[tuple[dict[str, Any], tuple[str, int]]] = []
    for fila in filas:
        if int(fila.get("n_candidatos_ccmn") or 0) <= 1:
            continue
        ccmn = (
            fila.get("ccmn_manual")
            or fila.get("ccmn_declarado_orden")
            or fila.get("ccmn_declarado_cert")
        )
        if ccmn is None:
            continue
        clave = ((fila.get("tipo_bien") or "").strip(), int(ccmn))
        objetivo.append((fila, clave))
    if not objetivo:
        return

    try:
        avances = pipeline_read_repo.avance_por_ccmn(
            db, ano, sorted({c for _, c in objetivo})
        )
    except Exception:  # noqa: BLE001 — degradar, no romper el kanban
        logger.warning(
            "No se pudo leer siga.v_ccmn_avance; los pedidos resueltos "
            "muestran el avance agregado de su bolsa",
            exc_info=True,
        )
        return

    for fila, clave in objetivo:
        avance = avances.get(clave)
        if avance is not None:
            pipeline_v2.aplicar_avance_ccmn(fila, avance)


# ─── API publica del servicio ─────────────────────────────────────────────


def _sincronizado_hasta(db: Session) -> datetime | None:
    """Ultimo sync SIGA exitoso (para la frescura de la UI, §01.4)."""
    row = db.execute(
        text(
            """
            SELECT MAX(fin) FROM logs.sincronizacion
             WHERE job LIKE 'siga_pipeline:%' AND estado = 'exito'
            """
        )
    ).first()
    return row[0] if row and row[0] else None


def clasificar_pedidos(
    db: Session, *, ano: int, centros: list[str] | None
) -> list[dict[str, Any]]:
    """Lista plana de cards v2 desde el snapshot (vista materializada).

    Guia Pipeline v2 §02: etapa por fecha cierta, avance de bolsa siempre
    visible, alertas honestas. Lee de Postgres (pipeline_read_repo), no de SIGA.
    """
    filas = pipeline_read_repo.pipeline_pedidos(db, ano, centros)
    _aplicar_resoluciones_manuales(db, filas, ano=ano)
    _acotar_avance_a_ccmn(db, filas, ano=ano)
    dias_fallback, por_macrofase = _cargar_umbrales(db)
    hoy = date.today()
    sinc = _sincronizado_hasta(db)

    # Devengado MEF por meta (§02.6): una sola consulta agregada para todas las
    # metas del lote, para la alerta desfase_devengado sin N+1.
    sec_funcs = sorted({int(f["sec_func"]) for f in filas if f.get("sec_func")})
    dev_mef = pipeline_read_repo.devengado_mef_por_sec_func(db, ano, sec_funcs)

    cards: list[dict[str, Any]] = []
    for f in filas:
        confianza = confianza_match(f)
        etapa, _fecha = pipeline_v2.clasificar_etapa(f, confianza)
        macrofase = ETAPA_A_MACROFASE[etapa]
        umbral = _umbral_para(macrofase, dias_fallback, por_macrofase)
        f["devengado_mef"] = dev_mef.get(int(f["sec_func"]), 0.0) if f.get("sec_func") else 0.0
        cards.append(pipeline_v2.construir_card(f, confianza, hoy, umbral, sinc))
    return cards


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
    estado_pedido = str(ficha.get("estado_pedido") or ficha.get("ESTADO") or "").strip()

    # FECHA_APROB/FECHA_ATENC de la cabecera vienen NULL en el 100% de los
    # pedidos de compra 2026: la fecha real vive en el seguimiento. Para los
    # pedidos '2' el hito de aprobacion es el VB del jefe (estado '1'); el
    # estado '2' (Aprobado) solo lo alcanzan otros tipos de pedido. El
    # fallback solo aplica si la cabecera dice aprobado/cerrado, para no
    # marcar aprobado un pedido aun en proceso con VB dado.
    fecha_aprob = _to_dt(ficha.get("FECHA_APROB") or ficha.get("fecha_aprob"))
    if fecha_aprob is None and estado_pedido in ("1", "7"):
        fecha_aprob = _to_dt(
            ficha.get("fecha_aprob_seg") or ficha.get("fecha_vb_jefe")
        )
    fecha_atenc = _to_dt(
        ficha.get("FECHA_ATENC") or ficha.get("fecha_atenc")
        or ficha.get("fecha_atendido_seg")
    )

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

    # FECHA_CUADRO viene NULL en el 97% de los cuadros 2026; el hito real de
    # "cuadro autorizado" es FECHA_AUTORIZ (100% poblada, = FECHA_COMPRA en el
    # 99%). Misma regla que el extractor del kanban (diagnostico_sesion6).
    fecha_cuadro = min(
        (c.get("FECHA_AUTORIZ") or c.get("fecha_autoriz")
         or c.get("FECHA_COMPRA") or c.get("fecha_compra")
         or c.get("FECHA_CUADRO") or c.get("fecha_cuadro") for c in cuadros
         if c.get("FECHA_AUTORIZ") or c.get("fecha_autoriz")
         or c.get("FECHA_COMPRA") or c.get("fecha_compra")
         or c.get("FECHA_CUADRO") or c.get("fecha_cuadro")),
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

    # Etapas 4-7: presencia por la cadena del CCMN (bolsa -> CCMN -> PAAC ->
    # cotizacion -> cuadro adq.), no por `cuadros`/`certificaciones`, que solo
    # existen si ya hay orden. Un pedido detenido en el estudio de mercado
    # tiene CCMN pero no orden: con el proxy viejo se veia en "cuadro
    # necesidad" (caso 311/S). Los flags vienen del repo (`_flags_programacion`).
    tiene_puente_paac = bool(ficha.get("tiene_puente_paac"))
    tiene_ccmn_prog = bool(ficha.get("tiene_ccmn"))
    tiene_cotizacion = bool(ficha.get("tiene_cotizacion"))
    # El cuadro de adquisicion puede verse por la cadena del CCMN o por la
    # orden ya emitida; cualquiera de las dos cuenta.
    tiene_cuadro_adq = bool(ficha.get("tiene_cuadro_adq")) or bool(cuadros)
    # Compromiso: la interfase al SIAF (FECHA_INTERFASE) es la senal que usa el
    # kanban. El compromiso se hizo aunque SIAF aun no devuelva FECHA_SIAF
    # (caso 1005/S). Se toma cualquiera de las dos para que detalle y kanban
    # coincidan; sin FECHA_INTERFASE el detalle subcontaba la etapa 10.
    tiene_compromiso = any(
        _to_dt(e.get("FECHA_INTERFASE") or e.get("fecha_interfase")
               or e.get("FECHA_SIAF") or e.get("fecha_siaf"))
        for e in expedientes
    )
    tiene_ejecucion = bool(conformidades) if not es_bien else bool(fecha_ingreso)
    tiene_cierre = estado_pedido == "7"

    # Estado de las etapas 4-7, que solo son observables a traves del CCMN.
    # Si el nivel no resuelve, el avance observado puede ser de OTRO pedido de
    # la bolsa: se marca `grupo` (ambar) y NO cuenta como alcanzada (§8).
    confianza = confianza_match(ficha)
    estado_prog = CONFIANZA_A_ESTADO.get(confianza, "sin_dato")

    hitos: list[dict[str, Any]] = []

    def _add(
        etapa: str,
        fecha: datetime | None,
        alcanzada: bool,
        detalle: str | None = None,
        *,
        via_ccmn: bool = False,
        docs: list[dict[str, Any]] | None = None,
    ):
        """Agrega un hito con su estado de UI y sus documentos identificadores.

        `via_ccmn=True` marca las etapas que solo se ven a traves del CCMN
        (4-7): ahi el estado sale de la cascada de confianza, no del booleano.
        El resto son evidencia directa del pedido.

        `docs` son los numeros con los que el funcionario encuentra el
        documento en SIGA (CCMN 2266, CCP 182, OC 132...). Sin esto el
        recorrido dice "llego a certificacion" pero no *cual* certificacion,
        que es justo lo que hace falta para verificarlo.
        """
        if not alcanzada:
            estado = "sin_dato"
        elif via_ccmn:
            estado = estado_prog
        else:
            estado = "directo"

        hitos.append({
            "etapa": etapa,
            "etapa_numero": ETAPA_A_NUMERO[etapa],
            "etapa_label": ETAPA_A_LABEL[etapa],
            "macrofase": ETAPA_A_MACROFASE[etapa],
            "fecha": fecha,
            "detalle": detalle,
            "estado": estado,
            # Solo tienen sentido si la etapa se alcanzo por este pedido.
            "documentos": (docs or []) if estado in ESTADOS_ALCANZADOS else [],
            # `alcanzada` se mantiene por compatibilidad, pero ahora excluye
            # `grupo`: un avance ajeno no es avance de este pedido.
            "alcanzada": estado in ESTADOS_ALCANZADOS,
        })

    def _doc(etiqueta: str, valor: Any) -> dict[str, Any] | None:
        """Un identificador para mostrar y copiar. None si no hay valor."""
        if valor in (None, "", 0):
            return None
        return {"etiqueta": etiqueta, "valor": str(valor).strip()}

    def _docs(*pares: tuple[str, Any]) -> list[dict[str, Any]]:
        return [d for e, v in pares if (d := _doc(e, v)) is not None]

    # Identificadores por etapa: son los numeros con los que el funcionario
    # busca el documento en SIGA. `detalle` queda como la tabla de origen (util
    # para auditar de donde sale el dato), pero lo que se lee es `documentos`.
    nro_pedido_txt = str(
        ficha.get("NRO_PEDIDO") or ficha.get("nro_pedido") or ""
    ).strip()
    ccmn = ficha.get("ccmn_atribuido") or ficha.get("ccmn_manual") \
        or ficha.get("ccmn_declarado_orden") or ficha.get("ccmn_declarado_cert")
    bolsa = ficha.get("sec_cua_mod_sal")

    # Las ordenes se matchean por composite (item + meta + clasificador), y en
    # una bolsa compartida los pedidos comparten esos campos: el match trae las
    # ordenes de TODOS. Si la cascada identifico el CCMN de este pedido, se usa
    # su cadena (cuadro -> CCP -> OC) para quedarse solo con lo suyo. Mostrar
    # las tres OC seria repetir el error de §7 en otro lugar.
    ordenes_propias = ordenes
    if ccmn is not None:
        del_ccmn = [
            o for o in ordenes
            if o.get("NRO_CONS_PAAC") is not None
            and int(o["NRO_CONS_PAAC"]) == int(ccmn)
        ]
        if del_ccmn:
            ordenes_propias = del_ccmn

    sec_cuadros_propios = {
        o.get("SEC_CUADRO") for o in ordenes_propias if o.get("SEC_CUADRO")
    }
    certifs_propias = {
        o.get("NRO_CERTIFICA") for o in ordenes_propias if o.get("NRO_CERTIFICA")
    }
    exp_sigas_propios = {
        o.get("EXP_SIGA") for o in ordenes_propias if o.get("EXP_SIGA")
    }

    # Cierre real del pedido: sus ordenes atribuidas recibieron todos sus items
    # (FLAG_RECEP='3'). Una O/S puede tener varias conformidades (entregables /
    # pagos); CANT_RECIBIDA ya las agrega, asi que FECHA_CIERRE solo llega
    # cuando el ultimo entregable entro. El pedido cierra cuando TODAS sus
    # ordenes atribuidas cerraron; la fecha es la mas tardia. ESTADO='7' de la
    # cabecera tambien cierra (rara vez ocurre en compras).
    ordenes_vivas = [o for o in ordenes_propias
                     if (o.get("ESTADO") or "").strip() != "4"]
    fechas_cierre_ord = [
        _to_dt(o.get("FECHA_CIERRE") or o.get("fecha_cierre"))
        for o in ordenes_vivas
    ]
    cierre_por_recepcion = (
        bool(ordenes_vivas)
        and all(f is not None for f in fechas_cierre_ord)
    )
    fecha_cierre_ord = (
        max(f for f in fechas_cierre_ord if f is not None)
        if cierre_por_recepcion else None
    )
    tiene_cierre = tiene_cierre or cierre_por_recepcion
    # Terminal negativo: todas las ordenes atribuidas estan anuladas.
    tiene_cierre_negativo = (
        bool(ordenes_propias) and not ordenes_vivas
    )

    cert_filtradas = [
        c for c in certificaciones
        if not certifs_propias or c.get("NRO_CERTIFICA") in certifs_propias
    ]
    cuadros_filtrados = [
        c for c in cuadros
        if not sec_cuadros_propios or c.get("SEC_CUADRO") in sec_cuadros_propios
    ]
    exp_filtrados = [
        e for e in expedientes
        if not exp_sigas_propios or e.get("EXP_SIGA") in exp_sigas_propios
    ]

    docs_cert = _docs(
        *[("CCP", c.get("NRO_CERTIFICA")) for c in cert_filtradas],
        *[("Certif. SIAF", c.get("NRO_CERTIFICA_SIAF")) for c in cert_filtradas],
    )
    docs_orden = _docs(*[("OC", o.get("NRO_ORDEN")) for o in ordenes_propias])
    docs_exp = _docs(
        *[("Exp. SIGA", e.get("EXP_SIGA")) for e in exp_filtrados],
        *[("Exp. SIAF", e.get("EXP_SIAF")) for e in exp_filtrados],
    )
    docs_cuadro = _docs(
        *[("Cuadro adq.", c.get("SEC_CUADRO")) for c in cuadros_filtrados]
    )
    pecosas = _docs(*[
        ("PECOSA", i.get("NRO_PECOSA") or i.get("nro_pecosa")) for i in items
    ])
    # Estudio de mercado: su numero identifica la etapa 5 cuando el pedido llego
    # ahi sin tener aun orden. Sale de la cadena del CCMN (`_flags_programacion`).
    # El CCMN es el "cuadro consolidado" (NRO_CONSOLID), distinto de la bolsa
    # (SEC_CUA_MOD_SAL) que se muestra en "Cuadro de necesidades" (etapa 3).
    # Etiquetarlos distinto evita que dos numeros lean como lo mismo.
    docs_estudio = _docs(
        ("Cuadro consolidado", ccmn),
        ("Estudio de mercado", ficha.get("nro_est_mdo")),
    )

    # El `detalle` de cada etapa es lenguaje del funcionario: explica QUE paso,
    # no de que tabla de SIGA sale (eso vivia aqui antes y no le servia a nadie
    # -- el numero del documento, que si sirve, va en `docs`).
    _add(ETAPA_PEDIDO_REGISTRADO, fecha_pedido, fecha_pedido is not None,
         "El area solicitante registro el pedido.",
         docs=_docs(("Pedido", nro_pedido_txt)))
    _add(ETAPA_PEDIDO_APROBADO, fecha_aprob,
         fecha_aprob is not None or estado_pedido in ("1", "7"),
         "El pedido fue aprobado.")
    _add(ETAPA_CUADRO_NECESIDAD, None, tiene_cuadro_neces,
         "La necesidad se incluyo en un cuadro de necesidades.",
         docs=_docs(("Cuadro necesidades", bolsa)))
    # Etapas 4-7: se ven por la cadena del CCMN -> estado por la cascada.
    # Fechas de la cadena de programacion (las devuelve `_flags_programacion`,
    # acotadas al CCMN resuelto cuando el puente resuelve).
    fecha_consolid = _to_dt(ficha.get("fecha_consolid"))
    fecha_cotiz = _to_dt(ficha.get("fecha_cotizacion_prog"))
    if fecha_cuadro is None:
        # Sin orden todavia, el cuadro de adquisicion no aparece en `cuadros`
        # (que se construye hacia abajo desde la orden); la fecha viene de la
        # cadena del CCMN hacia arriba.
        fecha_cuadro = _to_dt(ficha.get("fecha_cuadro_prog"))

    _add(ETAPA_PUENTE_PAAC, fecha_consolid, tiene_puente_paac,
         "La necesidad entro a la programacion anual (PAAC).", via_ccmn=True,
         docs=_docs(("Cuadro consolidado", ccmn)))
    _add(ETAPA_CCMN, fecha_consolid, tiene_ccmn_prog,
         "Se hizo el estudio de mercado del requerimiento.", via_ccmn=True,
         docs=docs_estudio)
    _add(ETAPA_COTIZACION, fecha_cotiz, tiene_cotizacion,
         "Se solicitaron cotizaciones a proveedores.", via_ccmn=True,
         docs=_docs(("Cuadro consolidado", ccmn)))
    _add(ETAPA_CUADRO_ADQUISICION, fecha_cuadro, tiene_cuadro_adq,
         "Se elaboro el cuadro de adquisicion.", via_ccmn=True, docs=docs_cuadro)
    _add(ETAPA_CERTIFICACION, fecha_certif, tiene_certif,
         "Se certifico el presupuesto (CCP).", docs=docs_cert)
    _add(ETAPA_ORDEN_EMITIDA, fecha_orden, tiene_orden,
         "Se emitio la orden de compra o de servicio.", docs=docs_orden)
    _add(ETAPA_COMPROMISO_SIAF, fecha_exp, tiene_compromiso,
         "El gasto se comprometio en el SIAF.", docs=docs_exp)
    _add(ETAPA_EJECUCION, fecha_confor or fecha_ingreso, tiene_ejecucion,
         "El bien o servicio se recibio con conformidad."
         if not es_bien else "El bien ingreso a almacen.",
         docs=docs_orden)

    if es_bien:
        _add(ETAPA_RECEPCION_KARDEX, fecha_kardex, fecha_kardex is not None,
             "El bien se registro en el kardex de almacen.")
        _add(ETAPA_PEDIDO_INTERNO, None, False,
             "Pedido interno para retirar el bien de almacen.")
        _add(ETAPA_DESPACHO_PECOSA, fecha_despacho, fecha_despacho is not None,
             "El almacen despacho el bien (PECOSA).", docs=pecosas)

    # Devengado presupuestal: es del MEF, pero a NIVEL META (sec_func), no por
    # orden — el clasificador SIGA no cruza 1:1 con SIAF y EXPEDIENTE_SIAF de la
    # conformidad viene NULL. Por eso el devengado MEF NO puede marcar por si
    # solo esta etapa: casi toda meta tiene algo devengado y marcaria devengado
    # a pedidos sin siquiera ejecucion (timeline incoherente: devengado [15]
    # alcanzado con ejecucion [11] pendiente). La etapa se alcanza con la
    # evidencia REAL de ejecucion del pedido (conformidad / entrada a almacen);
    # el devengado MEF de la meta se muestra como confirmacion en el texto.
    dev_mef = float(ficha.get("devengado_mef") or 0)
    _add(ETAPA_DEVENGADO, fecha_confor or fecha_ingreso, tiene_ejecucion,
         "El gasto se devengo. La meta del pedido registra devengado en el MEF."
         if (tiene_ejecucion and dev_mef > 0)
         else "El gasto se devengo (ejecucion con conformidad)."
         if tiene_ejecucion
         else "Devengado: el monto autoritativo proviene del MEF.")

    fecha_cierre_final = (
        fecha_cierre_ord or (fecha_atenc if estado_pedido == "7" else None)
    )
    if tiene_cierre_negativo:
        _add(ETAPA_CIERRE, fecha_orden, True,
             "El pedido se cerro: su orden fue anulada en SIGA.")
    else:
        _add(ETAPA_CIERRE, fecha_cierre_final, tiene_cierre,
             "El pedido se cerro: la orden recibio todo lo solicitado."
             if cierre_por_recepcion else "El pedido fue atendido y cerrado.")

    return hitos
