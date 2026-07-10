"""Repositorio SIGA: saldos presupuestales (`SIG_TECHO_PRESUPUESTO`).

Fuente autoritativa para PIM y saldo disponible (§18.2, §18.3 del diccionario).
Todas las queries fijan SEC_EJEC=300687 y filtran por centros_costo del usuario
cuando aplica (RN-04 filtro por CC).

`SIG_TECHO_PRESUPUESTO` tiene PK compuesta `ANO_EJE + SEC_EJEC + sec_func +
CLASIFICADOR + CENTRO_COSTO` (10,049 registros 2023-2026).
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
            COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0)                  AS devengado,
            COALESCE(t.PPTO_DISP_SIAF, 0)                         AS saldo_disponible,
            COALESCE(t.MNTO_RESERVA_PEDIDO, 0)                    AS reservado_pedido,
            CASE WHEN COALESCE(t.PPTO_MODIF, 0) > 0
                 THEN ROUND(COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0) / t.PPTO_MODIF * 100, 2)
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

    where = ["ANO_EJE = :ano", "SEC_EJEC = :sec_ejec"]
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

    where = ["t.ANO_EJE = :ano", "t.SEC_EJEC = :sec_ejec", "t.PPTO_MODIF > 0"]
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
            SUM(COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0))   AS devengado,
            CASE WHEN SUM(COALESCE(t.PPTO_MODIF, 0)) > 0
                 THEN ROUND(SUM(COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0)) / SUM(t.PPTO_MODIF) * 100, 2)
                 ELSE 0 END                 AS porcentaje_devengado
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        WHERE {" AND ".join(where)}
        GROUP BY t.sec_func, m.nombre, m.act_proy
        HAVING CASE WHEN SUM(COALESCE(t.PPTO_MODIF, 0)) > 0
                    THEN SUM(COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0)) / SUM(t.PPTO_MODIF) * 100
                    ELSE 0 END < :umbral
        ORDER BY porcentaje_devengado ASC
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]
