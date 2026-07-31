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


def _agrupar_declaraciones(rows: Any) -> dict[tuple[str, int], set[int]]:
    """(tipo_bien, nro_pedido) -> conjunto de CCMN que lo declaran."""
    out: dict[tuple[str, int], set[int]] = defaultdict(set)
    for r in rows:
        ped = parsear_nro_pedido(r["texto"])
        if ped is None or r["ccmn"] is None:
            continue
        out[((r["tipo_bien"] or "").strip(), ped)].add(int(r["ccmn"]))
    return out


def _elegir_declarado(
    declaraciones: dict[tuple[str, int], set[int]],
    tipo_bien: str,
    nro_pedido: int,
    candidatos: frozenset[int],
) -> int | None:
    """CCMN declarado inequivoco para el pedido, o None."""
    decl = declaraciones.get((tipo_bien, nro_pedido))
    if not decl:
        return None
    dentro = decl & candidatos
    if len(dentro) == 1:
        return next(iter(dentro))
    if dentro:
        return None
    return next(iter(decl)) if len(decl) == 1 else None


# ─── Declaraciones desde el snapshot (concepto de orden -> CCMN) ─────────
# La orden nombra el pedido en su concepto; su CCMN es siga.ordenes.nro_consolid
# (cadena dura via certificacion_fase, ya poblado en el sync).

_SQL_DECL_ORDEN = """
    SELECT o.tipo_bien, o.nro_consolid AS ccmn, o.concepto AS texto
    FROM siga.ordenes o
    WHERE o.ano_eje = :ano AND o.sec_ejec = :sec_ejec
      AND o.concepto IS NOT NULL AND o.nro_consolid IS NOT NULL
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
    fila: dict[str, Any], declaraciones: dict[tuple[str, int], set[int]]
) -> None:
    """Añade a la fila los insumos de la cascada del puente (candidatos, declarados).

    `ccmn_manual` lo inyecta el service desde Postgres (resoluciones).
    """
    tipo_bien = (fila.get("tipo_bien") or "").strip()
    nro_pedido = int(fila["nro_pedido"])
    csv = fila.get("ccmn_candidatos_csv")
    candidatos = frozenset(
        int(x) for x in csv.split(",") if x.strip()
    ) if csv else frozenset()
    fila["ccmn_candidatos"] = candidatos
    fila["ccmn_declarado_orden"] = _elegir_declarado(
        declaraciones, tipo_bien, nro_pedido, candidatos
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
            SELECT tipo_bien, nro_consolid, n_ordenes, ordenes_csv,
                   fecha_consolid, fecha_cotizacion, fecha_cuadro, fecha_certificacion,
                   fecha_orden, fecha_compromiso, fecha_ejecucion,
                   fecha_despacho, fecha_devengado
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

    Regla de agregacion SIAF (CLAUDE.md §5): la ejecucion son flujos mensuales,
    el total anual es SUM de los meses > 0. PIA/PIM viven en mes 0 y no se suman.
    """
    if not sec_funcs:
        return {}
    from sqlalchemy import bindparam

    rows = db.execute(
        text(
            """
            SELECT sec_func, COALESCE(SUM(monto_devengado), 0) AS dev
            FROM siaf.ejecucion_presupuestal
            WHERE ano_eje = :ano AND mes_eje > 0 AND sec_func IN :sfs
            GROUP BY sec_func
            """
        ).bindparams(bindparam("sfs", expanding=True)),
        {"ano": ano, "sfs": sec_funcs},
    ).all()
    return {int(r[0]): float(r[1]) for r in rows}
