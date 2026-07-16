-- =====================================================================
-- Sesión 5 · Script 10
-- Búsqueda por VALOR del testigo en toda tabla de usuario:
--   ¿en qué tablas aparece 232 (pedido) junto a otro id del pipeline?
--   ¿en qué tablas aparece 2266 (CCMN)?
--   ¿en qué tablas aparece 263 (CVR/EM)?
-- Genera dinámicamente COUNT por tabla que tenga la columna candidata.
-- =====================================================================

PRINT '=== 10.1 Tablas con NRO_PEDIDO donde exista fila con NRO_PEDIDO=232, 2026/300687 ===';
DECLARE @sql nvarchar(max) = '';
SELECT @sql = @sql
    + 'SELECT ''' + c.TABLE_NAME + ''' AS tabla, COUNT(*) AS filas_con_232 FROM ' + c.TABLE_NAME
    + ' WHERE 1=1'
    + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c2
                        WHERE c2.TABLE_NAME=c.TABLE_NAME AND c2.COLUMN_NAME IN ('ANO_EJE','ano_eje'))
           THEN ' AND ANO_EJE=2026' ELSE '' END
    + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c2
                        WHERE c2.TABLE_NAME=c.TABLE_NAME AND c2.COLUMN_NAME IN ('SEC_EJEC','sec_ejec'))
           THEN ' AND SEC_EJEC=300687' ELSE '' END
    + ' AND (TRY_CAST(' + c.COLUMN_NAME + ' AS INT)=232) UNION ALL '
FROM INFORMATION_SCHEMA.COLUMNS c
INNER JOIN INFORMATION_SCHEMA.TABLES t ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_TYPE='BASE TABLE'
WHERE c.COLUMN_NAME IN ('NRO_PEDIDO','nro_pedido')
  AND c.TABLE_NAME NOT LIKE 'TEMP_%'
  AND c.TABLE_NAME NOT LIKE 'tmp%'
  AND c.TABLE_NAME NOT LIKE 'SIG_TMP_%';
SET @sql = LEFT(@sql, LEN(@sql)-LEN(' UNION ALL '));
SET @sql = 'SELECT tabla, filas_con_232 FROM (' + @sql + ') x WHERE filas_con_232 > 0 ORDER BY filas_con_232 DESC';
EXEC sp_executesql @sql;

PRINT '';
PRINT '=== 10.2 Tablas con NRO_CONSOLID donde exista fila con NRO_CONSOLID=2266 ===';
SET @sql = '';
SELECT @sql = @sql
    + 'SELECT ''' + c.TABLE_NAME + ''' AS tabla, COUNT(*) AS filas FROM ' + c.TABLE_NAME
    + ' WHERE 1=1'
    + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c2
                        WHERE c2.TABLE_NAME=c.TABLE_NAME AND c2.COLUMN_NAME IN ('ANO_EJE','ano_eje'))
           THEN ' AND ANO_EJE=2026' ELSE '' END
    + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c2
                        WHERE c2.TABLE_NAME=c.TABLE_NAME AND c2.COLUMN_NAME IN ('SEC_EJEC','sec_ejec'))
           THEN ' AND SEC_EJEC=300687' ELSE '' END
    + ' AND ' + c.COLUMN_NAME + '=2266 UNION ALL '
FROM INFORMATION_SCHEMA.COLUMNS c
INNER JOIN INFORMATION_SCHEMA.TABLES t ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_TYPE='BASE TABLE'
WHERE c.COLUMN_NAME IN ('NRO_CONSOLID','nro_consolid')
  AND c.DATA_TYPE = 'numeric'
  AND c.TABLE_NAME NOT LIKE 'TEMP_%'
  AND c.TABLE_NAME NOT LIKE 'tmp%'
  AND c.TABLE_NAME NOT LIKE 'SIG_TMP_%'
  AND c.TABLE_NAME NOT LIKE 'V_%'
  AND c.TABLE_NAME NOT LIKE 'SGE_%'; -- SGE = MEF, no muni
SET @sql = LEFT(@sql, LEN(@sql)-LEN(' UNION ALL '));
SET @sql = 'SELECT tabla, filas FROM (' + @sql + ') x WHERE filas > 0 ORDER BY filas DESC';
EXEC sp_executesql @sql;

PRINT '';
PRINT '=== 10.3 Tablas con NRO_CONS_PAAC donde exista fila con NRO_CONS_PAAC=2266 ===';
SET @sql = '';
SELECT @sql = @sql
    + 'SELECT ''' + c.TABLE_NAME + ''' AS tabla, COUNT(*) AS filas FROM ' + c.TABLE_NAME
    + ' WHERE 1=1'
    + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c2
                        WHERE c2.TABLE_NAME=c.TABLE_NAME AND c2.COLUMN_NAME IN ('ANO_EJE','ano_eje'))
           THEN ' AND ANO_EJE=2026' ELSE '' END
    + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c2
                        WHERE c2.TABLE_NAME=c.TABLE_NAME AND c2.COLUMN_NAME IN ('SEC_EJEC','sec_ejec'))
           THEN ' AND SEC_EJEC=300687' ELSE '' END
    + ' AND NRO_CONS_PAAC=2266 UNION ALL '
FROM INFORMATION_SCHEMA.COLUMNS c
INNER JOIN INFORMATION_SCHEMA.TABLES t ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_TYPE='BASE TABLE'
WHERE c.COLUMN_NAME = 'NRO_CONS_PAAC'
  AND c.TABLE_NAME NOT LIKE 'TEMP_%'
  AND c.TABLE_NAME NOT LIKE 'tmp%'
  AND c.TABLE_NAME NOT LIKE 'SIG_TMP_%';
IF LEN(@sql) > 0
BEGIN
    SET @sql = LEFT(@sql, LEN(@sql)-LEN(' UNION ALL '));
    SET @sql = 'SELECT tabla, filas FROM (' + @sql + ') x WHERE filas > 0 ORDER BY filas DESC';
    EXEC sp_executesql @sql;
END

PRINT '';
PRINT '=== 10.4 Tablas de la BD con TIPO_CONSOLID (para descartar familias PAAC no vistas) ===';
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE COLUMN_NAME IN ('TIPO_CONSOLID','tipo_consolid')
  AND TABLE_NAME NOT LIKE 'TEMP_%'
  AND TABLE_NAME NOT LIKE 'tmp%'
  AND TABLE_NAME NOT LIKE 'SIG_TMP_%'
  AND TABLE_NAME NOT LIKE 'V_%'
  AND TABLE_NAME NOT LIKE 'SGE_%'
ORDER BY TABLE_NAME;
