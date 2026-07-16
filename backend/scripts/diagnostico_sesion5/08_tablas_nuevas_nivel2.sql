-- =====================================================================
-- Sesión 5 · Script 08
-- Estructura y volumen de tablas nuevas descubiertas en el segundo salto.
-- Foco: puentes potenciales al pedido/PAAC/orden que no vimos antes.
-- =====================================================================

DECLARE @tablas TABLE (nombre sysname);
INSERT INTO @tablas VALUES
    ('SIG_CUADRO_NECESIDAD_DET_PAAC'),
    ('SIG_CUADRO_MODIFICADO'),
    ('SIG_CUADRO_MODIFICADO_CMN'),
    ('SIG_CUADRO_MODIFICADO_DET_ORI'),
    ('SIG_CUADRO_MODIFICADO_DET_REF'),
    ('SIG_CUADRO_TRANSFERENCIA_DET'),
    ('SIG_CONTRATOS'),
    ('SIG_CONTRATO_MOVITEM_PPTAL'),
    ('SIG_ORDEN_ITEM'),
    ('SIG_ORDEN_ITEM_PPTO'),
    ('SIG_ORDEN_PRESUPUESTO'),
    ('SIG_DEVENGADO_SECUENCIA'),
    ('SIG_DEVENGADO_DOC_SECU'),
    ('SIG_CERTIFICACION_OPER_FUENTE'),
    ('SIG_DETALLE_MOVIM_ALMACEN'),
    ('SIG_DETALLE_MOVIM_CONFOR_SERV'),
    ('SIG_DETALLE_ITEM_ALMACEN'),
    ('SIG_DETALLE_ITEM_CONFOR_SERV'),
    ('SIG_SOLICITUD_MODIFICACION_DET'),
    ('SIG_SOLICITUD_ESPECIFICACIONES'),
    ('SIG_ESPECIFICAS_TECNICAS'),
    ('SIG_PAAC_DET'),
    ('SIG_PAAC_METAS'),
    ('SIG_PAAC_SECUENCIA'),
    ('SIG_PAAC_CENTRO_COSTO_ANEXO'),
    ('SIG_PAAC_CONSOLIDADO_UES');

PRINT '=== 8.A) Volumen 2026/300687 por tabla nueva (para filtrar candidatos) ===';
DECLARE @sql nvarchar(max) = '';
SELECT @sql = @sql
    + 'SELECT ''' + t.nombre + ''' AS tabla, COUNT(*) AS filas FROM ' + t.nombre
    + CASE
        WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c
                     WHERE c.TABLE_NAME = t.nombre AND c.COLUMN_NAME IN ('ANO_EJE','ano_eje','ANNO_EJEC'))
        THEN ' WHERE 1=1'
             + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c
                                 WHERE c.TABLE_NAME = t.nombre AND c.COLUMN_NAME IN ('ANO_EJE','ano_eje'))
                    THEN ' AND ANO_EJE=2026'
                    ELSE ' AND ANNO_EJEC=2026' END
             + CASE WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS c
                                 WHERE c.TABLE_NAME = t.nombre AND c.COLUMN_NAME IN ('SEC_EJEC','sec_ejec'))
                    THEN ' AND SEC_EJEC=300687' ELSE '' END
        ELSE ''
      END
    + ' UNION ALL '
FROM @tablas t;
SET @sql = LEFT(@sql, LEN(@sql) - LEN(' UNION ALL '));
SET @sql = @sql + ' ORDER BY filas DESC';
EXEC sp_executesql @sql;

PRINT '';
PRINT '=== 8.B) Columnas de las tablas nuevas ===';
SELECT
    c.TABLE_NAME,
    c.ORDINAL_POSITION AS pos,
    c.COLUMN_NAME,
    c.DATA_TYPE
    + CASE WHEN c.CHARACTER_MAXIMUM_LENGTH IS NOT NULL
           THEN '(' + CAST(c.CHARACTER_MAXIMUM_LENGTH AS varchar) + ')'
           ELSE '' END AS tipo
FROM INFORMATION_SCHEMA.COLUMNS c
INNER JOIN @tablas t ON t.nombre = c.TABLE_NAME
WHERE c.COLUMN_NAME IN (
    'ANO_EJE','ano_eje','ANNO_EJEC','SEC_EJEC','sec_ejec',
    'NRO_PEDIDO','nro_pedido','TIPO_PEDIDO','tipo_pedido',
    'NRO_CONSOLID','nro_consolid','NRO_CONS_PAAC','TIPO_CONSOLID',
    'NRO_CERTIFICA','NRO_ORDEN','TIPO_BIEN','tipo_bien',
    'SEC_CUADRO','SEC_ITEM','ANNO_PROG','SEC_CUA_MOD_SAL',
    'EXP_SIGA','EXP_SIAF','NRO_CONTRATO','SEC_CONTRATO',
    'CENTRO_COSTO','SEC_FUNC','sec_func','CLASIFICADOR',
    'PROVEEDOR','FECHA_REG','FECHA_DOCUMENTO'
)
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;
