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
               MAX(producto_proyecto_nombre) AS producto_proyecto_nombre,
               MAX(funcion_codigo)  AS funcion_codigo,
               MAX(funcion_nombre)  AS funcion_nombre,
               MAX(fuente_codigo)   AS fuente_codigo,
               MAX(fuente_nombre)   AS fuente_nombre,
               MAX(rubro)           AS rubro,
               MAX(rubro_nombre)    AS rubro_nombre,
               MAX(generica)        AS generica,
               MAX(generica_nombre) AS generica_nombre,
               MAX(subgenerica)     AS subgenerica,
               MAX(subgenerica_nombre) AS subgenerica_nombre,
               MAX(especifica)      AS especifica,
               MAX(especifica_nombre) AS especifica_nombre,
               MAX(especifica_det)  AS especifica_det,
               MAX(especifica_det_nombre) AS especifica_det_nombre,
               MAX(categoria_gasto) AS categoria_gasto,
               MAX(categoria_gasto_nombre) AS categoria_gasto_nombre
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
            m.producto_proyecto_nombre,
            m.funcion_codigo,
            m.funcion_nombre,
            m.fuente_codigo,
            m.fuente_nombre,
            m.rubro,
            m.rubro_nombre,
            m.generica,
            m.generica_nombre,
            m.subgenerica,
            m.subgenerica_nombre,
            m.especifica,
            m.especifica_nombre,
            m.especifica_det,
            m.especifica_det_nombre,
            m.categoria_gasto,
            m.categoria_gasto_nombre,
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
    rubro: str | None = None,
    generica: str | None = None,
    categoria_gasto: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort: str = "pim_desc",
) -> tuple[list[dict[str, Any]], int]:
    """Tabla detallada con filtros (HU-06).

    Devuelve una fila por meta con la cadena jerarquica completa:
    funcion -> rubro -> generica -> meta.
    """
    # Filtros que se aplican al CTE maestro (funcion, fuente son 1-a-1 con la meta)
    where_meta: list[str] = []
    # Filtros que se aplican a nivel fila-vista (rubro, generica, categoria son N-a-1 con la meta)
    # Se resuelven con EXISTS sobre la vista para no distorsionar los montos de la meta.
    where_exists: list[str] = []
    params = _params(ano)
    if funcion:
        where_meta.append("v.funcion_codigo = :funcion")
        params["funcion"] = funcion
    if fuente:
        where_meta.append("v.fuente_codigo = :fuente")
        params["fuente"] = fuente
    if rubro:
        where_exists.append("x.rubro = :rubro")
        params["rubro"] = rubro
    if generica:
        where_exists.append("x.generica = :generica")
        params["generica"] = generica
    if categoria_gasto:
        where_exists.append("x.categoria_gasto = :categoria")
        params["categoria"] = categoria_gasto

    order_map = {
        "pim_desc": "v.monto_pim DESC",
        "pim_asc": "v.monto_pim ASC",
        "devengado_desc": "v.monto_devengado DESC",
    }
    order_by = order_map.get(sort, order_map["pim_desc"])

    where_meta_sql = " AND ".join(["1=1", *where_meta])
    exists_sql = ""
    if where_exists:
        exists_sql = f"""
            AND EXISTS (
                SELECT 1 FROM siaf.v_ejecucion_normalizada x
                 WHERE x.ano_eje = :ano AND x.sec_ejec = :sec_ejec
                   AND x.sec_func = v.sec_func
                   AND {' AND '.join(where_exists)}
            )
        """

    inner_cte = _PRESUPUESTO_EJECUCION_CTE

    sql_total = f"""
        {inner_cte}
        SELECT COUNT(*) FROM vigentes v
         WHERE {where_meta_sql}
         {exists_sql}
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
            v.producto_proyecto_nombre,
            v.categoria_gasto,
            v.categoria_gasto_nombre,
            v.monto_pim       AS pim,
            v.monto_certificado AS certificado,
            v.monto_devengado AS devengado,
            v.monto_girado    AS girado,
            CASE WHEN v.monto_pim > 0
                 THEN ROUND(v.monto_devengado / v.monto_pim * 100, 2)
                 ELSE NULL END AS porcentaje_ejecucion
          FROM vigentes v
         WHERE {where_meta_sql}
         {exists_sql}
         ORDER BY {order_by}
         LIMIT :limit OFFSET :offset
    """
    rows = db.execute(
        text(sql_rows), {**params, "limit": limit, "offset": offset}
    ).mappings().all()
    return [dict(r) for r in rows], total


# ─── Jerarquia ciudadana: Funcion -> Rubro -> Generica ───────────────────
#
# IMPORTANTE (hallazgo 2026-07-14): una misma meta (sec_func) puede tener
# multiples rubros y multiples genericas. Cada combinacion (funcion, rubro,
# generica, categoria_gasto, especifica*) es una fila distinta en mes_eje=0.
# Por eso este endpoint NO usa el CTE maestro-por-meta (que colapsa con MAX
# y descarta valores). Agregamos directo sobre la vista para no perder N:N.

def jerarquia(
    db: Session,
    *,
    ano: int | None = None,
    nivel: str = "funcion",
    padre_funcion: str | None = None,
    padre_producto: str | None = None,
    filtro_rubro: str | None = None,
    filtro_generica: str | None = None,
) -> list[dict[str, Any]]:
    """Drill-down principal: Funcion -> Producto/Proyecto -> Meta.

    Rubro y generica NO son niveles de la jerarquia (son transversales, N:N
    con la meta). Se ofrecen como filtros opcionales que refinan el drill:
    'muestrame la jerarquia pero solo lo financiado por Canon' o 'solo lo
    gastado en Adquisicion de Activos'.

    Niveles:
      - "funcion":   agrega por funcion.
      - "producto":  agrega por producto/proyecto dentro de una funcion
                     (requiere padre_funcion). Distingue tipo (PROD/PROY).
      - "meta":      lista metas dentro de (funcion, producto) o solo funcion.

    Filtros transversales (opcionales, se aplican en cualquier nivel):
      - filtro_rubro:    solo agrega lo financiado por ese rubro.
      - filtro_generica: solo agrega lo gastado en esa generica.

    Cada fila:
      { codigo, nombre, tipo?, pim, devengado, girado, certificado,
        porcentaje_ejecucion, participacion_pim, tiene_hijos }

    Nota N:N: cuando se aplica filtro_rubro/generica, los montos por meta
    se recalculan sobre las filas que cumplan el filtro (fila-nivel, no
    meta-nivel). Sin filtro, los montos son la suma completa por meta.
    """
    params = _params(ano)
    where_extra: list[str] = []

    if filtro_rubro:
        where_extra.append("v.rubro = :filtro_rubro")
        params["filtro_rubro"] = filtro_rubro
    if filtro_generica:
        where_extra.append("v.generica = :filtro_generica")
        params["filtro_generica"] = filtro_generica

    if nivel == "funcion":
        group_col = "v.funcion_codigo"
        name_col = "v.funcion_nombre"
        extra_select = "NULL::text AS tipo"
        has_children_expr = "TRUE"
    elif nivel == "producto":
        if not padre_funcion:
            raise ValueError("padre_funcion es requerido para nivel=producto")
        where_extra.append("v.funcion_codigo = :padre_funcion")
        params["padre_funcion"] = padre_funcion
        group_col = "v.producto_proyecto"
        name_col = "v.producto_proyecto_nombre"
        # tipo_act_proy no esta en la vista; lo tomamos de la tabla base via lookup
        # Como esta consolidado por sec_func, usamos MAX del codigo (todas las filas de
        # un producto tienen el mismo tipo)
        extra_select = "NULL::text AS tipo"
        has_children_expr = "TRUE"
    elif nivel == "meta":
        if not padre_funcion:
            raise ValueError("padre_funcion es requerido para nivel=meta")
        where_extra.append("v.funcion_codigo = :padre_funcion")
        params["padre_funcion"] = padre_funcion
        if padre_producto:
            where_extra.append("v.producto_proyecto = :padre_producto")
            params["padre_producto"] = padre_producto
        # La meta se identifica por sec_func; nombre = meta_nombre (finalidad)
        group_col = "v.sec_func::text"
        name_col = "v.meta_nombre"
        extra_select = "NULL::text AS tipo"
        has_children_expr = "FALSE"
    else:
        raise ValueError(f"Nivel invalido: {nivel}")

    where_sql_pim = " AND ".join([
        "v.ano_eje = :ano",
        "v.sec_ejec = :sec_ejec",
        "v.mes_eje = 0",
        *where_extra,
    ])
    where_sql_ejec = " AND ".join([
        "v.ano_eje = :ano",
        "v.sec_ejec = :sec_ejec",
        "v.mes_eje > 0",
        *where_extra,
    ])

    sql = f"""
        WITH pim AS (
            SELECT
                {group_col} AS codigo,
                MAX({name_col}) AS nombre,
                SUM(v.monto_pim) AS pim,
                SUM(v.monto_pia) AS pia
              FROM siaf.v_ejecucion_normalizada v
             WHERE {where_sql_pim}
             GROUP BY {group_col}
        ),
        ejec AS (
            SELECT
                {group_col} AS codigo,
                SUM(v.monto_certificado) AS certificado,
                SUM(v.monto_devengado)   AS devengado,
                SUM(v.monto_girado)      AS girado
              FROM siaf.v_ejecucion_normalizada v
             WHERE {where_sql_ejec}
             GROUP BY {group_col}
        ),
        agregado AS (
            SELECT
                COALESCE(p.codigo, e.codigo) AS codigo,
                p.nombre,
                COALESCE(p.pim, 0)          AS pim,
                COALESCE(p.pia, 0)          AS pia,
                COALESCE(e.certificado, 0)  AS certificado,
                COALESCE(e.devengado, 0)    AS devengado,
                COALESCE(e.girado, 0)       AS girado
              FROM pim p FULL OUTER JOIN ejec e ON e.codigo = p.codigo
        ),
        total AS (
            SELECT NULLIF(SUM(pim), 0) AS pim_total FROM agregado
        )
        SELECT
            a.codigo,
            COALESCE(a.nombre, '(sin nombre)') AS nombre,
            {extra_select},
            a.pim,
            a.pia,
            a.certificado,
            a.devengado,
            a.girado,
            CASE WHEN a.pim > 0
                 THEN ROUND(a.devengado / a.pim * 100, 2)
                 ELSE NULL END AS porcentaje_ejecucion,
            CASE WHEN t.pim_total IS NOT NULL AND t.pim_total > 0
                 THEN ROUND(a.pim / t.pim_total * 100, 2)
                 ELSE NULL END AS participacion_pim,
            {has_children_expr} AS tiene_hijos
          FROM agregado a CROSS JOIN total t
         WHERE a.codigo IS NOT NULL
         ORDER BY a.pim DESC NULLS LAST
    """
    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def por_rubro(db: Session, *, ano: int | None = None) -> list[dict[str, Any]]:
    """Agregado por rubro (para card '¿De donde viene el dinero?').

    Agrega directo sobre la vista (no colapsa por meta): respeta N:N.
    """
    rows = db.execute(
        text(
            """
            WITH pim AS (
                SELECT rubro AS codigo, MAX(rubro_nombre) AS nombre,
                       SUM(monto_pim) AS pim
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje = 0
                   AND rubro IS NOT NULL
                 GROUP BY rubro
            ),
            ejec AS (
                SELECT rubro AS codigo,
                       SUM(monto_devengado) AS devengado
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje > 0
                   AND rubro IS NOT NULL
                 GROUP BY rubro
            ),
            j AS (
                SELECT COALESCE(p.codigo, e.codigo) AS codigo,
                       p.nombre,
                       COALESCE(p.pim, 0) AS pim,
                       COALESCE(e.devengado, 0) AS devengado
                  FROM pim p FULL OUTER JOIN ejec e ON e.codigo = p.codigo
            ),
            total AS (SELECT NULLIF(SUM(pim), 0) AS pim_total FROM j)
            SELECT j.codigo AS rubro_codigo,
                   COALESCE(j.nombre, '(sin nombre)') AS rubro_nombre,
                   j.pim, j.devengado,
                   CASE WHEN t.pim_total > 0
                        THEN ROUND(j.pim / t.pim_total * 100, 2)
                        ELSE NULL END AS participacion_pim
              FROM j CROSS JOIN total t
             ORDER BY j.pim DESC
            """
        ),
        _params(ano),
    ).mappings().all()
    return [dict(r) for r in rows]


def por_generica(db: Session, *, ano: int | None = None) -> list[dict[str, Any]]:
    """Agregado por generica (para card '¿En que tipo de gasto?').

    Agrega directo sobre la vista.
    """
    rows = db.execute(
        text(
            """
            WITH pim AS (
                SELECT generica AS codigo, MAX(generica_nombre) AS nombre,
                       SUM(monto_pim) AS pim
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje = 0
                   AND generica IS NOT NULL
                 GROUP BY generica
            ),
            ejec AS (
                SELECT generica AS codigo,
                       SUM(monto_devengado) AS devengado
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje > 0
                   AND generica IS NOT NULL
                 GROUP BY generica
            ),
            j AS (
                SELECT COALESCE(p.codigo, e.codigo) AS codigo,
                       p.nombre,
                       COALESCE(p.pim, 0) AS pim,
                       COALESCE(e.devengado, 0) AS devengado
                  FROM pim p FULL OUTER JOIN ejec e ON e.codigo = p.codigo
            ),
            total AS (SELECT NULLIF(SUM(pim), 0) AS pim_total FROM j)
            SELECT j.codigo AS generica_codigo,
                   COALESCE(j.nombre, '(sin nombre)') AS generica_nombre,
                   j.pim, j.devengado,
                   CASE WHEN t.pim_total > 0
                        THEN ROUND(j.pim / t.pim_total * 100, 2)
                        ELSE NULL END AS participacion_pim
              FROM j CROSS JOIN total t
             ORDER BY j.pim DESC
            """
        ),
        _params(ano),
    ).mappings().all()
    return [dict(r) for r in rows]


def mensual_acumulado(db: Session, *, ano: int | None = None) -> list[dict[str, Any]]:
    """Devuelve la evolucion acumulada del anio.

    Solucion al hallazgo de granularidad SIAF: los montos mensuales son FLUJOS
    (lo ejecutado ese mes), no acumulados. Aqui hacemos la suma acumulativa
    en el backend para que el frontend no la tenga que reinventar mal.

    Ver Docs/hallazgos-granularidad-siaf.md.
    """
    rows = db.execute(
        text(
            """
            WITH flujo AS (
                SELECT mes_eje,
                       SUM(monto_certificado) AS certificado,
                       SUM(monto_devengado)   AS devengado,
                       SUM(monto_girado)      AS girado
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje > 0
                 GROUP BY mes_eje
            ),
            pim_total AS (
                SELECT COALESCE(SUM(monto_pim), 0) AS pim
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje = 0
            )
            SELECT
                f.mes_eje,
                p.pim,
                f.certificado AS certificado_mes,
                f.devengado   AS devengado_mes,
                f.girado      AS girado_mes,
                SUM(f.certificado) OVER (ORDER BY f.mes_eje) AS certificado_acumulado,
                SUM(f.devengado)   OVER (ORDER BY f.mes_eje) AS devengado_acumulado,
                SUM(f.girado)      OVER (ORDER BY f.mes_eje) AS girado_acumulado
              FROM flujo f CROSS JOIN pim_total p
             ORDER BY f.mes_eje
            """
        ),
        _params(ano),
    ).mappings().all()
    return [dict(r) for r in rows]


def desglose_meta(
    db: Session, *, sec_func: int, ano: int | None = None,
) -> dict[str, Any]:
    """Desglose N:N de una meta: filas por combinacion (rubro, generica).

    Muestra literalmente 'de este PIM, X viene de tal rubro y se gasta en tal
    generica'. Es la unica vista que expone la relacion N:N cruda de la meta.
    """
    params = _params(ano)
    params["sec_func"] = sec_func

    # Cabecera de la meta (identificacion + monto agregado)
    cabecera_row = db.execute(
        text(
            """
            WITH m AS (
                SELECT SUM(monto_pim) AS pim, SUM(monto_pia) AS pia,
                       MAX(meta_codigo) AS meta_codigo,
                       MAX(meta_nombre) AS meta_nombre,
                       MAX(funcion_codigo) AS funcion_codigo,
                       MAX(funcion_nombre) AS funcion_nombre,
                       MAX(producto_proyecto) AS producto_proyecto,
                       MAX(producto_proyecto_nombre) AS producto_proyecto_nombre,
                       MAX(categoria_gasto) AS categoria_gasto,
                       MAX(categoria_gasto_nombre) AS categoria_gasto_nombre
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                   AND sec_func = :sec_func AND mes_eje = 0
            ),
            e AS (
                SELECT SUM(monto_certificado) AS certificado,
                       SUM(monto_devengado) AS devengado,
                       SUM(monto_girado) AS girado
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                   AND sec_func = :sec_func AND mes_eje > 0
            )
            SELECT m.*, COALESCE(e.certificado, 0) AS certificado,
                        COALESCE(e.devengado, 0) AS devengado,
                        COALESCE(e.girado, 0) AS girado
              FROM m, e
            """
        ),
        params,
    ).mappings().first()

    if not cabecera_row or cabecera_row["pim"] is None:
        return {"cabecera": None, "filas": []}

    cabecera = dict(cabecera_row)
    pim_meta = float(cabecera["pim"] or 0)
    cabecera["porcentaje_ejecucion"] = (
        round(float(cabecera["devengado"] or 0) / pim_meta * 100, 2)
        if pim_meta > 0
        else None
    )

    # Filas del desglose (rubro x generica)
    filas = db.execute(
        text(
            """
            WITH pim AS (
                SELECT rubro, rubro_nombre, generica, generica_nombre,
                       SUM(monto_pim) AS pim,
                       SUM(monto_pia) AS pia
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                   AND sec_func = :sec_func AND mes_eje = 0
                 GROUP BY rubro, rubro_nombre, generica, generica_nombre
            ),
            ejec AS (
                SELECT rubro, generica,
                       SUM(monto_certificado) AS certificado,
                       SUM(monto_devengado)   AS devengado,
                       SUM(monto_girado)      AS girado
                  FROM siaf.v_ejecucion_normalizada
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                   AND sec_func = :sec_func AND mes_eje > 0
                 GROUP BY rubro, generica
            )
            SELECT
                p.rubro AS rubro_codigo,
                p.rubro_nombre,
                p.generica AS generica_codigo,
                p.generica_nombre,
                p.pim,
                COALESCE(e.certificado, 0) AS certificado,
                COALESCE(e.devengado, 0)   AS devengado,
                COALESCE(e.girado, 0)      AS girado,
                CASE WHEN p.pim > 0
                     THEN ROUND(COALESCE(e.devengado, 0) / p.pim * 100, 2)
                     ELSE NULL END AS porcentaje_ejecucion
              FROM pim p
              LEFT JOIN ejec e ON e.rubro = p.rubro AND e.generica = p.generica
             ORDER BY p.pim DESC
            """
        ),
        params,
    ).mappings().all()

    return {"cabecera": cabecera, "filas": [dict(f) for f in filas]}
