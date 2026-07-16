CREATE PROCEDURE dbo.SP_CARGA_ORDEN_X_CC
(@pn_ano numeric, @pn_sec_ejec numeric, @pn_tipo_ppto numeric,
 @ps_mes varchar(2), @ls_tipo_proceso varchar(2),  @ln_identificador numeric)   
  
AS  

DECLARE @ls_tipo_bien VARCHAR(1)
DECLARE @ln_nro_orden NUMERIC

DECLARE @ls_centro_costo VARCHAR(800)
DECLARE @ls_cc_cadena    VARCHAR(800)
DECLARE @ls_cc_cadena_x  VARCHAR(800)
DECLARE @ls_separador    CHAR(1)
DECLARE @ln_cantidad     NUMERIC
DECLARE @lb_Exit         bit


IF @ls_tipo_proceso = '1'
BEGIN
DECLARE cc_orden CURSOR FOR 
SELECT  
a.tipo_bien,
a.nro_orden
FROM sig_orden_adquisicion a
WHERE 
( a.sec_ejec   = @pn_sec_ejec ) and         
( a.ano_eje    = @pn_ano )      and 
( a.tipo_bien  in ('B','S'))     and        
( a.tipo_ppto  = @pn_tipo_ppto ) and         
( a.mes_calend = @ps_mes ) 
ORDER BY 1,2

 OPEN cc_orden  
 FETCH cc_orden INTO @ls_tipo_bien,@ln_nro_orden
 
 WHILE @@FETCH_STATUS = 0  
 BEGIN  
         SELECT @lb_Exit = 0
         
 		 DECLARE  ccn_item CURSOR FOR  
		  SELECT DISTINCT 
		         coalesce(SIG_CENTRO_COSTO.ABREVIADO_DEPEND,'.')   
 		    FROM SIG_ORDEN_ADQUISICION,   
		         SIG_DETALLE_BSERV_CUADRO,   
		         SIG_DETALLE_METAS_CUADRO,   
		         SIG_DEPEN_META_CUADRO,   
		         SIG_CENTRO_COSTO   
		   WHERE ( SIG_ORDEN_ADQUISICION.ANO_CUADRO = SIG_DETALLE_BSERV_CUADRO.ANO_EJE ) and  
		         ( SIG_ORDEN_ADQUISICION.SEC_EJEC = SIG_DETALLE_BSERV_CUADRO.SEC_EJEC ) and  
		         ( SIG_ORDEN_ADQUISICION.TIPO_BIEN = SIG_DETALLE_BSERV_CUADRO.TIPO_BIEN ) and  
		         ( SIG_ORDEN_ADQUISICION.SEC_CUADRO = SIG_DETALLE_BSERV_CUADRO.SEC_CUADRO ) and  
		         ( SIG_DETALLE_BSERV_CUADRO.ANO_EJE = SIG_DETALLE_METAS_CUADRO.ANO_EJE ) and  
		         ( SIG_DETALLE_BSERV_CUADRO.SEC_EJEC = SIG_DETALLE_METAS_CUADRO.SEC_EJEC ) and  
		         ( SIG_DETALLE_BSERV_CUADRO.TIPO_BIEN = SIG_DETALLE_METAS_CUADRO.TIPO_BIEN ) and  
		         ( SIG_DETALLE_BSERV_CUADRO.SEC_CUADRO = SIG_DETALLE_METAS_CUADRO.SEC_CUADRO ) and  
		         ( SIG_DETALLE_BSERV_CUADRO.SECUENCIA = SIG_DETALLE_METAS_CUADRO.SECUENCIA ) and 
		         ( SIG_DEPEN_META_CUADRO.ANO_EJE = SIG_DETALLE_METAS_CUADRO.ANO_EJE ) and  
		         ( SIG_DEPEN_META_CUADRO.SEC_EJEC = SIG_DETALLE_METAS_CUADRO.SEC_EJEC ) and  
		         ( SIG_DEPEN_META_CUADRO.TIPO_BIEN = SIG_DETALLE_METAS_CUADRO.TIPO_BIEN ) and  
		         ( SIG_DEPEN_META_CUADRO.SEC_CUADRO = SIG_DETALLE_METAS_CUADRO.SEC_CUADRO ) and  
		         ( SIG_DEPEN_META_CUADRO.SECUENCIA = SIG_DETALLE_METAS_CUADRO.SECUENCIA ) and  
		         ( SIG_DEPEN_META_CUADRO.SEC_META = SIG_DETALLE_METAS_CUADRO.SEC_META ) and  
		         ( SIG_DEPEN_META_CUADRO.ANO_EJE = SIG_CENTRO_COSTO.ANO_EJE ) and  
		         ( SIG_DEPEN_META_CUADRO.SEC_EJEC = SIG_CENTRO_COSTO.SEC_EJEC ) and  
		         ( SIG_DEPEN_META_CUADRO.CENTRO_COSTO = SIG_CENTRO_COSTO.CENTRO_COSTO ) and 
		         ( ( SIG_ORDEN_ADQUISICION.SEC_EJEC = @pn_sec_ejec ) AND  
		         ( SIG_ORDEN_ADQUISICION.ANO_EJE    = @pn_ano ) AND  
		         ( SIG_ORDEN_ADQUISICION.TIPO_BIEN  = @ls_tipo_bien ) AND  
		         ( SIG_ORDEN_ADQUISICION.NRO_ORDEN  = @ln_nro_orden ) AND  
		         ( SIG_ORDEN_ADQUISICION.TIPO_PPTO  = @pn_tipo_ppto ) )  

         OPEN ccn_item  
	     FETCH ccn_item INTO @ls_centro_costo    
	     
	     SELECT @ls_cc_cadena = ' '
	     SELECT @ls_cc_cadena_x = ''
	     
 
		 WHILE @@FETCH_STATUS = 0 AND @lb_Exit = 0
		 BEGIN  
   	       SELECT @ls_cc_cadena = @ls_cc_cadena + @ls_centro_costo + ' , '
		   FETCH ccn_item INTO @ls_centro_costo   
		   
		   SELECT @ln_cantidad = LEN(@ls_cc_cadena) + LEN(@ls_centro_costo) 
   	       IF @ln_cantidad > 256 
   	          BEGIN
   	            SELECT @lb_Exit = 1
   	          END
		   
		   IF @@ERROR <> 0  
		      BEGIN  
				  CLOSE ccn_item  
				  DEALLOCATE ccn_item  
				  GOTO ERROR  
			  END   
		 END 
	 
         IF len(@ls_cc_cadena) > 2  
	      BEGIN
            SELECT @ls_cc_cadena_x = substring(@ls_cc_cadena,1,len(@ls_cc_cadena) - 2)    
          END 
        
		 INSERT INTO TMP_ORDEN_X_CC  
		        (ano_eje,sec_ejec,TIPO_BIEN,TIPO_PPTO,NRO_ORDEN,NOMBRE_CC_ORD,NRO_MES,IDENTIFICADOR ) 
		 VALUES (@pn_ano,@pn_sec_ejec,@ls_tipo_bien,@pn_tipo_ppto,@ln_nro_orden,@ls_cc_cadena_x,@ps_mes,@Ln_identificador)       
		
			IF @@ERROR <> 0  
			     BEGIN  
				  CLOSE ccn_item  
				  DEALLOCATE ccn_item  
				  GOTO ERROR  
			     END            
	 
		 CLOSE ccn_item  
		 DEALLOCATE ccn_item  
		 
  FETCH cc_orden INTO @ls_tipo_bien,@ln_nro_orden
  
 END  
 
 CLOSE cc_orden 
 DEALLOCATE cc_orden

END

IF @ls_tipo_proceso = '2' 
BEGIN
 DELETE FROM TMP_ORDEN_X_CC 
  WHERE ANO_EJE  = @pn_ano AND 
        SEC_EJEC  = @pn_sec_ejec AND 
        TIPO_PPTO = @pn_tipo_ppto AND
        NRO_MES  = @ps_mes AND 
        IDENTIFICADOR = @ln_identificador
	IF @@ERROR <> 0  
			     BEGIN  
				  CLOSE ccn_item  
				  DEALLOCATE ccn_item  
				  GOTO ERROR  
			     END           
END


RETURN 0  
   
ERROR:  
   RETURN 1 

