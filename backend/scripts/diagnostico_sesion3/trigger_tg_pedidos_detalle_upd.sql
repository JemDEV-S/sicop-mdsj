CREATE TRIGGER dbo.TG_PEDIDOS_DETALLE_UPD
on dbo.SIG_DETALLE_PEDIDOS
for update 
as

------------------------------------------------------
-- Autor : Jony Ancasi
-- Objeto: Cambio de tamaño de campo Pedido y PECOSA
-- Cambio:
--			PECOSA NUMERIC(6) x NUMERIC(5)
--			PEDIDO VARCHAR(6) x VARCHAR(5)
------------------------------------------------------

declare @vid_ano          numeric(4),
	@vid_ejecutora    numeric(6),
	@vis_tipo_bien       char(1),
	@vis_tipo_ped        char(1),	
	--@vis_nro_ped         char(5),
	@vis_nro_ped         varchar(6),
	@vid_sec_cuadro   numeric(6),
	@vid_tipo_trans1  numeric(2),
	@vid_nro_destino  numeric(6),
	@vid_tipo_trans   numeric(2),
	@vid_nro_origen   numeric(6),
	@vid_m		  numeric(2)	

	-- actualiza por Nº de Cuadro Adquisición
if update(nro_cuadro)
   begin
	select @vid_ano = ano_eje,
	@vid_ejecutora = sec_ejec, 
	@vis_tipo_bien = tipo_bien,
	@vis_tipo_ped = tipo_pedido,
	@vis_nro_ped =  nro_pedido,
	@vid_sec_cuadro =nro_cuadro
	from inserted
	
	if @vis_tipo_ped = '1' 
	begin
		select @vid_tipo_trans1 = 1
	end

	if @vis_tipo_ped = '2'
	begin
		select @vid_tipo_trans1 = 2
	end

	--dato del pedido
	select @vid_nro_destino = nro_origen
	from sig_seguimiento
	where ano_eje 	  = @vid_ano       and
	      sec_ejec 	  = @vid_ejecutora and
	      tipo_bien   = @vis_tipo_bien and
	      tipo_pedido = @vis_tipo_ped  and
	      nro_pedido  = @vis_nro_ped   and
	      tipo_transaccion = @vid_tipo_trans1

	--dato del cuadro
	select @vid_tipo_trans = tipo_transaccion,
	       @vid_nro_origen = nro_origen
	from sig_seguimiento
	where ano_eje 	       = @vid_ano       and
	      sec_ejec 	       = @vid_ejecutora and
	      tipo_bien        = @vis_tipo_bien and
              nro_transaccion  = @vid_sec_cuadro and
		tipo_transaccion = 5 -- Revisar por Julio 20060925

	if @vid_sec_cuadro > 0 and @vid_nro_destino > 0 and @vid_nro_origen > 0 and @vid_tipo_trans > 0
	begin
		if not exists (select * 
		from sig_seguimiento_secuencia
		where ano_eje 	       = @vid_ano 	 and
		      sec_ejec	       = @vid_ejecutora  and
		      tipo_transaccion = @vid_tipo_trans and
		      nro_origen       = @vid_nro_origen and
		      tipo_transaccion_destino = @vid_tipo_trans1 and
		      nro_destino      = @vid_nro_destino )
		begin

			insert into sig_seguimiento_secuencia(
		    	ano_eje,
		    	sec_ejec, 
		    	tipo_transaccion,
		    	nro_origen,
		   	tipo_transaccion_destino, 
		    	nro_destino	
			)
		 	values(@vid_ano, @vid_ejecutora, @vid_tipo_trans, @vid_nro_origen, 
		       	@vid_tipo_trans1, @vid_nro_destino)
		end 		
	  end	
    end
