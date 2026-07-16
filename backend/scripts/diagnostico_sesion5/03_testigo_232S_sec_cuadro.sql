-- =====================================================================
-- Sesión 5 · Script 03
-- Verificación en el caso testigo 232/S (2026, SEC_EJEC=300687):
-- - ¿SIG_DETALLE_PEDIDOS tiene SEC_CUADRO poblado?
-- - ¿Cuál es su valor?  (Debería ser 131, el cuadro del testigo).
-- =====================================================================

PRINT '=== 3.1 Cabecera del pedido 232/S ===';
SELECT NRO_PEDIDO, TIPO_PEDIDO, TIPO_BIEN, ESTADO,
       FECHA_PEDIDO, CENTRO_COSTO, SEC_FUNC
FROM SIG_PEDIDOS
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND TIPO_BIEN='S' AND CAST(NRO_PEDIDO AS INT)=232;

PRINT '';
PRINT '=== 3.2 Detalle del pedido 232/S — todas las columnas ===';
SELECT *
FROM SIG_DETALLE_PEDIDOS
WHERE ANO_EJE=2026 AND sec_ejec=300687
  AND TIPO_BIEN='S' AND CAST(NRO_PEDIDO AS INT)=232;

PRINT '';
PRINT '=== 3.3 Fill rate SEC_CUADRO en detalle pedidos 2026 ===';
SELECT TIPO_BIEN,
       COUNT(*) AS filas,
       COUNT(SEC_CUADRO) AS con_sec_cuadro,
       SUM(CASE WHEN SEC_CUADRO>0 THEN 1 ELSE 0 END) AS con_sec_cuadro_mayor_0,
       COUNT(SEC_ITEM)   AS con_sec_item,
       COUNT(SEC_CUA_MOD_SAL) AS con_sec_cua_mod_sal,
       COUNT(ANNO_PROG)  AS con_anno_prog
FROM SIG_DETALLE_PEDIDOS
WHERE ANO_EJE=2026 AND sec_ejec=300687
GROUP BY TIPO_BIEN;
