CREATE TRIGGER dbo.tg_pedido_compra_ins
on dbo.SIG_PEDIDOS
for insert 
as

------------------------------------------------------
-- Autor : Jony Ancasi
-- Objeto: Cambio de tamaño de campo Pedido y PECOSA
-- Cambio:
--			PECOSA NUMERIC(6) x NUMERIC(5)
--			PEDIDO VARCHAR(6) x VARCHAR(5)
------------------------------------------------------

declare @vid_tipo_trans numeric(2),
		@vid_nro_origen numeric(6),
		@vid_ano         numeric(4),
		@vid_ejecutora   numeric(6),
		@vid_error	 int,
		@vis_tipo_bien   char(1),
		@vis_tipo_ped    char(1),		
		--@vis_nro_ped	 char(5),
		@vis_nro_ped	 varchar(6),
		@vis_est_trans 	 char(1),
		@vd_fecha_ped    datetime,
		@vd_fecha_apr    datetime,
		@vd_tipo_ppto    numeric(1),
		@vis_flag_pad   char(1),		
		--@vis_nro_pedido_rela char(5),
		@vis_nro_pedido_rela varchar(6),
		@vid_tipo_trans_ant numeric(2),
		@vid_nro_destino	numeric(6),
		@vis_cuser_id	 varchar(30),
		@vis_equipo_reg	 varchar(20)	
BEGIN

	select @vid_ano		     = B.ano_eje	 ,
	       @vid_ejecutora	 = B.sec_ejec    ,
	       @vis_tipo_bien    = B.tipo_bien	 ,
	       @vis_tipo_ped     = B.tipo_pedido ,
	       @vis_nro_ped      = B.nro_pedido  ,
	       @vis_est_trans	 = B.estado	 ,
	       @vd_fecha_ped     = B.fecha_pedido,
	       @vd_fecha_apr	 = B.fecha_aprob ,
	       @vd_tipo_ppto	 = B.tipo_ppto   ,
	       @vis_flag_pad     = B.flag_pad    ,
	       @vis_nro_pedido_rela  = B.nro_pedido_rela,
	       @vis_cuser_id	 = B.cuser_id    ,
	       @vis_equipo_reg	 = B.equipo_reg
      from inserted B

	if   (@vis_tipo_ped = '1')
	--tipo_modulo : pedidos programados
	begin
		select @vid_tipo_trans = 1
	end

	if   (@vis_tipo_ped = '2')       
	--tipo_modulo : pedidos no programados
	begin
		select @vid_tipo_trans = 2
	end
	
--	if   (@vis_tipo_ped = '5' and @vis_flag_pad = '1' ) and  ( @vd_tipo_ppto = 2)
	if   (@vis_tipo_ped = '5' and @vis_flag_pad = '0' ) and  ( @vd_tipo_ppto = 2)
	--tipo_modulo : pedidos de encargos de pecosas padre
	begin
		select @vid_tipo_trans = 17
	end

	if   (@vis_tipo_ped = '6') and  ( @vd_tipo_ppto = 2)
	--tipo_modulo : pedidos de encargos de pecosas detalle por padre
	begin
		select @vid_tipo_trans = 18
	end

	if   (@vis_tipo_ped = '1') or (@vis_tipo_ped = '2')       
	--tipo modulo : pedidos programados y pedidos no programados
	begin
		  insert into sig_seguimiento(
		  ano_eje,
		  sec_ejec,
		  tipo_transaccion,
		  nro_origen,	
		  fecha_transaccion,	
		  centro_costo,
		  solicitante,
		  estado_transaccion,
		  tipo_ppto,
		  tipo_bien,
		  tipo_pedido,		
		  nro_pedido,
		  fecha_reg,
		  cuser_id,
		  equipo_reg
		  )
		select B.ano_eje,
	       	B.sec_ejec,
	       	@vid_tipo_trans,
		(select (isnull(max(A.nro_origen),0)+1)
		 from sig_seguimiento A
		 where (A.ano_eje 	   = B.ano_eje ) and
		       (A.sec_ejec 	   = B.sec_ejec) and
		       (A.tipo_transaccion = @vid_tipo_trans)  ),
	      	B.fecha_pedido,
	      	B.centro_costo,
	      	B.empleado,	
	      	B.estado,
	     	B.tipo_ppto,
	     	B.tipo_bien,
	      	B.tipo_pedido,
	      	B.nro_pedido,	
	      	getdate(),
	      	@vis_cuser_id,
	      	@vis_equipo_reg	        					
		from  inserted B

		select	@vid_nro_origen = A.nro_origen
		from sig_seguimiento A,
	     	inserted B
		where A.ano_eje 	= B.ano_eje and
	      	A.sec_ejec 	= B.sec_ejec and
	      	A.tipo_pedido     = B.tipo_pedido and
	      	A.tipo_bien       = B.tipo_bien and
	      	A.nro_pedido 	= B.nro_pedido and 
	      	A.tipo_transaccion = @vid_tipo_trans

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
	       		(select isnull(max(sec_estado),0) +1 
			from sig_seguimiento_estado
			where ano_eje  	       = A.ano_eje 	and               
		      	sec_ejec	       = A.sec_ejec 	and 
		      	tipo_transaccion = @vid_tipo_trans and
		      	nro_origen       = @vid_nro_origen ) ,
			getdate(),
			A.estado,
			getdate(),
			@vis_cuser_id,
			@vis_equipo_reg
			from inserted A
	       	 end
	end	       	

	--insertar pedido de encargos por pecosas
	else if  ((@vis_tipo_ped = '5' and @vis_flag_pad = '0') or (@vis_tipo_ped = '6')) and ((@vd_tipo_ppto = 2) and (@vid_tipo_trans > 0))
	begin
		insert into sig_seguimiento(
		  ano_eje,
		  sec_ejec,
		  tipo_transaccion,
		  nro_origen,	
		  fecha_transaccion,	
		  centro_costo,
		  solicitante,
		  estado_transaccion,
		  tipo_ppto,
		  tipo_bien,
		  tipo_pedido,		
		  nro_pedido,
		  fecha_reg,
		  cuser_id,
		  equipo_reg
		  )
		select B.ano_eje,
	       	B.sec_ejec,
	       	@vid_tipo_trans,
		(select (isnull(max(A.nro_origen),0)+1)
		 from sig_seguimiento A
		 where (A.ano_eje 	   = B.ano_eje ) and
		       (A.sec_ejec 	   = B.sec_ejec) and
		       (A.tipo_transaccion = @vid_tipo_trans)  ),
	      	B.fecha_pedido,
	      	B.centro_costo,
	      	B.empleado,	
	      	B.estado,
	     	B.tipo_ppto,
	     	B.tipo_bien,
	      	B.tipo_pedido,
	      	B.nro_pedido,	
	      	getdate(),
	      	@vis_cuser_id,
	      	@vis_equipo_reg	        					
		from  inserted B

		select	@vid_nro_origen = A.nro_origen
		from sig_seguimiento A,
	     	inserted B
		where A.ano_eje 	= B.ano_eje and
	      	A.sec_ejec 	= B.sec_ejec and
	      	A.tipo_pedido     = B.tipo_pedido and
	      	A.tipo_bien       = B.tipo_bien and
	      	A.nro_pedido 	= B.nro_pedido  AND
	      	A.tipo_transaccion = @vid_tipo_trans

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
	       		(select isnull(max(sec_estado),0) +1 
			from sig_seguimiento_estado
			where ano_eje  	       = A.ano_eje 	and               
		      	sec_ejec	       = A.sec_ejec 	and 
		      	tipo_transaccion = @vid_tipo_trans and
		      	nro_origen       = @vid_nro_origen ) ,
			getdate(),
			A.estado,
			getdate(),
			@vis_cuser_id,
			@vis_equipo_reg
			from inserted A
	       	end

		if (@vis_tipo_ped = '6') 		
		begin

			select @vid_tipo_trans_ant = tipo_transaccion,
			       @vid_nro_destino = nro_origen
			from sig_seguimiento
			where ano_eje = @vid_ano 	and
			sec_ejec  = @vid_ejecutora	and
	       		tipo_bien = @vis_tipo_bien 	and
		       	tipo_pedido = '5'	  	and
			nro_pedido  = @vis_nro_pedido_rela

			-- Inserta en tabla secuencia
			if (@vid_nro_origen > 0  ) and (@vid_nro_destino > 0 ) and (@vid_tipo_trans_ant  > 0 )
			begin

				if not exists 
			   	(select *
	    			from sig_seguimiento_secuencia
			    	where 
				ano_eje     = @vid_ano       and
				sec_ejec    = @vid_ejecutora and
				tipo_transaccion   = @vid_tipo_trans and
				nro_origen = @vid_nro_origen  and
				tipo_transaccion_destino  = @vid_tipo_trans_ant   and
				nro_destino = @vid_nro_destino )
				begin
					insert into sig_seguimiento_secuencia
					(
					 ano_eje,
					 sec_ejec,
					 tipo_transaccion, 
					 nro_origen,
					 tipo_transaccion_destino,
					 nro_destino )
					values	
					(@vid_ano,
					 @vid_ejecutora,
					 @vid_tipo_trans, 
					 @vid_nro_origen,
					 @vid_tipo_trans_ant,
					 @vid_nro_destino)
				end
			end 

		end

	end	       	
end
