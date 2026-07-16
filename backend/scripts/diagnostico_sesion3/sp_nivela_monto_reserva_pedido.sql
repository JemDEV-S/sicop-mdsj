CREATE  PROCEDURE dbo.SP_NIVELA_MONTO_RESERVA_PEDIDO
@P_ANO_EJE  NUMERIC(4,0),
@P_SEC_EJEC NUMERIC(6,0),    
@O_ERR_NUM  NUMERIC(6,0) OUTPUT,
@O_ERR_MSG  VARCHAR(255) OUTPUT
AS
BEGIN 

DECLARE @ll_SEC_FUNC        NUMERIC(4)  
DECLARE @LS_FUENTE_FTO      VARCHAR(2)
DECLARE @LS_CLASIFICADOR    VARCHAR(20) 
DECLARE @ld_monto_item      NUMERIC(15,2)
DECLARE @ls_uso_fuente      VARCHAR(1)
DECLARE @ls_flag_pnp        VARCHAR(1)

BEGIN

  SELECT @ls_uso_fuente = ltrim(rtrim(valor))  
    FROM sig_parametro_ejecutora  
   WHERE sec_ejec = @P_SEC_EJEC AND  
         cod_maestro = 'FLAG_FUENTE'

  IF @ls_uso_fuente IS NULL   
     SET @ls_uso_fuente = '0'

  SELECT @ls_flag_pnp = ltrim(rtrim(valor))
    FROM sig_parametro_ejecutora  
   WHERE sec_ejec = @P_SEC_EJEC AND  
         cod_maestro = 'FLAG_PED_NP'

  IF @ls_flag_pnp IS NULL   
     SET @ls_flag_pnp = '0'
		
  IF @ls_uso_fuente = '1' and @ls_flag_pnp = '1' AND @P_ANO_EJE > 2012 
  BEGIN


	UPDATE sig_techo_presupuesto
	SET MNTO_RESERVA_PEDIDO = 0
	WHERE sec_ejec  = @P_SEC_EJEC and
			ano_eje   = @P_ANO_EJE   and
			indicador = '4'           and
			flag_meta_aprob = '1'     and
			( '0' = '0')
        
     IF @@ERROR <> 0         
	 BEGIN
		 SET @O_ERR_MSG='Error actualizando tabla SIG_TECHO_PRESUPUESTO.'
		return -1
	 END    
	 
	UPDATE sig_techo_presupuesto
	SET MNTO_RESERVA_PEDIDO = 0
	WHERE sec_ejec  = @P_SEC_EJEC and
			ano_eje   = @P_ANO_EJE   and
			indicador = '0'           and
			flag_meta_aprob = '1'     and
			( '0' = '1')
        
     IF @@ERROR <> 0         
	 BEGIN
		 SET @O_ERR_MSG='Error actualizando tabla SIG_TECHO_PRESUPUESTO.'
		return -1
	 END    	 
		
  DECLARE C1 CURSOR FOR
		select D.SEC_FUNC,D.FUENTE_FTO,D.CLASIFICADOR,D.monto_item
		from (SELECT A.SEC_FUNC,
			A.FUENTE_FTO,
			B.CLASIFICADOR,
			SUM(coalesce(
			case 
				when A.tipo_bien= 'B' then (case 
					when (B.estado_ped= '1' or A.estado='1') then B.cant_solicitada
					when B.estado_ped= '4' then B.cant_aprobada
				end * B.PRECIO_UNIT)
				when A.tipo_bien= 'S' then (case 
					when (B.estado_ped= '1' or A.estado='1') then B.cant_solicitada
					else B.cant_aprobada
				end )
				end ,0)) monto_item
			 FROM SIG_PEDIDOS A,
			      SIG_DETALLE_PEDIDOS B
			WHERE
				A.ANO_EJE = B.ANO_EJE AND
				A.SEC_EJEC = B.SEC_EJEC AND
				A.TIPO_BIEN = B.TIPO_BIEN AND
				A.TIPO_PEDIDO = B.TIPO_PEDIDO AND
				A.NRO_PEDIDO = B.NRO_PEDIDO AND
				A.estado<> '0' and A.estado<> '3' and 
				( (B.TIPO_ORDEN = 'C' and B.TIPO_BIEN ='B') or (B.TIPO_BIEN ='S') ) and 
				not exists (select T.nro_consolid
						from sig_paac_consolidado T, sig_paac_metas M
						where T.ano_eje        = A.ANO_EJE 	 and
							T.sec_ejec       = A.SEC_EJEC  and
							T.tipo_bien      = A.tipo_bien and
							T.tipo_consolid  = '2' and
							T.tipo_generacion= '0' and
							T.sec_cuadro_ini = B.nro_cuadro and
							T.ano_eje      	= M.ano_eje 		and
							T.sec_ejec       	= M.sec_ejec  		and
							T.tipo_bien  		= M.tipo_bien 	 and 
							T.tipo_consolid  	= M.tipo_consolid	and
							T.nro_consolid   	= M.nro_consolid 	and
							T.tipo_generacion	= M.tipo_generacion and
							M.sec_func        = A.SEC_FUNC  	   and
							M.fuente_financ   = A.FUENTE_FTO  	and
							M.CLASIFICADOR    = B.CLASIFICADOR ) and
				A.ano_eje = @P_ANO_EJE and
				A.sec_ejec = @P_SEC_EJEC	
			group by A.SEC_FUNC, A.FUENTE_FTO, B.CLASIFICADOR

			union

			  select M.sec_func,
				M.fuente_financ,
				M.CLASIFICADOR,
				sum(case when O.monto > 0 then (case when I.tipo_bien = 'B' then I.cantidad * I.precio_moneda 
								     when I.tipo_bien = 'S' then I.cantidad end ) 
					 else 0 end ) AS monto_item 
				 from sig_paac_item I
						left join (select count(a.ano_eje) as monto, a.ano_eje,a.sec_ejec,a.nro_cons_paac,a.tipo_bien,a.grupo_bien,a.clase_bien,a.familia_bien,a.item_bien
									  from sig_detalle_bserv_cuadro  a, sig_detalle_metas_cuadro  b,
											 sig_depen_meta_cuadro     c,	sig_detalle_pedido_cuadro d
									 where a.ano_eje    = b.ano_eje   and a.sec_ejec   = b.sec_ejec   and
											 a.tipo_bien  = b.tipo_bien and a.sec_cuadro = b.sec_cuadro and
											 a.secuencia  = b.secuencia and 
											 c.ano_eje    = b.ano_eje   and c.sec_ejec   = b.sec_ejec   and
											 c.tipo_bien  = b.tipo_bien and c.sec_cuadro = b.sec_cuadro and
											 c.secuencia  = b.secuencia and c.sec_meta   = d.sec_meta   and
											 c.ano_eje    = d.ano_eje   and c.sec_ejec   = d.sec_ejec   and
											 c.tipo_bien  = d.tipo_bien and c.sec_cuadro = d.sec_cuadro and
											 c.secuencia  = d.secuencia and c.sec_meta   = d.sec_meta   and
											 c.sec_depend = d.sec_depend 
									group by a.ano_eje,a.sec_ejec,a.nro_cons_paac,a.tipo_bien,a.grupo_bien,a.clase_bien,a.familia_bien,a.item_bien) O
						on O.ano_eje    = I.ano_eje and 
							O.sec_ejec   = I.sec_ejec and 
							O.nro_cons_paac = I.nro_consolid and 
							O.tipo_bien   = I.tipo_bien and
							O.grupo_bien  = I.grupo_bien and
							O.clase_bien  = I.clase_bien and
							O.familia_bien= I.familia_bien and
							O.item_bien   = I.item_bien,
						sig_paac_metas M
						left join SIG_PAAC_CENTRO_COSTO S
						on ( S.ANO_EJE      = M.ANO_EJE ) AND  
							( S.SEC_EJEC     = M.SEC_EJEC ) AND  
							( S.TIPO_CONSOLID= M.TIPO_CONSOLID ) AND  
							( S.NRO_CONSOLID = M.NRO_CONSOLID ) AND  
							( S.TIPO_GENERACION = M.TIPO_GENERACION ) AND  
							( S.TIPO_BIEN    = M.TIPO_BIEN ) AND  
							( S.SEC_CONSOLID = M.SEC_CONSOLID ) AND  
							( S.SEC_RESUMEN  = M.SEC_RESUMEN ) AND  
							( S.SEC_META     = M.SEC_META ),
						sig_paac_consolidado T,
						(select distinct A.NRO_PEDIDO,B.ANO_EJE,B.SEC_EJEC,B.tipo_bien,
								B.nro_cuadro,A.SEC_FUNC,A.FUENTE_FTO,B.CLASIFICADOR
						from  SIG_PEDIDOS A, SIG_DETALLE_PEDIDOS B
						where A.ANO_EJE     = B.ANO_EJE AND
								A.SEC_EJEC    = B.SEC_EJEC AND
								A.TIPO_BIEN   = B.TIPO_BIEN AND
								A.TIPO_PEDIDO = B.TIPO_PEDIDO AND
								A.NRO_PEDIDO  = B.NRO_PEDIDO) P
				where M.ano_eje  		= I.ano_eje 		 and
						M.sec_ejec 		= I.sec_ejec 	 and
						M.tipo_consolid 	= I.tipo_consolid and
						M.nro_consolid  	= I.nro_consolid  and
						M.tipo_generacion = I.tipo_generacion and
						M.tipo_bien  		= I.tipo_bien 	 and 
						M.sec_consolid  	= I.sec_consolid and 
						M.sec_resumen  	= I.sec_resumen and	
						T.ano_eje      	= I.ano_eje 		and
						T.sec_ejec        = I.sec_ejec  and
						T.tipo_bien  		= I.tipo_bien 	 and 
						T.tipo_consolid  = I.tipo_consolid and
						T.nro_consolid   = I.nro_consolid and
						T.tipo_generacion= I.tipo_generacion and
	
						T.ano_eje        = P.ANO_EJE 	 and
						T.sec_ejec       = P.SEC_EJEC  and
						T.tipo_bien      = P.tipo_bien and
						T.tipo_consolid  = '2' and
						T.tipo_generacion= '0' and
						coalesce(T.verifica_ppto,'N')  = 'N' and
						T.sec_cuadro_ini = P.nro_cuadro  and
						M.sec_func       = P.SEC_FUNC  	and
						M.fuente_financ  = P.FUENTE_FTO  and
						M.CLASIFICADOR   = P.CLASIFICADOR and
						I.ano_eje = @P_ANO_EJE and
						I.sec_ejec = @P_SEC_EJEC						
				group by M.sec_func,M.fuente_financ,M.CLASIFICADOR) D  
                  
                  
	OPEN C1     
	 FETCH NEXT FROM C1
	  INTO  
	  @ll_SEC_FUNC, @LS_FUENTE_FTO, @LS_CLASIFICADOR, @ld_monto_item
	               
        WHILE @@FETCH_STATUS = 0
        BEGIN     

			UPDATE sig_techo_presupuesto
			SET MNTO_RESERVA_PEDIDO = @ld_monto_item
			WHERE sec_ejec  = @P_SEC_EJEC and
					ano_eje   = @P_ANO_EJE   and
					indicador = '4'           and
					flag_meta_aprob = '1'     and			
					sec_func = @ll_SEC_FUNC AND
					fuente_financ = @LS_FUENTE_FTO AND
					clasificador = @LS_CLASIFICADOR and 	
					( '0' = '0')
	            
	         IF @@ERROR <> 0         
			 BEGIN
				 SET @O_ERR_MSG='Error actualizando tabla SIG_TECHO_PRESUPUESTO.'
				return -1
			 END   

			UPDATE sig_techo_presupuesto
			SET MNTO_RESERVA_PEDIDO = @ld_monto_item
			WHERE sec_ejec  = @P_SEC_EJEC and
					ano_eje   = @P_ANO_EJE   and
					indicador = '0'           and
					flag_meta_aprob = '1'     and			
					sec_func = @ll_SEC_FUNC AND
					fuente_financ = @LS_FUENTE_FTO AND
					clasificador = @LS_CLASIFICADOR and 
					( '0' = '1')
	            
	         IF @@ERROR <> 0         
			 BEGIN
				 SET @O_ERR_MSG='Error actualizando tabla SIG_TECHO_PRESUPUESTO.'
				return -1
			 END   
          
	   FETCH NEXT FROM C1
           INTO  
           @ll_SEC_FUNC, @LS_FUENTE_FTO, @LS_CLASIFICADOR, @ld_monto_item
                          
      END          
      CLOSE C1
      DEALLOCATE C1            
              
   END
   END 
END
