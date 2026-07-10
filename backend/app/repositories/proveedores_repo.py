"""Repositorio: SIG_CONTRATISTAS + agregados de ordenes por proveedor.

HU-07 (directorio publico): sin datos de contacto.
HU-19 (perfil interno): incluye email, telefonos, historial.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


def listar_proveedores(
    *,
    ano: int | None = None,
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
    incluir_contacto: bool = False,
) -> list[dict[str, Any]]:
    """Devuelve el directorio de proveedores con monto acumulado del ano si aplica."""
    where = ["1 = 1"]
    params: dict[str, Any] = {"sec_ejec": settings.SEC_EJEC}

    if q:
        where.append(
            "(c.NRO_RUC LIKE :q OR c.NOMBRE_PROV LIKE :q)"
        )
        params["q"] = f"%{q}%"

    contacto_cols = ""
    if incluir_contacto:
        contacto_cols = """,
                LTRIM(RTRIM(c.EMAIL))            AS email,
                LTRIM(RTRIM(c.TELEFONOS))        AS telefonos,
                LTRIM(RTRIM(c.DIRECCION))        AS direccion"""

    if ano is not None:
        agg = """
                COALESCE(SUM(o.TOTAL_FACT_SOLES), 0) AS monto_acumulado,
                COUNT(DISTINCT o.NRO_ORDEN)          AS nro_ordenes
        """
        join = """
            LEFT JOIN SIG_ORDEN_ADQUISICION o
                ON o.PROVEEDOR = c.PROVEEDOR
               AND o.ANO_EJE = :ano
               AND o.SEC_EJEC = :sec_ejec
        """
        params["ano"] = ano
    else:
        agg = "CAST(NULL AS DECIMAL(18,2)) AS monto_acumulado, 0 AS nro_ordenes"
        join = ""

    sql = f"""
        SELECT
            c.PROVEEDOR                       AS proveedor_id,
            LTRIM(RTRIM(c.NRO_RUC))           AS ruc,
            LTRIM(RTRIM(c.NOMBRE_PROV))       AS nombre,
            LTRIM(RTRIM(c.TIPO_PERSONA))      AS tipo_persona,
            LTRIM(RTRIM(c.GIRO_GENERAL))      AS giro,
            LTRIM(RTRIM(c.FLAG_MYPE))         AS flag_mype,
            LTRIM(RTRIM(c.FLAG_RNP))          AS flag_rnp,
            LTRIM(RTRIM(c.FLAG_CONSORCIO))    AS flag_consorcio{contacto_cols},
            {agg}
        FROM SIG_CONTRATISTAS c
        {join}
        WHERE {" AND ".join(where)}
        GROUP BY
            c.PROVEEDOR, c.NRO_RUC, c.NOMBRE_PROV, c.TIPO_PERSONA,
            c.GIRO_GENERAL, c.FLAG_MYPE, c.FLAG_RNP, c.FLAG_CONSORCIO
            {', c.EMAIL, c.TELEFONOS, c.DIRECCION' if incluir_contacto else ''}
        ORDER BY monto_acumulado DESC, c.NOMBRE_PROV
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    params["limit"] = limit
    params["offset"] = offset

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def contar_proveedores(*, q: str | None = None) -> int:
    where = ["1 = 1"]
    params: dict[str, Any] = {}
    if q:
        where.append("(NRO_RUC LIKE :q OR NOMBRE_PROV LIKE :q)")
        params["q"] = f"%{q}%"
    sql = f"SELECT COUNT(*) FROM SIG_CONTRATISTAS WHERE {' AND '.join(where)}"
    with get_connection() as conn:
        return int(conn.execute(text(sql), params).scalar_one())


def obtener_proveedor_por_ruc(
    ruc: str, incluir_contacto: bool = True
) -> dict[str, Any] | None:
    contacto = ""
    if incluir_contacto:
        contacto = """,
            LTRIM(RTRIM(c.EMAIL))         AS email,
            LTRIM(RTRIM(c.TELEFONOS))     AS telefonos,
            LTRIM(RTRIM(c.DIRECCION))     AS direccion,
            LTRIM(RTRIM(c.NRO_RNP))       AS nro_rnp,
            c.FECHA_ISANCION, c.FECHA_FSANCION"""
    with get_connection() as conn:
        row = conn.execute(
            text(
                f"""
                SELECT
                    c.PROVEEDOR                 AS proveedor_id,
                    LTRIM(RTRIM(c.NRO_RUC))     AS ruc,
                    LTRIM(RTRIM(c.NOMBRE_PROV)) AS nombre,
                    LTRIM(RTRIM(c.TIPO_PERSONA))AS tipo_persona,
                    LTRIM(RTRIM(c.GIRO_GENERAL))AS giro,
                    LTRIM(RTRIM(c.FLAG_MYPE))   AS flag_mype,
                    LTRIM(RTRIM(c.FLAG_RNP))    AS flag_rnp,
                    LTRIM(RTRIM(c.FLAG_CONSORCIO)) AS flag_consorcio{contacto}
                FROM SIG_CONTRATISTAS c
                WHERE LTRIM(RTRIM(c.NRO_RUC)) = :ruc
                """
            ),
            {"ruc": ruc},
        ).mappings().first()
    return dict(row) if row else None


def ordenes_por_proveedor(
    ruc: str, *, ano: int | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    where = [
        "LTRIM(RTRIM(c.NRO_RUC)) = :ruc",
        "o.SEC_EJEC = :sec_ejec",
    ]
    params: dict[str, Any] = {"ruc": ruc, "sec_ejec": settings.SEC_EJEC, "limit": limit}
    if ano is not None:
        where.append("o.ANO_EJE = :ano")
        params["ano"] = ano

    sql = f"""
        SELECT TOP (:limit)
            o.ANO_EJE, o.NRO_ORDEN, o.TIPO_BIEN,
            o.EXP_SIAF, o.ESTADO, o.ESTADO_SIAF,
            o.TOTAL_FACT_SOLES,
            LTRIM(RTRIM(CAST(o.CONCEPTO AS VARCHAR(300)))) AS concepto,
            o.FECHA_ORDEN
        FROM SIG_ORDEN_ADQUISICION o
        INNER JOIN SIG_CONTRATISTAS c ON c.PROVEEDOR = o.PROVEEDOR
        WHERE {" AND ".join(where)}
        ORDER BY o.FECHA_ORDEN DESC
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]
