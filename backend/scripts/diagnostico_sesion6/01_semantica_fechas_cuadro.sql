-- Semantica de fechas en SIG_CUADRO_ADQUISICION (SEC_EJEC=300687, 2026)
-- Objetivo: decidir que columna representa "cuadro de adquisicion completado".
SET NOCOUNT ON;

-- A. Cobertura y rangos de cada fecha candidata
SELECT 'A_cobertura' AS q,
       COUNT(*) AS filas,
       SUM(CASE WHEN FECHA_CUADRO IS NOT NULL THEN 1 ELSE 0 END) AS con_fecha_cuadro,
       SUM(CASE WHEN FECHA_AUTORIZ IS NOT NULL THEN 1 ELSE 0 END) AS con_fecha_autoriz,
       SUM(CASE WHEN FECHA_COMPRA IS NOT NULL THEN 1 ELSE 0 END) AS con_fecha_compra,
       SUM(CASE WHEN FECHA_NRO_CUADRO IS NOT NULL THEN 1 ELSE 0 END) AS con_fecha_nro_cuadro,
       MIN(FECHA_AUTORIZ) AS min_autoriz, MAX(FECHA_AUTORIZ) AS max_autoriz,
       MIN(FECHA_COMPRA) AS min_compra, MAX(FECHA_COMPRA) AS max_compra,
       MIN(FECHA_NRO_CUADRO) AS min_nro_cuadro, MAX(FECHA_NRO_CUADRO) AS max_nro_cuadro
FROM SIG_CUADRO_ADQUISICION
WHERE ANO_EJE = 2026 AND SEC_EJEC = 300687;

-- B. En las 44 filas donde FECHA_CUADRO SI esta poblada: ¿coincide con las candidatas?
SELECT 'B_concordancia_con_fecha_cuadro' AS q,
       COUNT(*) AS filas,
       SUM(CASE WHEN CAST(FECHA_CUADRO AS date) = CAST(FECHA_AUTORIZ AS date) THEN 1 ELSE 0 END) AS igual_autoriz,
       SUM(CASE WHEN CAST(FECHA_CUADRO AS date) = CAST(FECHA_COMPRA AS date) THEN 1 ELSE 0 END) AS igual_compra,
       SUM(CASE WHEN CAST(FECHA_CUADRO AS date) = CAST(FECHA_NRO_CUADRO AS date) THEN 1 ELSE 0 END) AS igual_nro_cuadro,
       SUM(CASE WHEN FECHA_CUADRO < FECHA_AUTORIZ THEN 1 ELSE 0 END) AS cuadro_antes_autoriz,
       SUM(CASE WHEN FECHA_CUADRO > FECHA_AUTORIZ THEN 1 ELSE 0 END) AS cuadro_despues_autoriz
FROM SIG_CUADRO_ADQUISICION
WHERE ANO_EJE = 2026 AND SEC_EJEC = 300687 AND FECHA_CUADRO IS NOT NULL;

-- C. Relacion entre las tres candidatas entre si
SELECT 'C_relacion_candidatas' AS q,
       COUNT(*) AS filas,
       SUM(CASE WHEN CAST(FECHA_AUTORIZ AS date) = CAST(FECHA_COMPRA AS date) THEN 1 ELSE 0 END) AS autoriz_eq_compra,
       SUM(CASE WHEN FECHA_AUTORIZ < FECHA_COMPRA THEN 1 ELSE 0 END) AS autoriz_antes_compra,
       SUM(CASE WHEN FECHA_AUTORIZ > FECHA_COMPRA THEN 1 ELSE 0 END) AS autoriz_despues_compra,
       SUM(CASE WHEN CAST(FECHA_NRO_CUADRO AS date) = CAST(FECHA_AUTORIZ AS date) THEN 1 ELSE 0 END) AS nrocuadro_eq_autoriz,
       SUM(CASE WHEN FECHA_NRO_CUADRO < FECHA_AUTORIZ THEN 1 ELSE 0 END) AS nrocuadro_antes_autoriz,
       SUM(CASE WHEN FECHA_NRO_CUADRO > FECHA_AUTORIZ THEN 1 ELSE 0 END) AS nrocuadro_despues_autoriz,
       SUM(CASE WHEN CAST(FECHA_NRO_CUADRO AS date) = CAST(FECHA_REG AS date) THEN 1 ELSE 0 END) AS nrocuadro_eq_reg
FROM SIG_CUADRO_ADQUISICION
WHERE ANO_EJE = 2026 AND SEC_EJEC = 300687;

-- D. Orden temporal contra hitos vecinos del pipeline, por CCMN:
--    cotizacion (SIG_SOLICITUD_COTIZACION min FECHA_REG) debe venir ANTES del cuadro;
--    la orden (SIG_ORDEN_ADQUISICION FECHA_ORDEN) debe venir DESPUES del cuadro.
WITH ca AS (
    SELECT ANO_EJE, SEC_EJEC, TIPO_BIEN, NRO_CONS_PAAC,
           MIN(SEC_CUADRO) AS SEC_CUADRO,
           MAX(FECHA_AUTORIZ) AS FECHA_AUTORIZ,
           MAX(FECHA_COMPRA) AS FECHA_COMPRA,
           MAX(FECHA_NRO_CUADRO) AS FECHA_NRO_CUADRO
    FROM SIG_CUADRO_ADQUISICION
    WHERE ANO_EJE = 2026 AND SEC_EJEC = 300687
    GROUP BY ANO_EJE, SEC_EJEC, TIPO_BIEN, NRO_CONS_PAAC
),
cot AS (
    SELECT ANO_EJE, SEC_EJEC, tipo_bien, NRO_CONSOLID, MIN(FECHA_REG) AS FECHA_COT
    FROM SIG_SOLICITUD_COTIZACION
    WHERE ANO_EJE = 2026 AND SEC_EJEC = 300687
    GROUP BY ANO_EJE, SEC_EJEC, tipo_bien, NRO_CONSOLID
),
ord_ccmn AS (
    SELECT o.ANO_EJE, o.SEC_EJEC, o.TIPO_BIEN, x.NRO_CONS_PAAC,
           MIN(o.FECHA_ORDEN) AS FECHA_ORDEN
    FROM SIG_ORDEN_ADQUISICION o
    JOIN SIG_CUADRO_ADQUISICION x
      ON x.ANO_EJE = o.ANO_EJE AND x.SEC_EJEC = o.SEC_EJEC
     AND x.TIPO_BIEN = o.TIPO_BIEN AND x.SEC_CUADRO = o.SEC_CUADRO
    WHERE o.ANO_EJE = 2026 AND o.SEC_EJEC = 300687
    GROUP BY o.ANO_EJE, o.SEC_EJEC, o.TIPO_BIEN, x.NRO_CONS_PAAC
)
SELECT 'D_orden_temporal' AS q,
       COUNT(*) AS ccmn_con_orden,
       SUM(CASE WHEN cot.FECHA_COT IS NOT NULL THEN 1 ELSE 0 END) AS con_cotizacion,
       SUM(CASE WHEN cot.FECHA_COT <= ca.FECHA_AUTORIZ THEN 1 ELSE 0 END) AS cot_antes_autoriz,
       SUM(CASE WHEN cot.FECHA_COT > ca.FECHA_AUTORIZ THEN 1 ELSE 0 END) AS cot_despues_autoriz,
       SUM(CASE WHEN ca.FECHA_AUTORIZ <= o.FECHA_ORDEN THEN 1 ELSE 0 END) AS autoriz_antes_orden,
       SUM(CASE WHEN ca.FECHA_AUTORIZ > o.FECHA_ORDEN THEN 1 ELSE 0 END) AS autoriz_despues_orden,
       SUM(CASE WHEN ca.FECHA_COMPRA <= o.FECHA_ORDEN THEN 1 ELSE 0 END) AS compra_antes_orden,
       SUM(CASE WHEN ca.FECHA_COMPRA > o.FECHA_ORDEN THEN 1 ELSE 0 END) AS compra_despues_orden,
       SUM(CASE WHEN ca.FECHA_NRO_CUADRO <= o.FECHA_ORDEN THEN 1 ELSE 0 END) AS nrocuadro_antes_orden,
       SUM(CASE WHEN ca.FECHA_NRO_CUADRO > o.FECHA_ORDEN THEN 1 ELSE 0 END) AS nrocuadro_despues_orden
FROM ca
JOIN ord_ccmn o ON o.ANO_EJE = ca.ANO_EJE AND o.SEC_EJEC = ca.SEC_EJEC
  AND o.TIPO_BIEN = ca.TIPO_BIEN AND o.NRO_CONS_PAAC = ca.NRO_CONS_PAAC
LEFT JOIN cot ON cot.ANO_EJE = ca.ANO_EJE AND cot.SEC_EJEC = ca.SEC_EJEC
  AND cot.tipo_bien = ca.TIPO_BIEN AND cot.NRO_CONSOLID = ca.NRO_CONS_PAAC;

-- E. Muestra de 15 filas para inspeccion visual del orden de fechas
SELECT TOP 15 'E_muestra' AS q, TIPO_BIEN, NRO_CONS_PAAC, SEC_CUADRO, ESTADO,
       CONVERT(varchar(10), FECHA_CUADRO, 120) AS f_cuadro,
       CONVERT(varchar(10), FECHA_AUTORIZ, 120) AS f_autoriz,
       CONVERT(varchar(10), FECHA_COMPRA, 120) AS f_compra,
       CONVERT(varchar(10), FECHA_NRO_CUADRO, 120) AS f_nro_cuadro,
       CONVERT(varchar(10), FECHA_REG, 120) AS f_reg
FROM SIG_CUADRO_ADQUISICION
WHERE ANO_EJE = 2026 AND SEC_EJEC = 300687
ORDER BY SEC_CUADRO;
