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
