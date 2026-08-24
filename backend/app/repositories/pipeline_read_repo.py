"""Repositorio de LECTURA del pipeline (PostgreSQL, snapshot siga.*).

Guia Pipeline v2 §01.4. Reemplaza las lecturas en caliente de SIGA: el kanban,
el detalle y la bolsa leen del snapshot (vista materializada + tablas siga.*),
en milisegundos y sin tocar SIGA. La ESCRITURA del snapshot vive en los jobs
(app/jobs/sync_siga_pipeline.py, el "siga_sync_repo" de la guia).

Este repo NO clasifica ni aplica umbrales: devuelve la evidencia dura + fechas
+ avance de bolsa. La cascada de confianza y las alertas viven en el service
(pipeline_service), que asi se testea sin BD.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

# ─── Parseo de fuentes declarativas (idem que antes, ahora sobre snapshot) ─
#
# SIGA no vincula pedido y CCMN: solo queda el texto libre donde el usuario
# escribe de que pedido viene. Regex validado contra los formatos de 2026.

RE_PEDIDO = re.compile(
    r"PEDIDO\s*(?:DE\s*(?:SERVICIO|COMPRA)\s*)?N?[^0-9A-Z]{0,4}(\d{1,6})", re.I
)
RE_CONTRATO = re.compile(r"SEGUN\s+CONTRATO", re.I)


def parsear_nro_pedido(texto: str | None) -> int | None:
    """Extrae el nº de pedido declarado en texto libre. None si no nombra uno."""
    if not texto or RE_CONTRATO.search(texto):
        return None
    m = RE_PEDIDO.search(texto)
    return int(m.group(1)) if m else None


def _agrupar_declaraciones(rows: Any) -> dict[tuple[str, int], set[tuple[int, int | None]]]:
    """(tipo_bien, nro_pedido) -> conjunto de (CCMN, meta_de_la_orden).

    Se guarda la meta (SEC_FUNC) de la orden que declara: una declaracion de
    texto solo es fiable si la orden es de la MISMA meta que el pedido. El texto
    lo escribe logistica a mano y a veces trae un nº de pedido equivocado (caso
    O/S 73 declara "PEDIDO N°0069" pero la orden es meta 73 y el pedido 69 es
    meta 83 — servicios distintos). El cruce por meta descarta esos typos.
    """
    out: dict[tuple[str, int], set[tuple[int, int | None]]] = defaultdict(set)
    for r in rows:
        ped = parsear_nro_pedido(r["texto"])
        if ped is None or r["ccmn"] is None:
            continue
        meta = int(r["meta_orden"]) if r.get("meta_orden") is not None else None
        out[((r["tipo_bien"] or "").strip(), ped)].add((int(r["ccmn"]), meta))
    return out


def _elegir_declarado(
    declaraciones: dict[tuple[str, int], set[tuple[int, int | None]]],
    tipo_bien: str,
    nro_pedido: int,
    candidatos: frozenset[int],
    sec_func: int | None = None,
) -> int | None:
    """CCMN declarado inequivoco para el pedido, o None.

    Filtra por meta: solo cuentan las declaraciones de ordenes cuya meta
    coincide con la del pedido (`sec_func`). Asi un typo en el texto de la orden
    (declara un pedido de OTRA meta) no arrastra al pedido a un CCMN ajeno.
    Si no se conoce la meta del pedido o de la orden, no se filtra (se degrada
    al comportamiento anterior, conservador).
    """
    decl = declaraciones.get((tipo_bien, nro_pedido))
    if not decl:
        return None
    # Descarta las declaraciones de otra meta (typo de logistica).
    if sec_func is not None:
        decl = {
            (ccmn, meta) for (ccmn, meta) in decl
            if meta is None or meta == int(sec_func)
        }
        if not decl:
            return None
    ccmns = {ccmn for (ccmn, _meta) in decl}
    dentro = ccmns & candidatos
    if len(dentro) == 1:
        return next(iter(dentro))
    if dentro:
        return None
    return next(iter(ccmns)) if len(ccmns) == 1 else None


# ─── Declaraciones desde el snapshot (concepto de orden -> CCMN) ─────────
# La orden nombra el pedido en su concepto; su CCMN es siga.ordenes.nro_consolid
# (cadena dura via certificacion_fase, ya poblado en el sync).

# La orden nombra el pedido en su CONCEPTO o en las ESPECIFICACIONES del item.
# 751 ordenes 2026 lo dicen SOLO en especificaciones ("SEGUN PEDIDO DE SERVICIO
# N°0069"): sin mirar ambas, el kanban no resuelve el puente y discrepa del
# detalle (caso 69/S). Se emiten dos filas por orden (una por texto) para que el
# parser de Python las agrupe igual.
_SQL_DECL_ORDEN = """
    SELECT o.tipo_bien, o.nro_consolid AS ccmn, o.sec_func AS meta_orden,
           o.concepto AS texto
    FROM siga.ordenes o
    WHERE o.ano_eje = :ano AND o.sec_ejec = :sec_ejec
      AND o.concepto IS NOT NULL AND o.nro_consolid IS NOT NULL
    UNION ALL
    SELECT o.tipo_bien, o.nro_consolid AS ccmn, o.sec_func AS meta_orden,
           o.especificaciones AS texto
    FROM siga.ordenes o
    WHERE o.ano_eje = :ano AND o.sec_ejec = :sec_ejec
      AND o.especificaciones IS NOT NULL AND o.nro_consolid IS NOT NULL
"""


def _cargar_declaraciones(db: Session, ano: int) -> dict[tuple[str, int], set[int]]:
    p = {"ano": ano, "sec_ejec": int(settings.SEC_EJEC)}
    return _agrupar_declaraciones(
        db.execute(text(_SQL_DECL_ORDEN), p).mappings().all()
    )


# ─── Kanban: todas las filas del pipeline desde la vista materializada ───

_SQL_KANBAN = """
    SELECT * FROM siga.v_pipeline_pedido
    WHERE ano_eje = :ano
    {filtro_cc}
    ORDER BY fecha_pedido DESC NULLS LAST, nro_pedido DESC
"""


def pipeline_pedidos(
    db: Session, ano: int, centros: list[str] | None = None
) -> list[dict[str, Any]]:
    """Filas del kanban desde la vista materializada + insumos de la cascada.

    Cada fila trae la evidencia dura, las fechas por etapa (propia y de bolsa)
    y los CCMN candidatos/declarados. El service clasifica y alerta.
    """
    if centros is not None and len(centros) == 0:
        return []

    params: dict[str, Any] = {"ano": ano}
    if centros is not None:
        binds = ", ".join(f":cc{i}" for i in range(len(centros)))
        filtro_cc = f"AND centro_costo IN ({binds})"
        params.update({f"cc{i}": c for i, c in enumerate(centros)})
    else:
        filtro_cc = ""

    sql = _SQL_KANBAN.format(filtro_cc=filtro_cc)
    filas = [dict(r) for r in db.execute(text(sql), params).mappings()]

    declaraciones = _cargar_declaraciones(db, ano)
    for fila in filas:
        _adjuntar_puente(fila, declaraciones)
    return filas


def _adjuntar_puente(
    fila: dict[str, Any],
    declaraciones: dict[tuple[str, int], set[tuple[int, int | None]]],
) -> None:
    """Añade a la fila los insumos de la cascada del puente (candidatos, declarados).

    `ccmn_manual` lo inyecta el service desde Postgres (resoluciones).
    """
    tipo_bien = (fila.get("tipo_bien") or "").strip()
    nro_pedido = int(fila["nro_pedido"])
    sec_func = fila.get("sec_func")
    csv = fila.get("ccmn_candidatos_csv")
    candidatos = frozenset(
        int(x) for x in csv.split(",") if x.strip()
    ) if csv else frozenset()
    fila["ccmn_candidatos"] = candidatos
    fila["ccmn_declarado_orden"] = _elegir_declarado(
        declaraciones, tipo_bien, nro_pedido, candidatos,
        int(sec_func) if sec_func is not None else None,
    )
    # `declarado_cert` se fusiono en la fuente de orden (§02.5): el concepto de
    # la orden es la fuente unica. Se deja el campo por compatibilidad de cascada.
    fila["ccmn_declarado_cert"] = None
    fila["ccmn_manual"] = None


# ─── Avance por CCMN individual (caso 286/B) ─────────────────────────────
#
# `v_bolsa_avance` agrega sobre TODOS los candidatos de la bolsa; cuando el
# puente resuelve hacia un CCMN concreto, el avance atribuible es el de ESE
# CCMN. El service lo usa para sobrescribir los campos bolsa_* de las filas
# resueltas antes de clasificar.


def avance_por_ccmn(
    db: Session, ano: int, claves: list[tuple[str, int]]
) -> dict[tuple[str, int], dict[str, Any]]:
    """Avance de la cadena dura por (tipo_bien, nro_consolid) desde
    `siga.v_ccmn_avance`."""
    if not claves:
        return {}
    from sqlalchemy import bindparam

    ccmns = sorted({int(c) for _, c in claves})
    rows = db.execute(
        text(
            """
            SELECT tipo_bien, nro_consolid, n_ordenes, n_ordenes_anuladas,
                   ordenes_csv,
                   fecha_consolid, fecha_cotizacion, fecha_cuadro, fecha_certificacion,
                   fecha_orden, fecha_compromiso, fecha_ejecucion,
                   fecha_despacho, fecha_devengado, fecha_cierre
            FROM siga.v_ccmn_avance
            WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
              AND nro_consolid IN :ccmns
            """
        ).bindparams(bindparam("ccmns", expanding=True)),
        {"ano": ano, "sec_ejec": int(settings.SEC_EJEC), "ccmns": ccmns},
    ).mappings()
    out = {
        ((r["tipo_bien"] or "").strip(), int(r["nro_consolid"])): dict(r)
        for r in rows
    }
    return {k: v for k, v in out.items() if k in set(claves)}


# ─── Cruce MEF por celda (§02.6) ─────────────────────────────────────────
#
# El devengado presupuestal es SIEMPRE del MEF (principio 1), nunca de SIGA. La
# celda es (SEC_FUNC, CLASIFICADOR); la llave 100% fiable que ambos lados
# comparten es SEC_FUNC (la orden la trae de SIG_ORDEN_PRESUPUESTO). El
# clasificador de SIGA ('2.3. 2  9. 1  1') no cruza 1:1 con el desglose SIAF,
# asi que el cruce se hace a nivel meta (SEC_FUNC) y el EXP_SIAF/CCP se muestran
# como identificadores para la verificacion manual en SIAF (como pide el doc).


def devengado_mef_por_sec_func(
    db: Session, ano: int, sec_funcs: list[int]
) -> dict[int, float]:
    """Devengado MEF acumulado del año por SEC_FUNC (suma de meses > 0).

    Delega en `ejecucion_mef_repo.ejecucion_por_meta` (vista
    `siaf.v_ejecucion_meta_anual`) para que exista **una sola definición** de
    "devengado MEF" en todo el backend — saldos, cruce y pipeline la comparten
    (Docs/consolidacion-backend-presupuestal.md §1.3, convergencia de rutas).

    Mantiene la firma `dict[sec_func, float]` que el pipeline ya consume; extrae
    solo el devengado. Verificado equivalente al centavo con la query directa
    que reemplaza.
    """
    from app.repositories import ejecucion_mef_repo

    por_meta = ejecucion_mef_repo.ejecucion_por_meta(
        db, ano=ano, sec_funcs=sec_funcs
    )
    return {sf: float(v["devengado"]) for sf, v in por_meta.items()}


# ─── Clasificador de gasto por pedido (cruce fino §9.7) ──────────────────
#
# ACTUALIZA la conclusión de §232-239: el clasificador de la ORDEN no cruza,
# pero el del PEDIDO-ITEM sí, tras normalizarlo. El clasificador SIGA viene en
# ancho fijo con espacios ('2.3. 1 10. 1  1'); sus 6 enteros son
# transaccion.generica.subgenerica.subgen_det.especifica.espec_det. Tomando las
# posiciones 2-6 se obtiene la llave '3.1.10.1.1', IDÉNTICA a la de
# siaf.v_ejecucion_normalizada. Verificado sobre 2026: 390 celdas cruzan, 0
# solo-SIGA, 93.6% del devengado de bienes/servicios cubierto (Docs/
# pipeline-vista-profesional-v2.md §9.7).
#
# Un pedido puede tener ítems de varios clasificadores; se toma el DOMINANTE
# (mayor valor_soles), que es el que define la específica de gasto del pedido
# para el reporte. El monto por clasificador se conserva para el reparto.

# regexp_split_to_array(trim(clasificador), '[^0-9]+') parte por cualquier
# tramo no numérico (espacios y puntos), colapsando los anchos variables. Los
# 6 enteros salen en orden; [2..6] son generica..especifica_det.
#
# El pipeline de pedidos abarca genérica 3 (bienes y servicios) y genérica 6
# (activos no financieros / compras de proyectos de inversión) — ambas cruzan
# con SIAF por SEC_FUNC + clasificador (verificado 2026: g3 93.6%, g6 110/112
# celdas). La genérica 1 (planilla) no pasa por pedidos, así que no aparece.
_GENERICAS_PIPELINE = ("3", "6")
_SQL_CLASIF_POR_PEDIDO = """
    WITH parts AS (
        SELECT
            pi.tipo_bien, pi.tipo_pedido, pi.nro_pedido,
            pi.valor_soles,
            regexp_split_to_array(trim(pi.clasificador), '[^0-9]+') AS p
        FROM siga.pedido_items pi
        WHERE pi.ano_eje = :ano AND pi.sec_ejec = :sec_ejec
          AND pi.clasificador IS NOT NULL AND trim(pi.clasificador) <> ''
    ),
    clasif AS (
        SELECT
            trim(tipo_bien) AS tipo_bien,
            trim(tipo_pedido) AS tipo_pedido,
            nro_pedido,
            p[2] || '.' || p[3] || '.' || p[4] || '.' || p[5] || '.' || p[6]
                AS clasificador,
            COALESCE(valor_soles, 0) AS valor_soles
        FROM parts
        WHERE p[2] IN ('3', '6')
          AND p[3] IS NOT NULL AND p[4] IS NOT NULL
          AND p[5] IS NOT NULL AND p[6] IS NOT NULL
    ),
    por_clasif AS (
        SELECT tipo_bien, tipo_pedido, nro_pedido, clasificador,
               SUM(valor_soles) AS monto
        FROM clasif
        GROUP BY tipo_bien, tipo_pedido, nro_pedido, clasificador
    ),
    -- Clasificador dominante del pedido = el de mayor monto (desempate: menor
    -- código, determinista).
    ranked AS (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY tipo_bien, tipo_pedido, nro_pedido
                   ORDER BY monto DESC, clasificador ASC
               ) AS rn
        FROM por_clasif
    )
    SELECT tipo_bien, tipo_pedido, nro_pedido, clasificador, monto
    FROM ranked
    WHERE rn = 1
"""


def clasificador_por_pedido(
    db: Session, ano: int
) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Clasificador de gasto DOMINANTE de cada pedido, normalizado a la llave
    SIAF ('3.1.10.1.1').

    Returns:
        `{(tipo_bien, tipo_pedido, nro_pedido): {"clasificador": str,
        "monto": float}}`. Solo pedidos con al menos un ítem de genérica 3
        (bienes y servicios). Los pedidos sin clasificador cruzable no aparecen
        — el consumidor los agrupa bajo "sin clasificador".
    """
    rows = db.execute(
        text(_SQL_CLASIF_POR_PEDIDO),
        {"ano": ano, "sec_ejec": int(settings.SEC_EJEC)},
    ).mappings().all()
    return {
        (
            (r["tipo_bien"] or "").strip(),
            (r["tipo_pedido"] or "").strip(),
            int(r["nro_pedido"]),
        ): {"clasificador": r["clasificador"], "monto": float(r["monto"] or 0)}
        for r in rows
    }


# ─── Órdenes y PECOSAS por meta (pestañas del reporte, §9.7) ─────────────
#
# El reporte profesional lista, por meta, las órdenes de compra (O/C = bienes)
# y de servicio (O/S = servicios) y las PECOSAS (despacho de almacén). Todo sale
# del snapshot PG — cero llamadas en caliente a SIGA:
#
#   - `siga.ordenes` ya trae `sec_func` (la meta de la orden, vía
#     SIG_ORDEN_PRESUPUESTO) y `tipo_bien` ('B'→O/C, 'S'→O/S). Es la misma tabla
#     que alimenta el puente pedido↔orden, así que las cifras concuerdan con el
#     detalle del pedido.
#   - Las PECOSAS son movimientos de salida de almacén (`siga.movimientos_almacen`,
#     TIPO_MOVIMTO='S') colgados de una orden por `nro_orden`. La meta de la
#     PECOSA es la de su orden (el almacén no tiene SEC_FUNC propio).
#
# Solo se piden las metas visibles del alcance (RN-06): no se filtra ni se
# muestra dinero/trámite de metas que el usuario no ve.

_SQL_ORDENES_POR_META = """
    SELECT
        o.sec_func,
        o.tipo_bien,
        o.nro_orden,
        o.clasificador,
        o.estado,
        o.estado_siaf,
        o.exp_siaf,
        o.total_fact_soles,
        o.concepto,
        o.proveedor_nombre,
        o.proveedor_ruc,
        o.fecha_orden,
        o.flag_recep
    FROM siga.ordenes o
    WHERE o.ano_eje = :ano AND o.sec_ejec = :sec_ejec
      AND o.sec_func IN :sfs
    ORDER BY o.sec_func, o.tipo_bien, o.fecha_orden DESC NULLS LAST, o.nro_orden DESC
"""

# PECOSAS: la salida de almacén (TIPO_MOVIMTO='S') que despacha una orden. Se
# ata a la meta por la orden (siga.ordenes.sec_func). Una orden puede tener
# varias salidas; cada una es una PECOSA distinta (NRO_PECOSA).
_SQL_PECOSAS_POR_META = """
    SELECT
        o.sec_func,
        m.nro_pecosa,
        m.nro_orden,
        o.tipo_bien,
        m.nro_guia,
        m.fecha_movimto,
        o.proveedor_nombre,
        o.total_fact_soles
    FROM siga.movimientos_almacen m
    JOIN siga.ordenes o
        ON o.ano_eje = m.ano_eje AND o.sec_ejec = m.sec_ejec
       AND o.tipo_bien = m.tipo_bien AND o.nro_orden = m.nro_orden
    WHERE m.ano_eje = :ano AND m.sec_ejec = :sec_ejec
      AND m.tipo_movimto = 'S' AND m.nro_orden IS NOT NULL
      AND o.sec_func IN :sfs
    ORDER BY o.sec_func, m.fecha_movimto DESC NULLS LAST, m.nro_pecosa DESC
"""


def ordenes_pecosas_por_meta(
    db: Session, ano: int, sec_funcs: list[int]
) -> tuple[dict[int, list[dict[str, Any]]], dict[int, list[dict[str, Any]]]]:
    """Órdenes y PECOSAS del snapshot PG, agrupadas por SEC_FUNC (meta).

    Returns:
        `(ordenes_por_meta, pecosas_por_meta)`, cada uno
        `{sec_func: [fila, ...]}`. Las órdenes traen `tipo_bien` para que el
        consumidor separe O/C (bienes) de O/S (servicios). Vacío si `sec_funcs`
        lo está — no se consulta nada.
    """
    if not sec_funcs:
        return {}, {}
    from sqlalchemy import bindparam

    params = {"ano": ano, "sec_ejec": int(settings.SEC_EJEC), "sfs": sec_funcs}

    ord_rows = db.execute(
        text(_SQL_ORDENES_POR_META).bindparams(bindparam("sfs", expanding=True)),
        params,
    ).mappings().all()
    pec_rows = db.execute(
        text(_SQL_PECOSAS_POR_META).bindparams(bindparam("sfs", expanding=True)),
        params,
    ).mappings().all()

    ordenes: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in ord_rows:
        ordenes[int(r["sec_func"])].append({
            "nro_orden": int(r["nro_orden"]),
            "tipo_bien": (r["tipo_bien"] or "").strip(),
            "clasificador": (r["clasificador"] or "").strip() or None,
            "estado": (r["estado"] or "").strip() or None,
            "estado_siaf": (r["estado_siaf"] or "").strip() or None,
            "exp_siaf": int(r["exp_siaf"]) if r["exp_siaf"] is not None else None,
            "total_fact_soles": float(r["total_fact_soles"] or 0),
            "concepto": (r["concepto"] or "").strip() or None,
            "proveedor_nombre": (r["proveedor_nombre"] or "").strip() or None,
            "proveedor_ruc": (r["proveedor_ruc"] or "").strip() or None,
            "fecha_orden": r["fecha_orden"],
            # Recepción de la orden ('1'=pendiente, '2'=parcial, '3'=completa).
            "flag_recep": (r["flag_recep"] or "").strip() or None,
        })

    pecosas: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in pec_rows:
        pecosas[int(r["sec_func"])].append({
            "nro_pecosa": int(r["nro_pecosa"]),
            "nro_orden": int(r["nro_orden"]) if r["nro_orden"] is not None else None,
            "tipo_bien": (r["tipo_bien"] or "").strip(),
            "nro_guia": (r["nro_guia"] or "").strip() or None,
            "fecha_movimto": r["fecha_movimto"],
            "proveedor_nombre": (r["proveedor_nombre"] or "").strip() or None,
            "total_fact_soles": float(r["total_fact_soles"] or 0),
        })

    return dict(ordenes), dict(pecosas)
