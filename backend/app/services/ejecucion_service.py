"""Servicio de ejecucion presupuestal publica (HU-05, HU-06).

Se apoya en `siaf.v_ejecucion_normalizada` (nombres autoritativos vienen de
`ref.*`; ver CLAUDE.md §10). Todas las sumas usan el MAX(mes_eje) por
sec_func para no duplicar montos entre meses.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

# El PIA/PIM se leen de la fila mas reciente por sec_func (max mes_eje);
# el certificado/devengado son acumulados y tambien se toman del ultimo mes.
_ULTIMOS_MESES_CTE = """
    WITH ultimos AS (
        SELECT sec_func, MAX(mes_eje) AS max_mes
          FROM siaf.v_ejecucion_normalizada
         WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
         GROUP BY sec_func
    ),
    vigentes AS (
        SELECT v.*
          FROM siaf.v_ejecucion_normalizada v
          JOIN ultimos u
            ON u.sec_func = v.sec_func AND u.max_mes = v.mes_eje
         WHERE v.ano_eje = :ano AND v.sec_ejec = :sec_ejec
    )
"""


def _params(ano: int | None) -> dict[str, Any]:
    return {"ano": ano or settings.ANO_VIGENTE, "sec_ejec": settings.SEC_EJEC}


def resumen(db: Session, *, ano: int | None = None) -> dict[str, Any]:
    """KPIs para el dashboard (HU-05 AC-05.1)."""
    row = db.execute(
        text(
            _ULTIMOS_MESES_CTE
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
            _ULTIMOS_MESES_CTE
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
            _ULTIMOS_MESES_CTE
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
    where = ["v.ano_eje = :ano", "v.sec_ejec = :sec_ejec"]
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
    inner_cte = _ULTIMOS_MESES_CTE

    sql_total = f"""
        {inner_cte}
        SELECT COUNT(*) FROM (
            SELECT sec_func FROM vigentes v
             WHERE {where_sql.replace('v.ano_eje = :ano AND v.sec_ejec = :sec_ejec', '1=1')}
             GROUP BY sec_func
        ) t
    """
    total = int(db.execute(text(sql_total), params).scalar_one())

    sql_rows = f"""
        {inner_cte}
        SELECT
            MAX(v.funcion_codigo)  AS funcion_codigo,
            MAX(v.funcion_nombre)  AS funcion_nombre,
            v.sec_func,
            MAX(v.meta_codigo)     AS meta_codigo,
            MAX(v.meta_nombre)     AS meta_nombre,
            MAX(v.producto_proyecto) AS producto_proyecto,
            SUM(v.monto_pim)       AS pim,
            SUM(v.monto_certificado) AS certificado,
            SUM(v.monto_devengado) AS devengado,
            SUM(v.monto_girado)    AS girado,
            CASE WHEN SUM(v.monto_pim) > 0
                 THEN ROUND(SUM(v.monto_devengado) / SUM(v.monto_pim) * 100, 2)
                 ELSE NULL END     AS porcentaje_ejecucion
          FROM vigentes v
         WHERE {where_sql.replace('v.ano_eje = :ano AND v.sec_ejec = :sec_ejec', '1=1')}
         GROUP BY v.sec_func
         ORDER BY {order_by}
         LIMIT :limit OFFSET :offset
    """
    rows = db.execute(
        text(sql_rows), {**params, "limit": limit, "offset": offset}
    ).mappings().all()
    return [dict(r) for r in rows], total
