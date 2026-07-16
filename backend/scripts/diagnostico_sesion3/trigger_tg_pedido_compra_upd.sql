CREATE TRIGGER dbo.tg_pedido_compra_upd
on dbo.SIG_PEDIDOS
for update
as

------------------------------------------------------
-- Autor : Jony Ancasi
-- Objeto: Cambio de tamaño de campo Pedido y PECOSA
-- Cambio:
--			PECOSA NUMERIC(6) x NUMERIC(5)
--			PEDIDO VARCHAR(6) x VARCHAR(5)
------------------------------------------------------

declare @vid_ano         numeric(4),
		@vid_ejecutora   numeric(6),
		@vid_tipo_trans  numeric(2),
		@vid_nro_origen  numeric(6),
		@vid_error	     int,
		@vis_tipo_bien   char(1),
		@vis_tipo_ped    char(1),		
		--@vis_nro_ped	 char(5),
		@vis_nro_ped	 varchar(6),
		@vis_est_trans 	 char(1),
        @ls_estado_ori   varchar(1),
		@vd_fecha_ped    datetime,
		@vd_fecha_apr    datetime,
		@vd_tipo_ppto    numeric(1),
		@vis_flag_pad	 char(1),
		@vis_cuser_id	 varchar(30),
		@vis_equipo_reg	 varchar(20),
		@vid_tipo_trans_p numeric(2),		
		--@vis_nro_ped_p	 char(5),
		@vis_nro_ped_p	 varchar(6),
		@vid_sec         numeric(6),
		@vis_c_costo	 varchar(15)

BEGIN
select 
@vid_ano		   = ano_eje     ,
@vid_ejecutora  = sec_ejec    ,
@vis_tipo_bien  = tipo_bien   ,
@vis_tipo_ped   = tipo_pedido ,
@vis_nro_ped    = nro_pedido  ,
@vis_est_trans  = estado      ,
@vd_fecha_ped   = fecha_pedido,
@vd_fecha_apr   = fecha_aprob ,
@vd_tipo_ppto   = tipo_ppto   ,
@vis_flag_pad   = flag_pad    ,
@vis_c_costo    = centro_costo,
@vis_cuser_id   = CUSER_MOD,
@vis_equipo_reg = EQUIPO_MOD
from inserted

/*fact: si no se actualiza las campos mod, los actualizo de la sesion*/
IF  OBJECT_ID('tempdb..#SIG_SESION') IS  NOT NULL
    BEGIN
        SELECT  @vis_cuser_id   = CUSER_ID,
                @vis_equipo_reg = EQUIPO_REG
        FROM    #SIG_SESION
    END

update sig_pedidos 
set CUSER_MOD = @vis_cuser_id,
    EQUIPO_MOD = @vis_equipo_reg,
    FECHA_MOD  = getdate()
where  
ano_eje     = @vid_ano       and
sec_ejec    = @vid_ejecutora and	 
tipo_bien   = @vis_tipo_bien AND
tipo_pedido = @vis_tipo_ped and
nro_pedido  = @vis_nro_ped

/*obtengo el estado original*/
SELECT  @ls_estado_ori  = ESTADO
FROM    DELETED

/*si no ha cambiado el estado, salgo*/
IF @ls_estado_ori = @vis_est_trans
BEGIN
    RETURN
END

if update(estado)	
BEGIN

	-- valores leidos de tipo_modulo : sig_maestro_Det_numerico
	select @vid_tipo_trans = 0

	-- Valida si el estado: APROBADO
	-- estado de autorizacion
	if @vis_est_trans = '2'
	   --AUTORIZADO
	   begin
		select @vd_fecha_ped = @vd_fecha_apr				
	   end			

	if (@vis_tipo_ped = '2') 
		begin
			--tipo modulo : pedido no programado 
			select @vid_tipo_trans = 2		
		end
	else if (@vis_tipo_ped = '1')	
		begin
			--tipo modulo : pedido programado
			select @vid_tipo_trans = 1		
		end
	else if ((@vis_tipo_ped = '5'  and  @vis_flag_pad = '0' )	and (@vd_tipo_ppto = 2))
		--asignacion de tipo de pedido maestro de encargos padre
		begin
			--tipo modulo : pedido de encargos
			select @vid_tipo_trans = 17		
		end
	else if ( (@vis_tipo_ped = '6')	and   (@vd_tipo_ppto = 2) )
		--asignacion de tipo de pedido hijo de encargos detalle
		begin
			--tipo modulo : pedido de encargos
			select @vid_tipo_trans = 18		
		end

	--valida si es tipo_modulo = pedido programado o pedido no programado
	if (@vid_tipo_trans = 2) or (@vid_tipo_trans = 1) and (@vis_est_trans = '0' or @vis_est_trans = '1' or @vis_est_trans = '2' or @vis_est_trans = '3')
	--verifica que estado de pedido de encargo sea : pendiente(0) o visto bueno(1) o 
	--autorizado(2) o denegado(3)
	begin

		if not exists 
	   	(select *
	    	from sig_seguimiento
	    	where 
		ano_eje     = @vid_ano       and
		sec_ejec    = @vid_ejecutora and
		tipo_bien   = @vis_tipo_bien and
		tipo_pedido = @vis_tipo_ped  and
		nro_pedido  = @vis_nro_ped   and
		tipo_transaccion = @vid_tipo_trans )
		begin
			insert into sig_seguimiento
			(
			ano_eje,
			sec_ejec, 
			tipo_transaccion,
			nro_origen,
			centro_costo,
			solicitante, 
			tipo_ppto,
			tipo_bien,
			tipo_pedido,
			nro_transaccion,
	      		nro_pedido,
			fecha_transaccion,
			estado_transaccion,
			fecha_reg,
			cuser_id,
			equipo_reg)   		
			select 
			A.ano_eje, 
			A.sec_ejec,
			@vid_tipo_trans,
		       	(select (isnull(max(B.nro_origen),0)+1)
			from sig_seguimiento B
			where(B.ano_eje 	 = @vid_ano	   ) and
			     (B.sec_ejec 	 = @vid_ejecutora  ) and
			     (B.tipo_transaccion = @vid_tipo_trans )),		--3		
			A.centro_costo,
			A.empleado,
			A.tipo_ppto,
			A.tipo_bien, 
			A.tipo_pedido,
			convert(numeric(6),A.nro_pedido), 
			A.nro_pedido,
			A.fecha_pedido,
			A.estado,
			getdate(),
			@vis_cuser_id,
			@vis_equipo_reg
			from inserted A	
		end 		

		select @vid_nro_origen = nro_origen
		from sig_seguimiento
		where  
		ano_eje       = @vid_ano       and
	    sec_ejec      = @vid_ejecutora and	 
	    tipo_bien     = @vis_tipo_bien and
	    tipo_pedido   = @vis_tipo_ped  and 
	    nro_pedido    = @vis_nro_ped   and
		tipo_transaccion = @vid_tipo_trans
	
		-- Actualiza el seguimiento
		update sig_seguimiento 
		set estado_transaccion = @vis_est_trans
		where  
		ano_eje         = @vid_ano       and
	    sec_ejec        = @vid_ejecutora and	 
		tipo_transaccion = @vid_tipo_trans and
		nro_origen       = @vid_nro_origen

		if @vid_nro_origen > 0 
		begin	
			insert into sig_seguimiento_estado
			(
			ano_eje,
			sec_ejec,
			tipo_transaccion,
			nro_origen,
			sec_estado,
			fecha_estado,
			estado_seguimiento,
			fecha_reg,
			cuser_id,
			equipo_reg
			)
			select 
			A.ano_eje,
	       		A.sec_ejec,
	       		@vid_tipo_trans,
	       		@vid_nro_origen,
               		(select (isnull(max(C.sec_estado),0)+1)
			from sig_seguimiento_estado C
			where(C.ano_eje 	 = @vid_ano	   ) and
		     	(C.sec_ejec 	 = @vid_ejecutora  ) and
		     	(C.tipo_transaccion = @vid_tipo_trans ) and
		     	(C.nro_origen	 = @vid_nro_origen)),
	       		@vd_fecha_ped,
	       		B.estado,		
	       		getdate(),
	       		@vis_cuser_id,
	       		@vis_equipo_reg
			from deleted A
			inner join inserted B
			on A.ano_eje 		= B.ano_eje  and
	   		A.sec_ejec 		= B.sec_ejec and
	   		A.tipo_bien		= B.tipo_bien and
	   		A.tipo_pedido	        = B.tipo_pedido and
	   		A.nro_pedido		= B.nro_pedido and
	   		A.estado <> B.estado
		end
	end

	-- Adicionado por Jimmy
	if (@vis_est_trans = '4' or  @vis_est_trans = '5' or  @vis_est_trans = '6' or @vis_est_trans = '7')	
	--verifica que tipo_modulo sea de pedidos de encargos
	--verifica que estado de pedido de encargo sea : pecosa parcial por firmar(4) o 
	--pecosa parcial(5) o pecosa por firmar(6) o pecosa(7)
		begin
			--tipo modulo : pecosa 
			select @vid_tipo_trans_p = 19
			
            --select DISTINCT @vis_nro_ped_p = right('00000'+rtrim(LTRIM(convert(char(5),NRO_PECOSA))),5)
            select DISTINCT @vis_nro_ped_p = right('000000'+rtrim(LTRIM(convert(char(6),NRO_PECOSA))),6)
			from SIG_DETALLE_PEDIDOS
			where  
			ANO_EJE       = @vid_ano       and
	       	sec_ejec      = @vid_ejecutora and	 
	       	TIPO_BIEN     = @vis_tipo_bien and
	       	TIPO_PEDIDO   = @vis_tipo_ped  and 
	       	NRO_PEDIDO    = @vis_nro_ped  		
	
			if not exists 
				(select *
				from sig_seguimiento
				where 
			ano_eje     = @vid_ano       and
			sec_ejec    = @vid_ejecutora and
			tipo_bien   = @vis_tipo_bien and
			tipo_pedido = @vis_tipo_ped  and
			nro_pedido  = @vis_nro_ped_p and
			tipo_transaccion = @vid_tipo_trans_p )
			begin
				insert into sig_seguimiento
				(
				ano_eje,
				sec_ejec, 
				tipo_transaccion,
				nro_origen,
				centro_costo,
				solicitante, 
				tipo_ppto,
				tipo_bien,
				tipo_pedido,
				nro_transaccion,
				nro_pedido,
				fecha_transaccion,
				estado_transaccion,
				sec_transaccion,
				fecha_reg,
				cuser_id,
				equipo_reg)   		
				select 
				A.ano_eje, 
				A.sec_ejec,
				@vid_tipo_trans_p,
						(select (isnull(max(B.nro_origen),0)+1)
				from sig_seguimiento B
				where(B.ano_eje 	 = @vid_ano	   ) and
					  (B.sec_ejec 	 = @vid_ejecutora  ) and
					  (B.tipo_transaccion = @vid_tipo_trans_p )),--3		
				A.centro_costo,
				A.empleado,
				A.tipo_ppto,
				A.tipo_bien, 
				A.tipo_pedido,
				convert(numeric(6),@vis_nro_ped_p), 
				@vis_nro_ped_p,
				getdate(),
				A.estado,
				convert(numeric(6),@vis_nro_ped),
				getdate(),
				@vis_cuser_id,
				@vis_equipo_reg
				from inserted A	
			end 		
   
			select @vid_nro_origen = nro_origen
			from sig_seguimiento
			where  
			ano_eje       = @vid_ano       and
			sec_ejec      = @vid_ejecutora and	 
			tipo_bien     = @vis_tipo_bien and
			tipo_pedido   = @vis_tipo_ped  and 
			nro_pedido    = @vis_nro_ped_p and
			tipo_transaccion = @vid_tipo_trans_p
		
			-- Actualiza el seguimiento
			update sig_seguimiento 
			set estado_transaccion = @vis_est_trans
			where  
			ano_eje         = @vid_ano       and
			sec_ejec        = @vid_ejecutora and	 
			tipo_transaccion = @vid_tipo_trans_p and
			nro_origen       = @vid_nro_origen				
	
			if @vid_nro_origen > 0 
			begin
				insert into sig_seguimiento_estado
				(
				ano_eje,
				sec_ejec,
				tipo_transaccion,
				nro_origen,
				sec_estado,
				fecha_estado,
				estado_seguimiento,
				fecha_reg,
				cuser_id,
				equipo_reg
				)
				select 
				A.ano_eje,
				A.sec_ejec,
				@vid_tipo_trans_p,
				@vid_nro_origen,
				(select (isnull(max(C.sec_estado),0)+1)
				from sig_seguimiento_estado C
				where(C.ano_eje 	 = @vid_ano	   ) and
					(C.sec_ejec 	 = @vid_ejecutora  ) and
					(C.tipo_transaccion = @vid_tipo_trans_p ) and
					(C.nro_origen	 = @vid_nro_origen)),
						getdate(),
						B.estado,		
						getdate(),
						@vis_cuser_id,
						@vis_equipo_reg
				from deleted A
				inner join inserted B
				on A.ano_eje 		= B.ano_eje  and
					A.sec_ejec 		= B.sec_ejec and
					A.tipo_bien		= B.tipo_bien and
					A.tipo_pedido	        = B.tipo_pedido and
					A.nro_pedido		= B.nro_pedido and
				A.estado <> B.estado
			END									
		end
	ELSE IF (@vis_est_trans = '2')
	   begin
			--tipo modulo : pecosa 
			select @vid_tipo_trans_p = 19	     	
	       	
	       	select DISTINCT @vis_nro_ped_p = nro_pedido
			from sig_seguimiento
			where 
			ano_eje     = @vid_ano       and
			sec_ejec    = @vid_ejecutora and
			tipo_bien   = @vis_tipo_bien and
			tipo_pedido = @vis_tipo_ped  and
			tipo_transaccion = @vid_tipo_trans_p and
			sec_transaccion = convert(numeric(6),@vis_nro_ped)
	       	
			select @vid_nro_origen = 0   	
	       	
			if exists 
				(select *
				from sig_seguimiento
				where 
			ano_eje     = @vid_ano       and
			sec_ejec    = @vid_ejecutora and
			tipo_bien   = @vis_tipo_bien and
			tipo_pedido = @vis_tipo_ped  and
			nro_pedido  = @vis_nro_ped_p and
			tipo_transaccion = @vid_tipo_trans_p )
			begin
					
				-- Eliminar el Seguimiento
				select @vid_nro_origen = nro_origen
				from sig_seguimiento
				where  	ano_eje       = @vid_ano       and
						sec_ejec      = @vid_ejecutora and	 
						tipo_bien     = @vis_tipo_bien and
						tipo_pedido   = @vis_tipo_ped  and 
						nro_pedido    = @vis_nro_ped_p and
				tipo_transaccion = @vid_tipo_trans_p
		        
				-- Elimina en las tablas
				delete from sig_seguimiento_estado
				where ano_eje 		= @vid_ano 	  and
				      sec_ejec 		= @vid_ejecutora  and
				      tipo_transaccion	= @vid_tipo_trans_p and
				      nro_origen 	= @vid_nro_origen 
			
				delete from sig_seguimiento_secuencia
				where ano_eje 		= @vid_ano 	  and
				      sec_ejec 		= @vid_ejecutora  and
				      tipo_transaccion	= @vid_tipo_trans_p and
				      nro_origen 	= @vid_nro_origen 
			
				delete from sig_seguimiento	
				where ano_eje 		= @vid_ano 	  and
				      sec_ejec 		= @vid_ejecutora  and
				      tipo_transaccion	= @vid_tipo_trans_p and
				      nro_origen 	= @vid_nro_origen 		  	
				      
				select @vid_sec = isnull(max(secuencia),0)+1
				from sig_auditoria
				where ano_eje 	 	  = @vid_ano
				and sec_ejec		  = @vid_ejecutora
				and tipo_movimiento = 'D'

				insert into sig_auditoria
						(ano_eje     , sec_ejec   ,tipo_movimiento, secuencia	   , 	tipo_bien ,
						 tipo_pedido , nro_pedido ,nro_transaccion, fecha_transaccion, estado_transaccion ,
						 centro_costo, fecha_reg  , cuser_id	  , equipo_reg,      tipo_transaccion )
				values
						(@vid_ano     , @vid_ejecutora, 'D'		  ,	@vid_sec     ,	   @vis_tipo_bien ,
						 @vis_tipo_ped, @vis_nro_ped_p, convert(numeric(6),@vis_nro_ped_p), @vd_fecha_ped,  @vis_est_trans,
						 @vis_c_costo ,  getdate()    , @vis_cuser_id, @vis_equipo_reg, @vid_tipo_trans_p) 
			      				      
	       	END	      
	   end	
	-- Fin de adicionado por Jimmy

	ELSE if (@vis_tipo_ped = '5' and @vis_flag_pad = '0') and (@vid_tipo_trans = 17) and (@vis_est_trans = '0' or @vis_est_trans = '1' or @vis_est_trans = '2' or @vis_est_trans = '3' or  @vis_est_trans = '8')
	--verifica que tipo de pedido sea de encargo
	--verifica que tipo_modulo sea de pedidos de encargos
	--verifica que estado de pedido de encargo sea : pendiente(0) o visto bueno(0) o 
	--autorizado(2) o atendido(8), denegado(3)
	begin

		if not exists 
	   	(select *
	    	from sig_seguimiento
	    	where 
		ano_eje     = @vid_ano       and
		sec_ejec    = @vid_ejecutora and
		tipo_bien   = @vis_tipo_bien and
		tipo_pedido = @vis_tipo_ped  and
		nro_pedido  = @vis_nro_ped   and
		tipo_transaccion = @vid_tipo_trans )
		begin
			insert into sig_seguimiento
			(
			ano_eje,
			sec_ejec, 
			tipo_transaccion,
			nro_origen,
			centro_costo,
			solicitante, 
			tipo_ppto,
			tipo_bien,
			tipo_pedido,
			nro_transaccion,
	      	nro_pedido,
			fecha_transaccion,
			estado_transaccion,
			fecha_reg,
			cuser_id,
			equipo_reg)   		
			select 
			A.ano_eje, 
			A.sec_ejec,
			@vid_tipo_trans,
		    (select (isnull(max(B.nro_origen),0)+1)
			from sig_seguimiento B
			where(B.ano_eje 	 = @vid_ano	   ) and
			     (B.sec_ejec 	 = @vid_ejecutora  ) and
			     (B.tipo_transaccion = @vid_tipo_trans )),		--3		
			A.centro_costo,
			A.empleado,
			A.tipo_ppto,
			A.tipo_bien, 
			A.tipo_pedido,
			convert(numeric(6),A.nro_pedido), 
			A.nro_pedido,
			getdate(),
			A.estado,
			getdate(),
			@vis_cuser_id,
			@vis_equipo_reg
			from inserted A	
		end 		

		select @vid_nro_origen = nro_origen
		from sig_seguimiento
		where  
		ano_eje       = @vid_ano       and
	    sec_ejec      = @vid_ejecutora and	 
	    tipo_bien     = @vis_tipo_bien and
	    tipo_pedido   = @vis_tipo_ped  and 
	    nro_pedido    = @vis_nro_ped   and
		tipo_transaccion = @vid_tipo_trans
	
		-- Actualiza el seguimiento
		update sig_seguimiento 
		set estado_transaccion = @vis_est_trans
		where  
		ano_eje         = @vid_ano       and
	    sec_ejec        = @vid_ejecutora and	 
		tipo_transaccion = @vid_tipo_trans and
		nro_origen       = @vid_nro_origen

		if @vid_nro_origen > 0 
		begin		
			insert into sig_seguimiento_estado
			(
			ano_eje,
			sec_ejec,
			tipo_transaccion,
			nro_origen,
			sec_estado,
			fecha_estado,
			estado_seguimiento,
			fecha_reg,
			cuser_id,
			equipo_reg
			)
			select 
			A.ano_eje,
	       	A.sec_ejec,
	       	@vid_tipo_trans,
	       	@vid_nro_origen,
            (select (isnull(max(C.sec_estado),0)+1)
			from sig_seguimiento_estado C
			where(C.ano_eje 	 = @vid_ano	 ) and
		     	(C.sec_ejec 	 = @vid_ejecutora  ) and
		     	(C.tipo_transaccion = @vid_tipo_trans ) and
		     	(C.nro_origen	 = @vid_nro_origen)),
	       		getdate(),
	       		B.estado,		
	       		getdate(),
	       		@vis_cuser_id,
	       		@vis_equipo_reg
			from deleted A
			inner join inserted B
			on A.ano_eje 		= B.ano_eje  and
	   		A.sec_ejec 		= B.sec_ejec and
	   		A.tipo_bien		= B.tipo_bien and
	   		A.tipo_pedido	        = B.tipo_pedido and
	   		A.nro_pedido		= B.nro_pedido and
			A.estado <> B.estado
		end
	end	
	
	else 	if (@vis_tipo_ped = '6') and (@vid_tipo_trans = 18) and (@vis_est_trans = '2' or @vis_est_trans = '3' or @vis_est_trans = '4' or  @vis_est_trans = '5' or @vis_est_trans = '6' or  @vis_est_trans = '7')	
	--verifica que tipo de pedido sea de encargo hijo
	--verifica que tipo_modulo sea de pedidos de encargos
	--verifica que estado de pedido de encargo sea : autorizado(2) o denegado(3) o 
	--pecosa parcial por firmar(4) o pecosa parcial(5) o pecosa por firmar(6) o pecosa(7)
	begin

		if not exists 
	   	(select *
	    	from sig_seguimiento
	    	where 
		ano_eje     = @vid_ano       and
		sec_ejec    = @vid_ejecutora and
		tipo_bien   = @vis_tipo_bien and
		tipo_pedido = @vis_tipo_ped  and
		nro_pedido  = @vis_nro_ped   and
		tipo_transaccion = @vid_tipo_trans )
		begin
			insert into sig_seguimiento
			(
			ano_eje,
			sec_ejec, 
			tipo_transaccion,
			nro_origen,
			centro_costo,
			solicitante, 
			tipo_ppto,
			tipo_bien,
			tipo_pedido,
			nro_transaccion,
	      	nro_pedido,
			fecha_transaccion,
			estado_transaccion,
			fecha_reg,
			cuser_id,
			equipo_reg)   		
			select 
			A.ano_eje, 
			A.sec_ejec,
			@vid_tipo_trans,
		    (select (isnull(max(B.nro_origen),0)+1)
			from sig_seguimiento B
			where(B.ano_eje 	 = @vid_ano	   ) and
			     (B.sec_ejec 	 = @vid_ejecutora  ) and
			     (B.tipo_transaccion = @vid_tipo_trans )),		--3		
			A.centro_costo,
			A.empleado,
			A.tipo_ppto,
			A.tipo_bien, 
			A.tipo_pedido,
			convert(numeric(6),A.nro_pedido), 
			A.nro_pedido,
			getdate(),
			A.estado,
			getdate(),
			@vis_cuser_id,
			@vis_equipo_reg
			from inserted A	
		end 		

		select @vid_nro_origen = nro_origen
		from sig_seguimiento
		where  
		ano_eje       = @vid_ano       and
	    sec_ejec      = @vid_ejecutora and	 
	    tipo_bien     = @vis_tipo_bien and
	    tipo_pedido   = @vis_tipo_ped  and 
	    nro_pedido    = @vis_nro_ped   and
		tipo_transaccion = @vid_tipo_trans
	
		-- Actualiza el seguimiento
		update sig_seguimiento 
		set estado_transaccion = @vis_est_trans
		where  
		ano_eje         = @vid_ano       and
	    sec_ejec        = @vid_ejecutora and	 
		tipo_transaccion = @vid_tipo_trans and
		nro_origen       = @vid_nro_origen

		if @vid_nro_origen > 0 
		begin
			insert into sig_seguimiento_estado
			(
			ano_eje,
			sec_ejec,
			tipo_transaccion,
			nro_origen,
			sec_estado,
			fecha_estado,
			estado_seguimiento,
			fecha_reg,
			cuser_id,
			equipo_reg
			)
			select 
			A.ano_eje,
	       		A.sec_ejec,
	       		@vid_tipo_trans,
	       		@vid_nro_origen,
               		(select (isnull(max(C.sec_estado),0)+1)
			from sig_seguimiento_estado C
			where(C.ano_eje 	 = @vid_ano	   ) and
		     	(C.sec_ejec 	 = @vid_ejecutora  ) and
		     	(C.tipo_transaccion = @vid_tipo_trans ) and
		     	(C.nro_origen	 = @vid_nro_origen)),
	       		getdate(),
	       		B.estado,		
	       		getdate(),
	       		@vis_cuser_id,
	       		@vis_equipo_reg
			from deleted A
			inner join inserted B
			on A.ano_eje 		= B.ano_eje  and
	   		A.sec_ejec 		= B.sec_ejec and
	   		A.tipo_bien		= B.tipo_bien and
	   		A.tipo_pedido	        = B.tipo_pedido and
	   		A.nro_pedido		= B.nro_pedido and
			A.estado <> B.estado
		end

	end	
	
end

END
