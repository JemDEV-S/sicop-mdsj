"""Servicio de ejecucion presupuestal publica (HU-05, HU-06).

Se apoya en `siaf.v_ejecucion_normalizada` (nombres autoritativos vienen de
`ref.*`; ver CLAUDE.md §10).

Nota sobre granularidad de la API MEF:
  - PIA y PIM solo vienen con valor en mes_eje=0 (fila maestra). En meses 1-N
    esos campos llegan en 0 desde la API.
  - Devengado/Girado/Certificado son acumulados y solo aparecen en meses > 0.
Por eso el CTE bifurca: presupuesto desde mes_0, ejecucion desde max(mes>0).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

# PIA/PIM: solo vienen en mes_eje=0 (fila maestra de la API MEF). En meses 1-N vienen en 0.
# Devengado/Girado/Certificado/Comprometido: son flujos mensuales (no acumulados).
# Para obtener el total anual hay que sumar TODOS los meses > 0.
_PRESUPUESTO_EJECUCION_CTE = """
    WITH maestros AS (
        SELECT sec_func,
               SUM(monto_pia) AS monto_pia,
               SUM(monto_pim) AS monto_pim,
               MAX(meta_codigo)     AS meta_codigo,
               MAX(meta_nombre)     AS meta_nombre,
               MAX(tipo_meta)       AS tipo_meta,
               MAX(producto_proyecto) AS producto_proyecto,
               MAX(funcion_codigo)  AS funcion_codigo,
               MAX(funcion_nombre)  AS funcion_nombre,
               MAX(fuente_codigo)   AS fuente_codigo,
               MAX(fuente_nombre)   AS fuente_nombre,
               MAX(generica)        AS generica,
               MAX(generica_nombre) AS generica_nombre,
               MAX(categoria_gasto) AS categoria_gasto
          FROM siaf.v_ejecucion_normalizada
         WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje = 0
         GROUP BY sec_func
    ),
    ejecucion AS (
        SELECT sec_func,
               SUM(monto_certificado)        AS monto_certificado,
               SUM(monto_comprometido_anual) AS monto_comprometido_anual,
               SUM(monto_comprometido)       AS monto_comprometido,
               SUM(monto_devengado)          AS monto_devengado,
               SUM(monto_girado)             AS monto_girado
          FROM siaf.v_ejecucion_normalizada
         WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje > 0
         GROUP BY sec_func
    ),
    vigentes AS (
        SELECT
            m.sec_func,
            m.monto_pia,
            m.monto_pim,
            m.meta_codigo,
            m.meta_nombre,
            m.tipo_meta,
            m.producto_proyecto,
            m.funcion_codigo,
            m.funcion_nombre,
            m.fuente_codigo,
            m.fuente_nombre,
            m.generica,
            m.generica_nombre,
            m.categoria_gasto,
            COALESCE(e.monto_certificado, 0)        AS monto_certificado,
            COALESCE(e.monto_comprometido_anual, 0) AS monto_comprometido_anual,
            COALESCE(e.monto_comprometido, 0)       AS monto_comprometido,
            COALESCE(e.monto_devengado, 0)          AS monto_devengado,
            COALESCE(e.monto_girado, 0)             AS monto_girado
          FROM maestros m
          LEFT JOIN ejecucion e ON e.sec_func = m.sec_func
    )
"""


def _params(ano: int | None) -> dict[str, Any]:
    return {"ano": ano or settings.ANO_VIGENTE, "sec_ejec": settings.SEC_EJEC}


def resumen(db: Session, *, ano: int | None = None) -> dict[str, Any]:
    """KPIs para el dashboard (HU-05 AC-05.1)."""
    row = db.execute(
        text(
            _PRESUPUESTO_EJECUCION_CTE
            + """
            SELECT
                COALESCE(SUM(monto_pia), 0)             AS pia,
                COALESCE(SUM(monto_pim), 0)             AS pim,
                COALESCE(SUM(monto_certificado), 0)     AS certificado,
                COALESCE(SUM(monto_comprometido_anual), 0) AS comprometido_anual,
                COALESCE(SUM(monto_devengado), 0)       AS devengado,
                COALESCE(SUM(monto_girado), 0)          AS girado,
                COUNT(DISTINCT sec_func)                AS metas
              FROM vigentes
            """
        ),
        _params(ano),
    ).mappings().first()
    if row is None:
        return {}
    d = dict(row)
    pim = float(d["pim"] or 0)
    d["porcentaje_ejecucion"] = (
        round(float(d["devengado"] or 0) / pim * 100, 2) if pim > 0 else None
    )
    return d


def por_funcion(db: Session, *, ano: int | None = None) -> list[dict[str, Any]]:
    """Agregado por funcion (HU-05 AC-05.2)."""
    rows = db.execute(
        text(
            _PRESUPUESTO_EJECUCION_CTE
            + """
            SELECT
                funcion_codigo,
                funcion_nombre,
                SUM(monto_pim)        AS pim,
                SUM(monto_certificado) AS certificado,
                SUM(monto_devengado)  AS devengado,
                SUM(monto_girado)     AS girado
              FROM vigentes
             GROUP BY funcion_codigo, funcion_nombre
             ORDER BY SUM(monto_pim) DESC
            """
        ),
        _params(ano),
    ).mappings().all()
    return [dict(r) for r in rows]


def por_fuente(db: Session, *, ano: int | None = None) -> list[dict[str, Any]]:
    """Distribucion por fuente de financiamiento (HU-05 AC-05.3)."""
    rows = db.execute(
        text(
            _PRESUPUESTO_EJECUCION_CTE
            + """
            SELECT
                fuente_codigo,
                fuente_nombre,
                SUM(monto_pim)       AS pim,
                SUM(monto_devengado) AS devengado
              FROM vigentes
             GROUP BY fuente_codigo, fuente_nombre
             ORDER BY SUM(monto_pim) DESC
            """
        ),
        _params(ano),
    ).mappings().all()
    return [dict(r) for r in rows]


def mensual(db: Session, *, ano: int | None = None) -> list[dict[str, Any]]:
    """Devengado mensual acumulado (HU-05 AC-05.4).

    Aqui NO usamos el CTE de ultimos-mes porque queremos ver el corte de cada mes.
    """
    rows = db.execute(
        text(
            """
            SELECT
                mes_eje,
                SUM(monto_pim)       AS pim,
                SUM(monto_certificado) AS certificado,
                SUM(monto_devengado) AS devengado,
                SUM(monto_girado)    AS girado
              FROM siaf.v_ejecucion_normalizada
             WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
               AND mes_eje > 0
             GROUP BY mes_eje
             ORDER BY mes_eje
            """
        ),
        _params(ano),
    ).mappings().all()
    return [dict(r) for r in rows]


def detalle(
    db: Session,
    *,
    ano: int | None = None,
    funcion: str | None = None,
    fuente: str | None = None,
    categoria_gasto: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort: str = "pim_desc",
) -> tuple[list[dict[str, Any]], int]:
    """Tabla detallada con filtros (HU-06)."""
    where = ["1=1"]
    params = _params(ano)
    if funcion:
        where.append("v.funcion_codigo = :funcion")
        params["funcion"] = funcion
    if fuente:
        where.append("v.fuente_codigo = :fuente")
        params["fuente"] = fuente
    if categoria_gasto:
        where.append("v.categoria_gasto = :categoria")
        params["categoria"] = categoria_gasto

    order_map = {
        "pim_desc": "SUM(v.monto_pim) DESC",
        "pim_asc": "SUM(v.monto_pim) ASC",
        "devengado_desc": "SUM(v.monto_devengado) DESC",
    }
    order_by = order_map.get(sort, order_map["pim_desc"])

    where_sql = " AND ".join(where)
    inner_cte = _PRESUPUESTO_EJECUCION_CTE

    sql_total = f"""
        {inner_cte}
        SELECT COUNT(*) FROM (
            SELECT v.sec_func FROM vigentes v
             WHERE {where_sql}
             GROUP BY v.sec_func
        ) t
    """
    total = int(db.execute(text(sql_total), params).scalar_one())

    sql_rows = f"""
        {inner_cte}
        SELECT
            v.funcion_codigo,
            v.funcion_nombre,
            v.sec_func,
            v.meta_codigo,
            v.meta_nombre,
            v.producto_proyecto,
            v.monto_pim       AS pim,
            v.monto_certificado AS certificado,
            v.monto_devengado AS devengado,
            v.monto_girado    AS girado,
            CASE WHEN v.monto_pim > 0
                 THEN ROUND(v.monto_devengado / v.monto_pim * 100, 2)
                 ELSE NULL END AS porcentaje_ejecucion
          FROM vigentes v
         WHERE {where_sql}
         ORDER BY {order_by}
         LIMIT :limit OFFSET :offset
    """
    rows = db.execute(
        text(sql_rows), {**params, "limit": limit, "offset": offset}
    ).mappings().all()
    return [dict(r) for r in rows], total
