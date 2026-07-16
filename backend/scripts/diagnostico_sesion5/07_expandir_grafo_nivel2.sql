-- =====================================================================
-- Sesión 5 · Script 07
-- Expansión del grafo de FKs un salto más allá del pipeline conocido.
-- Vecinos descubiertos en el script 01 que aún no hemos volcado:
--     SIG_PAAC_CONSOLIDADO, SIG_CUADRO_MODIFICADO_DET,
--     SIG_CUADRO_MODIFICADO_SALDO, SIG_CUADRO_NECESIDAD,
--     SIG_ORDEN_SECUENCIA, SIG_DEVENGADO, SIG_ORDEN_INTERFASE,
--     SIG_OCE_DET, SIG_EXP_SIGA_DOCU, SIG_EXP_SIGA_PPTO,
--     SIG_CERTIFICACION_OPERACION, SIG_PAAC_ITEM,
--     SIG_SECUENCIA_MOV_ALMACEN, SIG_SECUENCIA_MOV_CONFOR_SERV,
--     SIG_DETALLE_ANEXO_CUADRO, SIG_DETALLE_METAS_CUADRO,
--     SIG_DETALLE_PECOSA, SIG_DETALLE_PEDIDOS_ANEXO,
--     SIG_DETALLE_PEDIDO_COMISIONADO, SIG_SOLICITUD_ESPECIFICACIONES,
--     SIG_DEPEN_META_CUADRO
-- =====================================================================

DECLARE @vecinos TABLE (nombre sysname);
INSERT INTO @vecinos VALUES
    ('SIG_PAAC_CONSOLIDADO'),
    ('SIG_PAAC_ITEM'),
    ('SIG_CUADRO_MODIFICADO_DET'),
    ('SIG_CUADRO_MODIFICADO_SALDO'),
    ('SIG_CUADRO_NECESIDAD'),
    ('SIG_ORDEN_SECUENCIA'),
    ('SIG_DEVENGADO'),
    ('SIG_ORDEN_INTERFASE'),
    ('SIG_OCE_DET'),
    ('SIG_EXP_SIGA_DOCU'),
    ('SIG_EXP_SIGA_PPTO'),
    ('SIG_CERTIFICACION_OPERACION'),
    ('SIG_SECUENCIA_MOV_ALMACEN'),
    ('SIG_SECUENCIA_MOV_CONFOR_SERV'),
    ('SIG_DETALLE_ANEXO_CUADRO'),
    ('SIG_DETALLE_METAS_CUADRO'),
    ('SIG_DETALLE_PECOSA'),
    ('SIG_DETALLE_PEDIDOS_ANEXO'),
    ('SIG_DETALLE_PEDIDO_COMISIONADO'),
    ('SIG_SOLICITUD_ESPECIFICACIONES'),
    ('SIG_DEPEN_META_CUADRO'),
    ('SIG_PAAC_CENTRO_COSTO'),
    ('SIG_PAAC_CENTRO_COSTO_ANEXO'),
    ('SIG_CUADRO_MODIFICADO_CMN');

PRINT '=== 7.A) FKs ENTRANTES a los vecinos (nuevas tablas que apuntan a estos) ===';
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
    ON c.object_id = fk.parent_object_id AND c.column_id = fkc.parent_column_id
INNER JOIN sys.columns rc
    ON rc.object_id = fk.referenced_object_id AND rc.column_id = fkc.referenced_column_id
WHERE OBJECT_NAME(fk.referenced_object_id) IN (SELECT nombre FROM @vecinos)
ORDER BY tabla_padre, tabla_hija, fkc.constraint_column_id;

PRINT '';
PRINT '=== 7.B) FKs SALIENTES de los vecinos ===';
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
    ON c.object_id = fk.parent_object_id AND c.column_id = fkc.parent_column_id
INNER JOIN sys.columns rc
    ON rc.object_id = fk.referenced_object_id AND rc.column_id = fkc.referenced_column_id
WHERE OBJECT_NAME(fk.parent_object_id) IN (SELECT nombre FROM @vecinos)
ORDER BY tabla_hija, tabla_padre, fkc.constraint_column_id;
