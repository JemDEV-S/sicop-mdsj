"""Repositorio SIGA: saldos presupuestales (`SIG_TECHO_PRESUPUESTO`).

Fuente para PIM/certificado/comprometido a nivel meta (§18.2, §18.3 del
diccionario). Todas las queries fijan SEC_EJEC=300687 y filtran por
centros_costo del usuario cuando aplica (RN-04 filtro por CC).

`SIG_TECHO_PRESUPUESTO` tiene PK compuesta `ANO_EJE + SEC_EJEC + sec_func +
CLASIFICADOR + CENTRO_COSTO`.

Hallazgos empíricos (2026-07-16, ver backend/scripts/diagnostico_cruce_mef_siga.py):

  1. **264 filas con SEC_FUNC IS NULL en 2026** — S/ 116.6M de PIM cargado a
     nivel de pliego (canon, impuestos, FONCOMUN) que aún no se ha desagregado
     a metas ejecutables. Se **excluyen** de las agregaciones para que el PIM
     y % de ejecución del widget reflejen "lo asignado a metas" y no infle.
     Estas filas tienen PPTO_DISP_SIAF=0 (no aparecen en la ejecución SIAF).

  2. **MNTO_ACUM_DEVGDO_SIGA = 0** en 2026 (columna no poblada por el SIGA de
     la muni). Antes usábamos `PPTO_MODIF - PPTO_DISP_SIAF` como proxy, pero
     ese proxy incluye el techo huérfano y sobreestima brutalmente (S/ 92M
     vs. S/ 31M reales). Ahora reportamos:
       - certificado (mnto_acum_cert) — S/ ~15.8M
       - comprometido (mnto_acum_coma) — S/ ~12.9M
     Y el widget usa el snapshot MEF (siaf.ejecucion_presupuestal) para el
     devengado oficial que sí cuadra con el portal público.

  3. El PIM SIGA (asignado a metas) = S/ 46.7M vs. PIM MEF = S/ 69.5M. La
     diferencia (S/ 22.8M) son fuentes cargadas en el SIAF pero aún no en el
     SIGA — es un lag operativo de la muni, no un bug del código.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


def listar_saldos(
    ano: int,
    centros: list[str] | None = None,
    *,
    sec_func: int | None = None,
    clasificador: str | None = None,
    fuente_financ: str | None = None,
    solo_con_pim: bool = True,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Devuelve saldos por meta + clasificador + centro de costo.

    `centros=None` = admin (sin filtro). `centros=[]` = usuario sin CC asignado
    (devuelve vacio).
    """
    if centros is not None and len(centros) == 0:
        return []

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        # Excluye ~264 filas de "techo del pliego sin desagregar a meta"
        # que inflan artificialmente el PIM (S/ 116M en 2026). Ver
        # diagnostico_cruce_mef_siga.py.
        "t.SEC_FUNC IS NOT NULL",
    ]
    params: dict[str, Any] = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
    }
    if solo_con_pim:
        where.append("t.PPTO_MODIF > 0")
    if sec_func is not None:
        where.append("t.sec_func = :sec_func")
        params["sec_func"] = sec_func
    if clasificador is not None:
        where.append("t.CLASIFICADOR = :clasificador")
        params["clasificador"] = clasificador
    if fuente_financ is not None:
        where.append("t.FUENTE_FINANC = :fuente")
        params["fuente"] = fuente_financ
    if centros is not None:
        # Bindeamos cada CC como :cc0, :cc1, ... porque SQL Server con pyodbc
        # no admite tuplas directas.
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"t.CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    sql = f"""
        SELECT
            t.sec_func,
            LTRIM(RTRIM(m.nombre))                                AS nombre_meta,
            LTRIM(RTRIM(m.act_proy))                              AS act_proy,
            LTRIM(RTRIM(t.CLASIFICADOR))                          AS clasificador,
            LTRIM(RTRIM(t.FUENTE_FINANC))                         AS fuente_financ,
            LTRIM(RTRIM(t.CENTRO_COSTO))                          AS centro_costo,
            LTRIM(RTRIM(cc.NOMBRE_DEPEND))                        AS centro_costo_nombre,
            COALESCE(t.PPTO_PIA, 0)                               AS pia,
            COALESCE(t.PPTO_MODIF, 0)                             AS pim,
            COALESCE(t.mnto_acum_cert, 0)                         AS certificado,
            COALESCE(t.mnto_acum_coma, 0)                         AS comprometido_anual,
            COALESCE(t.mnto_acum_comm, 0)                         AS comprometido_mensual,
            -- "Devengado" SIGA = certificado + comprometido (la col
            -- MNTO_ACUM_DEVGDO_SIGA está en 0 en 2026). El devengado
            -- oficial viene del snapshot MEF en el service.
            COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0) AS devengado,
            COALESCE(t.PPTO_DISP_SIAF, 0)                         AS saldo_disponible,
            COALESCE(t.MNTO_RESERVA_PEDIDO, 0)                    AS reservado_pedido,
            CASE WHEN COALESCE(t.PPTO_MODIF, 0) > 0
                 THEN ROUND(
                    (COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0))
                    / t.PPTO_MODIF * 100, 2)
                 ELSE 0 END                                       AS porcentaje_devengado
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        LEFT JOIN SIG_CENTRO_COSTO cc
            ON t.ANO_EJE = cc.ANO_EJE AND t.SEC_EJEC = cc.SEC_EJEC
           AND t.CENTRO_COSTO = cc.CENTRO_COSTO
        WHERE {" AND ".join(where)}
        ORDER BY t.PPTO_MODIF DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    params["limit"] = limit
    params["offset"] = offset

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def contar_saldos(
    ano: int,
    centros: list[str] | None = None,
    *,
    solo_con_pim: bool = True,
) -> int:
    """COUNT(*) para paginacion."""
    if centros is not None and len(centros) == 0:
        return 0

    where = [
        "ANO_EJE = :ano",
        "SEC_EJEC = :sec_ejec",
        "SEC_FUNC IS NOT NULL",  # Excluir techo del pliego sin desagregar.
    ]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    if solo_con_pim:
        where.append("PPTO_MODIF > 0")
    if centros is not None:
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    sql = f"SELECT COUNT(*) FROM SIG_TECHO_PRESUPUESTO WHERE {' AND '.join(where)}"
    with get_connection() as conn:
        return int(conn.execute(text(sql), params).scalar_one())


def resumen_saldos(
    ano: int,
    centros: list[str] | None = None,
    *,
    top_criticas_limit: int = 3,
    umbral_critico: float = 30.0,
) -> dict[str, Any]:
    """Agrega totales de saldos + top de metas críticas para el dashboard T-44.

    Una sola consulta a `SIG_TECHO_PRESUPUESTO` filtrada por año/CC devuelve los
    totales globales. La lista de top-N metas críticas se resuelve con una segunda
    consulta que agrupa por `sec_func` (misma agregación que `metas_rezagadas`).

    El semáforo global se aplica al % devengado agregado en el servicio.
    """
    if centros is not None and len(centros) == 0:
        return {
            "pia": 0, "pim": 0, "certificado": 0, "comprometido": 0,
            "devengado": 0, "saldo_disponible": 0, "reservado_pedido": 0,
            "porcentaje_devengado": 0, "metas_total": 0, "metas_criticas": 0,
            "top_metas_criticas": [],
        }

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        "t.PPTO_MODIF > 0",
        "t.SEC_FUNC IS NOT NULL",  # Excluir techo del pliego sin desagregar.
    ]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    if centros is not None:
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"t.CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    where_sql = " AND ".join(where)

    sql_totales = f"""
        SELECT
            COALESCE(SUM(t.PPTO_PIA), 0)                    AS pia,
            COALESCE(SUM(t.PPTO_MODIF), 0)                  AS pim,
            COALESCE(SUM(t.mnto_acum_cert), 0)              AS certificado,
            COALESCE(SUM(t.mnto_acum_coma), 0)              AS comprometido,
            -- "Devengado" SIGA = certificado + comprometido (MNTO_ACUM_DEVGDO_SIGA
            -- está en 0 en 2026). El devengado oficial viene del snapshot MEF.
            COALESCE(SUM(t.mnto_acum_cert + t.mnto_acum_coma), 0) AS devengado,
            COALESCE(SUM(t.PPTO_DISP_SIAF), 0)              AS saldo_disponible,
            COALESCE(SUM(t.MNTO_RESERVA_PEDIDO), 0)         AS reservado_pedido,
            COUNT(DISTINCT t.sec_func)                      AS metas_total
        FROM SIG_TECHO_PRESUPUESTO t
        WHERE {where_sql}
    """

    # Top-N metas críticas: mismo criterio que metas_rezagadas pero ordenando
    # además por PIM DESC para priorizar las de mayor peso presupuestal.
    params_top = dict(params)
    params_top["umbral_critico"] = umbral_critico
    params_top["top_limit"] = top_criticas_limit

    sql_top = f"""
        SELECT TOP (:top_limit)
            t.sec_func,
            LTRIM(RTRIM(m.nombre))                          AS nombre_meta,
            SUM(COALESCE(t.PPTO_MODIF, 0))                  AS pim,
            SUM(COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0)) AS devengado,
            CASE WHEN SUM(COALESCE(t.PPTO_MODIF, 0)) > 0
                 THEN ROUND(SUM(COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0))
                            / SUM(t.PPTO_MODIF) * 100, 2)
                 ELSE 0 END                                 AS porcentaje_devengado
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        WHERE {where_sql}
        GROUP BY t.sec_func, m.nombre
        HAVING CASE WHEN SUM(COALESCE(t.PPTO_MODIF, 0)) > 0
                    THEN SUM(COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0))
                         / SUM(t.PPTO_MODIF) * 100
                    ELSE 0 END < :umbral_critico
        ORDER BY SUM(t.PPTO_MODIF) DESC
    """

    sql_metas_criticas = f"""
        SELECT COUNT(*) FROM (
            SELECT t.sec_func
            FROM SIG_TECHO_PRESUPUESTO t
            WHERE {where_sql}
            GROUP BY t.sec_func
            HAVING CASE WHEN SUM(COALESCE(t.PPTO_MODIF, 0)) > 0
                        THEN SUM(COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0))
                             / SUM(t.PPTO_MODIF) * 100
                        ELSE 0 END < :umbral_critico
        ) x
    """
    params_count = dict(params)
    params_count["umbral_critico"] = umbral_critico

    with get_connection() as conn:
        totales = dict(conn.execute(text(sql_totales), params).mappings().one())
        top = [dict(r) for r in conn.execute(text(sql_top), params_top).mappings().all()]
        metas_criticas = int(
            conn.execute(text(sql_metas_criticas), params_count).scalar_one()
        )

    pim = float(totales.get("pim") or 0)
    devengado = float(totales.get("devengado") or 0)
    totales["porcentaje_devengado"] = round(devengado / pim * 100, 2) if pim > 0 else 0.0
    totales["metas_criticas"] = metas_criticas
    totales["top_metas_criticas"] = top
    return totales


def metas_rezagadas(
    ano: int,
    centros: list[str] | None = None,
    *,
    umbral_porcentaje: float = 50.0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Metas con % devengado < umbral (HU-16, RN-02 alerta configurable).

    Agrega por sec_func (una meta puede tener varias filas por clasificador/CC).
    """
    if centros is not None and len(centros) == 0:
        return []

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        "t.PPTO_MODIF > 0",
        "t.SEC_FUNC IS NOT NULL",  # Excluir techo del pliego sin desagregar.
    ]
    params: dict[str, Any] = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "umbral": umbral_porcentaje,
        "limit": limit,
    }
    if centros is not None:
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"t.CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    sql = f"""
        SELECT TOP (:limit)
            t.sec_func,
            LTRIM(RTRIM(m.nombre))          AS nombre_meta,
            LTRIM(RTRIM(m.act_proy))        AS act_proy,
            SUM(COALESCE(t.PPTO_MODIF, 0))              AS pim,
            SUM(COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0)) AS devengado,
            CASE WHEN SUM(COALESCE(t.PPTO_MODIF, 0)) > 0
                 THEN ROUND(SUM(COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0))
                            / SUM(t.PPTO_MODIF) * 100, 2)
                 ELSE 0 END                 AS porcentaje_devengado
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        WHERE {" AND ".join(where)}
        GROUP BY t.sec_func, m.nombre, m.act_proy
        HAVING CASE WHEN SUM(COALESCE(t.PPTO_MODIF, 0)) > 0
                    THEN SUM(COALESCE(t.mnto_acum_cert, 0) + COALESCE(t.mnto_acum_coma, 0))
                         / SUM(t.PPTO_MODIF) * 100
                    ELSE 0 END < :umbral
        ORDER BY porcentaje_devengado ASC
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]
