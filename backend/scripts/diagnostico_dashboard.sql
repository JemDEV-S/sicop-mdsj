-- ================================================================
-- Diagnóstico de coherencia SIGA para el dashboard T-44
-- Ejecutar en SSMS / Azure Data Studio conectado a SIGA_300687.
-- Cada query es independiente. Pega los resultados de vuelta.
-- ================================================================

-- ─── Q1 · Estado real del pedido 232 (todos los TIPO_BIEN) ─────────────
-- Muestra la cabecera + ítems + orden asociada + si tiene conformidad.
-- Con esto valido si mi lógica de etapa lo clasifica bien.
PRINT '===== Q1 · Pedido 232 - cabeceras =====';
SELECT
    p.ANO_EJE, p.NRO_PEDIDO, p.TIPO_BIEN, p.TIPO_PEDIDO,
    p.ESTADO         AS estado_pedido,
    p.CENTRO_COSTO, p.sec_func,
    p.FECHA_PEDIDO, p.FECHA_APROB, p.FECHA_ATENC,
    LTRIM(RTRIM(CAST(p.MOTIVO_PEDIDO AS VARCHAR(200)))) AS motivo
FROM SIG_PEDIDOS p
WHERE p.SEC_EJEC = 300687
  AND p.ANO_EJE = 2026
  AND p.NRO_PEDIDO = 232
ORDER BY p.TIPO_BIEN;

PRINT '===== Q1.1 · Pedido 232 - detalle ítems =====';
SELECT
    dp.TIPO_BIEN, dp.SECUENCIA, dp.NRO_ORDEN,
    dp.CANT_SOLICITADA, dp.CANT_APROBADA, dp.CANT_ATENDIDA,
    dp.VALOR_TOTAL,
    dp.ESTADO_PED, dp.ESTADO_ATEND, dp.ESTADO_CONFOR, dp.ESTADO_COMPRA,
    dp.FECHA_CONFOR
FROM SIG_DETALLE_PEDIDOS dp
WHERE dp.SEC_EJEC = 300687
  AND dp.ANO_EJE = 2026
  AND dp.NRO_PEDIDO = 232
ORDER BY dp.TIPO_BIEN, dp.SECUENCIA;

PRINT '===== Q1.2 · Pedido 232 - orden(es) asociada(s) =====';
SELECT DISTINCT
    o.NRO_ORDEN, o.TIPO_BIEN, o.ESTADO, o.ESTADO_SIAF,
    o.EXP_SIAF, o.FECHA_ORDEN, o.TOTAL_FACT_SOLES,
    LTRIM(RTRIM(CAST(o.CONCEPTO AS VARCHAR(200)))) AS concepto
FROM SIG_ORDEN_ADQUISICION o
INNER JOIN SIG_DETALLE_PEDIDOS dp
    ON dp.ANO_EJE = o.ANO_EJE AND dp.SEC_EJEC = o.SEC_EJEC
   AND dp.TIPO_BIEN = o.TIPO_BIEN AND dp.NRO_ORDEN = o.NRO_ORDEN
WHERE dp.SEC_EJEC = 300687
  AND dp.ANO_EJE = 2026
  AND dp.NRO_PEDIDO = 232;

PRINT '===== Q1.3 · Pedido 232 - conformidades registradas =====';
SELECT
    cf.NRO_ORDEN, cf.ANO_ORDEN, cf.TIPO_BIEN,
    cf.FECHA_MOVIMTO, cf.INDI_CONFOR, cf.ESTADO_DEVENG,
    cf.EXPEDIENTE_SIAF
FROM SIG_MOVIM_CONFOR_SERVICIO cf
INNER JOIN SIG_DETALLE_PEDIDOS dp
    ON dp.ANO_ORDEN_ORDEN_placeholder = cf.ANO_ORDEN  -- se corrige abajo
WHERE cf.SEC_EJEC = 300687;
-- Nota: si la línea anterior da error de columna, correr en su lugar:
-- SELECT * FROM SIG_MOVIM_CONFOR_SERVICIO WHERE SEC_EJEC=300687 AND EXPEDIENTE_SIAF IN (SELECT EXP_SIAF FROM SIG_ORDEN_ADQUISICION o JOIN SIG_DETALLE_PEDIDOS dp ON dp.NRO_ORDEN=o.NRO_ORDEN AND dp.TIPO_BIEN=o.TIPO_BIEN WHERE dp.NRO_PEDIDO=232 AND dp.ANO_EJE=2026);


-- ─── Q2 · ¿Cuántos pedidos hay realmente en 2026, y en qué estado? ────
PRINT '===== Q2 · Distribución de ESTADO en SIG_PEDIDOS 2026 =====';
SELECT ESTADO, COUNT(*) AS cuantos
FROM SIG_PEDIDOS
WHERE SEC_EJEC = 300687 AND ANO_EJE = 2026
GROUP BY ESTADO
ORDER BY ESTADO;

-- Comparar con lo que devuelve el dashboard (que filtra ESTADO IN ('1','7')).


-- ─── Q3 · Reproducción exacta de la lógica del dashboard ──────────────
-- Este es el query del kanban actual sin filtro por CC (admin).
-- Debería devolver ~N pedidos activos + cerrados. Si sale 0, hay bug.
PRINT '===== Q3 · Kanban admin 2026 - reproducción exacta =====';
WITH pedidos_base AS (
    SELECT
        p.ANO_EJE, p.SEC_EJEC, p.NRO_PEDIDO, p.TIPO_BIEN,
        p.ESTADO AS estado_pedido, p.CENTRO_COSTO
    FROM SIG_PEDIDOS p
    WHERE p.ANO_EJE = 2026
      AND p.SEC_EJEC = 300687
      AND p.ESTADO IN ('1', '7')
),
agrup AS (
    SELECT
        b.NRO_PEDIDO, b.TIPO_BIEN, b.estado_pedido,
        MAX(CASE WHEN dp.NRO_ORDEN IS NOT NULL AND dp.NRO_ORDEN > 0
                 THEN 1 ELSE 0 END) AS tiene_orden,
        MAX(CASE WHEN dp.ESTADO_CONFOR = '1' THEN 1 ELSE 0 END) AS tiene_confor,
        MAX(CASE WHEN o.ESTADO_SIAF = '2' THEN 1 ELSE 0 END) AS esta_devengado,
        COUNT(dp.SECUENCIA) AS items,
        SUM(COALESCE(dp.VALOR_TOTAL, 0)) AS monto_total
    FROM pedidos_base b
    LEFT JOIN SIG_DETALLE_PEDIDOS dp
        ON dp.ANO_EJE = b.ANO_EJE AND dp.SEC_EJEC = b.SEC_EJEC
       AND dp.TIPO_BIEN = b.TIPO_BIEN AND dp.NRO_PEDIDO = b.NRO_PEDIDO
    LEFT JOIN SIG_ORDEN_ADQUISICION o
        ON o.ANO_EJE = dp.ANO_EJE AND o.SEC_EJEC = dp.SEC_EJEC
       AND o.TIPO_BIEN = dp.TIPO_BIEN AND o.NRO_ORDEN = dp.NRO_ORDEN
    GROUP BY b.NRO_PEDIDO, b.TIPO_BIEN, b.estado_pedido
)
SELECT
    CASE
        WHEN estado_pedido = '7'          THEN 'cerrado'
        WHEN esta_devengado = 1           THEN 'devengado'
        WHEN tiene_confor = 1             THEN 'conformidad'
        WHEN tiene_orden = 1              THEN 'con_orden'
        ELSE 'solicitado'
    END AS etapa,
    COUNT(*) AS cuantos_pedidos,
    SUM(monto_total) AS monto_etapa
FROM agrup
GROUP BY
    CASE
        WHEN estado_pedido = '7'          THEN 'cerrado'
        WHEN esta_devengado = 1           THEN 'devengado'
        WHEN tiene_confor = 1             THEN 'conformidad'
        WHEN tiene_orden = 1              THEN 'con_orden'
        ELSE 'solicitado'
    END;


-- ─── Q4 · Totales de saldos que espera ver el admin ───────────────────
PRINT '===== Q4 · SIG_TECHO_PRESUPUESTO 2026 - totales admin =====';
SELECT
    COUNT(DISTINCT t.sec_func)                  AS metas_activas,
    COUNT(*)                                    AS filas_techo,
    SUM(COALESCE(t.PPTO_PIA, 0))                AS pia,
    SUM(COALESCE(t.PPTO_MODIF, 0))              AS pim,
    SUM(COALESCE(t.mnto_acum_cert, 0))          AS certificado,
    SUM(COALESCE(t.mnto_acum_coma, 0))          AS comprometido,
    SUM(COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0))   AS devengado,
    SUM(COALESCE(t.PPTO_DISP_SIAF, 0))          AS saldo_disponible
FROM SIG_TECHO_PRESUPUESTO t
WHERE t.SEC_EJEC = 300687
  AND t.ANO_EJE = 2026
  AND t.PPTO_MODIF > 0;

-- Sanity check: comparar el PIM total con lo que ves en el portal público
-- (ejecución 2026 debería coincidir con la suma agregada de SIAF).


-- ─── Q5 · ¿Los tipos de columna coinciden entre pedidos y órdenes? ────
-- Si esto muestra tipos distintos, hay bug de casting.
PRINT '===== Q5 · Metadatos de columnas críticas =====';
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME IN ('SIG_PEDIDOS', 'SIG_DETALLE_PEDIDOS', 'SIG_ORDEN_ADQUISICION')
  AND COLUMN_NAME IN ('SEC_EJEC', 'ANO_EJE', 'NRO_PEDIDO', 'NRO_ORDEN', 'TIPO_BIEN', 'ESTADO', 'ESTADO_SIAF', 'ESTADO_CONFOR')
ORDER BY TABLE_NAME, COLUMN_NAME;
