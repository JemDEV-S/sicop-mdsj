CREATE  trigger dbo.tg_orden_ins 
on sig_orden_adquisicion  
for insert 
as
declare @vi_tipo_trans      numeric(2),
	@vi_tipo_trans_ant  numeric(2),
	@vi_anio	        numeric(4),
	@vi_ejecutora	    numeric(6),
	@vi_nro_orden	    numeric(7),
	@vi_nro_origen      numeric(6),
	@vi_nro_destino     numeric(6),
	@vi_tipo_ppto       numeric(2),  	
	@vs_tipo_bien       char(1),
	@vi_ano_cuadro	    numeric(4),
	@vi_sec_cuadro      numeric(6),
	@vis_cuser_id	 varchar(30),
	@vis_equipo_reg	 varchar(20)	

    begin
	-- 15: Cuadro Adquisicion
	select @vi_tipo_trans_ant= 15

	select @vi_anio	       = ano_eje,
	       @vi_ejecutora   = sec_ejec,	
	       @vs_tipo_bien   = tipo_bien,
	       @vi_ano_cuadro  = ano_cuadro,
	       @vi_sec_cuadro  = sec_cuadro,
	       @vi_nro_orden   = nro_orden,		       	       
	       @vi_tipo_ppto   = tipo_ppto,
	       @vis_cuser_id	 = cuser_id,
	       @vis_equipo_reg	 = equipo_reg
	from inserted 

    --actualizo la fecha de registro
    UPDATE  SIG_ORDEN_ADQUISICION
    SET     FECHA_REG   = GETDATE()
    WHERE   ANO_EJE     = @vi_anio
    AND     SEC_EJEC    = @vi_ejecutora
    AND     NRO_ORDEN   = @vi_nro_orden
    AND     TIPO_BIEN   = @vs_tipo_bien
    AND     TIPO_PPTO   = @vi_tipo_ppto

	if @vs_tipo_bien = 'B'
	begin
	-- 8: Orden Compra	
	 select @vi_tipo_trans = 8
	end
	else
	begin
	 if @vs_tipo_bien = 'S'
	  begin
	-- 9: Orden Servicio
	   select @vi_tipo_trans = 9
	  end
	 else
	  begin
	   Goto salida
	  end 
	end
	
	
      delete from sig_seguimiento_secuencia            
      where ano_eje     = @vi_anio      AND
       sec_ejec          = @vi_ejecutora AND
       tipo_transaccion  = @vi_tipo_trans and
      nro_origen        in (select nro_origen
      from sig_seguimiento
      where ano_eje     = @vi_anio      AND
       sec_ejec          = @vi_ejecutora AND
       tipo_transaccion  = @vi_tipo_trans and
       tipo_bien         = @vs_tipo_bien and
      nro_transaccion  = @vi_nro_orden)
      
      delete from sig_seguimiento_estado
      where ano_eje     = @vi_anio      AND
       sec_ejec          = @vi_ejecutora AND
       tipo_transaccion  = @vi_tipo_trans and
      nro_origen        in (select nro_origen
      from sig_seguimiento
      where ano_eje     = @vi_anio      AND
       sec_ejec          = @vi_ejecutora AND
       tipo_transaccion  = @vi_tipo_trans and
       tipo_bien         = @vs_tipo_bien and
      nro_transaccion  = @vi_nro_orden)
      
      delete from sig_seguimiento
      where ano_eje     = @vi_anio      AND
       sec_ejec          = @vi_ejecutora AND
       tipo_transaccion  = @vi_tipo_trans and
       tipo_bien         = @vs_tipo_bien and
      nro_transaccion  = @vi_nro_orden    
      	

	-- Inserta Seguimiento
	insert into sig_seguimiento(
		  ano_eje,
		  sec_ejec,
		  tipo_transaccion,
		  nro_origen,	
		  nro_transaccion,		
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
      select  B.ano_eje,
              B.sec_ejec,
   	      @vi_tipo_trans,
	      (select (isnull(max(A.nro_origen),0)+1)
	       from sig_seguimiento A
	       where (A.ano_eje 	   = B.ano_eje ) and
		     (A.sec_ejec 	   = B.sec_ejec) and
		     (A.tipo_transaccion   = @vi_tipo_trans)  ),
	      B.nro_orden,		
	      B.fecha_orden,
	      null,
	      null,
	      B.estado,
	      B.tipo_ppto,
	      B.tipo_bien,
	      convert(varchar(2),@vi_tipo_trans),
	      convert(varchar(7), B.nro_orden),	
	      getdate(),
	      @vis_cuser_id,
	      @vis_equipo_reg
	from  inserted B

	
	-- Recupera Argumento
	select	@vi_nro_origen = A.nro_origen
	from sig_seguimiento A,
	     inserted B
	where A.ano_eje 	 = B.ano_eje   and
	      A.sec_ejec 	 = B.sec_ejec  and
	      A.nro_transaccion	 = B.nro_orden and
	      A.tipo_bien        = B.tipo_bien and
	      A.tipo_ppto        = B.tipo_ppto and
	      A.tipo_transaccion = @vi_tipo_trans

	-- Inserta estados
	insert into sig_seguimiento_estado(
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
	select A.ano_eje,
	       A.sec_ejec,
	       @vi_tipo_trans,
	       @vi_nro_origen,
	       (select isnull(max(sec_estado),0) +1 
		from sig_seguimiento_estado
		where ano_eje  	       = A.ano_eje	and               
		      sec_ejec	       = A.sec_ejec 	and 
		      tipo_transaccion = @vi_tipo_trans and
		      nro_origen       = @vi_nro_origen ) ,
		A.fecha_orden,
		A.estado,
		getdate(),
		@vis_cuser_id,
		@vis_equipo_reg
	from inserted A  	

	-- Inserta Secuencia 	
	select @vi_nro_destino = nro_origen
	from sig_seguimiento  
	where ano_eje   	= @vi_ano_cuadro  and
	      sec_ejec  	= @vi_ejecutora   and
	      tipo_bien  	= @vs_tipo_bien   and
	      nro_transaccion   = @vi_sec_cuadro  and
	      tipo_transaccion  = @vi_tipo_trans_ant
	if @vi_nro_destino is not null
	begin
		insert into sig_seguimiento_secuencia(ano_eje, sec_ejec, tipo_transaccion,
			nro_origen, tipo_transaccion_destino, nro_destino)
		values(@vi_anio, @vi_ejecutora, @vi_tipo_trans,
			@vi_nro_origen, @vi_tipo_trans_ant, @vi_nro_destino)		
	end
end

salida:
return

