-- =====================================================================
-- Sesión 5 · Script 02
-- Estructura (columnas) de las tablas descubiertas en el grafo de FKs
-- que NO estaban documentadas en el archivo de exploración.
-- =====================================================================

DECLARE @tablas TABLE (nombre sysname);
INSERT INTO @tablas VALUES
    ('SIG_PAAC_CONSOLIDADO'),
    ('SIG_PAAC_ITEM'),
    ('SIG_CUADRO_MODIFICADO_DET'),
    ('SIG_CUADRO_MODIFICADO_SALDO'),
    ('SIG_CUADRO_NECESIDAD'),
    ('SIG_DEVENGADO'),
    ('SIG_OCE_DET'),
    ('SIG_ORDEN_SECUENCIA'),
    ('SIG_ORDEN_INTERFASE'),
    ('SIG_EXP_SIGA_DOCU'),
    ('SIG_EXP_SIGA_PPTO'),
    ('SIG_CERTIFICACION_OPERACION');

SELECT
    c.TABLE_NAME,
    c.ORDINAL_POSITION AS pos,
    c.COLUMN_NAME,
    c.DATA_TYPE
    + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH IS NOT NULL
           THEN '(' + CAST(c.CHARACTER_MAXIMUM_LENGTH AS varchar) + ')'
           ELSE '' END AS tipo,
    c.IS_NULLABLE AS nul
FROM INFORMATION_SCHEMA.COLUMNS c
INNER JOIN @tablas t ON t.nombre = c.TABLE_NAME
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
