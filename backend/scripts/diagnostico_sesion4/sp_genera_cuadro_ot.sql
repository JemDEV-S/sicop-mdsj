CREATE PROCEDURE dbo.SP_GENERA_CUADRO_OT  
(@pn_ano NUMERIC, @pn_sec_ejec NUMERIC, @ps_tipo_contrato varchar(1),  
 @pn_nro_contrato NUMERIC,@ps_mes_periodo varchar(2),@pn_tipo_cambio NUMERIC,  
 @pd_fecha_pago DATE, @ps_flag_clcc varchar(1), @pn_nro_proceso numeric)  
  
AS  
DECLARE @ls_parametro VARCHAR(1)
DECLARE @ln_anio numeric(9,0)  
DECLARE @ln_cuenta NUMERIC(10,0)	
DECLARE @ln_ejecutora numeric(9,0)  
  
DECLARE @ln_sec_periodo  numeric(3,0)  
DECLARE @ln_sec_ppto     numeric(3,0)  	
DECLARE @ln_sec_depend   numeric(3,0)  
  
DECLARE @ls_centro_costo VARCHAR(15)  
DECLARE @ls_nivel_tarea  VARCHAR(1)  
DECLARE @ln_sec_cc       numeric(9,0)  
DECLARE @ls_clas_gast_param varchar(20)  
  
DECLARE @LN_ANO_EJE_I NUMERIC  
DECLARE @LN_SEC_EJEC_I NUMERIC  
DECLARE @LS_TIPO_CONTRATO_I VARCHAR(1)  
DECLARE @LN_NRO_CONTRATO_I NUMERIC  
DECLARE @LN_NRO_ITEM_I NUMERIC  
DECLARE @LS_TIPO_BIEN_I VARCHAR(1)  
DECLARE @LS_GRUPO_BIEN_I VARCHAR(2)  
DECLARE @LS_CLASE_BIEN_I VARCHAR(2)  
DECLARE @LS_FAMILIA_BIEN_I VARCHAR(4)  
DECLARE @LS_ITEM_BIEN_I VARCHAR(4)  
  
DECLARE @LN_ANO_EJE_C NUMERIC  
DECLARE @LN_SEC_EJEC_C NUMERIC  
DECLARE @LS_TIPO_CONTRATO_C VARCHAR(1)  
DECLARE @LN_NRO_CONTRATO_C NUMERIC  
DECLARE @LN_NRO_ITEM_C NUMERIC  
DECLARE @LN_SEC_PERIODO_C NUMERIC  
DECLARE @LS_TIPO_BIEN_C VARCHAR(1)  
DECLARE @LS_GRUPO_BIEN_C VARCHAR(2)  
DECLARE @LS_CLASE_BIEN_C VARCHAR(2)  
DECLARE @LS_FAMILIA_BIEN_C VARCHAR(4)  
DECLARE @LS_ITEM_BIEN_C VARCHAR(4)  
  
DECLARE @LN_ANO_EJE_S NUMERIC  
DECLARE @LN_SEC_EJEC_S NUMERIC  
DECLARE @LS_TIPO_CONTRATO_S VARCHAR(1)  
DECLARE @LN_NRO_CONTRATO_S NUMERIC  
DECLARE @LN_NRO_ITEM_S NUMERIC  
DECLARE @LN_SEC_PERIODO_S NUMERIC  
DECLARE @LN_SEC_PPTO_S NUMERIC  
DECLARE @LS_TIPO_BIEN_S VARCHAR(1)  
DECLARE @LS_GRUPO_BIEN_S VARCHAR(2)  
DECLARE @LS_CLASE_BIEN_S VARCHAR(2)  
DECLARE @LS_FAMILIA_BIEN_S VARCHAR(4)  
DECLARE @LS_ITEM_BIEN_S VARCHAR(4)  


DECLARE @LN_ANO_EJE_S_1 NUMERIC  
DECLARE @LN_SEC_EJEC_S_1 NUMERIC  
DECLARE @LS_TIPO_CONTRATO_S_1 VARCHAR(1)  
DECLARE @LN_NRO_CONTRATO_S_1 NUMERIC  
DECLARE @LN_NRO_ITEM_S_1 NUMERIC  
DECLARE @LN_SEC_PERIODO_S_1 NUMERIC  
DECLARE @LN_SEC_PPTO_S_1 NUMERIC  


DECLARE  ccn_item CURSOR FOR  
SELECT distinct CTI.ANO_EJE,  
       CTI.SEC_EJEC,  
       CTI.TIPO_CONTRATO,  
       CTI.NRO_CONTRATO,  
       CTI.NRO_ITEM,  
       CTI.TIPO_BIEN,  
       CTI.GRUPO_BIEN,  
       CTI.CLASE_BIEN,  
       CTI.FAMILIA_BIEN,  
       CTI.ITEM_BIEN  
 FROM  SIG_CONTRATO_ITEM CTI,  
       SIG_CONTRATOS CTR  
WHERE  CTI.ano_eje  = @pn_ano AND  
       CTI.SEC_EJEC = @PN_SEC_EJEC AND  
       CTI.TIPO_CONTRATO = @PS_TIPO_CONTRATO AND  
       CTI.NRO_CONTRATO  = @PN_NRO_CONTRATO AND  
       CTI.ano_eje  >= 2013 AND  
       CTI.TIPO_BIEN  = 'S' AND  
       CTR.ANO_EJE      = CTI.ANO_EJE AND  
       CTR.SEC_EJEC     = CTI.SEC_EJEC AND  
       CTR.TIPO_CONTRATO= CTI.TIPO_CONTRATO AND  
       CTR.NRO_CONTRATO = CTI.NRO_CONTRATO AND  
       CTR.TIPO_BIEN  = 'S' AND  
       COALESCE(CTR.FLAG_CONTR_OT,'0') = '1' AND  
         
   EXISTS( 
   SELECT PED.ANO_EJE  
   FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET  
   WHERE DET.ANO_EJE = PED.ANO_EJE AND  
         DET.SEC_EJEC = PED.SEC_EJEC AND  
         DET.TIPO_BIEN = PED.TIPO_BIEN AND  
         DET.NRO_PEDIDO = PED.NRO_PEDIDO AND  
         DET.ANO_EJE  = @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND   
         COALESCE(DET.FLAG_PEDIDO_OT,'0') = '1' AND  
         COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND
    DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND  
      
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO IN (   
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO    
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')
 
   UNION
 
   SELECT PED.ANO_EJE  
   FROM SIG_PEDIDOS PED,  
        SIG_DETALLE_PEDIDOS DET  ,
        SIG_METAS_X_CENTRO SMC
   WHERE DET.ANO_EJE = PED.ANO_EJE AND  
         DET.SEC_EJEC = PED.SEC_EJEC AND  
         DET.TIPO_BIEN = PED.TIPO_BIEN AND  
         DET.NRO_PEDIDO = PED.NRO_PEDIDO AND  
         PED.ANO_EJE = SMC.ANO_EJE AND
         PED.SEC_EJEC = SMC.SEC_EJEC AND
         PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
         PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE  = @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND   
         COALESCE(DET.FLAG_PEDIDO_OT,'0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT,'0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND  
      
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  

         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO IN (   
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO    
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
   X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')

         )   
       
DECLARE ccn_item_mensual CURSOR FOR  
SELECT DISTINCT CTM.ANO_EJE,  
       CTM.SEC_EJEC,  
       CTM.TIPO_CONTRATO,  
       CTM.NRO_CONTRATO,  
       CTM.NRO_ITEM,  
       CTM.SEC_PERIODO,  
       CTI.GRUPO_BIEN,  
       CTI.CLASE_BIEN,  
       CTI.FAMILIA_BIEN,  
       CTI.ITEM_BIEN  
FROM   SIG_CONTRATO_ITEM_MENSUAL CTM,   
       SIG_CONTRATO_ITEM CTI,  
       SIG_CONTRATOS CTR  
WHERE  CTM.ano_eje  = @pn_ano AND  
       CTM.SEC_EJEC = @PN_SEC_EJEC AND  
       CTM.TIPO_CONTRATO = @PS_TIPO_CONTRATO AND  
       CTM.NRO_CONTRATO  = @PN_NRO_CONTRATO AND  
       CTM.ANO_EJE       = CTI.ANO_EJE  AND        
       CTM.SEC_EJEC      = CTI.SEC_EJEC AND        
       CTM.TIPO_CONTRATO = CTI.TIPO_CONTRATO AND    
       CTM.NRO_CONTRATO  = CTI.NRO_CONTRATO AND    
       CTM.NRO_ITEM      = CTI.NRO_ITEM AND        
       CTM.ano_eje  >= 2013 AND  
       CTI.ANO_EJE       = CTR.ANO_EJE AND         
       CTI.SEC_EJEC      = CTR.SEC_EJEC AND        
       CTI.TIPO_CONTRATO = CTR.TIPO_CONTRATO AND    
       CTI.NRO_CONTRATO  = CTR.NRO_CONTRATO AND    
       CTR.TIPO_BIEN  = 'S' AND  
       CTR.FLAG_CONTR_OT = '1' AND   
       CTM.FECHA_PAGO = @pd_fecha_pago AND
         
   EXISTS( 
   SELECT PED.ANO_EJE  
   FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET  
   WHERE DET.ANO_EJE = PED.ANO_EJE AND  
         DET.SEC_EJEC = PED.SEC_EJEC AND  
         DET.TIPO_BIEN = PED.TIPO_BIEN AND  
         DET.NRO_PEDIDO = PED.NRO_PEDIDO AND  
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND   
         COALESCE(DET.FLAG_PEDIDO_OT,'0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT,'0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND      

         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  

         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')
 
   UNION
 
   SELECT PED.ANO_EJE  
   FROM   SIG_PEDIDOS PED,  
          SIG_DETALLE_PEDIDOS DET ,
          SIG_METAS_X_CENTRO SMC 
   WHERE DET.ANO_EJE = PED.ANO_EJE AND  
         DET.SEC_EJEC = PED.SEC_EJEC AND  
         DET.TIPO_BIEN = PED.TIPO_BIEN AND  
         DET.NRO_PEDIDO = PED.NRO_PEDIDO AND  
         PED.ANO_EJE = SMC.ANO_EJE AND     
         PED.SEC_EJEC = SMC.SEC_EJEC AND
         PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
         PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND   
         COALESCE(DET.FLAG_PEDIDO_OT,'0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT,'0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND      

         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  

         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')

	 )   
  
DECLARE @ls_parametro_fuente VARCHAR(1)  
DECLARE @ls_flag_procedencia VARCHAR(1)

SELECT @ls_parametro_fuente = sig_parametro_ejecutora.valor  
  FROM sig_parametro_ejecutora  
 WHERE sec_ejec    =  @pn_sec_ejec AND  
       cod_maestro = 'FLAG_FUENTE'
       
IF @ls_parametro_fuente IS NULL   
   BEGIN   
    SELECT @ls_parametro_fuente= '0'  
   END   

SELECT @ls_flag_procedencia = SIG_CONTRATOS.flag_procedencia
   FROM SIG_CONTRATOS
  WHERE ANO_EJE =  @pn_ano AND
        sec_ejec = @pn_sec_ejec AND
        tipo_contrato = @ps_tipo_contrato  AND
        NRO_CONTRATO = @pn_nro_contrato


 OPEN ccn_item  
 FETCH ccn_item INTO   
     @LN_ANO_EJE_I,@LN_SEC_EJEC_I,@LS_TIPO_CONTRATO_I,@LN_NRO_CONTRATO_I,   
        @LN_NRO_ITEM_I,@LS_TIPO_BIEN_I,@LS_GRUPO_BIEN_I,@LS_CLASE_BIEN_I,  
        @LS_FAMILIA_BIEN_I,@LS_ITEM_BIEN_I      
  
 WHILE @@FETCH_STATUS = 0  
 BEGIN  
           
   SELECT @ln_sec_periodo = MAX(SIG_CONTRATO_ITEM_MENSUAL.sec_periodo)  
   FROM SIG_CONTRATO_ITEM_MENSUAL  
   WHERE ANO_EJE = @LN_ANO_EJE_I  AND SEC_EJEC = @LN_SEC_EJEC_I AND   
         TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
         NRO_ITEM = @LN_NRO_ITEM_I  
     
   IF @ln_sec_periodo IS NULL   
   BEGIN   
      SELECT @ln_sec_periodo= 0  
   END   
     
  
    IF @ls_parametro_fuente = '1'
    BEGIN
    
    SELECT @ln_sec_periodo = @ln_sec_periodo + 1  
                 
   INSERT INTO sig_contrato_item_mensual  
            ( ano_eje    , sec_ejec   , tipo_contrato, nro_contrato  , nro_item,  
              sec_periodo, ano_proceso, mes_proceso  , cantidad      , valor_moneda, 
              valor_soles, fecha_reg  , cuser_id     , flag_proceso  , sec_movimiento, 
              fecha_pago,  flag_origen, tipo_cambio  , precio_moneda )  
   SELECT @LN_ANO_EJE_I         , @LN_SEC_EJEC_I, @LS_TIPO_CONTRATO_I, @LN_NRO_CONTRATO_I    , @LN_NRO_ITEM_I,            
          @ln_sec_periodo       , @pn_ano   , @ps_mes_periodo    , coalesce(sum(DET.cant_aprobada),0), coalesce(sum(DET.cant_aprobada),0),  
          coalesce(sum(DET.cant_aprobada),0), GETDATE()     , '1'                , 'N'                   , NULL,      
          @pd_fecha_pago        , '0'           , @pn_tipo_cambio    , 1 
    FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET  
   WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN   = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         DET.ANO_EJE =  @pn_ano AND    
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
         COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND    
       
         DET.TIPO_BIEN  = @LS_TIPO_BIEN_I AND  
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_I AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_I AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_I AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_I AND   
           
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec  AND  
         X.PERIODO  = @ps_mes_periodo  AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S') AND
	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mensual X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo)

 
        IF @@ERROR <> 0  
       	BEGIN  
	  CLOSE ccn_item  
	  DEALLOCATE ccn_item  
	  GOTO ERROR  
	END   
	
   END	

  IF @ls_parametro_fuente = '0'
    BEGIN

   SELECT @ln_sec_periodo = @ln_sec_periodo + 1  

   INSERT INTO sig_contrato_item_mensual  
            ( ano_eje, sec_ejec, tipo_contrato, nro_contrato, nro_item,  
           sec_periodo, ano_proceso, mes_proceso, cantidad, valor_moneda, valor_soles, 
           fecha_reg, cuser_id, flag_proceso, sec_movimiento, fecha_pago,  
           flag_origen, tipo_cambio, precio_moneda )  
   SELECT @LN_ANO_EJE_I, @LN_SEC_EJEC_I, @LS_TIPO_CONTRATO_I, @LN_NRO_CONTRATO_I, @LN_NRO_ITEM_I,            
         @ln_sec_periodo,                 @pn_ano,              @ps_mes_periodo,
         coalesce(sum(DET.cant_aprobada),0),coalesce(sum(DET.cant_aprobada),0), coalesce(sum(DET.cant_aprobada),0),  
         GETDATE(),      '1',             'N',       NULL,  @pd_fecha_pago,   
         '0',            @pn_tipo_cambio, 1 
   FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET ,
         SIG_METAS_X_CENTRO SMC 
   WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         PED.ANO_EJE = SMC.ANO_EJE AND     
         PED.SEC_EJEC = SMC.SEC_EJEC AND
         PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
         PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE =  @pn_ano AND    
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
         COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
         DET.TIPO_BIEN  = @LS_TIPO_BIEN_I AND  
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_I AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_I AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_I AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_I AND   
           
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec  AND  
         X.PERIODO  = @ps_mes_periodo  AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S') AND
	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mensual X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo)


        IF @@ERROR <> 0  
       	BEGIN  
	  CLOSE ccn_item  
	  DEALLOCATE ccn_item  
	  GOTO ERROR  
	END   
           
  END

     INSERT INTO SIG_CONTRATO_ITEM_MENS_PED        
      ( ano_eje, sec_ejec, tipo_contrato, nro_contrato, nro_item,sec_periodo,TIPO_PEDIDO,TIPO_BIEN,NRO_PEDIDO,SECUENCIA)  
     SELECT @LN_ANO_EJE_I, @LN_SEC_EJEC_I, @LS_TIPO_CONTRATO_I, @LN_NRO_CONTRATO_I, @LN_NRO_ITEM_I,@ln_sec_periodo,
     PED.TIPO_PEDIDO,PED.TIPO_BIEN, PED.NRO_PEDIDO,DET.SECUENCIA  
       FROM SIG_PEDIDOS PED,  
            SIG_DETALLE_PEDIDOS DET  
      WHERE PED.ANO_EJE = DET.ANO_EJE AND  
            PED.SEC_EJEC = DET.SEC_EJEC AND  
            PED.TIPO_BIEN = DET.TIPO_BIEN AND  
            PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
        DET.ANO_EJE =  @pn_ano AND    
            DET.SEC_EJEC = @pn_sec_ejec AND  
            DET.TIPO_BIEN = 'S'   AND  
            DET.TIPO_PEDIDO = '2' AND  
            COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
            COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND
            PED.ESTADO =  '2' AND  
            PED.ANO_EJE >= 2013  AND  
	    COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND           
            DET.TIPO_BIEN  = @LS_TIPO_BIEN_I AND  
            DET.GRUPO_BIEN = @LS_GRUPO_BIEN_I AND  
            DET.CLASE_BIEN = @LS_CLASE_BIEN_I AND  
            DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_I AND  
            DET.ITEM_BIEN    = @LS_ITEM_BIEN_I AND   
        
            PED.SEC_FUNC IN (   
            SELECT X.SEC_FUNC   
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE   
            X.ANO_EJE = @pn_ano AND  
            X.SEC_EJEC = @pn_sec_ejec  AND  
            X.PERIODO  = @ps_mes_periodo  AND  
	  X.PROCESO  = @pn_nro_proceso AND
            X.TIPO = 'M'  
            ) AND  
              
            DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
            SELECT X.CODIGO_ITEM  
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE   
            X.ANO_EJE = @pn_ano AND  
            X.SEC_EJEC = @pn_sec_ejec AND  
            X.PERIODO = @ps_mes_periodo AND  
	    X.PROCESO  = @pn_nro_proceso AND
            X.TIPO = 'I') AND  
              
            DET.CLASIFICADOR IN (  
            SELECT X.CLASIFICADOR  
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE  
            X.ANO_EJE  = @pn_ano AND  
            X.SEC_EJEC = @pn_sec_ejec AND  
            X.PERIODO  = @ps_mes_periodo AND  
	    X.PROCESO  = @pn_nro_proceso AND
            X.TIPO     = 'C') AND  
              
            PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO IN (  
            SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE  
            X.ANO_EJE  = @pn_ano AND  
            X.SEC_EJEC = @pn_sec_ejec AND  
            X.PERIODO  = @ps_mes_periodo AND  
	    X.PROCESO  = @pn_nro_proceso AND
            X.TIPO     = 'S')  
           
     UNION
           
     SELECT @LN_ANO_EJE_I, @LN_SEC_EJEC_I, @LS_TIPO_CONTRATO_I, @LN_NRO_CONTRATO_I, @LN_NRO_ITEM_I,
     @ln_sec_periodo, PED.TIPO_PEDIDO,PED.TIPO_BIEN, PED.NRO_PEDIDO,DET.SECUENCIA  
       FROM SIG_PEDIDOS PED,  
            SIG_DETALLE_PEDIDOS DET ,
            SIG_METAS_X_CENTRO SMC  
      WHERE PED.ANO_EJE = DET.ANO_EJE AND  
            PED.SEC_EJEC = DET.SEC_EJEC AND  
            PED.TIPO_BIEN = DET.TIPO_BIEN AND  
            PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
            PED.ANO_EJE = SMC.ANO_EJE AND     
            PED.SEC_EJEC = SMC.SEC_EJEC AND
            PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
            PED.SEC_FUNC = SMC.SEC_FUNC AND
            DET.ANO_EJE =  @pn_ano AND    
            DET.SEC_EJEC = @pn_sec_ejec AND  
            DET.TIPO_BIEN = 'S'   AND  
            DET.TIPO_PEDIDO = '2' AND  
            COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
            COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND
            PED.ESTADO =  '2' AND  
            PED.ANO_EJE >= 2013  AND  
            COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
            DET.TIPO_BIEN  = @LS_TIPO_BIEN_I AND  
            DET.GRUPO_BIEN = @LS_GRUPO_BIEN_I AND  
            DET.CLASE_BIEN = @LS_CLASE_BIEN_I AND  
            DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_I AND  
            DET.ITEM_BIEN    = @LS_ITEM_BIEN_I AND   
        
            PED.SEC_FUNC IN (   
            SELECT X.SEC_FUNC   
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE   
            X.ANO_EJE = @pn_ano AND  
            X.SEC_EJEC = @pn_sec_ejec  AND  
            X.PERIODO  = @ps_mes_periodo  AND  
	    X.PROCESO  = @pn_nro_proceso AND
            X.TIPO = 'M'  
            ) AND  
              
            DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
            SELECT X.CODIGO_ITEM  
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE   
            X.ANO_EJE = @pn_ano AND  
   X.SEC_EJEC = @pn_sec_ejec AND  
            X.PERIODO = @ps_mes_periodo AND  
	    X.PROCESO  = @pn_nro_proceso AND
            X.TIPO = 'I') AND  
              
            DET.CLASIFICADOR IN (  
            SELECT X.CLASIFICADOR  
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE  
            X.ANO_EJE  = @pn_ano AND  
            X.SEC_EJEC = @pn_sec_ejec AND  
            X.PERIODO  = @ps_mes_periodo AND  
	    X.PROCESO  = @pn_nro_proceso AND
            X.TIPO     = 'C') AND  
              
            PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO IN (  
            SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
            FROM TMP_PARAMETROS_CRON_OT X  
            WHERE  
      X.ANO_EJE  = @pn_ano AND  
            X.SEC_EJEC = @pn_sec_ejec AND  
            X.PERIODO  = @ps_mes_periodo AND  
	    X.PROCESO  = @pn_nro_proceso AND
            X.TIPO     = 'S')  
	GROUP BY PED.TIPO_PEDIDO,PED.TIPO_BIEN, PED.NRO_PEDIDO,DET.SECUENCIA 
	HAVING sum(DET.cant_aprobada) > 0
           
        IF @@ERROR <> 0  
       	BEGIN  
	  CLOSE ccn_item  
	  DEALLOCATE ccn_item  
	  GOTO ERROR  
	END   
        
           
        FETCH ccn_item INTO   
        @LN_ANO_EJE_I,@LN_SEC_EJEC_I,@LS_TIPO_CONTRATO_I,@LN_NRO_CONTRATO_I,   
        @LN_NRO_ITEM_I,@LS_TIPO_BIEN_I,@LS_GRUPO_BIEN_I,@LS_CLASE_BIEN_I,  
        @LS_FAMILIA_BIEN_I,@LS_ITEM_BIEN_I      
   
          
        IF @@ERROR <> 0  
       	BEGIN  
	  CLOSE ccn_item  
	  DEALLOCATE ccn_item  
	  GOTO ERROR  
	END   
END  
CLOSE ccn_item  
DEALLOCATE ccn_item  
  

OPEN ccn_item_mensual  
 FETCH ccn_item_mensual INTO   
     @LN_ANO_EJE_C,@LN_SEC_EJEC_C,@LS_TIPO_CONTRATO_C,@LN_NRO_CONTRATO_C,   
        @LN_NRO_ITEM_C,@LN_SEC_PERIODO_C,@LS_GRUPO_BIEN_C,@LS_CLASE_BIEN_C,  
        @LS_FAMILIA_BIEN_C,@LS_ITEM_BIEN_C   
  
 WHILE @@FETCH_STATUS = 0  
 BEGIN  
  
  SELECT @ln_sec_ppto = MAX(SEC_PPTO)  
    FROM sig_contrato_item_mens_pptal  
   WHERE ANO_EJE = @LN_ANO_EJE_C   AND SEC_EJEC = @LN_SEC_EJEC_C AND   
         TIPO_CONTRATO = @LS_TIPO_CONTRATO_C AND NRO_CONTRATO = @LN_NRO_CONTRATO_C AND   
         NRO_ITEM = @LN_NRO_ITEM_C AND SEC_PERIODO = @LN_SEC_PERIODO_C  
     
   IF @ln_sec_ppto IS NULL   
      BEGIN   
          SELECT @ln_sec_ppto =0  
      END  
     
      
   IF @ls_parametro_fuente = '1'
    BEGIN
    
       INSERT INTO sig_contrato_item_mens_pptal  
        (ano_eje,        sec_ejec,       tipo_contrato, nro_contrato, nro_item,     sec_periodo,  
        sec_ppto,       origen,         fuente_financ, sec_func,     clasificador, cantidad,  
        valor_moneda,   valor_adelanto, fecha_reg,     cuser_id,     tipo_uso,     tipo_uso_orig,  
        id_clasIFicador,tipo_impto,     tasa_impto,    fte_fto_impto, valor_soles)  
     
         SELECT @LN_ANO_EJE_C,  @LN_SEC_EJEC_C,  @LS_TIPO_CONTRATO_C, @LN_NRO_CONTRATO_C, @LN_NRO_ITEM_C, @LN_SEC_PERIODO_C,  
         @ln_sec_ppto + ROW_NUMBER() OVER(ORDER BY PED.SEC_FUNC DESC),  PED.ORIGEN      ,    PED.FUENTE_FTO, PED.SEC_FUNC,    DET.CLASIFICADOR,   coalesce(SUM(DET.cant_aprobada),0),                
         coalesce(SUM(DET.cant_aprobada),0),  0,             GETDATE(),          '1',             'C',             'C',  
         DET.id_clasificador,'0', 0, NULL , coalesce(SUM(DET.cant_aprobada),0)
         FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET  
         WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013 AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND           
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_C AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_C AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_C AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_C AND   
           
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
        
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')  AND

	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mens_pptal X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo and
	x.FUENTE_FINANC = PED.FUENTE_FTO AND
	X.SEC_FUNC =PED.SEC_FUNC AND
	X.CLASIFICADOR = DET.CLASIFICADOR)

     GROUP BY  PED.ORIGEN, PED.FUENTE_FTO, PED.SEC_FUNC, DET.CLASIFICADOR,   
                DET.id_clasificador    
  
     IF @@ERROR <> 0  
         BEGIN  
	  CLOSE ccn_item_mensual  
	  DEALLOCATE ccn_item_mensual  
	  GOTO ERROR  
        END   
        
    END


   IF @ls_parametro_fuente = '0'
    BEGIN
    
      INSERT INTO sig_contrato_item_mens_pptal  
        (ano_eje,        sec_ejec,       tipo_contrato, nro_contrato, nro_item,     sec_periodo,  
        sec_ppto,       origen,         fuente_financ, sec_func,     clasificador, cantidad,  
        valor_moneda,   valor_adelanto, fecha_reg,     cuser_id,     tipo_uso,     tipo_uso_orig,  
        id_clasIFicador,tipo_impto,     tasa_impto,    fte_fto_impto, valor_soles)  

       SELECT @LN_ANO_EJE_C,  @LN_SEC_EJEC_C,  @LS_TIPO_CONTRATO_C, @LN_NRO_CONTRATO_C, @LN_NRO_ITEM_C, @LN_SEC_PERIODO_C,  
         @ln_sec_ppto + ROW_NUMBER() OVER(ORDER BY PED.SEC_FUNC DESC), PED.ORIGEN,    SMC.FUENTE_FINANC, PED.SEC_FUNC,    DET.CLASIFICADOR, coalesce( SUM(DET.cant_aprobada),0),                
         coalesce(SUM(DET.cant_aprobada),0),  0,             GETDATE(),          '1',             'C',             '1',  
         DET.id_clasificador,'0', 0, NULL , coalesce(SUM(DET.cant_aprobada),0)
         FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET  ,
         SIG_METAS_X_CENTRO SMC  
         WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
	 PED.ANO_EJE = SMC.ANO_EJE AND     
	 PED.SEC_EJEC = SMC.SEC_EJEC AND
	 PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
	 PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_C AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_C AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_C AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_C AND   
           
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
        
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')  AND
	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mens_pptal X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo and
	x.FUENTE_FINANC = SMC.FUENTE_FINANC AND
	X.SEC_FUNC =SMC.SEC_FUNC AND
	X.CLASIFICADOR = DET.CLASIFICADOR)
     GROUP BY  PED.ORIGEN, SMC.FUENTE_FINANC, PED.SEC_FUNC, DET.CLASIFICADOR,   
               DET.id_clasificador    
	HAVING sum(DET.cant_aprobada) > 0

     IF @@ERROR <> 0  
         BEGIN  
	  CLOSE ccn_item_mensual  
	  DEALLOCATE ccn_item_mensual  
	  GOTO ERROR  
        END   
  END

     FETCH ccn_item_mensual INTO   
     @LN_ANO_EJE_C,@LN_SEC_EJEC_C,@LS_TIPO_CONTRATO_C,@LN_NRO_CONTRATO_C,   
        @LN_NRO_ITEM_C,@LN_SEC_PERIODO_C,@LS_GRUPO_BIEN_C,@LS_CLASE_BIEN_C,  
        @LS_FAMILIA_BIEN_C,@LS_ITEM_BIEN_C       
  
     IF @@ERROR <> 0  
        BEGIN  
	  CLOSE ccn_item_mensual  
	  DEALLOCATE ccn_item_mensual  
	  GOTO ERROR  
        END   
END   
CLOSE ccn_item_mensual  
DEALLOCATE ccn_item_mensual        
     

IF @ls_flag_procedencia = 'X'

BEGIN

IF @ps_flag_clcc = '1'
BEGIN  
DECLARE ccn_clasificador CURSOR FOR  
SELECT DISTINCT CTP.ANO_EJE,  
       CTP.SEC_EJEC,  
       CTP.TIPO_CONTRATO,  
       CTP.NRO_CONTRATO,  
       CTP.NRO_ITEM,  
       CTP.SEC_PERIODO,  
       CTP.SEC_PPTO,  
       CTI.GRUPO_BIEN,  
       CTI.CLASE_BIEN,  
       CTI.FAMILIA_BIEN,  
       CTI.ITEM_BIEN  
FROM   SIG_CONTRATO_ITEM_MENS_PPTAL CTP,   
       SIG_CONTRATO_ITEM_MENSUAL CTM,   
       SIG_CONTRATO_ITEM CTI,  
       SIG_CONTRATOS CTR         
WHERE  CTP.ano_eje  = @pn_ano AND  
       CTP.SEC_EJEC = @PN_SEC_EJEC AND  
       CTP.TIPO_CONTRATO = @PS_TIPO_CONTRATO AND  
       CTP.NRO_CONTRATO  = @PN_NRO_CONTRATO AND  
       CTP.ano_eje  >= 2013 AND  
       CTP.ANO_EJE      = CTM.ANO_EJE AND  
       CTP.SEC_EJEC     = CTM.SEC_EJEC AND  
       CTP.TIPO_CONTRATO= CTM.TIPO_CONTRATO AND  
       CTP.NRO_CONTRATO = CTM.NRO_CONTRATO AND  
       CTP.NRO_ITEM     = CTM.NRO_ITEM AND  
       CTP.SEC_PERIODO  = CTM.SEC_PERIODO AND  
       CTM.ANO_EJE  = CTI.ANO_EJE AND  
       CTM.SEC_EJEC     = CTI.SEC_EJEC AND  
       CTM.TIPO_CONTRATO= CTI.TIPO_CONTRATO AND  
       CTM.NRO_CONTRATO = CTI.NRO_CONTRATO AND  
       CTM.NRO_ITEM  = CTI.NRO_ITEM AND  
       CTI.ANO_EJE      = CTR.ANO_EJE AND  
       CTI.SEC_EJEC     = CTR.SEC_EJEC AND  
       CTI.TIPO_CONTRATO= CTR.TIPO_CONTRATO AND  
       CTI.NRO_CONTRATO = CTR.NRO_CONTRATO AND  
       CTR.TIPO_BIEN  = 'S' AND  
       CTR.FLAG_CONTR_OT = '1' AND  
       CTM.FECHA_PAGO = @pd_fecha_pago AND
       
   EXISTS( 
   SELECT PED.ANO_EJE  
   FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET  
   WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
        DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT,'0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND                      
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND               
      
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  

         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')
 
   UNION
 
   SELECT PED.ANO_EJE  
   FROM  SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET,
         SIG_METAS_X_CENTRO SMC   
   WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         PED.ANO_EJE = SMC.ANO_EJE AND     
         PED.SEC_EJEC = SMC.SEC_EJEC AND
         PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
 PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND               

         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  

         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
   X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')

         )   

    OPEN ccn_clasificador      
    FETCH ccn_clasificador INTO   
    @LN_ANO_EJE_S,@LN_SEC_EJEC_S,@LS_TIPO_CONTRATO_S,@LN_NRO_CONTRATO_S,   
    @LN_NRO_ITEM_S,@LN_SEC_PERIODO_S,@LN_SEC_PPTO_S,@LS_GRUPO_BIEN_S,  
    @LS_CLASE_BIEN_S,@LS_FAMILIA_BIEN_S,@LS_ITEM_BIEN_S   
  
    WHILE @@FETCH_STATUS = 0  
    BEGIN  
  
  
      SELECT @ln_sec_depend=MAX(SEC_DEPEND)  
      FROM sig_contrato_item_mens_depe  
      WHERE 
	ANO_EJE = @LN_ANO_EJE_S   AND   
	SEC_EJEC = @LN_SEC_EJEC_S AND   
	TIPO_CONTRATO = @LS_TIPO_CONTRATO_S AND   
	NRO_CONTRATO = @LN_NRO_CONTRATO_S AND   
	NRO_ITEM = @LN_NRO_ITEM_S AND   
	SEC_PERIODO = @LN_SEC_PERIODO_S AND   
	SEC_PPTO = @LN_SEC_PPTO_S  
     
      IF @ln_sec_depend IS NULL   
      BEGIN  
         SELECT @ln_sec_depend= 0  
      END   
  
      SELECT @ln_sec_depend= @ln_sec_depend + 1  
      
  
      INSERT INTO sig_contrato_item_mens_depe  
      (ano_eje,    sec_ejec,     tipo_contrato, nro_contrato,       nro_item,     sec_periodo,      sec_ppto,  
      sec_depend, centro_costo, tipo_tarea,    nivel_tarea,        codigo_tarea, cant_depend,      fecha_reg,  
      cuser_id,   equipo_reg,   valor_moneda,  valor_impto_moneda, valor_soles,  valor_impto_soles)  
     
      SELECT @LN_ANO_EJE_S, @LN_SEC_EJEC_S, @LS_TIPO_CONTRATO_S, @LN_NRO_CONTRATO_S, @LN_NRO_ITEM_S, @LN_SEC_PERIODO_S, @LN_SEC_PPTO_S,    
      @ln_sec_depend, PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA, coalesce(sum(DET.cant_aprobada),0),  GETDATE(),  
      '1',            '1Eq', coalesce(sum(DET.cant_aprobada),0),0, coalesce(sum(DET.cant_aprobada),0),       0  
      FROM 
      SIG_PEDIDOS PED,  
      SIG_DETALLE_PEDIDOS DET  
      WHERE 
	 PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
         COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013 AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND           
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_S AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_S AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_S AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_S AND   
                    
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO  IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')  AND
	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mens_depe X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo and
	x.SEC_PPTO = @LN_SEC_PPTO_S AND
	x.CENTRO_COSTO = PED.CENTRO_COSTO AND
	X.TIPO_TAREA =PED.TIPO_TAREA AND
	X.NIVEL_TAREA = PED.NIVEL_TAREA AND
	X.CODIGO_TAREA = PED.CODIGO_TAREA) 
         GROUP BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
         ORDER BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
  
         IF @@ERROR <> 0  
         BEGIN  
            CLOSE ccn_clasificador  
            DEALLOCATE ccn_clasificador  
            GOTO ERROR  
         END   


      SELECT @ln_sec_depend= @ln_sec_depend + 1  
  
      INSERT INTO sig_contrato_item_mens_depe  
      (ano_eje,    sec_ejec,     tipo_contrato, nro_contrato,       nro_item,     sec_periodo,      sec_ppto,  
      sec_depend, centro_costo, tipo_tarea,    nivel_tarea,        codigo_tarea, cant_depend,      fecha_reg,  
      cuser_id,   equipo_reg,   valor_moneda,  valor_impto_moneda, valor_soles,  valor_impto_soles)  
     
      SELECT @LN_ANO_EJE_S, @LN_SEC_EJEC_S, @LS_TIPO_CONTRATO_S, @LN_NRO_CONTRATO_S, @LN_NRO_ITEM_S, @LN_SEC_PERIODO_S, @LN_SEC_PPTO_S,    
      @ln_sec_depend, PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA, coalesce(sum(DET.cant_aprobada),0),  GETDATE(),  
      '1',            '1Eq', coalesce(sum(DET.cant_aprobada),0),0, coalesce(sum(DET.cant_aprobada),0),       0  
      FROM 
      SIG_PEDIDOS PED,  
      SIG_DETALLE_PEDIDOS DET  ,
      SIG_METAS_X_CENTRO SMC  
      WHERE 
	 PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND 
	 PED.ANO_EJE = SMC.ANO_EJE AND     
	 PED.SEC_EJEC = SMC.SEC_EJEC AND
	 PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
	 PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
         COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013 AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_S AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_S AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_S AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_S AND   
                    
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO  IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')  AND
	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mens_depe X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo and
	x.SEC_PPTO = @LN_SEC_PPTO_S AND
	x.CENTRO_COSTO = PED.CENTRO_COSTO AND
	X.TIPO_TAREA =PED.TIPO_TAREA AND
	X.NIVEL_TAREA = PED.NIVEL_TAREA AND
	X.CODIGO_TAREA = PED.CODIGO_TAREA) 

       GROUP BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
       ORDER BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
  
         IF @@ERROR <> 0  
         BEGIN  
            CLOSE ccn_clasificador  
            DEALLOCATE ccn_clasificador  
            GOTO ERROR  
         END   

  
        FETCH ccn_clasificador INTO   
        @LN_ANO_EJE_S,@LN_SEC_EJEC_S,@LS_TIPO_CONTRATO_S,@LN_NRO_CONTRATO_S,   
        @LN_NRO_ITEM_S,@LN_SEC_PERIODO_S,@LN_SEC_PPTO_S,@LS_GRUPO_BIEN_S,  
        @LS_CLASE_BIEN_S,@LS_FAMILIA_BIEN_S,@LS_ITEM_BIEN_S   
  
         IF @@ERROR <> 0  
         BEGIN  
            CLOSE ccn_clasificador  
            DEALLOCATE ccn_clasificador  
            GOTO ERROR  
         END   
     END
  
     CLOSE ccn_clasificador  
     DEALLOCATE ccn_clasificador
    
END 

END


IF @ls_flag_procedencia <> 'X'

BEGIN

IF @ps_flag_clcc = '1'
BEGIN

DECLARE ccn_clasificador_1 CURSOR FOR  
SELECT DISTINCT CTP.ANO_EJE,  
       CTP.SEC_EJEC,  
       CTP.TIPO_CONTRATO,  
       CTP.NRO_CONTRATO,  
       CTP.NRO_ITEM,  
       CTP.SEC_PERIODO,  
       CTP.SEC_PPTO
FROM   SIG_CONTRATO_ITEM_MENS_PPTAL CTP,   
       SIG_CONTRATO_ITEM_MENSUAL CTM,   
       SIG_CONTRATO_ITEM CTI,  
       SIG_CONTRATOS CTR         
WHERE  CTP.ano_eje  = @pn_ano AND  
       CTP.SEC_EJEC = @PN_SEC_EJEC AND  
       CTP.TIPO_CONTRATO = @PS_TIPO_CONTRATO AND  
       CTP.NRO_CONTRATO  = @PN_NRO_CONTRATO AND  
       CTP.ano_eje  >= 2013 AND  
     CTP.ANO_EJE      = CTM.ANO_EJE AND  
       CTP.SEC_EJEC     = CTM.SEC_EJEC AND  
       CTP.TIPO_CONTRATO= CTM.TIPO_CONTRATO AND  
       CTP.NRO_CONTRATO = CTM.NRO_CONTRATO AND  
       CTP.NRO_ITEM     = CTM.NRO_ITEM AND  
       CTP.SEC_PERIODO  = CTM.SEC_PERIODO AND  
       CTM.ANO_EJE  = CTI.ANO_EJE AND  
       CTM.SEC_EJEC     = CTI.SEC_EJEC AND  
       CTM.TIPO_CONTRATO= CTI.TIPO_CONTRATO AND  
       CTM.NRO_CONTRATO = CTI.NRO_CONTRATO AND  
       CTM.NRO_ITEM  = CTI.NRO_ITEM AND  
       CTI.ANO_EJE      = CTR.ANO_EJE AND  
       CTI.SEC_EJEC     = CTR.SEC_EJEC AND  
       CTI.TIPO_CONTRATO= CTR.TIPO_CONTRATO AND  
       CTI.NRO_CONTRATO = CTR.NRO_CONTRATO AND  
       CTR.TIPO_BIEN  = 'S' AND  
       CTR.FLAG_CONTR_OT = '1' AND  
       CTM.FECHA_PAGO = @pd_fecha_pago AND
       
   EXISTS( 
   SELECT PED.ANO_EJE  
   FROM SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET  
   WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT,'0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND                      
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND               
      
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  

         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')
 
   UNION
 
   SELECT PED.ANO_EJE  
   FROM  SIG_PEDIDOS PED,  
         SIG_DETALLE_PEDIDOS DET,
         SIG_METAS_X_CENTRO SMC   
   WHERE PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         PED.ANO_EJE = SMC.ANO_EJE AND     
  PED.SEC_EJEC = SMC.SEC_EJEC AND
         PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
         PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
	 COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013  AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN = CTI.GRUPO_BIEN  +  CTI.CLASE_BIEN  +  CTI.FAMILIA_BIEN  +  CTI.ITEM_BIEN AND               

         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  

         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')

         )   



    OPEN ccn_clasificador_1   
    FETCH ccn_clasificador_1 INTO   
    @LN_ANO_EJE_S_1,@LN_SEC_EJEC_S_1,@LS_TIPO_CONTRATO_S_1,@LN_NRO_CONTRATO_S_1,   
    @LN_NRO_ITEM_S_1,@LN_SEC_PERIODO_S_1,@LN_SEC_PPTO_S_1

    IF @@ERROR <> 0  
     BEGIN  
        CLOSE ccn_clasificador_1  
        DEALLOCATE ccn_clasificador_1 
        GOTO ERROR  
     END           

  
    WHILE @@FETCH_STATUS = 0  
    BEGIN  
      SELECT @ln_sec_depend=MAX(SEC_DEPEND)  
      FROM sig_contrato_item_mens_depe  
      WHERE 
	ANO_EJE = @LN_ANO_EJE_S_1   AND   
	SEC_EJEC = @LN_SEC_EJEC_S_1 AND   
	TIPO_CONTRATO = @LS_TIPO_CONTRATO_S_1 AND   
	NRO_CONTRATO = @LN_NRO_CONTRATO_S_1 AND   
	NRO_ITEM = @LN_NRO_ITEM_S_1 AND   
	SEC_PERIODO = @LN_SEC_PERIODO_S_1 AND   
	SEC_PPTO = @LN_SEC_PPTO_S_1  
     
      IF @ln_sec_depend IS NULL   
      BEGIN  
         SELECT @ln_sec_depend= 0  
      END   

      

      SELECT @ln_sec_depend= @ln_sec_depend + 1  
      
 
      INSERT INTO sig_contrato_item_mens_depe  
      (ano_eje,    sec_ejec,     tipo_contrato, nro_contrato,       nro_item,     sec_periodo,      sec_ppto,  
      sec_depend, centro_costo, tipo_tarea,    nivel_tarea,        codigo_tarea, cant_depend,      fecha_reg,  
      cuser_id,   equipo_reg,   valor_moneda,  valor_impto_moneda, valor_soles,  valor_impto_soles)  
     
      SELECT DISTINCT @LN_ANO_EJE_S_1, @LN_SEC_EJEC_S_1, @LS_TIPO_CONTRATO_S_1, @LN_NRO_CONTRATO_S_1, @LN_NRO_ITEM_S_1, @LN_SEC_PERIODO_S_1, @LN_SEC_PPTO_S_1,    
      @ln_sec_depend, PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA, coalesce(sum(DET.cant_aprobada),0),  GETDATE(),  
      '1',            '1Eq', coalesce(sum(DET.cant_aprobada),0),0, coalesce(sum(DET.cant_aprobada),0),       0  
      FROM 
      SIG_PEDIDOS PED,  
      SIG_DETALLE_PEDIDOS DET  
      WHERE 
	 PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
         COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013 AND  
         COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND    
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_S AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_S AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_S AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_S AND        
                    
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
         PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO  IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND 
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')  AND
	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mens_depe X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo and
	x.SEC_PPTO = @LN_SEC_PPTO_S_1 AND
	x.CENTRO_COSTO = PED.CENTRO_COSTO AND
	X.TIPO_TAREA =PED.TIPO_TAREA AND
	X.NIVEL_TAREA = PED.NIVEL_TAREA AND
	X.CODIGO_TAREA = PED.CODIGO_TAREA) 
         GROUP BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
         ORDER BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
  
         IF @@ERROR <> 0  
         BEGIN  
            CLOSE ccn_clasificador_1  
            DEALLOCATE ccn_clasificador_1  
            GOTO ERROR  
         END   
    
      SELECT @ln_sec_depend= @ln_sec_depend + 1  
  
      INSERT INTO sig_contrato_item_mens_depe  
      (ano_eje,    sec_ejec,     tipo_contrato, nro_contrato,       nro_item,     sec_periodo,      sec_ppto,  
      sec_depend, centro_costo, tipo_tarea,    nivel_tarea,        codigo_tarea, cant_depend,      fecha_reg,  
      cuser_id,   equipo_reg,   valor_moneda,  valor_impto_moneda, valor_soles,  valor_impto_soles)  
     
      SELECT DISTINCT @LN_ANO_EJE_S_1, @LN_SEC_EJEC_S_1, @LS_TIPO_CONTRATO_S_1, @LN_NRO_CONTRATO_S_1, @LN_NRO_ITEM_S_1, @LN_SEC_PERIODO_S_1, @LN_SEC_PPTO_S_1,    
      @ln_sec_depend, PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA, coalesce(sum(DET.cant_aprobada),0),  GETDATE(),  
      '1',            '1Eq', coalesce(sum(DET.cant_aprobada),0),0, coalesce(sum(DET.cant_aprobada),0),       0  
      FROM 
      SIG_PEDIDOS PED,  
      SIG_DETALLE_PEDIDOS DET  ,
      SIG_METAS_X_CENTRO SMC  
      WHERE 
	 PED.ANO_EJE = DET.ANO_EJE AND  
         PED.SEC_EJEC = DET.SEC_EJEC AND  
         PED.TIPO_BIEN = DET.TIPO_BIEN AND  
         PED.NRO_PEDIDO = DET.NRO_PEDIDO AND 
	 PED.ANO_EJE = SMC.ANO_EJE AND     
	 PED.SEC_EJEC = SMC.SEC_EJEC AND
	 PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
	 PED.SEC_FUNC = SMC.SEC_FUNC AND
         DET.ANO_EJE =  @pn_ano AND  
         DET.SEC_EJEC = @pn_sec_ejec AND  
         DET.TIPO_BIEN = 'S'   AND  
         DET.TIPO_PEDIDO = '2' AND  
         COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
         COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
         PED.ESTADO =  '2' AND  
         PED.ANO_EJE >= 2013 AND  
         COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
         DET.GRUPO_BIEN = @LS_GRUPO_BIEN_S AND  
         DET.CLASE_BIEN = @LS_CLASE_BIEN_S AND  
         DET.FAMILIA_BIEN = @LS_FAMILIA_BIEN_S AND  
         DET.ITEM_BIEN    = @LS_ITEM_BIEN_S AND   
                    
         PED.SEC_FUNC IN (   
         SELECT X.SEC_FUNC   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'M'  
         ) AND  
           
         DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
         SELECT X.CODIGO_ITEM  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE   
         X.ANO_EJE = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO = 'I') AND  
           
         DET.CLASIFICADOR IN (  
         SELECT X.CLASIFICADOR  
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'C') AND  
           
   PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO  IN (  
         SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
         FROM TMP_PARAMETROS_CRON_OT X  
         WHERE  
         X.ANO_EJE  = @pn_ano AND  
         X.SEC_EJEC = @pn_sec_ejec AND  
         X.PERIODO  = @ps_mes_periodo AND  
	 X.PROCESO  = @pn_nro_proceso AND
         X.TIPO     = 'S')  AND
	NOT EXISTS(SELECT X.ANO_EJE 
	FROM sig_contrato_item_mens_depe X
	WHERE
        X.ANO_EJE =  @pn_ano AND    
        X.SEC_EJEC = @pn_sec_ejec AND  
	X.TIPO_CONTRATO = @LS_TIPO_CONTRATO_I AND 
	X.NRO_CONTRATO = @LN_NRO_CONTRATO_I AND   
        X.NRO_ITEM = @LN_NRO_ITEM_I AND
	X.SEC_PERIODO = @ln_sec_periodo and
	x.SEC_PPTO = @LN_SEC_PPTO_S AND
	x.CENTRO_COSTO = PED.CENTRO_COSTO AND
	X.TIPO_TAREA =PED.TIPO_TAREA AND
	X.NIVEL_TAREA = PED.NIVEL_TAREA AND
	X.CODIGO_TAREA = PED.CODIGO_TAREA) 

       GROUP BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
       ORDER BY   PED.CENTRO_COSTO,  PED.TIPO_TAREA, PED.NIVEL_TAREA, PED.CODIGO_TAREA  
  
         IF @@ERROR <> 0  
         BEGIN  
            CLOSE ccn_clasificador_1  
            DEALLOCATE ccn_clasificador_1
            
            GOTO ERROR  
         END   

        FETCH ccn_clasificador_1 INTO   
        @LN_ANO_EJE_S_1,@LN_SEC_EJEC_S_1,@LS_TIPO_CONTRATO_S_1,@LN_NRO_CONTRATO_S_1,   
        @LN_NRO_ITEM_S_1,@LN_SEC_PERIODO_S_1,@LN_SEC_PPTO_S_1

  
        IF @@ERROR <> 0  
         BEGIN  
            CLOSE ccn_clasificador_1  
            DEALLOCATE ccn_clasificador_1 
            GOTO ERROR  
         END           
       
     END
  
CLOSE ccn_clasificador_1  
DEALLOCATE ccn_clasificador_1
     
     
END 

END


 
UPDATE SIG_DETALLE_PEDIDOS
SET FLAG_PROC_OT = '1'
WHERE
ANO_EJE =  @pn_ano AND  
SEC_EJEC = @pn_sec_ejec AND  
TIPO_BIEN = 'S'   AND  
TIPO_PEDIDO = '2' AND  
COALESCE(FLAG_PEDIDO_OT, '0') = '1' AND  
COALESCE(FLAG_PROC_OT, '0') = '0' AND
EXISTS( 
SELECT PED.ANO_EJE
FROM SIG_PEDIDOS PED,  
SIG_DETALLE_PEDIDOS DET  
WHERE 
PED.ANO_EJE = DET.ANO_EJE AND  
PED.SEC_EJEC = DET.SEC_EJEC AND  
PED.TIPO_BIEN = DET.TIPO_BIEN AND  
PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
 
SIG_DETALLE_PEDIDOS.ANO_EJE = DET.ANO_EJE AND  
SIG_DETALLE_PEDIDOS.SEC_EJEC = DET.SEC_EJEC AND  
SIG_DETALLE_PEDIDOS.TIPO_BIEN = DET.TIPO_BIEN AND  
SIG_DETALLE_PEDIDOS.TIPO_PEDIDO = DET.TIPO_PEDIDO AND  
SIG_DETALLE_PEDIDOS.SECUENCIA = DET.SECUENCIA AND
SIG_DETALLE_PEDIDOS.NRO_PEDIDO = DET.NRO_PEDIDO AND
 
DET.ANO_EJE =  @pn_ano AND  
DET.SEC_EJEC = @pn_sec_ejec AND  
DET.TIPO_BIEN = 'S'   AND  
DET.TIPO_PEDIDO = '2' AND  
COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
PED.ESTADO =  '2' AND  
PED.ANO_EJE >= 2013 AND  
COALESCE(PED.FUENTE_FTO, 'XX') <> 'XX' AND           
 
PED.SEC_FUNC IN (   
SELECT X.SEC_FUNC   
FROM TMP_PARAMETROS_CRON_OT X  
WHERE   
X.ANO_EJE  = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO  = @ps_mes_periodo AND 
X.PROCESO  = @pn_nro_proceso AND 
X.TIPO = 'M'  
) AND  
 
DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
SELECT X.CODIGO_ITEM  
FROM TMP_PARAMETROS_CRON_OT X  
WHERE   
X.ANO_EJE = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO = @ps_mes_periodo AND  
X.PROCESO  = @pn_nro_proceso AND
X.TIPO = 'I') AND  
 
DET.CLASIFICADOR IN (  
SELECT X.CLASIFICADOR  
FROM TMP_PARAMETROS_CRON_OT X  
WHERE  
X.ANO_EJE  = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO  = @ps_mes_periodo AND  
X.PROCESO  = @pn_nro_proceso AND
X.TIPO     = 'C') AND  
 
PED.CENTRO_COSTO  +  PED.FUENTE_FTO  +  PED.NRO_PEDIDO  IN (  
SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
FROM TMP_PARAMETROS_CRON_OT X  
WHERE  
X.ANO_EJE  = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO  = @ps_mes_periodo AND  
X.PROCESO  = @pn_nro_proceso AND
X.TIPO     = 'S')  


UNION

SELECT PED.ANO_EJE
FROM SIG_PEDIDOS PED,  
SIG_DETALLE_PEDIDOS DET  ,
SIG_METAS_X_CENTRO SMC  
WHERE 
PED.ANO_EJE = DET.ANO_EJE AND  
PED.SEC_EJEC = DET.SEC_EJEC AND  
PED.TIPO_BIEN = DET.TIPO_BIEN AND  
PED.NRO_PEDIDO = DET.NRO_PEDIDO AND  
PED.ANO_EJE = SMC.ANO_EJE AND     
PED.SEC_EJEC = SMC.SEC_EJEC AND
PED.CENTRO_COSTO = SMC.CENTRO_COSTO AND
PED.SEC_FUNC = SMC.SEC_FUNC AND
 
SIG_DETALLE_PEDIDOS.ANO_EJE = DET.ANO_EJE AND  
SIG_DETALLE_PEDIDOS.SEC_EJEC = DET.SEC_EJEC AND  
SIG_DETALLE_PEDIDOS.TIPO_BIEN = DET.TIPO_BIEN AND  
SIG_DETALLE_PEDIDOS.TIPO_PEDIDO = DET.TIPO_PEDIDO AND  
SIG_DETALLE_PEDIDOS.SECUENCIA = DET.SECUENCIA AND
SIG_DETALLE_PEDIDOS.NRO_PEDIDO = DET.NRO_PEDIDO AND
 
DET.ANO_EJE =  @pn_ano AND  
DET.SEC_EJEC = @pn_sec_ejec AND  
DET.TIPO_BIEN = 'S'   AND  
DET.TIPO_PEDIDO = '2' AND  
COALESCE(DET.FLAG_PEDIDO_OT, '0') = '1' AND  
COALESCE(DET.FLAG_PROC_OT, '0') = '0' AND  
PED.ESTADO =  '2' AND  
PED.ANO_EJE >= 2013 AND  
COALESCE(PED.FUENTE_FTO, 'XX') = 'XX' AND           
 
PED.SEC_FUNC IN (   
SELECT X.SEC_FUNC   
FROM TMP_PARAMETROS_CRON_OT X  
WHERE   
X.ANO_EJE  = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO  = @ps_mes_periodo AND 
X.PROCESO  = @pn_nro_proceso AND 
X.TIPO = 'M'  
) AND  
 
DET.GRUPO_BIEN  +  DET.CLASE_BIEN  +  DET.FAMILIA_BIEN  +  DET.ITEM_BIEN IN (   
SELECT X.CODIGO_ITEM  
FROM TMP_PARAMETROS_CRON_OT X  
WHERE   
X.ANO_EJE = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO = @ps_mes_periodo AND  
X.PROCESO  = @pn_nro_proceso AND
X.TIPO = 'I') AND  
 
DET.CLASIFICADOR IN (  
SELECT X.CLASIFICADOR  
FROM TMP_PARAMETROS_CRON_OT X  
WHERE  
X.ANO_EJE  = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO  = @ps_mes_periodo AND  
X.PROCESO  = @pn_nro_proceso AND
X.TIPO     = 'C') AND  
 
PED.CENTRO_COSTO  +  SMC.FUENTE_FINANC  +  PED.NRO_PEDIDO  IN (  
SELECT X.CENTRO_COSTO  +  X.FUENTE_FINANC  +  X.NRO_PEDIDO   
FROM TMP_PARAMETROS_CRON_OT X  
WHERE  
X.ANO_EJE  = @pn_ano AND  
X.SEC_EJEC = @pn_sec_ejec AND  
X.PERIODO  = @ps_mes_periodo AND  
X.PROCESO  = @pn_nro_proceso AND
X.TIPO     = 'S')  

)
 
IF @@ERROR <> 0  
BEGIN  
    GOTO ERROR  
END   


RETURN 0  
   
ERROR:  
   RETURN 1 


