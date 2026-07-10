"""Repositorio SIGA: cruce SIAF-SIGA (HU-12, HU-13).

Cadena de cruce (§17 diccionario):
    EXP_SIAF -> SIG_ORDEN_ADQUISICION -> SIG_ORDEN_PRESUPUESTO -> META (por sec_func)
    Luego: SIG_DETALLE_PEDIDOS (por NRO_ORDEN) -> SIG_PEDIDOS
    Y: SIG_MOVIM_CONFOR_SERVICIO por NRO_ORDEN, SIG_CONTRATISTAS por PROVEEDOR
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


def buscar_por_exp_siaf(
    ano: int, exp_siaf: str
) -> dict[str, Any] | None:
    """Devuelve toda la trazabilidad del expediente SIAF."""
    with get_connection() as conn:
        # 1) Orden(es) con ese EXP_SIAF
        ordenes = conn.execute(
            text(
                """
                SELECT
                    o.ANO_EJE, o.SEC_EJEC, o.NRO_ORDEN, o.TIPO_BIEN,
                    o.EXP_SIAF, o.EXP_SIGA,
                    o.ESTADO, o.ESTADO_SIAF,
                    o.TOTAL_FACT_SOLES,
                    LTRIM(RTRIM(CAST(o.CONCEPTO AS VARCHAR(500)))) AS concepto,
                    o.FECHA_ORDEN,
                    o.NRO_CONTRATO, o.ANO_CONTRATO, o.SEC_CONTRATO,
                    LTRIM(RTRIM(c.NRO_RUC))     AS proveedor_ruc,
                    LTRIM(RTRIM(c.NOMBRE_PROV)) AS proveedor_nombre
                FROM SIG_ORDEN_ADQUISICION o
                LEFT JOIN SIG_CONTRATISTAS c ON c.PROVEEDOR = o.PROVEEDOR
                WHERE o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
                  AND o.EXP_SIAF = :exp
                """
            ),
            {"ano": ano, "sec_ejec": settings.SEC_EJEC, "exp": exp_siaf},
        ).mappings().all()

        if not ordenes:
            return None

        # 2) Afectacion presupuestal (SIG_ORDEN_PRESUPUESTO)
        afectacion = conn.execute(
            text(
                """
                SELECT
                    p.NRO_ORDEN, p.TIPO_BIEN, p.SEC_FUNC,
                    LTRIM(RTRIM(p.CLASIFICADOR)) AS clasificador,
                    LTRIM(RTRIM(p.FUENTE_FINANC)) AS fuente_financ,
                    p.EXP_SIAF, p.VALOR_SOLES,
                    LTRIM(RTRIM(m.nombre)) AS nombre_meta,
                    LTRIM(RTRIM(m.act_proy)) AS act_proy,
                    LTRIM(RTRIM(m.funcion)) AS funcion
                FROM SIG_ORDEN_PRESUPUESTO p
                INNER JOIN META m
                    ON m.sec_func = p.SEC_FUNC AND m.ano_eje = p.ANO_EJE
                WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
                  AND p.EXP_SIAF = :exp
                """
            ),
            {"ano": ano, "sec_ejec": settings.SEC_EJEC, "exp": exp_siaf},
        ).mappings().all()

        # 3) Pedidos origen (por NRO_ORDEN)
        nros_orden = list({(o["NRO_ORDEN"], o["TIPO_BIEN"]) for o in ordenes})
        pedidos: list[dict[str, Any]] = []
        if nros_orden:
            # Bindeamos cada orden como par (nro, tipo)
            filtros = []
            params: dict[str, Any] = {
                "ano": ano, "sec_ejec": settings.SEC_EJEC,
            }
            for i, (nro, tipo) in enumerate(nros_orden):
                filtros.append(f"(dp.NRO_ORDEN = :nro{i} AND dp.TIPO_BIEN = :tipo{i})")
                params[f"nro{i}"] = nro
                params[f"tipo{i}"] = tipo
            filtro_sql = " OR ".join(filtros)

            pedidos = list(conn.execute(
                text(
                    f"""
                    SELECT DISTINCT
                        pe.NRO_PEDIDO, pe.TIPO_BIEN,
                        pe.CENTRO_COSTO,
                        pe.sec_func,
                        pe.FECHA_PEDIDO, pe.ESTADO AS estado_pedido,
                        LTRIM(RTRIM(CAST(pe.MOTIVO_PEDIDO AS VARCHAR(500)))) AS motivo,
                        LTRIM(RTRIM(pe.NOMBRE_EMPLEADO)) AS solicitante,
                        dp.NRO_ORDEN
                    FROM SIG_DETALLE_PEDIDOS dp
                    INNER JOIN SIG_PEDIDOS pe
                        ON pe.ANO_EJE = dp.ANO_EJE AND pe.SEC_EJEC = dp.sec_ejec
                       AND pe.NRO_PEDIDO = dp.NRO_PEDIDO AND pe.TIPO_BIEN = dp.TIPO_BIEN
                    WHERE dp.ANO_EJE = :ano AND dp.sec_ejec = :sec_ejec
                      AND ({filtro_sql})
                    """
                ),
                params,
            ).mappings().all())

        # 4) Conformidades (por NRO_ORDEN)
        conformidades: list[dict[str, Any]] = []
        if nros_orden:
            filtros = []
            params2: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
            for i, (nro, tipo) in enumerate(nros_orden):
                filtros.append(f"(cf.NRO_ORDEN = :nro{i} AND cf.TIPO_BIEN = :tipo{i})")
                params2[f"nro{i}"] = nro
                params2[f"tipo{i}"] = tipo
            filtro_sql = " OR ".join(filtros)
            conformidades = list(conn.execute(
                text(
                    f"""
                    SELECT
                        cf.NRO_ORDEN, cf.ANO_ORDEN, cf.TIPO_BIEN,
                        cf.FECHA_MOVIMTO,
                        LTRIM(RTRIM(cf.INDI_CONFOR))          AS indi_confor,
                        cf.ESTADO_DEVENG,
                        LTRIM(RTRIM(cf.EXPEDIENTE_SIAF))      AS exp_siaf,
                        LTRIM(RTRIM(cf.RESPONSABLE))          AS responsable,
                        LTRIM(RTRIM(CAST(cf.OBSERVACION AS VARCHAR(500)))) AS observacion
                    FROM SIG_MOVIM_CONFOR_SERVICIO cf
                    WHERE cf.SEC_EJEC = :sec_ejec AND cf.ANO_ORDEN = :ano
                      AND ({filtro_sql})
                    """
                ),
                params2,
            ).mappings().all())

    return {
        "exp_siaf": exp_siaf,
        "ano": ano,
        "ordenes": [dict(o) for o in ordenes],
        "afectacion_presupuestal": [dict(a) for a in afectacion],
        "pedidos_origen": [dict(p) for p in pedidos],
        "conformidades": [dict(c) for c in conformidades],
    }


def consolidado_por_meta(
    ano: int, sec_func: int, centros: list[str] | None = None
) -> dict[str, Any] | None:
    """Vista consolidada por meta (HU-13): presupuesto + ordenes + conformidades + pedidos."""
    if centros is not None and len(centros) == 0:
        return None

    where_cc = ""
    params: dict[str, Any] = {
        "ano": ano, "sec_ejec": settings.SEC_EJEC, "sec_func": sec_func,
    }
    if centros is not None:
        binds = ", ".join(f":cc{i}" for i in range(len(centros)))
        where_cc = f" AND t.CENTRO_COSTO IN ({binds})"
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    with get_connection() as conn:
        meta = conn.execute(
            text(
                """
                SELECT
                    m.sec_func, m.ano_eje,
                    LTRIM(RTRIM(m.meta))         AS meta,
                    LTRIM(RTRIM(m.nombre))       AS nombre,
                    LTRIM(RTRIM(m.act_proy))     AS act_proy,
                    LTRIM(RTRIM(m.funcion))      AS funcion,
                    LTRIM(RTRIM(m.programa))     AS programa,
                    LTRIM(RTRIM(m.finalidad))    AS finalidad
                FROM META m
                WHERE m.ano_eje = :ano AND m.sec_ejec = :sec_ejec
                  AND m.sec_func = :sec_func
                """
            ),
            {"ano": ano, "sec_ejec": settings.SEC_EJEC, "sec_func": sec_func},
        ).mappings().first()

        if meta is None:
            return None

        # Saldo consolidado por meta
        presupuesto = conn.execute(
            text(
                f"""
                SELECT
                    SUM(COALESCE(t.PPTO_PIA, 0))              AS pia,
                    SUM(COALESCE(t.PPTO_MODIF, 0))            AS pim,
                    SUM(COALESCE(t.mnto_acum_cert, 0))        AS certificado,
                    SUM(COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0)) AS devengado,
                    SUM(COALESCE(t.PPTO_DISP_SIAF, 0))        AS saldo_disponible
                FROM SIG_TECHO_PRESUPUESTO t
                WHERE t.ANO_EJE = :ano AND t.SEC_EJEC = :sec_ejec
                  AND t.sec_func = :sec_func{where_cc}
                """
            ),
            params,
        ).mappings().first()

        # Ordenes asociadas a la meta
        ordenes = conn.execute(
            text(
                """
                SELECT DISTINCT
                    o.ANO_EJE, o.SEC_EJEC,
                    o.NRO_ORDEN, o.TIPO_BIEN,
                    o.EXP_SIAF, o.EXP_SIGA,
                    o.ESTADO, o.ESTADO_SIAF, o.TOTAL_FACT_SOLES,
                    o.FECHA_ORDEN,
                    LTRIM(RTRIM(CAST(o.CONCEPTO AS VARCHAR(300)))) AS concepto,
                    LTRIM(RTRIM(c.NRO_RUC))     AS proveedor_ruc,
                    LTRIM(RTRIM(c.NOMBRE_PROV)) AS proveedor_nombre
                FROM SIG_ORDEN_PRESUPUESTO p
                INNER JOIN SIG_ORDEN_ADQUISICION o
                    ON o.ANO_EJE = p.ANO_EJE AND o.SEC_EJEC = p.SEC_EJEC
                   AND o.NRO_ORDEN = p.NRO_ORDEN AND o.TIPO_BIEN = p.TIPO_BIEN
                LEFT JOIN SIG_CONTRATISTAS c ON c.PROVEEDOR = o.PROVEEDOR
                WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
                  AND p.SEC_FUNC = :sec_func
                """
            ),
            {"ano": ano, "sec_ejec": settings.SEC_EJEC, "sec_func": sec_func},
        ).mappings().all()

        # Pedidos que apuntan a la meta
        pedidos = conn.execute(
            text(
                """
                SELECT
                    pe.NRO_PEDIDO, pe.TIPO_BIEN,
                    pe.CENTRO_COSTO,
                    pe.FECHA_PEDIDO, pe.ESTADO AS estado_pedido,
                    LTRIM(RTRIM(CAST(pe.MOTIVO_PEDIDO AS VARCHAR(300)))) AS motivo
                FROM SIG_PEDIDOS pe
                WHERE pe.ANO_EJE = :ano AND pe.SEC_EJEC = :sec_ejec
                  AND pe.sec_func = :sec_func
                ORDER BY pe.FECHA_PEDIDO DESC
                """
            ),
            {"ano": ano, "sec_ejec": settings.SEC_EJEC, "sec_func": sec_func},
        ).mappings().all()

        # Certificaciones
        certificaciones = conn.execute(
            text(
                """
                SELECT
                    c.NRO_CERTIFICA,
                    LTRIM(RTRIM(c.CLASIFICADOR)) AS clasificador,
                    c.VALOR_SOLES,
                    c.FECHA_REG
                FROM SIG_CERTIFICACION_PPTO c
                WHERE c.ANO_EJE = :ano AND c.SEC_EJEC = :sec_ejec
                  AND c.SEC_FUNC = :sec_func
                ORDER BY c.FECHA_REG DESC
                """
            ),
            {"ano": ano, "sec_ejec": settings.SEC_EJEC, "sec_func": sec_func},
        ).mappings().all()

    return {
        "meta": dict(meta),
        "presupuesto": dict(presupuesto) if presupuesto else {},
        "ordenes": [dict(o) for o in ordenes],
        "pedidos": [dict(p) for p in pedidos],
        "certificaciones": [dict(c) for c in certificaciones],
    }


def sugerir_exp_siaf(ano: int, prefijo: str, limit: int = 10) -> list[str]:
    """Autocomplete de EXP_SIAF (para HU-12 AC-12.1)."""
    with get_connection() as conn:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT TOP (:limit) EXP_SIAF
                  FROM SIG_ORDEN_ADQUISICION
                 WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
                   AND EXP_SIAF LIKE :prefijo
                 ORDER BY EXP_SIAF
                """
            ),
            {
                "ano": ano, "sec_ejec": settings.SEC_EJEC,
                "prefijo": f"{prefijo}%", "limit": limit,
            },
        ).all()
    return [r.EXP_SIAF for r in rows]
