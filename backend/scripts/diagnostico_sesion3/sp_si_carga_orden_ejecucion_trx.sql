CREATE PROCEDURE dbo.SP_SI_CARGA_ORDEN_EJECUCION_TRX
     @P_ANO_EJE			  NUMERIC(4,0),
     @P_SEC_EJEC		  NUMERIC(6,0),
     @fecha_carga_inicio  VARCHAR(10), 
     @fecha_carga_fin     VARCHAR(10),
     @usuario_n           varchar(30),
     @O_ERR_NUM			  NUMERIC(6,0) OUTPUT,
     @O_ERR_MSG			  VARCHAR(255) OUTPUT 
 AS        
 DECLARE @fecha_carga_inicio_1         DATETIME
 DECLARE @fecha_carga_fin_1            DATETIME
 
 DECLARE @LN_ID_SI_ORDEN            NUMERIC(10,0)
 DECLARE @LN_ID_SI_ORDEN_DETA       NUMERIC(10,0)
 DECLARE @LS_NOM_PROVEEDOR         VARCHAR(100)
 DECLARE @LS_PROVEEDOR_GIRO        VARCHAR(250)
 DECLARE @LN_NRO_ORDEN              NUMERIC(7,0)
 DECLARE @LC_TIPO_BIEN              CHAR(1)
 DECLARE @LC_NOMBRE_ITEM            VARCHAR(100)
 DECLARE @LC_NOMBRE_UM              VARCHAR(100)
 DECLARE @LC_ITEM_CATALOGO          VARCHAR(20)
 DECLARE @LC_FUNCION                CHAR(2)
 DECLARE @LC_PROGRAMA               CHAR(3)
 DECLARE @LC_SUB_PROGRAMA           CHAR(4)
 DECLARE @LC_ACT_PROY               CHAR(7)
 DECLARE @LC_COMPONENTE				CHAR(7)
 DECLARE @LC_META                   VARCHAR(5)
 DECLARE @LN_MONTO_META             NUMERIC(19,2)
 DECLARE @LN_CANTIDAD_META			NUMERIC(20,3)
 DECLARE @LC_UNIDAD_MEDIDA_META     NUMERIC(3,0)
 DECLARE @LC_D_UNIDAD_MEDIDA_META   VARCHAR(100)
 DECLARE @LC_DEPARTAMENTO           CHAR(2)
 DECLARE @LC_PROVINCIA              CHAR(2)
 DECLARE @LC_DISTRITO               CHAR(2)
 DECLARE @LC_FINALIDAD              CHAR(5)
 DECLARE @LC_D_FINALIDAD            VARCHAR(250)
 DECLARE @LC_PROGRAMA_INSTITUCIONAL VARCHAR(6)
 DECLARE @LN_CANT_ITEM              NUMERIC(16,6)
 DECLARE @LN_PRECIO_TOTAL           NUMERIC(16,2)
 DECLARE @LD_FECHA_INI              DATETIME
 DECLARE @LD_FECHA_FIN              DATETIME
 DECLARE @LD_FECHA_ORDEN            DATETIME
 DECLARE @LS_CONCEPTO               VARCHAR(350)
 DECLARE @LN_MNTO_SUBTOTAL          NUMERIC(16,2)
 DECLARE @LN_MNTO_DESCUENTO         NUMERIC(16,2)
 DECLARE @LN_MNTO_TOTAL             NUMERIC(16,2)
 DECLARE @LS_NRO_CONTRATO           VARCHAR(50)
 DECLARE @LD_FECHA_CONTRATO         DATETIME
 DECLARE @LS_DOCUM_REFERENCIA       VARCHAR(100)
 DECLARE @LN_EXP_SIAF               NUMERIC(10,0)
 DECLARE @LS_NRO_PROC_SEL           VARCHAR(50)
 DECLARE @LS_GLOSA                  varchar(3000)
 DECLARE @LC_ESTADO                 CHAR(1)
 DECLARE @LC_ESTADO_SIAF            CHAR(1)
 DECLARE @LN_SEC_FUNC               NUMERIC(4,0)
 DECLARE @LS_CLASIFICADOR           VARCHAR(20)
 DECLARE @LS_FUENTE_FINANC          VARCHAR(2)
 DECLARE @LC_GRUPO_BIEN             CHAR(2)
 DECLARE @LC_CLASE_BIEN             CHAR(2)
 DECLARE @LC_FAMILIA_BIEN           CHAR(4)
 DECLARE @LC_ITEM_BIEN              CHAR(4)
 DECLARE @LN_PREC_UNIT_MONEDA       NUMERIC(16,6)
 DECLARE @LN_PREC_TOT_SOLES         NUMERIC(16,2)
 DECLARE @LN_UNIDAD_MEDIDA          NUMERIC(3,0)
 DECLARE @LN_MARCA                  NUMERIC(5,0)
 DECLARE @LC_TIPO_MARCA             CHAR(1)
 DECLARE @LS_ESPECIFICACIONES       varchar(3000)
 DECLARE @LN_CANT_ARTICULO          NUMERIC(16,6)
 DECLARE @LN_MNTO_SOLES             NUMERIC(16,2)
 DECLARE @LN_TIPO_PPTO		    NUMERIC(2,0)
 DECLARE @LS_RUC_PROVEEDOR  	VARCHAR(11)

 
 BEGIN
     SET @fecha_carga_inicio_1 = Convert(DATETIME, @fecha_carga_inicio, 101)
     SET @fecha_carga_fin_1    = Convert(DATETIME, @fecha_carga_fin, 101)                                                             
     
     DELETE FROM SI_ORDEN_DETA_TRX
     DELETE FROM SI_ORDEN_TRX
 
     SELECT @LN_ID_SI_ORDEN = MAX(ID_SI_ORDEN) 
       FROM SI_ORDEN_TRX
      WHERE ANO_EJE  = @P_ANO_EJE AND SEC_EJEC = @P_SEC_EJEC
	 
     IF @LN_ID_SI_ORDEN IS NULL
	 SET @LN_ID_SI_ORDEN = 0
 
     --Cursor de órdenes.  ESTADO=1: Orden Comprometida, ESTADO_SIAF=2: Orden Aprobada por SIAF
     DECLARE C_1 CURSOR FOR
        SELECT 		    
		    A.NRO_ORDEN,
		    A.TIPO_BIEN,
		    A.TIPO_PPTO,
		    A.FECHA_ORDEN,
		    A.CONCEPTO CONCEPTO_ORDEN,
		    B.NRO_RUC PROVEEDOR_NRO_RUC,
		    dbo.f_elimina_tabs(B.NOMBRE_PROV) D_PROVEEDOR,
		    B.GIRO_GENERAL PROVEEDOR_GIRO,
		    A.SUBTOTAL_MONEDA MONTO_SUBTOTAL,
		    A.TOTAL_IGV_MONEDA MONTO_DESCUENTO,
		    A.TOTAL_FACT_MONEDA MONTO_TOTAL,
		    A.NRO_CONTRATO,
		    NULL FECHA_CONTRATO,
		    A.DOCUM_REFERENCIA DOCUMENTO_REFERENCIA,
		    A.EXP_SIAF EXPEDIENTE_SIAF,
		    A.NRO_PROC_SEL NRO_PROCESO_SELECCION,
		    dbo.f_elimina_tabs(A.GLOSA) GLOSA_ORDEN,
		    A.ESTADO ESTADO_ORDEN,
		    A.ESTADO_SIAF		    
		FROM SIG_ORDEN_ADQUISICION A
		JOIN SIG_CONTRATISTAS B
		    ON B.PROVEEDOR = A.PROVEEDOR
		WHERE A.ANO_EJE  = @P_ANO_EJE AND
		      A.SEC_EJEC = @P_SEC_EJEC       
        
     OPEN C_1
     FETCH NEXT FROM C_1
     INTO @LN_NRO_ORDEN,	     @LC_TIPO_BIEN,		     @LN_TIPO_PPTO,		@LD_FECHA_ORDEN,	
     	  @LS_CONCEPTO,          @LS_RUC_PROVEEDOR,	     @LS_NOM_PROVEEDOR,	@LS_PROVEEDOR_GIRO, 
     	  @LN_MNTO_SUBTOTAL,  	 @LN_MNTO_DESCUENTO, 	 @LN_MNTO_TOTAL,	@LS_NRO_CONTRATO,   
     	  @LD_FECHA_CONTRATO,    @LS_DOCUM_REFERENCIA,   @LN_EXP_SIAF,		@LS_NRO_PROC_SEL, 
    	  @LS_GLOSA, @LC_ESTADO, @LC_ESTADO_SIAF
 
     WHILE @@FETCH_STATUS = 0
     BEGIN
		SET @LN_ID_SI_ORDEN = @LN_ID_SI_ORDEN + 1
		INSERT INTO SI_ORDEN_TRX
			(ANO_EJE, SEC_EJEC, ID_SI_ORDEN, NRO_ORDEN, TIPO_BIEN, FECHA_ORDEN, CONCEPTO_ORDEN,                      
			PROVEEDOR_NRO_RUC, D_PROVEEDOR, PROVEEDOR_GIRO,                                                        
			MONTO_SUBTOTAL, MONTO_DESCUENTO, MONTO_TOTAL,                                                           
			NRO_CONTRATO, FECHA_CONTRATO, DOCUMENTO_REFERENCIA, EXPEDIENTE_SIAF,                                    
			NRO_PROCESO_SELECCION, GLOSA_ORDEN, ESTADO_ORDEN, ESTADO_SIAF,                                          
			FECHA_CARGA_INICIO, FECHA_CARGA_FIN, FECHA_ENVIO, USUARIO_ENVIO)                                               
		VALUES      
			(@P_ANO_EJE, @P_SEC_EJEC, @LN_ID_SI_ORDEN, @LN_NRO_ORDEN, @LC_TIPO_BIEN, @LD_FECHA_ORDEN, @LS_CONCEPTO,        
			@LS_RUC_PROVEEDOR, @LS_NOM_PROVEEDOR,  @LS_PROVEEDOR_GIRO, 
			@LN_MNTO_SUBTOTAL, @LN_MNTO_DESCUENTO, @LN_MNTO_TOTAL,  
			@LS_NRO_CONTRATO,  @LD_FECHA_CONTRATO, @LS_DOCUM_REFERENCIA, @LN_EXP_SIAF,                               
			@LS_NRO_PROC_SEL,  @LS_GLOSA, @LC_ESTADO, @LC_ESTADO_SIAF,                                               
			@fecha_carga_inicio_1, @fecha_carga_fin_1, Getdate(), @usuario_n)                                  
                                                                                                                  
	--CURSOR DE DETALLE_ORDEN                                                                            
		DECLARE C_2 CURSOR FOR                                                                                   
		 SELECT OIP.SEC_FUNC,                                                                                 
	                OIP.CLASIFICADOR,                                                                             
	                OIP.FUENTE_FINANC,                                                                            
	                OI.GRUPO_BIEN,                                                                                
	                OI.CLASE_BIEN,                                                                                
	                OI.FAMILIA_BIEN,                                                                              
	                OI.ITEM_BIEN,                                                                                 
	                OI.CANT_ITEM,                                                                                 
	                OI.PREC_UNIT_MONEDA,                                                                          
	                OI.PREC_TOT_SOLES,                                                                            
	                OI.UNIDAD_MEDIDA,                                                                             
	                OI.MARCA,                                                                                     
	                OI.TIPO_MARCA,                                                                                
	                dbo.f_elimina_tabs(OI.ESPECIFICACIONES) ESPECIFICACIONES,                                                                          
	                OIP.CANT_ARTICULO,                                                                            
	                OIP.MNTO_SOLES,
	                OIP.TIPO_PPTO                                                                                
		 FROM SIG_ORDEN_ITEM_PPTO OIP,                                                                        
		      SIG_ORDEN_ITEM OI                                                                               
		WHERE OIP.ANO_EJE   = OI.ANO_EJE      
		  AND OIP.SEC_EJEC  = OI.SEC_EJEC                                                                    
		  AND OIP.NRO_ORDEN = OI.NRO_ORDEN                                                                   
		  AND OIP.TIPO_BIEN = OI.TIPO_BIEN                                                                   
	 	  AND OIP.SEC_ITEM  = OI.SEC_ITEM                                                                    
		  AND OI.ANO_EJE    = @P_ANO_EJE                                                                     
		  AND OI.SEC_EJEC   = @P_SEC_EJEC                                                                    
		  AND OI.NRO_ORDEN  = @LN_NRO_ORDEN                                                                  
		  AND OI.TIPO_BIEN  = @LC_TIPO_BIEN                                             
		ORDER BY OIP.SEC_ITEM     		             
                                                                                                                  
        OPEN C_2                                                                                                 
        FETCH NEXT FROM C_2 INTO 
		@LN_SEC_FUNC,     @LS_CLASIFICADOR, 	@LS_FUENTE_FINANC, 	@LC_GRUPO_BIEN, 		@LC_CLASE_BIEN, 	
		@LC_FAMILIA_BIEN, @LC_ITEM_BIEN,  		@LN_CANT_ITEM,  	@LN_PREC_UNIT_MONEDA, 	@LN_PREC_TOT_SOLES,
		@LN_UNIDAD_MEDIDA,@LN_MARCA, 			@LC_TIPO_MARCA, 	@LS_ESPECIFICACIONES, 	@LN_CANT_ARTICULO, 
		@LN_MNTO_SOLES,   @LN_TIPO_PPTO                                                  
                                                                                                                  
        WHILE @@FETCH_STATUS = 0                    
        BEGIN                                                                                                    
		SET @LC_ITEM_CATALOGO = @LC_GRUPO_BIEN + @LC_CLASE_BIEN + @LC_FAMILIA_BIEN + @LC_ITEM_BIEN           
		set @LC_NOMBRE_ITEM = ''
		set @LC_NOMBRE_UM   = ''

              --CAMPOS DE META SEGUN AÑO, EJECUTORA Y SEC_FUNC                                                 
              SELECT @LC_FUNCION                = ME.FUNCION,                                                     
                     @LC_PROGRAMA               = ME.PROGRAMA,                         
                     @LC_SUB_PROGRAMA           = ME.SUB_PROGRAMA,                                                
                     @LC_ACT_PROY               = ME.ACT_PROY,                                                    
                     @LC_COMPONENTE             = ME.COMPONENTE,                                             
                     @LC_META                   = ME.META,                                                        
                     @LN_MONTO_META             = ME.MONTO,                                                       
                     @LN_CANTIDAD_META          = ME.CANTIDAD,                                                    
                     @LC_UNIDAD_MEDIDA_META     = ME.UNIDAD_MEDIDA,                                               
                     @LC_DEPARTAMENTO           = ME.DEPARTAMENTO,                                                
                     @LC_PROVINCIA              = ME.PROVINCIA,                                                   
                     @LC_DISTRITO               = ME.DISTRITO,                                                    
                     @LC_PROGRAMA_INSTITUCIONAL = ME.PROGRAMA_INSTITUCIONAL,                                      
                     @LC_FINALIDAD              = ME.FINALIDAD                                                    
                FROM META ME                                                                                      
               WHERE ME.ANO_EJE  = @P_ANO_EJE                                              
                 AND ME.SEC_EJEC = @P_SEC_EJEC   
                 AND ME.SEC_FUNC = @LN_SEC_FUNC                                                                  
			
					
                SELECT @LC_D_UNIDAD_MEDIDA_META = M.NOMBRE 
                  FROM UNIDAD_MEDIDA M
                 WHERE M.UNIDAD_MEDIDA = @LN_UNIDAD_MEDIDA


               SELECT @LC_D_FINALIDAD= F.NOMBRE 
                 FROM FINALIDAD F
                WHERE F.ANO_EJE = @P_ANO_EJE 
                  AND F.FINALIDAD=( SELECT FINALIDAD
                                      FROM META
                                     WHERE ANO_EJE  = @P_ANO_EJE 
                                       AND SEC_EJEC = @P_SEC_EJEC
                                       AND SEC_FUNC = @LN_SEC_FUNC )
                		
		
		
			 
		        SET @LN_CANT_ITEM  = @LN_CANT_ARTICULO                                                            
				SET @LN_PRECIO_TOTAL = @LN_MNTO_SOLES                                                            
		                                                               
		                                                                                                                  
		        --MAXIMO SECUENCIAL EN SI_ORDEN_DETA                                                             
		        SELECT @LN_ID_SI_ORDEN_DETA = MAX(SIOD.ID_SI_ORDEN_DETA)                                            
				  FROM SI_ORDEN_DETA_TRX SIOD                                                                             
			     WHERE SIOD.ANO_EJE= @P_ANO_EJE  AND SIOD.SEC_EJEC = @P_SEC_EJEC                                                                   
				   AND SIOD.ID_SI_ORDEN = @LN_ID_SI_ORDEN                                                            
		                                                                                                                  
		        IF @LN_ID_SI_ORDEN_DETA IS NULL  SET @LN_ID_SI_ORDEN_DETA = 0                                                                       
		                                                                                    
				SET @LN_ID_SI_ORDEN_DETA = @LN_ID_SI_ORDEN_DETA + 1 

	                                                               
                                                                                                                  
              INSERT INTO SI_ORDEN_DETA_TRX
              (ANO_EJE,		   SEC_EJEC,	   ID_SI_ORDEN,			 ID_SI_ORDEN_DETA,		  NRO_ORDEN,				TIPO_BIEN,                                 
               ITEM_CATALOGO,  D_ITEM_CATALOGO,GRUPO_BS,			 CLASE_BS,FAMILIA_BS,	  ITEM_BS,					CANTIDAD_ITEM_BS,
               PRECIO_UNITARIO,PRECIO_TOTAL,   UNIDAD_MEDIDA_ITEM_BS,D_UNIDAD_MEDIDA_ITEM_BS, ESPECIFICACIONES_ITEM_BS, SEC_FUNC,                          
               CLASIFICADOR,   FUENTE_FINANCIAMIENTO,FUNCION,		 PROGRAMA,				  SUB_PROGRAMA,				ACT_PROY,
               COMPONENTE,     META,		   UNIDAD_MEDIDA_META,	 D_UNIDAD_MEDIDA_META,    DEPARTAMENTO_META,		PROVINCIA_META,
               DISTRITO_META,  FINALIDAD,	   D_FINALIDAD,			 PROGRAMA_INSTITUCIONAL,  FECHA_CARGA_INICIO, 		FECHA_CARGA_FIN, 
               FECHA_ENVIO,    USUARIO_ENVIO)
              VALUES                                                                                              
              (@P_ANO_EJE, 	    @P_SEC_EJEC,     @LN_ID_SI_ORDEN, 	 @LN_ID_SI_ORDEN_DETA,    @LN_NRO_ORDEN,		     @LC_TIPO_BIEN,        
               @LC_ITEM_CATALOGO,@LC_NOMBRE_ITEM, @LC_GRUPO_BIEN, 	 @LC_CLASE_BIEN, 		  @LC_FAMILIA_BIEN, 		 @LC_ITEM_BIEN, 
               @LN_CANT_ITEM,    @LN_PREC_UNIT_MONEDA,@LN_PRECIO_TOTAL,@LN_UNIDAD_MEDIDA, 	  @LC_D_UNIDAD_MEDIDA_META,  @LS_ESPECIFICACIONES,                                            
               @LN_SEC_FUNC, 	 @LS_CLASIFICADOR,@LS_FUENTE_FINANC, @LC_FUNCION, 			  @LC_PROGRAMA, 			 @LC_SUB_PROGRAMA, 
               @LC_ACT_PROY,	 @LC_COMPONENTE,  @LC_META,  		 @LC_UNIDAD_MEDIDA_META,  @LC_D_UNIDAD_MEDIDA_META,  @LC_DEPARTAMENTO, 
               @LC_PROVINCIA, 	 @LC_DISTRITO,    @LC_FINALIDAD, 	 @LC_D_FINALIDAD,  		  @LC_PROGRAMA_INSTITUCIONAL,@fecha_carga_inicio_1, 
               @fecha_carga_fin_1,Getdate(), 	  @usuario_n )             
                            
	     -- SELECT @LS_SUBFIN=''     
                                                                                            
               FETCH NEXT FROM C_2                                                                                
               INTO 	@LN_SEC_FUNC,     @LS_CLASIFICADOR, 	@LS_FUENTE_FINANC, 	@LC_GRUPO_BIEN, 		@LC_CLASE_BIEN, 	
						@LC_FAMILIA_BIEN, @LC_ITEM_BIEN,  		@LN_CANT_ITEM,  	@LN_PREC_UNIT_MONEDA, 	@LN_PREC_TOT_SOLES,
						@LN_UNIDAD_MEDIDA,@LN_MARCA, 			@LC_TIPO_MARCA, 	@LS_ESPECIFICACIONES, 	@LN_CANT_ARTICULO, 
						@LN_MNTO_SOLES,   @LN_TIPO_PPTO                                     
	           END                                                                                                    
	           CLOSE C_2                                                                                              
	           DEALLOCATE C_2                                                                                         
	                                                                                                                  
	   FETCH NEXT FROM C_1                                                                                    
	    INTO  @LN_NRO_ORDEN,	     @LC_TIPO_BIEN,		     @LN_TIPO_PPTO,		@LD_FECHA_ORDEN,	
	     	  @LS_CONCEPTO,          @LS_RUC_PROVEEDOR,	     @LS_NOM_PROVEEDOR,	@LS_PROVEEDOR_GIRO, 
	     	  @LN_MNTO_SUBTOTAL,  	 @LN_MNTO_DESCUENTO, 	 @LN_MNTO_TOTAL,	@LS_NRO_CONTRATO,   
	     	  @LD_FECHA_CONTRATO,    @LS_DOCUM_REFERENCIA,   @LN_EXP_SIAF,		@LS_NRO_PROC_SEL, 
	    	  @LS_GLOSA, @LC_ESTADO, @LC_ESTADO_SIAF                      
       END                                                                                                        
       CLOSE C_1                                                                                                  
       DEALLOCATE C_1                                                                                             
END

