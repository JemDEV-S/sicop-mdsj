"""Repositorio SIGA: pipeline de pedidos y ordenes (HU-09, HU-10, HU-11).

Cubre `SIG_PEDIDOS`, `SIG_DETALLE_PEDIDOS`, `SIG_ORDEN_ADQUISICION`,
`SIG_ORDEN_PRESUPUESTO`, `SIG_MOVIM_CONFOR_SERVICIO`.

Deteccion de etapas segun §10.9 del diccionario:
    Solicitado     : PEDIDOS.ESTADO='1' + DETALLE.ESTADO_PED='1' + sin NRO_ORDEN
    Con orden      : DETALLE.NRO_ORDEN > 0 + ORDEN.ESTADO='1'
    En conformidad : DETALLE.ESTADO_CONFOR='1' o hay MOVIM_CONFOR
    Devengado      : ORDEN.ESTADO_SIAF='2'
    Cerrado        : PEDIDOS.ESTADO='7'

Filtro por CC del usuario (RN-04): `SIG_PEDIDOS.CENTRO_COSTO IN (...)`.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection

# Etiquetas canonicas de las columnas del kanban.
ETAPA_SOLICITADO = "solicitado"
ETAPA_CON_ORDEN = "con_orden"
ETAPA_CONFORMIDAD = "conformidad"
ETAPA_DEVENGADO = "devengado"
ETAPA_CERRADO = "cerrado"

ETAPAS = [
    ETAPA_SOLICITADO,
    ETAPA_CON_ORDEN,
    ETAPA_CONFORMIDAD,
    ETAPA_DEVENGADO,
    ETAPA_CERRADO,
]


def _bind_centros(centros: list[str]) -> tuple[str, dict[str, str]]:
    binds = [f":cc{i}" for i in range(len(centros))]
    params = {f"cc{i}": c for i, c in enumerate(centros)}
    return ", ".join(binds), params


def pipeline_kanban(
    ano: int,
    centros: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Devuelve `{etapa: [pedidos]}` con los tarjetones agrupados por etapa.

    Un pedido puede estar "estirado" entre etapas si sus items estan en distinto
    estado. La etapa del pedido se toma del ITEM mas atrasado (min de la escala
    solicitado->cerrado). Simplificado: usamos el estado del propio pedido +
    el maximo estado de sus items para clasificarlo.
    """
    if centros is not None and len(centros) == 0:
        return {e: [] for e in ETAPAS}

    where_pedido = [
        "p.ANO_EJE = :ano",
        "p.SEC_EJEC = :sec_ejec",
        "p.ESTADO IN ('1', '7')",  # descartamos borradores
    ]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}

    if centros is not None:
        binds_sql, binds_params = _bind_centros(centros)
        where_pedido.append(f"p.CENTRO_COSTO IN ({binds_sql})")
        params.update(binds_params)

    sql = f"""
        WITH pedidos_base AS (
            SELECT
                p.ANO_EJE, p.SEC_EJEC, p.NRO_PEDIDO, p.TIPO_BIEN,
                p.ESTADO             AS estado_pedido,
                p.CENTRO_COSTO,
                p.sec_func,
                p.FECHA_PEDIDO,
                p.FECHA_APROB,
                p.FECHA_ATENC,
                LTRIM(RTRIM(CAST(p.MOTIVO_PEDIDO AS VARCHAR(500)))) AS motivo,
                LTRIM(RTRIM(p.NOMBRE_EMPLEADO))  AS solicitante,
                LTRIM(RTRIM(p.FUENTE_FINANC))    AS fuente_financ
            FROM SIG_PEDIDOS p
            WHERE {" AND ".join(where_pedido)}
        ),
        agrup AS (
            SELECT
                b.ANO_EJE, b.SEC_EJEC, b.NRO_PEDIDO, b.TIPO_BIEN,
                b.estado_pedido, b.CENTRO_COSTO, b.sec_func,
                b.FECHA_PEDIDO, b.FECHA_APROB, b.FECHA_ATENC,
                b.motivo, b.solicitante, b.fuente_financ,
                MAX(CASE WHEN dp.NRO_ORDEN IS NOT NULL AND dp.NRO_ORDEN > 0
                         THEN 1 ELSE 0 END)             AS tiene_orden,
                MAX(CASE WHEN dp.ESTADO_CONFOR = '1'
                         THEN 1 ELSE 0 END)             AS tiene_conformidad,
                MAX(CASE WHEN o.ESTADO_SIAF = '2'
                         THEN 1 ELSE 0 END)             AS esta_devengado,
                SUM(COALESCE(dp.VALOR_TOTAL, 0))        AS monto_total,
                COUNT(dp.SECUENCIA)                     AS items,
                MAX(o.NRO_ORDEN)                        AS nro_orden_muestra
            FROM pedidos_base b
            LEFT JOIN SIG_DETALLE_PEDIDOS dp
                ON dp.ANO_EJE = b.ANO_EJE AND dp.sec_ejec = b.SEC_EJEC
               AND dp.TIPO_BIEN = b.TIPO_BIEN AND dp.NRO_PEDIDO = b.NRO_PEDIDO
            LEFT JOIN SIG_ORDEN_ADQUISICION o
                ON o.ANO_EJE = dp.ANO_EJE AND o.SEC_EJEC = dp.sec_ejec
               AND o.TIPO_BIEN = dp.TIPO_BIEN AND o.NRO_ORDEN = dp.NRO_ORDEN
            GROUP BY b.ANO_EJE, b.SEC_EJEC, b.NRO_PEDIDO, b.TIPO_BIEN,
                     b.estado_pedido, b.CENTRO_COSTO, b.sec_func,
                     b.FECHA_PEDIDO, b.FECHA_APROB, b.FECHA_ATENC,
                     b.motivo, b.solicitante, b.fuente_financ
        )
        SELECT
            ANO_EJE, SEC_EJEC, NRO_PEDIDO, TIPO_BIEN,
            estado_pedido, CENTRO_COSTO, sec_func,
            FECHA_PEDIDO, FECHA_APROB, FECHA_ATENC,
            motivo, solicitante, fuente_financ,
            tiene_orden, tiene_conformidad, esta_devengado,
            monto_total, items, nro_orden_muestra,
            CASE
                WHEN estado_pedido = '7'                                  THEN 'cerrado'
                WHEN esta_devengado = 1                                   THEN 'devengado'
                WHEN tiene_conformidad = 1                                THEN 'conformidad'
                WHEN tiene_orden = 1                                      THEN 'con_orden'
                ELSE 'solicitado'
            END AS etapa
        FROM agrup
        ORDER BY FECHA_PEDIDO DESC
    """

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    kanban: dict[str, list[dict[str, Any]]] = {e: [] for e in ETAPAS}
    for r in rows:
        etapa = r["etapa"]
        kanban[etapa].append(dict(r))
    return kanban


def contar_por_etapa(
    ano: int, centros: list[str] | None = None
) -> dict[str, int]:
    kanban = pipeline_kanban(ano, centros)
    return {e: len(kanban[e]) for e in ETAPAS}


def listar_pedidos(
    ano: int,
    centros: list[str] | None = None,
    *,
    etapa: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Listado plano paginado (para tabla + filtros libres).

    Reutiliza pipeline_kanban y filtra en Python — el volumen de pedidos por CC
    es pequeno (< miles) y el join en SIGA es el paso caro.
    """
    kanban = pipeline_kanban(ano, centros)
    # Aplanar y filtrar
    if etapa:
        filas = list(kanban.get(etapa, []))
    else:
        filas = [f for lst in kanban.values() for f in lst]

    if q:
        ql = q.lower()
        filas = [
            f
            for f in filas
            if (f.get("motivo") or "").lower().find(ql) >= 0
            or (f.get("solicitante") or "").lower().find(ql) >= 0
            or str(f.get("NRO_PEDIDO")) == q
        ]
    return filas[offset : offset + limit]


def obtener_pedido(
    ano: int, nro_pedido: int, tipo_bien: str
) -> dict[str, Any] | None:
    """Cabecera + items + orden(es) asociada(s) + conformidades del pedido."""
    with get_connection() as conn:
        cab = conn.execute(
            text(
                """
                SELECT
                    p.ANO_EJE, p.SEC_EJEC, p.NRO_PEDIDO, p.TIPO_BIEN,
                    p.TIPO_PEDIDO, p.CENTRO_COSTO, p.sec_func,
                    LTRIM(RTRIM(p.ACT_PROY))         AS act_proy,
                    p.ESTADO                         AS estado_pedido,
                    p.FECHA_PEDIDO, p.FECHA_APROB, p.FECHA_ATENC,
                    LTRIM(RTRIM(CAST(p.MOTIVO_PEDIDO AS VARCHAR(500)))) AS motivo,
                    LTRIM(RTRIM(p.NOMBRE_EMPLEADO))  AS solicitante,
                    LTRIM(RTRIM(p.FUENTE_FINANC))    AS fuente_financ,
                    LTRIM(RTRIM(cc.NOMBRE_DEPEND))   AS centro_costo_nombre,
                    LTRIM(RTRIM(m.nombre))           AS nombre_meta
                FROM SIG_PEDIDOS p
                LEFT JOIN SIG_CENTRO_COSTO cc
                    ON cc.ANO_EJE = p.ANO_EJE AND cc.SEC_EJEC = p.SEC_EJEC
                   AND cc.CENTRO_COSTO = p.CENTRO_COSTO
                LEFT JOIN META m
                    ON m.ano_eje = p.ANO_EJE AND m.sec_ejec = p.SEC_EJEC
                   AND m.sec_func = p.sec_func
                WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
                  AND p.NRO_PEDIDO = :nro AND p.TIPO_BIEN = :tipo
                """
            ),
            {
                "ano": ano, "sec_ejec": settings.SEC_EJEC,
                "nro": nro_pedido, "tipo": tipo_bien,
            },
        ).mappings().first()

        if cab is None:
            return None

        items = conn.execute(
            text(
                """
                SELECT
                    dp.SECUENCIA,
                    LTRIM(RTRIM(dp.ITEM_BIEN))      AS item_bien,
                    dp.CANT_SOLICITADA, dp.CANT_APROBADA, dp.CANT_ATENDIDA,
                    dp.VALOR_TOTAL,
                    LTRIM(RTRIM(dp.CLASIFICADOR))    AS clasificador,
                    dp.NRO_ORDEN,
                    dp.ESTADO_PED, dp.ESTADO_ATEND,
                    dp.ESTADO_CONFOR, dp.ESTADO_COMPRA,
                    dp.FECHA_CONFOR
                FROM SIG_DETALLE_PEDIDOS dp
                WHERE dp.ANO_EJE = :ano AND dp.sec_ejec = :sec_ejec
                  AND dp.NRO_PEDIDO = :nro AND dp.TIPO_BIEN = :tipo
                ORDER BY dp.SECUENCIA
                """
            ),
            {
                "ano": ano, "sec_ejec": settings.SEC_EJEC,
                "nro": nro_pedido, "tipo": tipo_bien,
            },
        ).mappings().all()

        ordenes = conn.execute(
            text(
                """
                SELECT DISTINCT
                    o.NRO_ORDEN, o.TIPO_BIEN,
                    o.EXP_SIAF, o.EXP_SIGA,
                    o.ESTADO, o.ESTADO_SIAF,
                    o.TOTAL_FACT_SOLES,
                    LTRIM(RTRIM(CAST(o.CONCEPTO AS VARCHAR(500)))) AS concepto,
                    o.FECHA_ORDEN,
                    LTRIM(RTRIM(c.NOMBRE_PROV))      AS proveedor_nombre,
                    LTRIM(RTRIM(c.NRO_RUC))          AS proveedor_ruc
                FROM SIG_ORDEN_ADQUISICION o
                INNER JOIN SIG_DETALLE_PEDIDOS dp
                    ON dp.ANO_EJE = o.ANO_EJE AND dp.sec_ejec = o.SEC_EJEC
                   AND dp.TIPO_BIEN = o.TIPO_BIEN AND dp.NRO_ORDEN = o.NRO_ORDEN
                LEFT JOIN SIG_CONTRATISTAS c ON c.PROVEEDOR = o.PROVEEDOR
                WHERE dp.ANO_EJE = :ano AND dp.sec_ejec = :sec_ejec
                  AND dp.NRO_PEDIDO = :nro AND dp.TIPO_BIEN = :tipo
                """
            ),
            {
                "ano": ano, "sec_ejec": settings.SEC_EJEC,
                "nro": nro_pedido, "tipo": tipo_bien,
            },
        ).mappings().all()

        conformidades = conn.execute(
            text(
                """
                SELECT
                    cf.NRO_ORDEN, cf.ANO_ORDEN, cf.TIPO_BIEN,
                    cf.FECHA_MOVIMTO,
                    LTRIM(RTRIM(cf.INDI_CONFOR))        AS indi_confor,
                    LTRIM(RTRIM(cf.NOMBRE_PROVEEDOR))   AS proveedor,
                    cf.ESTADO_DEVENG,
                    LTRIM(RTRIM(cf.EXPEDIENTE_SIAF))    AS exp_siaf,
                    LTRIM(RTRIM(cf.RESPONSABLE))        AS responsable,
                    LTRIM(RTRIM(CAST(cf.OBSERVACION AS VARCHAR(500)))) AS observacion
                FROM SIG_MOVIM_CONFOR_SERVICIO cf
                INNER JOIN SIG_DETALLE_PEDIDOS dp
                    ON dp.ANO_EJE = cf.ANO_ORDEN AND dp.sec_ejec = cf.SEC_EJEC
                   AND dp.TIPO_BIEN = cf.TIPO_BIEN AND dp.NRO_ORDEN = cf.NRO_ORDEN
                WHERE dp.ANO_EJE = :ano AND dp.sec_ejec = :sec_ejec
                  AND dp.NRO_PEDIDO = :nro AND dp.TIPO_BIEN = :tipo
                ORDER BY cf.FECHA_MOVIMTO DESC
                """
            ),
            {
                "ano": ano, "sec_ejec": settings.SEC_EJEC,
                "nro": nro_pedido, "tipo": tipo_bien,
            },
        ).mappings().all()

    return {
        **dict(cab),
        "items": [dict(i) for i in items],
        "ordenes": [dict(o) for o in ordenes],
        "conformidades": [dict(c) for c in conformidades],
    }
