CREATE  trigger dbo.tg_orden_del
on sig_orden_adquisicion for delete
as
DECLARE

@vi_nro_origen              NUMERIC(6),
@ll_tipo_transaccion        NUMERIC(10),
@ll_secuencia_max           NUMERIC(10),
@ll_cur_ano_eje             NUMERIC(4),
@ll_cur_sec_ejec            NUMERIC(6),
@ll_cur_tipo_ppto           NUMERIC(10),
@ls_tipo_movimiento         VARCHAR(1)  = 'D',
@ls_cur_nro_pedido          VARCHAR(50)  = '0',
@ls_cur_estado_transaccion  VARCHAR(1),
@ls_cur_tipo_bien           VARCHAR(1),
@ls_cur_cuser_id            VARCHAR(30),
@ls_cur_equipo_reg          VARCHAR(20),
@ls_cur_tipo_pedido         VARCHAR(2),
@ldt_cur_fecha_transaccion  DATETIME

BEGIN

SELECT
@ll_cur_ano_eje             = ANO_EJE,
@ll_cur_sec_ejec            = SEC_EJEC,
@ls_cur_nro_pedido          = NRO_ORDEN,
@ll_cur_tipo_ppto           = TIPO_PPTO,
@ls_cur_estado_transaccion  = ESTADO,
@ldt_cur_fecha_transaccion  = FECHA_ORDEN,
@ls_cur_tipo_bien           = TIPO_BIEN,
@ls_cur_cuser_id            = CUSER_MOD,
@ls_cur_equipo_reg          = EQUIPO_MOD,
@ls_cur_tipo_pedido         = NULL
FROM    DELETED

--si existe la tabla de sesion, saco de ahi los datos
IF  OBJECT_ID('tempdb..#SIG_SESION') IS  NOT NULL
    BEGIN
        SELECT  @ls_cur_cuser_id    = CUSER_ID,
                @ls_cur_equipo_reg  = EQUIPO_REG
        FROM    #SIG_SESION
    END

IF  @ls_cur_tipo_bien = 'B'
BEGIN
    --8: Orden Compra
    SELECT  @ll_tipo_transaccion    = 8
END
ELSE
    BEGIN
        IF  @ls_cur_tipo_bien = 'S'
        BEGIN
            -- 9: Orden Servicio
            SELECT  @ll_tipo_transaccion    = 9
        END
    ELSE
        BEGIN
            GOTO    salida
        END
    END

-- Recupera Argumento
select	@vi_nro_origen = nro_origen
from sig_seguimiento 
where ano_eje 	       = @ll_cur_ano_eje      and
      sec_ejec	       = @ll_cur_sec_ejec and
      nro_transaccion  = @ls_cur_nro_pedido and
      tipo_bien        = @ls_cur_tipo_bien and
      tipo_ppto        = @ll_cur_tipo_ppto and
      tipo_transaccion = @ll_tipo_transaccion


-- Inserta estados
delete from sig_seguimiento_estado	
where ano_eje   	= @ll_cur_ano_eje	     and
      sec_ejec  	= @ll_cur_sec_ejec      and
      tipo_transaccion  = @ll_tipo_transaccion     and
      nro_origen	= @vi_nro_origen     

-- Inserta Secuencia 	
delete from sig_seguimiento_secuencia
where ano_eje   	= @ll_cur_ano_eje	     and
      sec_ejec  	= @ll_cur_sec_ejec      and
      tipo_transaccion  = @ll_tipo_transaccion     and
      nro_origen	= @vi_nro_origen     

-- Inserta Seguimiento
delete from sig_seguimiento
where ano_eje   	= @ll_cur_ano_eje     	     and
      sec_ejec  	= @ll_cur_sec_ejec      and
      tipo_transaccion  = @ll_tipo_transaccion     and
      nro_origen	= @vi_nro_origen     

/*obtengo el secuencial de auditoria*/
SELECT  @ll_secuencia_max   = COALESCE(MAX(SECUENCIA), 0) + 1
FROM    SIG_AUDITORIA
WHERE   ANO_EJE             = @ll_cur_ano_eje
AND     SEC_EJEC            = @ll_cur_sec_ejec
AND     TIPO_MOVIMIENTO     = @ls_tipo_movimiento

INSERT  INTO    SIG_AUDITORIA(
                ANO_EJE, SEC_EJEC, TIPO_MOVIMIENTO, SECUENCIA,
                TIPO_TRANSACCION, NRO_ORIGEN, CENTRO_COSTO, SOLICITANTE,
                TIPO_PPTO, TIPO_BIEN, TIPO_PEDIDO, NRO_PEDIDO,
                NRO_CONSOLID, NRO_TRANSACCION, FECHA_TRANSACCION, ESTADO_TRANSACCION,
                SEC_TRANSACCION, FECHA_REG, CUSER_ID, EQUIPO_REG,
                TIPO_CONSOLID
                )
VALUES          (
                @ll_cur_ano_eje, @ll_cur_sec_ejec, @ls_tipo_movimiento,	@ll_secuencia_max,
                @ll_tipo_transaccion, NULL, NULL, NULL,
                @ll_cur_tipo_ppto, @ls_cur_tipo_bien, @ls_cur_tipo_pedido, @ls_cur_nro_pedido,
                NULL, CAST(@ls_cur_nro_pedido AS NUMERIC(10)), @ldt_cur_fecha_transaccion, @ls_cur_estado_transaccion,
                NULL, GETDATE(), @ls_cur_cuser_id, @ls_cur_equipo_reg,
                NULL
                )

END

salida:
RETURN

