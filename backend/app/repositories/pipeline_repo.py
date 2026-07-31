"""Repositorio SIGA de DETALLE del pipeline (lectura puntual de un documento).

Guia Pipeline v2 §07: el kanban ya NO vive aqui. La query masiva de 12 CTE
(`_SQL_KANBAN`) y el match composite por monto se retiraron: el kanban lee del
snapshot (siga.v_pipeline_pedido via pipeline_read_repo), sin tocar SIGA en
caliente. Lo que queda aqui consulta SIGA para UN pedido/bolsa a la vez
(detalle, vista de bolsa, validacion al asociar) — costo bajo, pocas filas.

Cadena estructural (FK real o composite verificado en 232/S y 005/B):

    [3]  SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL IS NOT NULL        -> cuadro necesidad
    [4]  SIG_CUADRO_MODIFICADO_CMN (puente pedido<->PAAC)       -> CCMN candidato
    [5]  SIG_PAAC_CONSOLIDADO.NRO_CONSOLID                      -> CCMN / EM(CVR)
    [6]  SIG_SOLICITUD_COTIZACION.NRO_CONSOLID                  -> cotizacion
    [7]  SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC                   -> cuadro adquisicion
    [8]  SIG_CERTIFICACION.NRO_CERTIFICA_SIAF IS NOT NULL       -> CCP
    [9]  SIG_ORDEN_ADQUISICION (cadena dura CCMN)               -> orden emitida

Filtro por CC del usuario (RN-04) via SIG_PEDIDOS.CENTRO_COSTO IN (...).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


# ─── Parseo de las fuentes declarativas ──────────────────────────────────
#
# SIGA no vincula pedido y CCMN (§1): logistica copia los datos del pedido a
# un CCMN nuevo sin relacionarlos. Lo unico que queda es el texto libre, donde
# el usuario escribe de que pedido viene. Regex validado contra todos los
# formatos observados en 2026 (§3.3):
#
#   PEDIDO 76 · PEDIDO 0225 · PEDIDO DE COMPRA N°000026-2026
#   PEDIDO DE SERVICIO N°228-2026 ACTUALIZADO · PEDIOD 0041 (typo)
#
# `SEGUN CONTRATO` se descarta: no es un pedido.

RE_PEDIDO = re.compile(
    r"PEDIDO\s*(?:DE\s*(?:SERVICIO|COMPRA)\s*)?N?[^0-9A-Z]{0,4}(\d{1,6})", re.I
)
RE_CONTRATO = re.compile(r"SEGUN\s+CONTRATO", re.I)


def parsear_nro_pedido(texto: str | None) -> int | None:
    """Extrae el numero de pedido declarado en un texto libre de SIGA.

    Devuelve None cuando el texto no nombra un pedido (p.ej. `INFORME
    275-2026-MDSJ`, o `SEGUN CONTRATO`) — no adivina.
    """
    if not texto or RE_CONTRATO.search(texto):
        return None
    m = RE_PEDIDO.search(texto)
    return int(m.group(1)) if m else None


def _agrupar_declaraciones(rows: Any) -> dict[tuple[str, int], set[int]]:
    """(tipo_bien, nro_pedido) -> conjunto de CCMN que lo declaran.

    Se guarda el conjunto y no un ganador: si dos CCMN declaran el mismo
    pedido, elegir uno seria exactamente el "ganador por parecido" que la
    cascada existe para evitar.
    """
    out: dict[tuple[str, int], set[int]] = defaultdict(set)
    for r in rows:
        ped = parsear_nro_pedido(r["texto"])
        if ped is None or r["ccmn"] is None:
            continue
        out[((r["TIPO_BIEN"] or "").strip(), ped)].add(int(r["ccmn"]))
    return out


def _elegir_declarado(
    declaraciones: dict[tuple[str, int], set[int]],
    tipo_bien: str,
    nro_pedido: int,
    candidatos: frozenset[int],
) -> int | None:
    """CCMN declarado para el pedido, si la declaracion es inequivoca.

    Con varios CCMN declarando el mismo pedido se prefiere el que este entre
    los candidatos de la bolsa. Si queda mas de uno, se devuelve None: la
    fuente no desambigua y el pedido sigue `ambiguo`. Si el unico declarado
    esta FUERA de los candidatos se devuelve igual, para que la cascada lo
    marque `conflicto` en vez de silenciarlo.
    """
    decl = declaraciones.get((tipo_bien, nro_pedido))
    if not decl:
        return None
    dentro = decl & candidatos
    if len(dentro) == 1:
        return next(iter(dentro))
    if dentro:
        return None  # varios candidatos declarados: no desambigua
    return next(iter(decl)) if len(decl) == 1 else None



# ─── Fuentes declarativas (§3.3) ─────────────────────────────────────────
#
# Ambas emiten (tipo_bien, ccmn, texto). El texto nombra el PEDIDO; el parseo
# se hace en Python con RE_PEDIDO, no en SQL: el regex esta validado contra
# los formatos reales y en T-SQL seria ilegible e imposible de testear.

# La orden nombra el pedido en el texto libre del item. Su CCMN sale de la
# cadena propia de la orden (SEC_CUADRO -> NRO_CONS_PAAC), poblada en las
# 1,473 ordenes de 2026. Es la fuente de mayor prioridad: la orden es
# posterior en el proceso y estuvo bajo mas escrutinio.
_SQL_DECL_ORDEN = """
SELECT
    o.TIPO_BIEN,
    ca.NRO_CONS_PAAC                            AS ccmn,
    CAST(oi.ESPECIFICACIONES AS VARCHAR(2000))  AS texto
FROM SIG_ORDEN_ADQUISICION o
JOIN SIG_CUADRO_ADQUISICION ca
    ON ca.ANO_EJE = o.ANO_EJE
   AND ca.SEC_EJEC = o.SEC_EJEC
   AND ca.TIPO_BIEN = o.TIPO_BIEN
   AND ca.SEC_CUADRO = o.SEC_CUADRO
JOIN SIG_ORDEN_ITEM oi
    ON oi.ANO_EJE = o.ANO_EJE
   AND oi.SEC_EJEC = o.SEC_EJEC
   AND oi.TIPO_BIEN = o.TIPO_BIEN
   AND oi.NRO_ORDEN = o.NRO_ORDEN
WHERE o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
  AND oi.ESPECIFICACIONES IS NOT NULL
"""

# SIG_CERTIFICACION_DOC trae NRO_CONSOLID propio al 100% (876 S / 659 B en
# 2026) -- no hace falta pasar por SIG_CERTIFICACION_FASE.
_SQL_DECL_CERT = """
SELECT
    cd.TIPO_BIEN,
    cd.NRO_CONSOLID                         AS ccmn,
    CAST(cd.REQUERIMIENTO AS VARCHAR(500))  AS texto
FROM SIG_CERTIFICACION_DOC cd
WHERE cd.ANO_EJE = :ano AND cd.SEC_EJEC = :sec_ejec
  AND cd.REQUERIMIENTO IS NOT NULL
"""




# ─── Vista de bolsa (SEC_CUA_MOD_SAL) ────────────────────────────────────


def contexto_pedido_bolsa(
    ano: int, tipo_bien: str, tipo_pedido: str, nro_pedido: int
) -> dict[str, Any] | None:
    """Bolsa(s), CC y CCMN candidatos de un pedido — para validar al asociar.

    Se usa antes de escribir una resolucion manual: comprueba que el pedido
    existe, de que CC es (RN-04) y que el CCMN elegido esta de verdad entre
    los candidatos de su bolsa. Sin esto se podria asociar cualquier numero.
    """
    params = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "tipo": tipo_bien,
        "tipo_ped": tipo_pedido,
        "nro": nro_pedido,
    }
    with get_connection() as conn:
        cab = conn.execute(
            text(
                """
                SELECT TOP 1 p.NRO_PEDIDO, p.TIPO_BIEN, p.TIPO_PEDIDO,
                       LTRIM(RTRIM(p.CENTRO_COSTO)) AS CENTRO_COSTO,
                       p.sec_func, p.ESTADO AS estado_pedido, p.FECHA_PEDIDO
                FROM SIG_PEDIDOS p
                WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
                  AND p.TIPO_BIEN = :tipo AND p.TIPO_PEDIDO = :tipo_ped
                  AND p.NRO_PEDIDO = :nro
                """
            ),
            params,
        ).mappings().first()

        if cab is None:
            return None

        filas = conn.execute(
            text(
                """
                SELECT DISTINCT dp.SEC_CUA_MOD_SAL, cmn.NRO_CONSOLID
                FROM SIG_DETALLE_PEDIDOS dp
                LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
                    ON cmn.SEC_EJEC = dp.SEC_EJEC
                   AND cmn.ANNO_EJEC = dp.ANO_EJE
                   AND cmn.SEC_CUA_MOD_SAL = dp.SEC_CUA_MOD_SAL
                   AND cmn.TIPO_BIEN = dp.TIPO_BIEN
                WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                  AND dp.TIPO_BIEN = :tipo AND dp.NRO_PEDIDO = :nro
                  AND dp.SEC_CUA_MOD_SAL IS NOT NULL
                """
            ),
            params,
        ).all()

    bolsas = sorted({int(b) for b, _ in filas if b is not None})
    candidatos = sorted({int(c) for _, c in filas if c is not None})
    cand_set = frozenset(candidatos)

    # Declaraciones de las dos fuentes de texto (§3.3), para que el caller
    # pueda resolver la cascada sin repetir el parseo.
    p_decl = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    with get_connection() as conn:
        decl_orden = _agrupar_declaraciones(
            conn.execute(text(_SQL_DECL_ORDEN), p_decl).mappings().all()
        )
        decl_cert = _agrupar_declaraciones(
            conn.execute(text(_SQL_DECL_CERT), p_decl).mappings().all()
        )

    return {
        **dict(cab),
        "centro_costo": (cab["CENTRO_COSTO"] or "").strip(),
        "bolsas": bolsas,
        "candidatos": candidatos,
        "ccmn_declarado_orden": _elegir_declarado(
            decl_orden, tipo_bien, nro_pedido, cand_set
        ),
        "ccmn_declarado_cert": _elegir_declarado(
            decl_cert, tipo_bien, nro_pedido, cand_set
        ),
    }


def obtener_bolsa(
    ano: int, sec_cua_mod_sal: int, tipo_bien: str
) -> dict[str, Any] | None:
    """Pedidos y CCMN candidatos que comparten una bolsa `SEC_CUA_MOD_SAL`.

    La bolsa es donde vive la ambiguedad (§2.1): el CCMN es una copia del
    pedido, asi que comparten item, meta, clasificador y centro de costo
    **por construccion** -- justo los campos que los agrupan aqui.

    Orden **cronologico y neutro**, de mas reciente a mas antiguo, con
    desempate por numero descendente para que sea estable entre recargas.
    El monto se devuelve para mostrarlo, pero NO se ordena ni se sugiere por
    el: ordenar por proximidad de monto seria una recomendacion disfrazada, y
    ese metodo esta descartado en §2 -- pierde el CCMN correcto en 33 casos.

    Ref: doc de refactorizacion §8.2
    """
    params = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "bolsa": sec_cua_mod_sal,
        "tipo": tipo_bien,
    }
    with get_connection() as conn:
        pedidos = conn.execute(
            text(
                """
                SELECT DISTINCT
                    p.NRO_PEDIDO, p.TIPO_BIEN, p.TIPO_PEDIDO,
                    p.CENTRO_COSTO, p.sec_func, p.ESTADO AS estado_pedido,
                    p.FECHA_PEDIDO,
                    LTRIM(RTRIM(CAST(p.MOTIVO_PEDIDO AS VARCHAR(500)))) AS motivo,
                    LTRIM(RTRIM(p.NOMBRE_EMPLEADO))                     AS solicitante,
                    -- VALOR_TOTAL viene en 0.00 en los servicios (verificado
                    -- en los 3 pedidos de la bolsa 11553): el monto real esta
                    -- en CANT_SOLICITADA * PRECIO_UNIT. Tomar VALOR_TOTAL a
                    -- secas mostraria toda la bolsa en S/ 0 -- fallo silencioso.
                    CASE
                        WHEN COALESCE(dp.VALOR_TOTAL, 0) > 0 THEN dp.VALOR_TOTAL
                        ELSE COALESCE(dp.CANT_SOLICITADA, 0)
                             * COALESCE(dp.PRECIO_UNIT, 0)
                    END                                                 AS valor_soles,
                    LTRIM(RTRIM(dp.GRUPO_BIEN)) + '-' + LTRIM(RTRIM(dp.CLASE_BIEN))
                      + '-' + LTRIM(RTRIM(dp.FAMILIA_BIEN)) + '-'
                      + LTRIM(RTRIM(dp.ITEM_BIEN))                      AS item
                FROM SIG_DETALLE_PEDIDOS dp
                INNER JOIN SIG_PEDIDOS p
                    ON p.ANO_EJE = dp.ANO_EJE AND p.SEC_EJEC = dp.SEC_EJEC
                   AND p.TIPO_BIEN = dp.TIPO_BIEN AND p.NRO_PEDIDO = dp.NRO_PEDIDO
                WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                  AND dp.SEC_CUA_MOD_SAL = :bolsa
                  AND dp.TIPO_BIEN = :tipo
                  AND p.ESTADO IN ('0', '1', '7')
                ORDER BY p.FECHA_PEDIDO DESC, p.NRO_PEDIDO DESC
                """
            ),
            params,
        ).mappings().all()

        if not pedidos:
            return None

        candidatos = conn.execute(
            text(
                """
                SELECT DISTINCT
                    pc.NRO_CONSOLID, pc.TIPO_CONSOLID,
                    pc.FECHA_CONS, pc.VALOR_PLAN,
                    pc.NRO_EST_MDO, pc.NRO_CERTIFICA,
                    c.NRO_CERTIFICA_SIAF,
                    ca.SEC_CUADRO,
                    o.NRO_ORDEN, o.FECHA_ORDEN
                FROM SIG_CUADRO_MODIFICADO_CMN cmn
                INNER JOIN SIG_PAAC_CONSOLIDADO pc
                    ON pc.ANO_EJE = cmn.ANNO_EJEC
                   AND pc.SEC_EJEC = cmn.SEC_EJEC
                   AND pc.TIPO_CONSOLID = cmn.TIPO_CONSOLID
                   AND pc.NRO_CONSOLID = cmn.NRO_CONSOLID
                   AND pc.TIPO_BIEN = cmn.TIPO_BIEN
                LEFT JOIN SIG_CERTIFICACION c
                    ON c.ANO_EJE = pc.ANO_EJE AND c.SEC_EJEC = pc.SEC_EJEC
                   AND c.NRO_CERTIFICA = pc.NRO_CERTIFICA
                LEFT JOIN SIG_CUADRO_ADQUISICION ca
                    ON ca.ANO_EJE = pc.ANO_EJE AND ca.SEC_EJEC = pc.SEC_EJEC
                   AND ca.TIPO_BIEN = pc.TIPO_BIEN
                   AND ca.NRO_CONS_PAAC = pc.NRO_CONSOLID
                LEFT JOIN SIG_ORDEN_ADQUISICION o
                    ON o.ANO_EJE = ca.ANO_EJE AND o.SEC_EJEC = ca.SEC_EJEC
                   AND o.TIPO_BIEN = ca.TIPO_BIEN AND o.SEC_CUADRO = ca.SEC_CUADRO
                WHERE cmn.ANNO_EJEC = :ano AND cmn.SEC_EJEC = :sec_ejec
                  AND cmn.SEC_CUA_MOD_SAL = :bolsa
                  AND cmn.TIPO_BIEN = :tipo
                ORDER BY pc.FECHA_CONS DESC, pc.NRO_CONSOLID DESC
                """
            ),
            params,
        ).mappings().all()

    return {
        "sec_cua_mod_sal": sec_cua_mod_sal,
        "ano_eje": ano,
        "tipo_bien": tipo_bien,
        "pedidos": [dict(p) for p in pedidos],
        "candidatos": [dict(c) for c in candidatos],
    }


# ─── Detalle de un pedido con la cadena completa ─────────────────────────


def _flags_programacion(
    ano: int, tipo_bien: str, tipo_pedido: str, nro_pedido: int
) -> dict[str, Any]:
    """Presencia de las etapas 4-7 mirando la cadena del CCMN hacia arriba.

    Mismos joins que los CTE del kanban (bolsa -> CCMN -> PAAC -> cotizacion ->
    cuadro de adquisicion). Devuelve los flags que `construir_timeline` usa para
    distinguir cada etapa, y `nro_est_mdo` / `nro_consolid` como identificadores
    del estudio de mercado.

    Sin esto el detalle solo veia la cadena hacia abajo desde la orden, y un
    pedido detenido en el estudio de mercado se mostraba en "cuadro necesidad"
    (caso 311/S).
    """
    params = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "tipo": tipo_bien,
        "tipo_ped": tipo_pedido,
        "nro": nro_pedido,
    }
    with get_connection() as conn:
        fila = conn.execute(
            text(
                """
                WITH det AS (
                    SELECT DISTINCT dp.SEC_CUA_MOD_SAL, dp.TIPO_BIEN,
                           dp.ANO_EJE, dp.SEC_EJEC
                    FROM SIG_DETALLE_PEDIDOS dp
                    WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                      AND dp.TIPO_BIEN = :tipo AND dp.TIPO_PEDIDO = :tipo_ped
                      AND dp.NRO_PEDIDO = :nro
                      AND dp.SEC_CUA_MOD_SAL IS NOT NULL
                )
                SELECT
                    MAX(CASE WHEN cmn.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END) AS tiene_puente_paac,
                    MAX(CASE WHEN pc.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END)  AS tiene_ccmn,
                    MAX(CASE WHEN sc.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END)  AS tiene_cotizacion,
                    MAX(CASE WHEN ca.SEC_CUADRO IS NOT NULL THEN 1 ELSE 0 END)    AS tiene_cuadro_adq,
                    MIN(pc.NRO_CONSOLID)                                          AS nro_consolid,
                    MIN(pc.NRO_EST_MDO)                                           AS nro_est_mdo,
                    MIN(ca.SEC_CUADRO)                                            AS sec_cuadro_prog
                FROM det d
                LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
                    ON cmn.SEC_EJEC = d.SEC_EJEC
                   AND cmn.ANNO_EJEC = d.ANO_EJE
                   AND cmn.SEC_CUA_MOD_SAL = d.SEC_CUA_MOD_SAL
                   AND cmn.TIPO_BIEN = d.TIPO_BIEN
                LEFT JOIN SIG_PAAC_CONSOLIDADO pc
                    ON pc.ANO_EJE = cmn.ANNO_EJEC
                   AND pc.SEC_EJEC = cmn.SEC_EJEC
                   AND pc.TIPO_CONSOLID = cmn.TIPO_CONSOLID
                   AND pc.NRO_CONSOLID = cmn.NRO_CONSOLID
                   AND pc.TIPO_BIEN = cmn.TIPO_BIEN
                LEFT JOIN SIG_SOLICITUD_COTIZACION sc
                    ON sc.ANO_EJE = cmn.ANNO_EJEC
                   AND sc.SEC_EJEC = cmn.SEC_EJEC
                   AND sc.tipo_bien = cmn.TIPO_BIEN
                   AND sc.NRO_CONSOLID = cmn.NRO_CONSOLID
                LEFT JOIN SIG_CUADRO_ADQUISICION ca
                    ON ca.ANO_EJE = cmn.ANNO_EJEC
                   AND ca.SEC_EJEC = cmn.SEC_EJEC
                   AND ca.TIPO_BIEN = cmn.TIPO_BIEN
                   AND ca.NRO_CONS_PAAC = cmn.NRO_CONSOLID
                """
            ),
            params,
        ).mappings().first()

    if fila is None:
        return {
            "tiene_puente_paac": 0, "tiene_ccmn": 0,
            "tiene_cotizacion": 0, "tiene_cuadro_adq": 0,
            "nro_consolid": None, "nro_est_mdo": None, "sec_cuadro_prog": None,
        }
    return dict(fila)


def obtener_pedido(
    ano: int, nro_pedido: int, tipo_bien: str
) -> dict[str, Any] | None:
    """Cabecera + items + orden(es) + cadena arriba + conformidades + almacen.

    Igual que antes; el timeline lo arma el service a partir de estos datos.
    """
    params = {
        "ano": ano, "sec_ejec": settings.SEC_EJEC,
        "nro": nro_pedido, "tipo": tipo_bien,
    }
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
            params,
        ).mappings().first()

        if cab is None:
            return None

        items = conn.execute(
            text(
                """
                SELECT
                    dp.SECUENCIA,
                    LTRIM(RTRIM(dp.GRUPO_BIEN))     AS grupo_bien,
                    LTRIM(RTRIM(dp.CLASE_BIEN))     AS clase_bien,
                    LTRIM(RTRIM(dp.FAMILIA_BIEN))   AS familia_bien,
                    LTRIM(RTRIM(dp.ITEM_BIEN))      AS item_bien,
                    dp.CANT_SOLICITADA, dp.CANT_APROBADA, dp.CANT_ATENDIDA,
                    -- VALOR_TOTAL viene en 0.00 en servicios; el monto real
                    -- es CANT_SOLICITADA * PRECIO_UNIT. Ver §9.5 del doc.
                    CASE
                        WHEN COALESCE(dp.VALOR_TOTAL, 0) > 0 THEN dp.VALOR_TOTAL
                        ELSE COALESCE(dp.CANT_SOLICITADA, 0)
                             * COALESCE(dp.PRECIO_UNIT, 0)
                    END                             AS VALOR_TOTAL,
                    LTRIM(RTRIM(dp.CLASIFICADOR))   AS clasificador,
                    dp.NRO_ORDEN                    AS nro_orden_declarado,
                    dp.NRO_PECOSA,
                    dp.SEC_CUA_MOD_SAL,
                    dp.ESTADO_PED, dp.ESTADO_ATEND,
                    dp.ESTADO_CONFOR, dp.ESTADO_COMPRA,
                    dp.FECHA_CONFOR
                FROM SIG_DETALLE_PEDIDOS dp
                WHERE dp.ANO_EJE = :ano AND dp.sec_ejec = :sec_ejec
                  AND dp.NRO_PEDIDO = :nro AND dp.TIPO_BIEN = :tipo
                ORDER BY dp.SECUENCIA
                """
            ),
            params,
        ).mappings().all()

        ordenes = conn.execute(
            text(
                """
                WITH det AS (
                    SELECT
                        dp.NRO_PECOSA,
                        dp.NRO_ORDEN                                AS nro_orden_declarado,
                        p.sec_func                                  AS sec_func_item,
                        LTRIM(RTRIM(dp.CLASIFICADOR))               AS clasificador,
                        LTRIM(RTRIM(dp.GRUPO_BIEN))                 AS grupo_bien,
                        LTRIM(RTRIM(dp.CLASE_BIEN))                 AS clase_bien,
                        LTRIM(RTRIM(dp.FAMILIA_BIEN))               AS familia_bien,
                        LTRIM(RTRIM(dp.ITEM_BIEN))                  AS item_bien,
                        -- Mismo fallback que el kanban: con VALOR_TOTAL en 0
                        -- el composite acepta cualquier monto y trae las
                        -- ordenes de los demas pedidos de la bolsa.
                        CASE
                            WHEN COALESCE(dp.VALOR_TOTAL, 0) > 0
                                THEN dp.VALOR_TOTAL
                            ELSE COALESCE(dp.CANT_SOLICITADA, 0)
                                 * COALESCE(dp.PRECIO_UNIT, 0)
                        END                                         AS valor_soles
                    FROM SIG_DETALLE_PEDIDOS dp
                    INNER JOIN SIG_PEDIDOS p
                        ON p.ANO_EJE = dp.ANO_EJE AND p.SEC_EJEC = dp.SEC_EJEC
                       AND p.TIPO_BIEN = dp.TIPO_BIEN AND p.NRO_PEDIDO = dp.NRO_PEDIDO
                    WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                      AND dp.TIPO_BIEN = :tipo AND dp.NRO_PEDIDO = :nro
                ),
                pecosa AS (
                    SELECT DISTINCT ma.NRO_ORDEN
                    FROM det d
                    INNER JOIN SIG_MOVIM_ALMACEN ma
                        ON ma.ANO_EJE = :ano AND ma.SEC_EJEC = :sec_ejec
                       AND ma.TIPO_BIEN = :tipo AND ma.NRO_MOVIMTO = d.NRO_PECOSA
                    WHERE d.NRO_PECOSA > 0
                ),
                composite AS (
                    SELECT DISTINCT oi.NRO_ORDEN
                    FROM det d
                    INNER JOIN SIG_ORDEN_ITEM oi
                        ON oi.ANO_EJE = :ano AND oi.SEC_EJEC = :sec_ejec
                       AND oi.TIPO_BIEN = :tipo
                       AND LTRIM(RTRIM(oi.GRUPO_BIEN)) = d.grupo_bien
                       AND LTRIM(RTRIM(oi.CLASE_BIEN)) = d.clase_bien
                       AND LTRIM(RTRIM(oi.FAMILIA_BIEN)) = d.familia_bien
                       AND LTRIM(RTRIM(oi.ITEM_BIEN)) = d.item_bien
                    INNER JOIN SIG_ORDEN_ITEM_PPTO op
                        ON op.ANO_EJE = oi.ANO_EJE AND op.SEC_EJEC = oi.SEC_EJEC
                       AND op.NRO_ORDEN = oi.NRO_ORDEN AND op.TIPO_BIEN = oi.TIPO_BIEN
                       AND op.TIPO_PPTO = oi.TIPO_PPTO AND op.SEC_ORDEN = oi.SEC_ORDEN
                       AND op.SEC_ITEM = oi.SEC_ITEM
                       AND op.SEC_FUNC = d.sec_func_item
                       AND LTRIM(RTRIM(op.CLASIFICADOR)) = d.clasificador
                       AND (d.valor_soles = 0 OR ROUND(op.VALOR_SOLES, 2) = ROUND(d.valor_soles, 2))
                ),
                declarado AS (
                    SELECT DISTINCT nro_orden_declarado AS NRO_ORDEN
                    FROM det WHERE nro_orden_declarado > 0
                ),
                -- Cadena dura CCMN -> cuadro de adquisicion -> orden. FK real
                -- de SIGA, no heuristica de monto. Solo se activa cuando la
                -- bolsa tiene UN SOLO CCMN candidato (caso `unico`): ahi el
                -- cuadro es de ESTE pedido con certeza, asi que no reintroduce
                -- el fallo de §2 (mezcla ordenes en bolsas compartidas).
                -- Recupera ordenes que el composite pierde cuando el monto
                -- cambio tras cotizar (226/S: pidio 5600, la OC 97 salio 5500).
                bolsa_unica AS (
                    SELECT dp.SEC_CUA_MOD_SAL, MIN(cmn.NRO_CONSOLID) AS ccmn
                    FROM SIG_DETALLE_PEDIDOS dp
                    JOIN SIG_CUADRO_MODIFICADO_CMN cmn
                        ON cmn.SEC_EJEC = dp.SEC_EJEC
                       AND cmn.ANNO_EJEC = dp.ANO_EJE
                       AND cmn.SEC_CUA_MOD_SAL = dp.SEC_CUA_MOD_SAL
                       AND cmn.TIPO_BIEN = dp.TIPO_BIEN
                    WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                      AND dp.TIPO_BIEN = :tipo AND dp.NRO_PEDIDO = :nro
                      AND dp.SEC_CUA_MOD_SAL IS NOT NULL
                    GROUP BY dp.SEC_CUA_MOD_SAL
                    HAVING COUNT(DISTINCT cmn.NRO_CONSOLID) = 1
                ),
                cadena_ccmn AS (
                    SELECT DISTINCT o.NRO_ORDEN
                    FROM bolsa_unica b
                    JOIN SIG_CUADRO_ADQUISICION ca
                        ON ca.ANO_EJE = :ano AND ca.SEC_EJEC = :sec_ejec
                       AND ca.TIPO_BIEN = :tipo AND ca.NRO_CONS_PAAC = b.ccmn
                    JOIN SIG_ORDEN_ADQUISICION o
                        ON o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
                       AND o.TIPO_BIEN = :tipo AND o.SEC_CUADRO = ca.SEC_CUADRO
                ),
                todas AS (
                    SELECT NRO_ORDEN, 'pecosa' AS metodo FROM pecosa
                    UNION SELECT NRO_ORDEN, 'composite' FROM composite
                    UNION SELECT NRO_ORDEN, 'declarado' FROM declarado
                    UNION SELECT NRO_ORDEN, 'cadena_ccmn' FROM cadena_ccmn
                )
                SELECT
                    o.NRO_ORDEN, o.TIPO_BIEN,
                    o.EXP_SIAF, o.EXP_SIGA,
                    o.SEC_CUADRO, o.NRO_CERTIFICA,
                    -- CCMN del que sale la orden: permite quedarse solo con
                    -- las ordenes del CCMN atribuido a ESTE pedido.
                    ca_o.NRO_CONS_PAAC,
                    o.ESTADO, o.ESTADO_SIAF,
                    o.TOTAL_FACT_SOLES,
                    LTRIM(RTRIM(CAST(o.CONCEPTO AS VARCHAR(500)))) AS concepto,
                    o.FECHA_ORDEN,
                    LTRIM(RTRIM(c.NOMBRE_PROV))      AS proveedor_nombre,
                    LTRIM(RTRIM(c.NRO_RUC))          AS proveedor_ruc,
                    STUFF((
                        SELECT ',' + t2.metodo
                        FROM todas t2 WHERE t2.NRO_ORDEN = o.NRO_ORDEN
                        FOR XML PATH('')
                    ), 1, 1, '')                     AS match_metodos
                FROM SIG_ORDEN_ADQUISICION o
                INNER JOIN (SELECT DISTINCT NRO_ORDEN FROM todas) t
                    ON t.NRO_ORDEN = o.NRO_ORDEN
                LEFT JOIN SIG_CUADRO_ADQUISICION ca_o
                    ON ca_o.ANO_EJE = o.ANO_EJE AND ca_o.SEC_EJEC = o.SEC_EJEC
                   AND ca_o.TIPO_BIEN = o.TIPO_BIEN
                   AND ca_o.SEC_CUADRO = o.SEC_CUADRO
                LEFT JOIN SIG_CONTRATISTAS c ON c.PROVEEDOR = o.PROVEEDOR
                WHERE o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
                  AND o.TIPO_BIEN = :tipo
                ORDER BY o.FECHA_ORDEN
                """
            ),
            params,
        ).mappings().all()

        ordenes_list = [dict(o) for o in ordenes]

        cadena_ids = {
            "sec_cuadros": sorted({o["SEC_CUADRO"] for o in ordenes_list if o.get("SEC_CUADRO")}),
            "nro_certifs": sorted({o["NRO_CERTIFICA"] for o in ordenes_list if o.get("NRO_CERTIFICA")}),
            "exp_sigas": sorted({o["EXP_SIGA"] for o in ordenes_list if o.get("EXP_SIGA")}),
            "exp_siafs": sorted({o["EXP_SIAF"] for o in ordenes_list if o.get("EXP_SIAF")}),
        }

        cuadros: list[dict[str, Any]] = []
        if cadena_ids["sec_cuadros"]:
            binds = ", ".join(f":sc{i}" for i in range(len(cadena_ids["sec_cuadros"])))
            p = {f"sc{i}": v for i, v in enumerate(cadena_ids["sec_cuadros"])}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC, "tipo": tipo_bien})
            cuadros = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
                        SELECT ca.SEC_CUADRO, ca.TIPO_BIEN, ca.ESTADO,
                               ca.FECHA_CUADRO, ca.FECHA_AUTORIZ, ca.FECHA_COMPRA,
                               ca.VALOR_TOTAL
                        FROM SIG_CUADRO_ADQUISICION ca
                        WHERE ca.ANO_EJE = :ano AND ca.SEC_EJEC = :sec_ejec
                          AND ca.TIPO_BIEN = :tipo
                          AND ca.SEC_CUADRO IN ({binds})
                        ORDER BY ca.SEC_CUADRO
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        certificaciones: list[dict[str, Any]] = []
        if cadena_ids["nro_certifs"]:
            binds = ", ".join(f":ce{i}" for i in range(len(cadena_ids["nro_certifs"])))
            p = {f"ce{i}": v for i, v in enumerate(cadena_ids["nro_certifs"])}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC})
            certificaciones = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
                        SELECT c.NRO_CERTIFICA, c.NRO_CERTIFICA_SIAF,
                               c.ESTADO_CERTIFICA_SIAF, c.FECHA
                        FROM SIG_CERTIFICACION c
                        WHERE c.ANO_EJE = :ano AND c.SEC_EJEC = :sec_ejec
                          AND c.NRO_CERTIFICA IN ({binds})
                        ORDER BY c.NRO_CERTIFICA
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        expedientes: list[dict[str, Any]] = []
        if cadena_ids["exp_sigas"]:
            binds = ", ".join(f":es{i}" for i in range(len(cadena_ids["exp_sigas"])))
            p = {f"es{i}": v for i, v in enumerate(cadena_ids["exp_sigas"])}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC})
            expedientes = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
                        SELECT e.EXP_SIGA, e.TIPO_PPTO, e.TIPO_FASE,
                               e.EXP_SIAF, e.ESTADO_SIAF,
                               e.FECHA_EXP_SIGA, e.FECHA_DOCUMENTO, e.FECHA_SIAF,
                               -- Fecha de interfase al SIAF (compromiso). Es la
                               -- misma senal que usa el kanban: el compromiso se
                               -- hizo aunque SIAF aun no devuelva EXP_SIAF /
                               -- FECHA_SIAF (caso 1005/S). Sin esto el detalle
                               -- subcuenta la etapa 10 respecto al kanban.
                               doc.FECHA_INTERFASE
                        FROM SIG_EXP_SIGA e
                        LEFT JOIN (
                            SELECT ANO_EJE, SEC_EJEC, EXP_SIGA,
                                   MIN(FECHA_INTERFASE) AS FECHA_INTERFASE
                            FROM SIG_EXP_SIGA_DOCU
                            WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
                              AND FECHA_INTERFASE IS NOT NULL
                            GROUP BY ANO_EJE, SEC_EJEC, EXP_SIGA
                        ) doc
                            ON doc.ANO_EJE = e.ANO_EJE
                           AND doc.SEC_EJEC = e.SEC_EJEC
                           AND doc.EXP_SIGA = e.EXP_SIGA
                        WHERE e.ANO_EJE = :ano AND e.SEC_EJEC = :sec_ejec
                          AND e.EXP_SIGA IN ({binds})
                        ORDER BY e.EXP_SIGA
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        conformidades: list[dict[str, Any]] = []
        nro_ordenes = [o["NRO_ORDEN"] for o in ordenes_list]
        if nro_ordenes:
            binds = ", ".join(f":no{i}" for i in range(len(nro_ordenes)))
            p = {f"no{i}": v for i, v in enumerate(nro_ordenes)}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC, "tipo": tipo_bien})
            conformidades = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
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
                        WHERE cf.ANO_ORDEN = :ano AND cf.SEC_EJEC = :sec_ejec
                          AND cf.TIPO_BIEN = :tipo
                          AND cf.NRO_ORDEN IN ({binds})
                        ORDER BY cf.FECHA_MOVIMTO DESC
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        movimientos_almacen: list[dict[str, Any]] = []
        if tipo_bien == "B":
            movimientos_almacen = [
                dict(r) for r in conn.execute(
                    text(
                        """
                        SELECT DISTINCT
                            ma.NRO_MOVIMTO, ma.NRO_ORDEN, ma.TIPO_MOVIMTO,
                            ma.TIPO_TRANSAC, ma.TIPO_PPTO,
                            ma.FECHA_MOVIMTO,
                            LTRIM(RTRIM(ma.NRO_GUIA))       AS nro_guia
                        FROM SIG_MOVIM_ALMACEN ma
                        INNER JOIN SIG_DETALLE_PEDIDOS dp
                            ON dp.ANO_EJE = ma.ANO_EJE AND dp.SEC_EJEC = ma.SEC_EJEC
                           AND dp.TIPO_BIEN = ma.TIPO_BIEN
                           AND dp.NRO_PECOSA = ma.NRO_MOVIMTO
                        WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                          AND dp.NRO_PEDIDO = :nro AND dp.TIPO_BIEN = :tipo
                          AND dp.NRO_PECOSA > 0
                        ORDER BY ma.FECHA_MOVIMTO
                        """
                    ),
                    params,
                ).mappings().all()
            ]

    # Campos de la cascada de confianza: el timeline los necesita para saber
    # si las etapas 4-7 son de ESTE pedido o avance del grupo (§4). Sin esto
    # el detalle pintaria verdes ajenos, que es el bug que §7 describe.
    tipo_pedido = str(cab["TIPO_PEDIDO"] or "").strip()
    ctx = contexto_pedido_bolsa(ano, tipo_bien, tipo_pedido, nro_pedido) or {}
    candidatos = frozenset(ctx.get("candidatos") or ())

    # Etapas 4-7 (programacion): solo se ven por la cadena del CCMN, y este
    # `obtener_pedido` construye la cadena hacia abajo DESDE la orden. Un pedido
    # que llego al estudio de mercado pero no tiene orden aun no traeria ninguna
    # de estas etapas, y el detalle se cortaba en "cuadro de necesidad" aunque
    # el estudio de mercado ya existiera (caso 311/S). Estos flags miran la
    # cadena hacia ARRIBA, igual que el kanban, para que el detalle coincida.
    prog = _flags_programacion(ano, tipo_bien, tipo_pedido, nro_pedido)

    return {
        **dict(cab),
        **prog,
        "n_candidatos_ccmn": len(candidatos),
        "ccmn_candidatos": candidatos,
        "ccmn_declarado_orden": ctx.get("ccmn_declarado_orden"),
        "ccmn_declarado_cert": ctx.get("ccmn_declarado_cert"),
        "ccmn_manual": None,  # lo inyecta el router desde Postgres
        "sec_cua_mod_sal": (ctx.get("bolsas") or [None])[0],
        "items": [dict(i) for i in items],
        "ordenes": ordenes_list,
        "cuadros": cuadros,
        "certificaciones": certificaciones,
        "expedientes": expedientes,
        "conformidades": conformidades,
        "movimientos_almacen": movimientos_almacen,
    }
