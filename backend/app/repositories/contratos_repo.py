"""Repositorio: SIG_CONTRATOS (HU-19, HU-20).

HU-20: alerta de contratos por vencer — `FECHA_FINAL - hoy <= Y dias` (default 30).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


def listar_contratos(
    *,
    ano: int | None = None,
    proveedor_ruc: str | None = None,
    estado: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    where = ["c.SEC_EJEC = :sec_ejec"]
    params: dict[str, Any] = {"sec_ejec": settings.SEC_EJEC}

    if ano is not None:
        where.append("c.ANO_EJE = :ano")
        params["ano"] = ano
    if proveedor_ruc:
        where.append("LTRIM(RTRIM(p.NRO_RUC)) = :ruc")
        params["ruc"] = proveedor_ruc
    if estado:
        where.append("LTRIM(RTRIM(c.ESTADO)) = :estado")
        params["estado"] = estado

    sql = f"""
        SELECT
            c.ANO_EJE, c.SEC_EJEC, c.TIPO_CONTRATO, c.NRO_CONTRATO, c.SEC_CONTRATO,
            c.TIPO_BIEN,
            c.PROVEEDOR                       AS proveedor_id,
            LTRIM(RTRIM(p.NRO_RUC))           AS proveedor_ruc,
            LTRIM(RTRIM(p.NOMBRE_PROV))       AS proveedor_nombre,
            c.FECHA_INICIAL, c.FECHA_FINAL, c.FECHA_CESE,
            c.VALOR_SOLES,
            LTRIM(RTRIM(CAST(c.OBJETO AS VARCHAR(500)))) AS objeto,
            LTRIM(RTRIM(c.TIPO_COMPRA))       AS tipo_compra,
            LTRIM(RTRIM(c.MODAL_COMPRA))      AS modal_compra,
            LTRIM(RTRIM(c.ID_PROCESO))        AS id_proceso,
            LTRIM(RTRIM(c.ID_CONTRATO))       AS id_contrato,
            LTRIM(RTRIM(c.NRO_DOCUMENTO))     AS nro_documento,
            LTRIM(RTRIM(c.ESTADO))            AS estado,
            LTRIM(RTRIM(c.FLAG_SNP))          AS flag_snp
        FROM SIG_CONTRATOS c
        LEFT JOIN SIG_CONTRATISTAS p ON p.PROVEEDOR = c.PROVEEDOR
        WHERE {" AND ".join(where)}
        ORDER BY c.FECHA_FINAL DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    params["limit"] = limit
    params["offset"] = offset

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def contar_contratos(
    *,
    ano: int | None = None,
    proveedor_ruc: str | None = None,
    estado: str | None = None,
) -> int:
    where = ["c.SEC_EJEC = :sec_ejec"]
    params: dict[str, Any] = {"sec_ejec": settings.SEC_EJEC}
    if ano is not None:
        where.append("c.ANO_EJE = :ano")
        params["ano"] = ano
    if proveedor_ruc:
        where.append("LTRIM(RTRIM(p.NRO_RUC)) = :ruc")
        params["ruc"] = proveedor_ruc
    if estado:
        where.append("LTRIM(RTRIM(c.ESTADO)) = :estado")
        params["estado"] = estado
    sql = f"""
        SELECT COUNT(*)
        FROM SIG_CONTRATOS c
        LEFT JOIN SIG_CONTRATISTAS p ON p.PROVEEDOR = c.PROVEEDOR
        WHERE {" AND ".join(where)}
    """
    with get_connection() as conn:
        return int(conn.execute(text(sql), params).scalar_one())


def contratos_por_vencer(
    dias: int = 30, limit: int = 100
) -> list[dict[str, Any]]:
    """Contratos cuya FECHA_FINAL cae dentro de los proximos `dias`."""
    sql = """
        SELECT TOP (:limit)
            c.ANO_EJE, c.NRO_CONTRATO, c.SEC_CONTRATO, c.TIPO_CONTRATO, c.TIPO_BIEN,
            LTRIM(RTRIM(p.NRO_RUC))     AS proveedor_ruc,
            LTRIM(RTRIM(p.NOMBRE_PROV)) AS proveedor_nombre,
            c.FECHA_INICIAL, c.FECHA_FINAL,
            c.VALOR_SOLES,
            LTRIM(RTRIM(CAST(c.OBJETO AS VARCHAR(500)))) AS objeto,
            LTRIM(RTRIM(c.ESTADO)) AS estado,
            DATEDIFF(day, GETDATE(), c.FECHA_FINAL) AS dias_restantes
        FROM SIG_CONTRATOS c
        LEFT JOIN SIG_CONTRATISTAS p ON p.PROVEEDOR = c.PROVEEDOR
        WHERE c.SEC_EJEC = :sec_ejec
          AND c.FECHA_FINAL IS NOT NULL
          AND c.FECHA_FINAL >= CAST(GETDATE() AS DATE)
          AND c.FECHA_FINAL <= DATEADD(day, :dias, CAST(GETDATE() AS DATE))
        ORDER BY c.FECHA_FINAL ASC
    """
    with get_connection() as conn:
        rows = conn.execute(
            text(sql),
            {"sec_ejec": settings.SEC_EJEC, "dias": dias, "limit": limit},
        ).mappings().all()
    return [dict(r) for r in rows]


def obtener_contrato(
    ano: int, nro_contrato: int, sec_contrato: int, tipo_contrato: str
) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    c.ANO_EJE, c.SEC_EJEC, c.TIPO_CONTRATO, c.NRO_CONTRATO,
                    c.SEC_CONTRATO, c.TIPO_BIEN,
                    c.PROVEEDOR                  AS proveedor_id,
                    LTRIM(RTRIM(p.NRO_RUC))      AS proveedor_ruc,
                    LTRIM(RTRIM(p.NOMBRE_PROV))  AS proveedor_nombre,
                    c.FECHA_INICIAL, c.FECHA_FINAL, c.FECHA_CESE,
                    c.VALOR_SOLES,
                    LTRIM(RTRIM(CAST(c.OBJETO AS VARCHAR(500))))  AS objeto,
                    LTRIM(RTRIM(CAST(c.GLOSA  AS VARCHAR(500))))  AS glosa,
                    LTRIM(RTRIM(c.TIPO_COMPRA))  AS tipo_compra,
                    LTRIM(RTRIM(c.MODAL_COMPRA)) AS modal_compra,
                    LTRIM(RTRIM(c.ID_PROCESO))   AS id_proceso,
                    LTRIM(RTRIM(c.ID_CONTRATO))  AS id_contrato,
                    LTRIM(RTRIM(c.NRO_DOCUMENTO))AS nro_documento,
                    LTRIM(RTRIM(c.ESTADO))       AS estado,
                    LTRIM(RTRIM(c.FLAG_SNP))     AS flag_snp,
                    c.NRO_MESES, c.MONTO_SUELDO_SOLES
                FROM SIG_CONTRATOS c
                LEFT JOIN SIG_CONTRATISTAS p ON p.PROVEEDOR = c.PROVEEDOR
                WHERE c.SEC_EJEC = :sec_ejec
                  AND c.ANO_EJE = :ano
                  AND c.NRO_CONTRATO = :nro
                  AND c.SEC_CONTRATO = :sec
                  AND LTRIM(RTRIM(c.TIPO_CONTRATO)) = :tipo
                """
            ),
            {
                "sec_ejec": settings.SEC_EJEC,
                "ano": ano, "nro": nro_contrato,
                "sec": sec_contrato, "tipo": tipo_contrato,
            },
        ).mappings().first()
    return dict(row) if row else None
