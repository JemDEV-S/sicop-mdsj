CREATE PROCEDURE dbo.SP_SI_CARGA_EJEC_PEDIDO_TRX
	@P_ANO_EJE    NUMERIC(4,0),
	@P_SEC_EJEC   NUMERIC(6,0),
	@fecha_carga_inicio VARCHAR(10),
	@fecha_carga_fin    VARCHAR(10),
	@usuario_n    varchar(30),
	@O_ERR_NUM    NUMERIC(6,0) OUTPUT,
	@O_ERR_MSG    VARCHAR(255) OUTPUT
AS
DECLARE @fecha_carga_inicio_1 DATETIME,
		@fecha_carga_fin_1    DATETIME,
		@LS_TIPO_PEDIDO 	CHAR(1),  
		@LS_TIPO_BIEN 	    CHAR(1),    
		@LN_NRO_PEDIDO 		CHAR(5),	
	  	@LS_CENTRO_COSTO 	VARCHAR(15), 
	  	@LS_D_CENTRO_COSTO  VARCHAR(100), 
	  	@LD_FECHA_PEDIDO	DATETIME,
	  	@LS_MES_PEDIDO		CHAR(2),   
	  	@LS_MOTIVO_PEDIDO	VARCHAR(500), 
	  	@LN_SEC_FUNC		NUMERIC(16, 0),  	
	  	@LS_FINALIDAD		CHAR(5),		
	  	@LS_D_FINALIDAD  	VARCHAR(250),
	  	@LS_UNIDAD_MEDIDA	CHAR(3),
	  	@LS_D_UNIDAD_MEDIDA VARCHAR(100), 
	  	@LN_EMPLEADO		VARCHAR(15),		  		
	  	@LS_TIPO_USO		CHAR(1),
	  	@LS_ESTADO		    CHAR(1),		  
	  	@LS_D_EMPLEADO		VARCHAR(60),
	  	@LN_ID_SI_PEDIDO	NUMERIC(16,0),
       --/*DETALLE*/-----
        @LN_ID_SI_PEDIDO_DETA NUMERIC(16),  
        @LS_ITEM_CATALOGO     VARCHAR(20),
        @LS_D_ITEM_CATALOGO   VARCHAR(150),	/*FACT*/
        @LS_UNIDAD_MEDIDA_ITEM_BS   NUMERIC(3),	
        @LS_D_UNIDAD_MEDIDA_ITEM_BS VARCHAR(100),
        @LS_CLASIFICADOR 	CHAR(20),		
        @LN_CANT_SOLICITADA NUMERIC(16,6),	         
        @LN_PRECIO_UNIT NUMERIC(16,6),			
        @LN_VALOR_TOTAL NUMERIC(16,2),			
        @LN_NRO_ORDEN   NUMERIC(18),				
        @LN_NRO_CUADRO  NUMERIC(18),			
        @LS_ESTADO_PED  CHAR(1),
        @LN_CANT_APROBADA NUMERIC(16,6),		
        @LN_CANT_ATENDIDA NUMERIC(16,6),			
        @LN_NRO_PECOSA    NUMERIC(18),				
        @LD_FECHA_PECOSA  DATETIME ,
	@LS_GRUPO_BIEN  CHAR(2) ,
	@LS_CLASE_BIEN  CHAR(2),
	@LS_FAMILIA_BIEN CHAR(4),  
	@LS_ITEM_BIEN CHAR(4)
		
DECLARE C_1 CURSOR FOR
	SELECT
	    A.TIPO_PEDIDO,
	    A.TIPO_BIEN,
	    A.NRO_PEDIDO,
	    A.CENTRO_COSTO,
        dbo.f_elimina_tabs(E.NOMBRE_DEPEND) D_CENTRO_COSTO,
	    A.FECHA_PEDIDO,
	    A.MES_PEDIDO,
	    dbo.f_elimina_tabs(A.MOTIVO_PEDIDO) MOTIVO_PEDIDO,
	    A.sec_func,
	    B.finalidad,
	    C.nombre D_FINALIDAD,
	    B.unidad_med UNIDAD_MEDIDA_META,
	    dbo.f_elimina_tabs(D.NOMBRE) D_UNIDAD_MEDIDA_META,
	    A.EMPLEADO,
	    A.TIPO_USO,
	    A.ESTADO,	    
	    F.nombre_completo D_EMPLEADO
	FROM SIG_PEDIDOS A
	JOIN META B
	    ON  B.ano_eje = A.ANO_EJE
	    AND B.sec_ejec = A.SEC_EJEC
	    AND B.sec_func = A.sec_func
	JOIN FINALIDAD C
	    ON  C.ANO_EJE = B.ano_eje
	    AND C.finalidad = B.finalidad
	LEFT JOIN UNIDAD_MEDIDA D
	    ON  D.UNIDAD_MEDIDA = B.unidad_med
	JOIN SIG_CENTRO_COSTO E
	    ON  E.ANO_EJE = A.ANO_EJE
	    AND E.SEC_EJEC = A.SEC_EJEC
	    AND E.CENTRO_COSTO = A.CENTRO_COSTO
	LEFT JOIN SIG_PERSONAL F
	    ON  F.sec_ejec = A.SEC_EJEC
	    AND F.empleado = A.EMPLEADO
	WHERE A.ANO_EJE = @P_ANO_EJE
          AND A.SEC_EJEC= @P_SEC_EJEC	
          AND A.TIPO_PEDIDO = '2'	
BEGIN 		

     SET @fecha_carga_inicio_1 = Convert(DATETIME, @fecha_carga_inicio, 101)
     SET @fecha_carga_fin_1    = Convert(DATETIME, @fecha_carga_fin, 101)    
     
	-- Actualiza cod_renaes para el @P_ANO_EJE	
	update sig_ppr_establecimiento	
	   set cod_ogei = (select top 1 eess.cod_ogei
			     from sig_ppr_establecimiento eess					
			    where (@P_ANO_EJE + 1) = eess.ano_eje				and 
			     sig_ppr_establecimiento.sec_ejec = eess.sec_ejec	and 
			     sig_ppr_establecimiento.cod_establec = eess.cod_establec And 
			     eess.cod_ogei is not null)	
	 where sig_ppr_establecimiento.ano_eje  = @P_ANO_EJE	and 
	   	   sig_ppr_establecimiento.sec_ejec = @P_SEC_EJEC 
	   	   
	-- Elimina tabla que genera el txt
	DELETE FROM SI_PEDIDO_DETA_TRX
     	delete from SI_PEDIDO_TRX


     SELECT @LN_ID_SI_PEDIDO = MAX(ID_SI_PEDIDO) 
       FROM SI_PEDIDO_TRX
      WHERE ANO_EJE  = @P_ANO_EJE AND SEC_EJEC = @P_SEC_EJEC
	 
     IF @LN_ID_SI_PEDIDO IS NULL  SET @LN_ID_SI_PEDIDO = 0

     OPEN C_1
	FETCH NEXT FROM C_1
	INTO @LS_TIPO_PEDIDO,  @LS_TIPO_BIEN,    @LN_NRO_PEDIDO,	
	     @LS_CENTRO_COSTO,	@LS_D_CENTRO_COSTO, 	@LD_FECHA_PEDIDO, @LS_MES_PEDIDO,   @LS_MOTIVO_PEDIDO, 
	     @LN_SEC_FUNC,  	@LS_FINALIDAD,		@LS_D_FINALIDAD,  @LS_UNIDAD_MEDIDA,@LS_D_UNIDAD_MEDIDA, 
	     @LN_EMPLEADO,  	@LS_TIPO_USO, 		@LS_ESTADO,	  @LS_D_EMPLEADO

	     WHILE @@FETCH_STATUS = 0
	     BEGIN
	     	SET @LN_ID_SI_PEDIDO = @LN_ID_SI_PEDIDO + 1 
		-- Carga data en tabla
		INSERT INTO dbo.SI_PEDIDO_TRX
		(ANO_EJE,         SEC_EJEC,       ID_SI_PEDIDO,	 TIPO_PEDIDO,    TIPO_BIEN,          NRO_PEDIDO,
	     CENTRO_COSTO,    D_CENTRO_COSTO, FECHA_PEDIDO,   MES_PEDIDO,         MOTIVO_PEDIDO,  
	     sec_func,        finalidad,      D_FINALIDAD,    UNIDAD_MEDIDA_META, D_UNIDAD_MEDIDA_META , 
	     EMPLEADO,        TIPO_USO,       ESTADO,         D_EMPLEADO,         META,          
	     FECHA_CARGA_INICIO, FECHA_CARGA_FIN, FECHA_ENVIO,  USUARIO_ENVIO  )      
		VALUES
	  	(@P_ANO_EJE ,	    @P_SEC_EJEC,	   @LN_ID_SI_PEDIDO, @LS_TIPO_PEDIDO,  @LS_TIPO_BIEN,    @LN_NRO_PEDIDO,	
	  	 @LS_CENTRO_COSTO,  @LS_D_CENTRO_COSTO,@LD_FECHA_PEDIDO, @LS_MES_PEDIDO,   @LS_MOTIVO_PEDIDO, 
	  	 @LN_SEC_FUNC,      @LS_FINALIDAD,	   @LS_D_FINALIDAD,  @LS_UNIDAD_MEDIDA,@LS_D_UNIDAD_MEDIDA  , 
	  	 @LN_EMPLEADO,      @LS_TIPO_USO, 	   @LS_ESTADO,	  	 @LS_D_EMPLEADO,   @LN_SEC_FUNC,
		 @fecha_carga_inicio_1, @fecha_carga_fin_1,GETDATE(), 	@usuario_n)

		DECLARE C_2 CURSOR FOR  
		SELECT
			    A.GRUPO_BIEN,
			    A.CLASE_BIEN,
			    A.FAMILIA_BIEN,
			    A.ITEM_BIEN,
			    dbo.f_elimina_tabs(B.NOMBRE_ITEM) D_ITEM_CATALOGO,
			    B.UNIDAD_MEDIDA UNIDAD_MEDIDA_ITEM_BS,
			    C.NOMBRE D_UNIDAD_MEDIDA_ITEM_BS,
			    A.CLASIFICADOR,
			    A.CANT_SOLICITADA,
			    A.PRECIO_UNIT,
			    A.VALOR_TOTAL,
			    A.NRO_ORDEN,
			    A.NRO_CUADRO,
			    A.ESTADO_PED,
			    A.CANT_APROBADA,
			    A.CANT_ATENDIDA,
			    A.NRO_PECOSA,
			    A.FECHA_PECOSA
			FROM SIG_DETALLE_PEDIDOS A
			JOIN CATALOGO_BIEN_SERV B
				    ON  B.SEC_EJEC = A.sec_ejec
				    AND B.TIPO_BIEN = A.TIPO_BIEN
				    AND B.GRUPO_BIEN = A.GRUPO_BIEN
				    AND B.CLASE_BIEN = A.CLASE_BIEN
				    AND B.FAMILIA_BIEN = A.FAMILIA_BIEN
				    AND B.ITEM_BIEN = A.ITEM_BIEN
				LEFT JOIN UNIDAD_MEDIDA C
				    ON  C.UNIDAD_MEDIDA = B.UNIDAD_MEDIDA
			WHERE 
				    A.ANO_EJE        = @P_ANO_EJE        AND 
				    A.sec_ejec       = @P_SEC_EJEC        AND
				    A.TIPO_BIEN      = @LS_TIPO_BIEN    AND
				    A.TIPO_PEDIDO    = '2' AND
				    A.NRO_PEDIDO     = @LN_NRO_PEDIDO
			
			
		 SELECT @LN_ID_SI_PEDIDO_DETA = MAX(ID_SI_PEDIDO_DETA) 
		   FROM SI_PEDIDO_DETA_TRX
	 	  WHERE ANO_EJE  = @P_ANO_EJE AND SEC_EJEC = @P_SEC_EJEC
	 
	    	 IF @LN_ID_SI_PEDIDO_DETA IS NULL  	SET @LN_ID_SI_PEDIDO_DETA = 0
	 
		 OPEN C_2                                                                                                 
	     FETCH NEXT FROM C_2                                                                                      
		      INTO @LS_GRUPO_BIEN, 	@LS_CLASE_BIEN, 	@LS_FAMILIA_BIEN,   @LS_ITEM_BIEN,--,	@LS_ITEM_CATALOGO,
			   @LS_D_ITEM_CATALOGO, @LS_UNIDAD_MEDIDA_ITEM_BS,@LS_D_UNIDAD_MEDIDA_ITEM_BS,	@LS_CLASIFICADOR,	    
			   @LN_CANT_SOLICITADA, @LN_PRECIO_UNIT,	@LN_VALOR_TOTAL,		@LN_NRO_ORDEN,		
			   @LN_NRO_CUADRO,		@LS_ESTADO_PED,     @LN_CANT_APROBADA,		@LN_CANT_ATENDIDA,	    
			   @LN_NRO_PECOSA,      @LD_FECHA_PECOSA
				
		 WHILE @@FETCH_STATUS = 0                    
	     BEGIN 
        	 set @LS_ITEM_CATALOGO     = @LS_GRUPO_BIEN+@LS_CLASE_BIEN+@LS_FAMILIA_BIEN+@LS_ITEM_BIEN
		 	 set @LN_ID_SI_PEDIDO_DETA = @LN_ID_SI_PEDIDO_DETA + 1

	      INSERT INTO SI_PEDIDO_DETA_TRX
	     (ANO_EJE, 			SEC_EJEC, 		ID_SI_PEDIDO,			ID_SI_PEDIDO_DETA,	ITEM_CATALOGO, 
	      D_ITEM_CATALOGO,  UNIDAD_MEDIDA_ITEM_BS,D_UNIDAD_MEDIDA_ITEM_BS,	CLASIFICADOR,		CANT_SOLICITADA,
		  PRECIO_UNIT,		VALOR_TOTAL,		NRO_ORDEN,			NRO_CUADRO,		ESTADO_PED,
		  CANT_APROBADA,	CANT_ATENDIDA,		NRO_PECOSA,			FECHA_PECOSA,  	FECHA_CARGA_INICIO,
		  FECHA_CARGA_FIN,	FECHA_ENVIO,		USUARIO_ENVIO          )
         VALUES
         (@P_ANO_EJE, 			@P_SEC_EJEC, 			  @LN_ID_SI_PEDIDO, 		@LN_ID_SI_PEDIDO_DETA,  @LS_ITEM_CATALOGO,
          @LS_D_ITEM_CATALOGO,	@LS_UNIDAD_MEDIDA_ITEM_BS,@LS_D_UNIDAD_MEDIDA_ITEM_BS,	@LS_CLASIFICADOR,	@LN_CANT_SOLICITADA,	         
          COALESCE(@LN_PRECIO_UNIT, 0),		COALESCE(@LN_VALOR_TOTAL, 0),		  @LN_NRO_ORDEN,			@LN_NRO_CUADRO,			@LS_ESTADO_PED,
          @LN_CANT_APROBADA,	@LN_CANT_ATENDIDA,		  @LN_NRO_PECOSA,			@LD_FECHA_PECOSA,		@fecha_carga_inicio_1,
          @fecha_carga_inicio_1,GETDATE(),				  @usuario_n )
         
          	 FETCH NEXT FROM C_2                                                                                
               	 INTO  @LS_GRUPO_BIEN, 	@LS_CLASE_BIEN, 	@LS_FAMILIA_BIEN,   @LS_ITEM_BIEN,--,	@LS_ITEM_CATALOGO,
			   @LS_D_ITEM_CATALOGO, @LS_UNIDAD_MEDIDA_ITEM_BS,@LS_D_UNIDAD_MEDIDA_ITEM_BS,	@LS_CLASIFICADOR,	    
			   @LN_CANT_SOLICITADA, @LN_PRECIO_UNIT,	@LN_VALOR_TOTAL,		@LN_NRO_ORDEN,		
			   @LN_NRO_CUADRO,		@LS_ESTADO_PED,     @LN_CANT_APROBADA,		@LN_CANT_ATENDIDA,	    
			   @LN_NRO_PECOSA,      @LD_FECHA_PECOSA                             
             END                                                                                                    
             CLOSE C_2                                                                                              
             DEALLOCATE C_2                                                                                         
                                                                                                                  
          FETCH NEXT FROM C_1                                                                                    
          INTO @LS_TIPO_PEDIDO,  @LS_TIPO_BIEN,    @LN_NRO_PEDIDO,	
	     @LS_CENTRO_COSTO,	@LS_D_CENTRO_COSTO, 	@LD_FECHA_PEDIDO, @LS_MES_PEDIDO,   @LS_MOTIVO_PEDIDO, 
	     @LN_SEC_FUNC,  	@LS_FINALIDAD,		@LS_D_FINALIDAD,  @LS_UNIDAD_MEDIDA,@LS_D_UNIDAD_MEDIDA, 
	     @LN_EMPLEADO,  	@LS_TIPO_USO, 		@LS_ESTADO,	  @LS_D_EMPLEADO                   
       END                                                                                                        
       CLOSE C_1                                                                                                  
       DEALLOCATE C_1                                                                                             
END

