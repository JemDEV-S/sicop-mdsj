-- =====================================================================
-- Sesión 5 · Script 01
-- Grafo de FKs declaradas alrededor de las tablas del pipeline extendido.
--
-- Objetivo: obtener el esqueleto REAL de relaciones (no basado en nombres)
-- entre las tablas conocidas del ciclo pedido → cotización → cuadro →
-- certificación → orden → devengado → conformidad.
--
-- Salida esperada: dos secciones —
--   A) FKs entrantes (otras tablas apuntan a las del pipeline)
--   B) FKs salientes (las del pipeline apuntan a otras)
-- =====================================================================

DECLARE @pipeline TABLE (nombre sysname);
INSERT INTO @pipeline VALUES
    ('SIG_PEDIDOS'),
    ('SIG_DETALLE_PEDIDOS'),
    ('SIG_SOLICITUD_COTIZACION'),
    ('SIG_SOLICITUD_COTIZACION_ITEM'),
    ('SIG_CUADRO_ADQUISICION'),
    ('SIG_DETALLE_BSERV_CUADRO'),
    ('SIG_CUADRO_NECESIDAD_DET'),
    ('SIG_DETALLE_PEDIDO_CUADRO'),
    ('SIG_CERTIFICACION'),
    ('SIG_CERTIFICACION_FASE'),
    ('SIG_ORDEN_ADQUISICION'),
    ('SIG_EXP_SIGA'),
    ('SIG_EXP_SIGA_SECU'),
    ('SIG_MOVIM_CONFOR_SERVICIO'),
    ('SIG_MOVIM_ALMACEN');

PRINT '=== A) FKs ENTRANTES (tabla_hija -> tabla_pipeline) ===';
SELECT
    OBJECT_NAME(fk.parent_object_id)     AS tabla_hija,
    c.name                               AS col_hija,
    OBJECT_NAME(fk.referenced_object_id) AS tabla_padre,
    rc.name                              AS col_padre,
    fk.name                              AS fk_nombre
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fkc
    ON fkc.constraint_object_id = fk.object_id
INNER JOIN sys.columns c
    ON c.object_id = fk.parent_object_id
   AND c.column_id = fkc.parent_column_id
INNER JOIN sys.columns rc
    ON rc.object_id = fk.referenced_object_id
   AND rc.column_id = fkc.referenced_column_id
WHERE OBJECT_NAME(fk.referenced_object_id) IN (SELECT nombre FROM @pipeline)
ORDER BY tabla_padre, tabla_hija, fkc.constraint_column_id;

PRINT '';
PRINT '=== B) FKs SALIENTES (tabla_pipeline -> tabla_padre) ===';
SELECT
    OBJECT_NAME(fk.parent_object_id)     AS tabla_hija,
    c.name                               AS col_hija,
    OBJECT_NAME(fk.referenced_object_id) AS tabla_padre,
    rc.name                              AS col_padre,
    fk.name                              AS fk_nombre
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fkc
    ON fkc.constraint_object_id = fk.object_id
INNER JOIN sys.columns c
    ON c.object_id = fk.parent_object_id
   AND c.column_id = fkc.parent_column_id
INNER JOIN sys.columns rc
    ON rc.object_id = fk.referenced_object_id
   AND rc.column_id = fkc.referenced_column_id
WHERE OBJECT_NAME(fk.parent_object_id) IN (SELECT nombre FROM @pipeline)
ORDER BY tabla_hija, tabla_padre, fkc.constraint_column_id;
