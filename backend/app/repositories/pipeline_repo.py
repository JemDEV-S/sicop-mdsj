"""Repositorio SIGA: pipeline de pedidos con 13 etapas para servicios y 16 para bienes.

Ver:
    - Docs/exploracion-siga-pipeline-extendido.md §16 (puente CMN, mapa final)
    - Docs/exploracion-siga-pipeline-extendido.md §17 (pipeline bienes con pecosa)

Cadena estructural (FK real o composite verificado en 232/S y 005/B):

    [1]  SIG_PEDIDOS.ESTADO='0'                                 -> pedido registrado
    [2]  SIG_PEDIDOS.ESTADO='1' AND FECHA_APROB IS NOT NULL     -> pedido aprobado
    [3]  SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL IS NOT NULL        -> cuadro necesidad
    [4]  SIG_CUADRO_MODIFICADO_CMN (puente pedido<->PAAC)       -> CCMN candidato
    [5]  SIG_PAAC_CONSOLIDADO.NRO_CONSOLID                      -> CCMN / EM(CVR)
    [6]  SIG_SOLICITUD_COTIZACION.NRO_CONSOLID                  -> cotizacion
    [7]  SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC                   -> cuadro adquisicion
    [8]  SIG_CERTIFICACION.NRO_CERTIFICA_SIAF IS NOT NULL       -> CCP
    [9]  SIG_ORDEN_ADQUISICION matcheada                        -> orden emitida
    [10] SIG_EXP_SIGA_DOCU.FECHA_INTERFASE IS NOT NULL          -> compromiso / SIAF
    [11] S: SIG_MOVIM_CONFOR_SERVICIO   B: SIG_MOVIM_ALMACEN(I,1)  -> ejecucion
    [12] SIG_MOVIM_ALMACEN(R,1)   solo B                        -> recepcion kardex
    [13] SIG_PEDIDOS TIPO_PEDIDO=1 misma meta+cc     solo B     -> pedido interno
    [14] SIG_MOVIM_ALMACEN(S,1) + NRO_PECOSA         solo B     -> despacho pecosa
    [15] S: TOTAL_FACT_SOLES cubierto      B: EXP fase D        -> devengado
    [16] SIG_PEDIDOS.ESTADO='7' OR SIG_SEGUIMIENTO t=19         -> cierre

Match pedido<->orden (sin FK):
    - Bienes con NRO_PECOSA>0: llave dura via SIG_MOVIM_ALMACEN.NRO_MOVIMTO
    - Resto: composite (SEC_FUNC + CLASIFICADOR + item + VALOR_SOLES)

Filtro por CC del usuario (RN-04) via SIG_PEDIDOS.CENTRO_COSTO IN (...).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


def _bind_centros(centros: list[str]) -> tuple[str, dict[str, str]]:
    binds = [f":cc{i}" for i in range(len(centros))]
    params = {f"cc{i}": c for i, c in enumerate(centros)}
    return ", ".join(binds), params


# ─── Query principal del kanban ──────────────────────────────────────────
#
# Emite UNA fila por pedido con flags de evidencia para cada una de las 16
# etapas. La clasificacion final (etapa maxima alcanzada) la hace el service.
# Cada rama es LEFT JOIN + agregada para evitar explosion de filas.

_SQL_KANBAN = """
WITH pedidos_base AS (
    SELECT
        p.ANO_EJE, p.SEC_EJEC, p.NRO_PEDIDO, p.TIPO_BIEN, p.TIPO_PEDIDO,
        p.ESTADO                                              AS estado_pedido,
        p.CENTRO_COSTO, p.sec_func,
        p.FECHA_PEDIDO, p.FECHA_APROB, p.FECHA_ATENC,
        LTRIM(RTRIM(CAST(p.MOTIVO_PEDIDO AS VARCHAR(500))))   AS motivo,
        LTRIM(RTRIM(p.NOMBRE_EMPLEADO))                       AS solicitante,
        LTRIM(RTRIM(p.FUENTE_FINANC))                         AS fuente_financ
    FROM SIG_PEDIDOS p
    WHERE p.ANO_EJE = :ano
      AND p.SEC_EJEC = :sec_ejec
      -- ESTADO=0 son "en proceso" reales (no borradores puros), ver §4.2 handoff.
      AND p.ESTADO IN ('0', '1', '7')
      {filtro_cc}
),
-- Cada item del pedido con los atributos del composite (para match a orden).
det AS (
    SELECT
        pb.ANO_EJE, pb.SEC_EJEC, pb.NRO_PEDIDO, pb.TIPO_BIEN, pb.TIPO_PEDIDO,
        dp.SECUENCIA,
        dp.NRO_PECOSA,
        dp.NRO_ORDEN                                          AS nro_orden_declarado,
        dp.SEC_CUA_MOD_SAL,
        dp.ESTADO_CONFOR,
        pb.sec_func                                           AS sec_func_item,
        LTRIM(RTRIM(dp.CLASIFICADOR))                         AS clasificador,
        LTRIM(RTRIM(dp.GRUPO_BIEN))                           AS grupo_bien,
        LTRIM(RTRIM(dp.CLASE_BIEN))                           AS clase_bien,
        LTRIM(RTRIM(dp.FAMILIA_BIEN))                         AS familia_bien,
        LTRIM(RTRIM(dp.ITEM_BIEN))                            AS item_bien,
        COALESCE(dp.VALOR_TOTAL, 0)                           AS valor_soles
    FROM pedidos_base pb
    LEFT JOIN SIG_DETALLE_PEDIDOS dp
        ON dp.ANO_EJE = pb.ANO_EJE
       AND dp.SEC_EJEC = pb.SEC_EJEC
       AND dp.TIPO_BIEN = pb.TIPO_BIEN
       AND dp.NRO_PEDIDO = pb.NRO_PEDIDO
),
-- [3][4][5] Cadena programacion via puente SIG_CUADRO_MODIFICADO_CMN.
-- Un mismo SEC_CUA_MOD_SAL puede tener N CCMN (§16.1) -- agrupamos por pedido.
programacion AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO,
        MAX(CASE WHEN d.SEC_CUA_MOD_SAL IS NOT NULL THEN 1 ELSE 0 END) AS tiene_cuadro_neces,
        MAX(CASE WHEN cmn.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END)  AS tiene_puente_paac,
        MAX(CASE WHEN pc.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END)   AS tiene_ccmn,
        MIN(pc.NRO_CONSOLID)                                            AS nro_consolid_muestra,
        MIN(pc.NRO_EST_MDO)                                             AS nro_est_mdo_muestra,
        MIN(pc.NRO_CERTIFICA)                                           AS nro_certifica_via_paac,
        MAX(pc.FECHA_CONS)                                              AS fecha_ccmn,
        -- Nº de CCMN candidatos de la bolsa. 1 => nivel `unico`; >1 => ambiguo
        -- salvo que una fuente declarativa resuelva. Ver §4 del doc de refactorizacion.
        COUNT(DISTINCT cmn.NRO_CONSOLID)                                AS n_candidatos_ccmn
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
    GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO
),
-- [6] Cotizacion: hay solicitud para algun CCMN del pedido.
cotizacion AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO,
        MAX(CASE WHEN sc.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END) AS tiene_cotizacion
    FROM det d
    LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
        ON cmn.SEC_EJEC = d.SEC_EJEC
       AND cmn.ANNO_EJEC = d.ANO_EJE
       AND cmn.SEC_CUA_MOD_SAL = d.SEC_CUA_MOD_SAL
       AND cmn.TIPO_BIEN = d.TIPO_BIEN
    LEFT JOIN SIG_SOLICITUD_COTIZACION sc
        ON sc.ANO_EJE = cmn.ANNO_EJEC
       AND sc.SEC_EJEC = cmn.SEC_EJEC
       AND sc.tipo_bien = cmn.TIPO_BIEN
       AND sc.NRO_CONSOLID = cmn.NRO_CONSOLID
    GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO
),
-- [7] Cuadro de adquisicion: FK dura via NRO_CONS_PAAC.
cuadro_adq AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO,
        MAX(CASE WHEN ca.SEC_CUADRO IS NOT NULL THEN 1 ELSE 0 END) AS tiene_cuadro_adq,
        MIN(ca.SEC_CUADRO)                                          AS sec_cuadro_muestra,
        MAX(ca.FECHA_CUADRO)                                        AS fecha_cuadro_adq
    FROM det d
    LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
        ON cmn.SEC_EJEC = d.SEC_EJEC
       AND cmn.ANNO_EJEC = d.ANO_EJE
       AND cmn.SEC_CUA_MOD_SAL = d.SEC_CUA_MOD_SAL
       AND cmn.TIPO_BIEN = d.TIPO_BIEN
    LEFT JOIN SIG_CUADRO_ADQUISICION ca
        ON ca.ANO_EJE = cmn.ANNO_EJEC
       AND ca.SEC_EJEC = cmn.SEC_EJEC
       AND ca.TIPO_BIEN = cmn.TIPO_BIEN
       AND ca.NRO_CONS_PAAC = cmn.NRO_CONSOLID
    GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO
),
-- [8] Certificacion CCP (SIGA -> SIAF). Se llega desde la cabecera PAAC.
certificacion AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO,
        MAX(CASE WHEN c.NRO_CERTIFICA IS NOT NULL THEN 1 ELSE 0 END)         AS tiene_certificacion,
        MAX(CASE WHEN c.NRO_CERTIFICA_SIAF IS NOT NULL THEN 1 ELSE 0 END)    AS tiene_ccp_siaf,
        MIN(c.NRO_CERTIFICA)                                                  AS nro_certifica_muestra,
        MIN(c.NRO_CERTIFICA_SIAF)                                             AS nro_certifica_siaf_muestra,
        MAX(c.FECHA)                                                          AS fecha_certificacion
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
    LEFT JOIN SIG_CERTIFICACION c
        ON c.ANO_EJE = pc.ANO_EJE
       AND c.SEC_EJEC = pc.SEC_EJEC
       AND c.NRO_CERTIFICA = pc.NRO_CERTIFICA
    GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO
),
-- [9] Orden emitida: llave dura pecosa (bienes) o composite.
match_pecosa AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO, d.SECUENCIA,
        MIN(ma.NRO_ORDEN) AS nro_orden
    FROM det d
    INNER JOIN SIG_MOVIM_ALMACEN ma
        ON ma.ANO_EJE = d.ANO_EJE
       AND ma.SEC_EJEC = d.SEC_EJEC
       AND ma.TIPO_BIEN = d.TIPO_BIEN
       AND ma.NRO_MOVIMTO = d.NRO_PECOSA
    WHERE d.TIPO_BIEN = 'B' AND d.NRO_PECOSA > 0
    GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO, d.SECUENCIA
),
match_composite AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO, d.SECUENCIA,
        MIN(oi.NRO_ORDEN) AS nro_orden
    FROM det d
    LEFT JOIN match_pecosa mp
        ON mp.ANO_EJE = d.ANO_EJE AND mp.SEC_EJEC = d.SEC_EJEC
       AND mp.NRO_PEDIDO = d.NRO_PEDIDO AND mp.TIPO_BIEN = d.TIPO_BIEN
       AND mp.TIPO_PEDIDO = d.TIPO_PEDIDO
       AND mp.SECUENCIA = d.SECUENCIA
    INNER JOIN SIG_ORDEN_ITEM oi
        ON oi.ANO_EJE = d.ANO_EJE
       AND oi.SEC_EJEC = d.SEC_EJEC
       AND oi.TIPO_BIEN = d.TIPO_BIEN
       AND LTRIM(RTRIM(oi.GRUPO_BIEN)) = d.grupo_bien
       AND LTRIM(RTRIM(oi.CLASE_BIEN)) = d.clase_bien
       AND LTRIM(RTRIM(oi.FAMILIA_BIEN)) = d.familia_bien
       AND LTRIM(RTRIM(oi.ITEM_BIEN)) = d.item_bien
    INNER JOIN SIG_ORDEN_ITEM_PPTO op
        ON op.ANO_EJE = oi.ANO_EJE
       AND op.SEC_EJEC = oi.SEC_EJEC
       AND op.NRO_ORDEN = oi.NRO_ORDEN
       AND op.TIPO_BIEN = oi.TIPO_BIEN
       AND op.TIPO_PPTO = oi.TIPO_PPTO
       AND op.SEC_ORDEN = oi.SEC_ORDEN
       AND op.SEC_ITEM = oi.SEC_ITEM
       AND op.SEC_FUNC = d.sec_func_item
       AND LTRIM(RTRIM(op.CLASIFICADOR)) = d.clasificador
       AND (d.valor_soles = 0 OR ROUND(op.VALOR_SOLES, 2) = ROUND(d.valor_soles, 2))
    WHERE mp.nro_orden IS NULL
    GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO, d.SECUENCIA
),
-- Orden final por item con marca de metodo.
det_matched AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO, d.SECUENCIA,
        d.NRO_PECOSA, d.ESTADO_CONFOR, d.valor_soles,
        COALESCE(mp.nro_orden, mc.nro_orden, NULLIF(d.nro_orden_declarado, 0)) AS nro_orden_final,
        CASE
            WHEN mp.nro_orden IS NOT NULL             THEN 'pecosa'
            WHEN mc.nro_orden IS NOT NULL             THEN 'composite'
            WHEN d.nro_orden_declarado > 0            THEN 'declarado'
            ELSE NULL
        END AS match_metodo
    FROM det d
    LEFT JOIN match_pecosa mp
        ON mp.ANO_EJE = d.ANO_EJE AND mp.SEC_EJEC = d.SEC_EJEC
       AND mp.NRO_PEDIDO = d.NRO_PEDIDO AND mp.TIPO_BIEN = d.TIPO_BIEN
       AND mp.TIPO_PEDIDO = d.TIPO_PEDIDO
       AND mp.SECUENCIA = d.SECUENCIA
    LEFT JOIN match_composite mc
        ON mc.ANO_EJE = d.ANO_EJE AND mc.SEC_EJEC = d.SEC_EJEC
       AND mc.NRO_PEDIDO = d.NRO_PEDIDO AND mc.TIPO_BIEN = d.TIPO_BIEN
       AND mc.TIPO_PEDIDO = d.TIPO_PEDIDO
       AND mc.SECUENCIA = d.SECUENCIA
),
-- [9][10][15-bienes] Datos de la orden + expediente + interfase SIAF.
orden_enriquecida AS (
    SELECT
        dm.ANO_EJE, dm.SEC_EJEC, dm.NRO_PEDIDO, dm.TIPO_BIEN, dm.TIPO_PEDIDO, dm.SECUENCIA,
        dm.NRO_PECOSA, dm.ESTADO_CONFOR, dm.valor_soles,
        dm.nro_orden_final, dm.match_metodo,
        o.EXP_SIAF, o.EXP_SIGA, o.TOTAL_FACT_SOLES,
        o.FECHA_ORDEN,
        exd.FECHA_INTERFASE,
        MAX(CASE WHEN LTRIM(RTRIM(exd.TIPO_OPERACION)) = 'DV'
                 THEN 1 ELSE 0 END) OVER (
            PARTITION BY dm.ANO_EJE, dm.SEC_EJEC, dm.NRO_PEDIDO, dm.TIPO_BIEN,
                         dm.TIPO_PEDIDO
        ) AS tiene_devengado_exp
    FROM det_matched dm
    LEFT JOIN SIG_ORDEN_ADQUISICION o
        ON o.ANO_EJE = dm.ANO_EJE
       AND o.SEC_EJEC = dm.SEC_EJEC
       AND o.TIPO_BIEN = dm.TIPO_BIEN
       AND o.NRO_ORDEN = dm.nro_orden_final
    LEFT JOIN SIG_EXP_SIGA_DOCU exd
        ON exd.ANO_EJE = o.ANO_EJE
       AND exd.SEC_EJEC = o.SEC_EJEC
       AND exd.EXP_SIGA = o.EXP_SIGA
),
-- [11] Servicios: conformidades SIG_MOVIM_CONFOR_SERVICIO por orden.
--       Bienes: entrada al almacen (I,1) por orden (excluye kardex R).
ejecucion AS (
    SELECT
        oe.ANO_EJE, oe.SEC_EJEC, oe.NRO_PEDIDO, oe.TIPO_BIEN, oe.TIPO_PEDIDO,
        MAX(CASE
            WHEN oe.TIPO_BIEN = 'S' AND cf.NRO_ORDEN IS NOT NULL      THEN 1
            WHEN oe.TIPO_BIEN = 'B' AND ma_i.NRO_MOVIMTO IS NOT NULL  THEN 1
            ELSE 0
        END)                                                          AS tiene_ejecucion,
        MAX(CASE WHEN ma_r.NRO_MOVIMTO IS NOT NULL THEN 1 ELSE 0 END) AS tiene_kardex,
        -- Suma facturada acumulada por orden (para umbral devengado servicio).
        SUM(COALESCE(cf.n_confor, 0))                                 AS n_conformidades_srv,
        -- Última fecha de movimiento (conformidad para S, entrada al almacén para B).
        MAX(COALESCE(cf.ultima_fecha_confor, ma_i.FECHA_MOVIMTO))     AS fecha_ejecucion,
        MAX(ma_r.FECHA_MOVIMTO)                                       AS fecha_kardex
    FROM orden_enriquecida oe
    LEFT JOIN (
        SELECT ANO_ORDEN, SEC_EJEC, TIPO_BIEN, NRO_ORDEN,
               COUNT(*)               AS n_confor,
               MAX(FECHA_MOVIMTO)     AS ultima_fecha_confor
        FROM SIG_MOVIM_CONFOR_SERVICIO
        WHERE ANO_ORDEN = :ano AND SEC_EJEC = :sec_ejec
        GROUP BY ANO_ORDEN, SEC_EJEC, TIPO_BIEN, NRO_ORDEN
    ) cf ON cf.ANO_ORDEN = oe.ANO_EJE AND cf.SEC_EJEC = oe.SEC_EJEC
        AND cf.TIPO_BIEN = oe.TIPO_BIEN AND cf.NRO_ORDEN = oe.nro_orden_final
    LEFT JOIN SIG_MOVIM_ALMACEN ma_i
        ON ma_i.ANO_EJE = oe.ANO_EJE
       AND ma_i.SEC_EJEC = oe.SEC_EJEC
       AND ma_i.TIPO_BIEN = oe.TIPO_BIEN
       AND ma_i.NRO_ORDEN = oe.nro_orden_final
       AND ma_i.TIPO_MOVIMTO = 'I' AND ma_i.TIPO_TRANSAC = 1
    LEFT JOIN SIG_MOVIM_ALMACEN ma_r
        ON ma_r.ANO_EJE = oe.ANO_EJE
       AND ma_r.SEC_EJEC = oe.SEC_EJEC
       AND ma_r.TIPO_BIEN = oe.TIPO_BIEN
       AND ma_r.NRO_ORDEN = oe.nro_orden_final
       AND ma_r.TIPO_MOVIMTO = 'R' AND ma_r.TIPO_TRANSAC = 1
    GROUP BY oe.ANO_EJE, oe.SEC_EJEC, oe.NRO_PEDIDO, oe.TIPO_BIEN, oe.TIPO_PEDIDO
),
-- [13] Pedido interno (TIPO_PEDIDO=1) que consume lo comprado.
--      Se detecta si existe otro pedido con misma meta+CC y fecha posterior.
pedido_interno AS (
    SELECT
        pb.ANO_EJE, pb.SEC_EJEC, pb.NRO_PEDIDO, pb.TIPO_BIEN, pb.TIPO_PEDIDO,
        MAX(CASE WHEN pi2.NRO_PEDIDO IS NOT NULL THEN 1 ELSE 0 END) AS tiene_pedido_interno
    FROM pedidos_base pb
    LEFT JOIN SIG_PEDIDOS pi2
        ON pi2.ANO_EJE = pb.ANO_EJE
       AND pi2.SEC_EJEC = pb.SEC_EJEC
       AND pi2.TIPO_BIEN = pb.TIPO_BIEN
       AND pi2.TIPO_PEDIDO = '1'
       AND pi2.sec_func = pb.sec_func
       AND pi2.CENTRO_COSTO = pb.CENTRO_COSTO
       AND pi2.FECHA_PEDIDO >= pb.FECHA_PEDIDO
       AND pi2.NRO_PEDIDO <> pb.NRO_PEDIDO
    WHERE pb.TIPO_BIEN = 'B' AND pb.TIPO_PEDIDO = '2'
    GROUP BY pb.ANO_EJE, pb.SEC_EJEC, pb.NRO_PEDIDO, pb.TIPO_BIEN, pb.TIPO_PEDIDO
),
-- [14] Despacho / pecosa: SIG_MOVIM_ALMACEN (S,1) con NRO_PECOSA del detalle.
pecosa AS (
    SELECT
        d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO,
        MAX(CASE WHEN ma.NRO_MOVIMTO IS NOT NULL THEN 1 ELSE 0 END) AS tiene_pecosa,
        MAX(ma.FECHA_MOVIMTO)                                        AS fecha_pecosa
    FROM det d
    LEFT JOIN SIG_MOVIM_ALMACEN ma
        ON ma.ANO_EJE = d.ANO_EJE
       AND ma.SEC_EJEC = d.SEC_EJEC
       AND ma.TIPO_BIEN = d.TIPO_BIEN
       AND ma.NRO_MOVIMTO = d.NRO_PECOSA
       AND ma.TIPO_MOVIMTO = 'S' AND ma.TIPO_TRANSAC = 1
    WHERE d.TIPO_BIEN = 'B' AND d.NRO_PECOSA > 0
    GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN, d.TIPO_PEDIDO
),
-- [16] Cierre: ESTADO='7' o rastro en SIG_SEGUIMIENTO t=19.
cierre AS (
    SELECT
        pb.ANO_EJE, pb.SEC_EJEC, pb.NRO_PEDIDO, pb.TIPO_BIEN, pb.TIPO_PEDIDO,
        MAX(CASE WHEN pb.estado_pedido = '7' THEN 1
                 WHEN sg.NRO_PEDIDO IS NOT NULL THEN 1 ELSE 0 END) AS tiene_cierre,
        MAX(sg.FECHA_TRANSACCION)                                   AS fecha_cierre_seg
    FROM pedidos_base pb
    LEFT JOIN SIG_SEGUIMIENTO sg
        ON sg.ANO_EJE = pb.ANO_EJE
       AND sg.SEC_EJEC = pb.SEC_EJEC
       AND sg.TIPO_BIEN = pb.TIPO_BIEN
       AND sg.TIPO_TRANSACCION = 19
       AND TRY_CAST(sg.NRO_PEDIDO AS INT) = pb.NRO_PEDIDO
    GROUP BY pb.ANO_EJE, pb.SEC_EJEC, pb.NRO_PEDIDO, pb.TIPO_BIEN, pb.TIPO_PEDIDO
),
-- Agregacion por pedido de todas las evidencias + valor total.
agrup AS (
    SELECT
        pb.ANO_EJE, pb.SEC_EJEC, pb.NRO_PEDIDO, pb.TIPO_BIEN, pb.TIPO_PEDIDO,
        pb.estado_pedido, pb.CENTRO_COSTO, pb.sec_func,
        pb.FECHA_PEDIDO, pb.FECHA_APROB, pb.FECHA_ATENC,
        pb.motivo, pb.solicitante, pb.fuente_financ,
        COALESCE(pg.tiene_cuadro_neces, 0)                    AS tiene_cuadro_neces,
        COALESCE(pg.tiene_puente_paac, 0)                     AS tiene_puente_paac,
        COALESCE(pg.tiene_ccmn, 0)                            AS tiene_ccmn,
        COALESCE(cot.tiene_cotizacion, 0)                     AS tiene_cotizacion,
        COALESCE(cad.tiene_cuadro_adq, 0)                     AS tiene_cuadro_adq,
        COALESCE(cer.tiene_certificacion, 0)                  AS tiene_certificacion,
        COALESCE(cer.tiene_ccp_siaf, 0)                       AS tiene_ccp_siaf,
        MAX(CASE WHEN oe.nro_orden_final IS NOT NULL THEN 1 ELSE 0 END) AS tiene_orden,
        MAX(CASE WHEN oe.FECHA_INTERFASE IS NOT NULL THEN 1 ELSE 0 END) AS tiene_compromiso,
        COALESCE(ej.tiene_ejecucion, 0)                       AS tiene_ejecucion,
        COALESCE(ej.tiene_kardex, 0)                          AS tiene_kardex,
        COALESCE(pin.tiene_pedido_interno, 0)                 AS tiene_pedido_interno,
        COALESCE(pec.tiene_pecosa, 0)                         AS tiene_pecosa,
        -- Devengado: para bienes usamos EXP fase DV; para servicios,
        -- cuando la sumatoria facturada cubre el TOTAL_FACT_SOLES de la orden.
        MAX(CASE
            WHEN pb.TIPO_BIEN = 'B' AND oe.tiene_devengado_exp = 1 THEN 1
            WHEN pb.TIPO_BIEN = 'S' AND COALESCE(ej.n_conformidades_srv, 0) >= 1
                 -- Sin datos de MNTO_FACT por conformidad, aproximamos con "hay
                 -- al menos una conformidad" para ejecucion; el devengado real
                 -- vendra del Fix #2 SIAF. Aqui no se marca todavia.
                 THEN 0
            ELSE 0
        END)                                                  AS tiene_devengado,
        COALESCE(cie.tiene_cierre, 0)                         AS tiene_cierre,
        SUM(COALESCE(oe.valor_soles, 0))                      AS monto_total,
        COUNT(oe.SECUENCIA)                                   AS items,
        MIN(pg.nro_consolid_muestra)                          AS nro_consolid_muestra,
        MIN(pg.nro_est_mdo_muestra)                           AS nro_est_mdo_muestra,
        MAX(COALESCE(pg.n_candidatos_ccmn, 0))                AS n_candidatos_ccmn,
        MAX(oe.nro_orden_final)                               AS nro_orden_muestra,
        MAX(oe.EXP_SIAF)                                      AS exp_siaf_muestra,
        MAX(oe.EXP_SIGA)                                      AS exp_siga_muestra,
        MIN(cad.sec_cuadro_muestra)                           AS sec_cuadro_muestra,
        MIN(cer.nro_certifica_muestra)                        AS nro_certifica_muestra,
        MIN(cer.nro_certifica_siaf_muestra)                   AS nro_certifica_siaf_muestra,
        MAX(oe.match_metodo)                                  AS match_metodo,
        -- Fechas por etapa (para calcular dias_en_etapa correctamente en el service).
        MAX(pg.fecha_ccmn)                                    AS fecha_ccmn,
        MAX(cad.fecha_cuadro_adq)                             AS fecha_cuadro_adq,
        MAX(cer.fecha_certificacion)                          AS fecha_certificacion,
        MAX(oe.FECHA_ORDEN)                                   AS fecha_orden,
        MAX(oe.FECHA_INTERFASE)                               AS fecha_compromiso,
        MAX(ej.fecha_ejecucion)                               AS fecha_ejecucion,
        MAX(ej.fecha_kardex)                                  AS fecha_kardex,
        MAX(pec.fecha_pecosa)                                 AS fecha_pecosa,
        MAX(cie.fecha_cierre_seg)                             AS fecha_cierre_seg
    FROM pedidos_base pb
    LEFT JOIN programacion pg
        ON pg.ANO_EJE = pb.ANO_EJE AND pg.SEC_EJEC = pb.SEC_EJEC
       AND pg.NRO_PEDIDO = pb.NRO_PEDIDO AND pg.TIPO_BIEN = pb.TIPO_BIEN
       AND pg.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN cotizacion cot
        ON cot.ANO_EJE = pb.ANO_EJE AND cot.SEC_EJEC = pb.SEC_EJEC
       AND cot.NRO_PEDIDO = pb.NRO_PEDIDO AND cot.TIPO_BIEN = pb.TIPO_BIEN
       AND cot.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN cuadro_adq cad
        ON cad.ANO_EJE = pb.ANO_EJE AND cad.SEC_EJEC = pb.SEC_EJEC
       AND cad.NRO_PEDIDO = pb.NRO_PEDIDO AND cad.TIPO_BIEN = pb.TIPO_BIEN
       AND cad.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN certificacion cer
        ON cer.ANO_EJE = pb.ANO_EJE AND cer.SEC_EJEC = pb.SEC_EJEC
       AND cer.NRO_PEDIDO = pb.NRO_PEDIDO AND cer.TIPO_BIEN = pb.TIPO_BIEN
       AND cer.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN orden_enriquecida oe
        ON oe.ANO_EJE = pb.ANO_EJE AND oe.SEC_EJEC = pb.SEC_EJEC
       AND oe.NRO_PEDIDO = pb.NRO_PEDIDO AND oe.TIPO_BIEN = pb.TIPO_BIEN
       AND oe.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN ejecucion ej
        ON ej.ANO_EJE = pb.ANO_EJE AND ej.SEC_EJEC = pb.SEC_EJEC
       AND ej.NRO_PEDIDO = pb.NRO_PEDIDO AND ej.TIPO_BIEN = pb.TIPO_BIEN
       AND ej.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN pedido_interno pin
        ON pin.ANO_EJE = pb.ANO_EJE AND pin.SEC_EJEC = pb.SEC_EJEC
       AND pin.NRO_PEDIDO = pb.NRO_PEDIDO AND pin.TIPO_BIEN = pb.TIPO_BIEN
       AND pin.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN pecosa pec
        ON pec.ANO_EJE = pb.ANO_EJE AND pec.SEC_EJEC = pb.SEC_EJEC
       AND pec.NRO_PEDIDO = pb.NRO_PEDIDO AND pec.TIPO_BIEN = pb.TIPO_BIEN
       AND pec.TIPO_PEDIDO = pb.TIPO_PEDIDO
    LEFT JOIN cierre cie
        ON cie.ANO_EJE = pb.ANO_EJE AND cie.SEC_EJEC = pb.SEC_EJEC
       AND cie.NRO_PEDIDO = pb.NRO_PEDIDO AND cie.TIPO_BIEN = pb.TIPO_BIEN
       AND cie.TIPO_PEDIDO = pb.TIPO_PEDIDO
    GROUP BY
        pb.ANO_EJE, pb.SEC_EJEC, pb.NRO_PEDIDO, pb.TIPO_BIEN, pb.TIPO_PEDIDO,
        pb.estado_pedido, pb.CENTRO_COSTO, pb.sec_func,
        pb.FECHA_PEDIDO, pb.FECHA_APROB, pb.FECHA_ATENC,
        pb.motivo, pb.solicitante, pb.fuente_financ,
        pg.tiene_cuadro_neces, pg.tiene_puente_paac, pg.tiene_ccmn,
        cot.tiene_cotizacion, cad.tiene_cuadro_adq,
        cer.tiene_certificacion, cer.tiene_ccp_siaf,
        ej.tiene_ejecucion, ej.tiene_kardex,
        pin.tiene_pedido_interno, pec.tiene_pecosa, cie.tiene_cierre
)
SELECT * FROM agrup
ORDER BY FECHA_PEDIDO DESC
"""


def pipeline_pedidos_raw(
    ano: int,
    centros: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Devuelve una lista de pedidos con los flags de evidencia de las 16 etapas.

    La clasificacion a etapa maxima alcanzada + macrofase se hace en el
    service (para poder testearlo sin BD).
    """
    if centros is not None and len(centros) == 0:
        return []

    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}

    if centros is not None:
        binds_sql, binds_params = _bind_centros(centros)
        filtro_cc = f"AND p.CENTRO_COSTO IN ({binds_sql})"
        params.update(binds_params)
    else:
        filtro_cc = ""

    sql = _SQL_KANBAN.format(filtro_cc=filtro_cc)

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    return [dict(r) for r in rows]


# ─── Detalle de un pedido con la cadena completa ─────────────────────────


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
                    dp.VALOR_TOTAL,
                    LTRIM(RTRIM(dp.CLASIFICADOR))   AS clasificador,
                    dp.NRO_ORDEN                    AS nro_orden_declarado,
                    dp.NRO_PECOSA,
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
                        COALESCE(dp.VALOR_TOTAL, 0)                 AS valor_soles
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
                todas AS (
                    SELECT NRO_ORDEN, 'pecosa' AS metodo FROM pecosa
                    UNION SELECT NRO_ORDEN, 'composite' FROM composite
                    UNION SELECT NRO_ORDEN, 'declarado' FROM declarado
                )
                SELECT
                    o.NRO_ORDEN, o.TIPO_BIEN,
                    o.EXP_SIAF, o.EXP_SIGA,
                    o.SEC_CUADRO, o.NRO_CERTIFICA,
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
                               e.FECHA_EXP_SIGA, e.FECHA_DOCUMENTO, e.FECHA_SIAF
                        FROM SIG_EXP_SIGA e
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

    return {
        **dict(cab),
        "items": [dict(i) for i in items],
        "ordenes": ordenes_list,
        "cuadros": cuadros,
        "certificaciones": certificaciones,
        "expedientes": expedientes,
        "conformidades": conformidades,
        "movimientos_almacen": movimientos_almacen,
    }
