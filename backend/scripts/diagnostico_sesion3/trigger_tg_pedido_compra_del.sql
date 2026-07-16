CREATE trigger dbo.tg_pedido_compra_del
on sig_pedidos for delete
as
DECLARE
@ll_cont                    NUMERIC(10),
@ll_cur_ano_eje             NUMERIC(4),
@ll_cur_sec_ejec            NUMERIC(6),
@ll_cur_tipo_ppto           NUMERIC(10),
@vid_tipo_trans             NUMERIC(2),
@vid_nro_origen             NUMERIC(6),
@ll_secuencia_max           NUMERIC(10),
@ll_tipo_transaccion        NUMERIC(10),
@ls_tipo_movimiento         VARCHAR(1)  = 'D',
@ls_cur_flag_pad            VARCHAR(1),
@ls_cur_tipo_bien           VARCHAR(1),
@ls_cur_tipo_pedido         VARCHAR(2),
@ls_cur_nro_pedido          VARCHAR(50),
@ls_cur_estado_transaccion  VARCHAR(1),
@ls_cur_centro_costo        VARCHAR(15),
@ls_cur_cuser_id            VARCHAR(30),
@ls_cur_equipo_reg          VARCHAR(20),
@ldt_cur_fecha_transaccion  DATETIME

BEGIN

SELECT  @ll_cont = COUNT(1)
FROM    DELETED
IF @ll_cont <> 1 
    RETURN

SELECT  
@ll_cur_ano_eje             = ANO_EJE,
@ll_cur_sec_ejec            = SEC_EJEC,
@ls_cur_nro_pedido          = NRO_PEDIDO,
@ll_cur_tipo_ppto           = TIPO_PPTO,
@ls_cur_estado_transaccion  = ESTADO,
@ldt_cur_fecha_transaccion  = FECHA_PEDIDO,
@ls_cur_centro_costo        = CENTRO_COSTO,
@ls_cur_cuser_id            = CUSER_MOD,
@ls_cur_equipo_reg          = EQUIPO_MOD,
@ls_cur_tipo_bien           = TIPO_BIEN,
@ls_cur_tipo_pedido         = TIPO_PEDIDO,
@ls_cur_flag_pad            = FLAG_PAD
FROM    DELETED


--si existe la tabla de sesion, saco de ahi los datos
IF  OBJECT_ID('tempdb..#SIG_SESION') IS  NOT NULL
    BEGIN
        SELECT  @ls_cur_cuser_id    = CUSER_ID,
                @ls_cur_equipo_reg  = EQUIPO_REG
        FROM    #SIG_SESION
    END

-- Eliminar el Seguimiento	
select @vid_tipo_trans = isnull( A.tipo_transaccion,0),
       @vid_nro_origen = isnull(A.nro_origen,0)
from sig_seguimiento A
where A.ano_eje 	= @ll_cur_ano_eje 	 and
      A.sec_ejec	= @ll_cur_sec_ejec and
      A.tipo_bien	= @ls_cur_tipo_bien and
      A.tipo_pedido     = @ls_cur_tipo_pedido  and
      A.nro_pedido      = @ls_cur_nro_pedido and	
      A.tipo_transaccion in (1,2,17,18)
      
-- Elimina en las tablas
delete from sig_seguimiento_estado
where ano_eje 		= @ll_cur_ano_eje 	  and
      sec_ejec 		= @ll_cur_sec_ejec  and
      tipo_transaccion	= @vid_tipo_trans and
      nro_origen 	= @vid_nro_origen 

delete from sig_seguimiento_secuencia
where ano_eje 		= @ll_cur_ano_eje 	  and
      sec_ejec 		= @ll_cur_sec_ejec  and
      tipo_transaccion	= @vid_tipo_trans and
      nro_origen 	= @vid_nro_origen 

delete from sig_seguimiento	
where ano_eje 		= @ll_cur_ano_eje 	  and
      sec_ejec 		= @ll_cur_sec_ejec  and
      tipo_transaccion	= @vid_tipo_trans and
      nro_origen 	= @vid_nro_origen

/*FACT, se migro funcionalidad de uo_auditoria*/

--pedidos programados
IF  @ls_cur_tipo_pedido   = '1'
BEGIN
    SELECT  @ll_tipo_transaccion    = 1
END

--pedidos no programados
IF  @ls_cur_tipo_pedido   = '2'
BEGIN
    SELECT  @ll_tipo_transaccion    = 2
END

--tipo modulo : pedido de encargos
IF  @ls_cur_tipo_pedido = '5'   AND @ls_cur_flag_pad    =   '0' AND @ll_cur_tipo_ppto   = 2
BEGIN
    SELECT  @ll_tipo_transaccion    = 17
END
        
--tipo modulo : pedido de encargos
IF  @ls_cur_tipo_pedido = '6'   AND @ll_cur_tipo_ppto   = 2
BEGIN
    SELECT  @ll_tipo_transaccion    = 18
END

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
                NULL, @ls_cur_tipo_bien, @ls_cur_tipo_pedido, @ls_cur_nro_pedido,
                NULL, CAST(@ls_cur_nro_pedido AS NUMERIC(10)), @ldt_cur_fecha_transaccion, @ls_cur_estado_transaccion,
                NULL, GETDATE(), @ls_cur_cuser_id, @ls_cur_equipo_reg,
                NULL
                )

END

