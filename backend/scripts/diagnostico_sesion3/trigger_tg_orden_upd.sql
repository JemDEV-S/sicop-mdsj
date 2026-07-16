CREATE  trigger dbo.tg_orden_upd
 on sig_orden_adquisicion  
for update
as
declare @anio	   	    numeric(4),
	@ejecutora	    numeric(6),
	@tipo_bien          char(1),
	@tipo_ppto      numeric(2),
	@estado		    char(1),
	@estado_siaf	    char(1),
    @ls_estado_ori      varchar(1),
    @ls_estado_siaf_ori varchar(1),
	@estado_ant	    char(1),
	@estado_siaf_ant    char(1),
	@estado_seg	    char(1),
	@nro_orden          numeric(7),
	@vi_tipo_transaccion numeric(2),
	@vi_tipo_trans_ant  numeric(2),
	@vi_nro_origen      numeric(6),
	@cuenta		    integer, 	
    @vi_ano_cuadro      numeric(4),
    @vi_sec_cuadro      numeric(6),
	@vi_nro_destino     numeric(6),
	@vis_cuser_id	 varchar(30),
	@vis_equipo_reg	 varchar(20)
    
select 
@anio	    = ano_eje,
@ejecutora   = sec_ejec,
@nro_orden   =  nro_orden,
@tipo_bien   =  tipo_bien,
@tipo_ppto   =  tipo_ppto,
@estado      =  estado,
@estado_siaf =  estado_siaf,
@vi_ano_cuadro  = ano_cuadro,
@vi_sec_cuadro  = sec_cuadro,
@vis_cuser_id   = CUSER_MOD,
@vis_equipo_reg = EQUIPO_MOD
from  inserted

/*fact: si no se actualiza las campos mod, los actualizo de la sesion*/
IF  OBJECT_ID('tempdb..#SIG_SESION') IS  NOT NULL
    BEGIN
        SELECT  @vis_cuser_id   = CUSER_ID,
                @vis_equipo_reg = EQUIPO_REG
        FROM    #SIG_SESION
    END

update sig_orden_adquisicion 
set CUSER_MOD = @vis_cuser_id,
    EQUIPO_MOD = @vis_equipo_reg,
    FECHA_MOD  = getdate()
where  
ano_eje     = @anio      and
sec_ejec    = @ejecutora and	 
nro_orden   = @nro_orden AND
tipo_bien 	= @tipo_bien and
tipo_ppto   = @tipo_ppto 


/*obtengo el estado original*/
SELECT  @ls_estado_ori      = ESTADO,
        @ls_estado_siaf_ori = ESTADO_SIAF
FROM    DELETED

/*si no ha cambiado el estado, salgo*/
IF @ls_estado_ori       = @estado AND
    @ls_estado_siaf_ori = @estado_siaf
BEGIN
    RETURN
END

if update(estado) or update(ESTADO_SIAF)
begin
	Select @estado_ant      =  A.estado,
	       @estado_siaf_ant =  A.estado_siaf 
	from  deleted A
	
	if @estado = @estado_ant and @estado_siaf = @estado_siaf_ant
	begin
	 Goto salida
	end 	

-- 15: Cuadro Adquisicion
select @vi_tipo_trans_ant= 15

if @tipo_bien = 'B'
begin
 select @vi_tipo_transaccion = 8
end
else
begin
 if @tipo_bien = 'S'
  begin
   select @vi_tipo_transaccion = 9
  end
 else
  begin
   Goto salida
  end 
end

select	@cuenta = count(*)
from sig_seguimiento A, 
     inserted B 
where A.ano_eje 	 = B.ano_eje   and 
      A.sec_ejec 	 = B.sec_ejec  and 
      A.nro_transaccion	 = B.nro_orden and 
      A.tipo_bien        = B.tipo_bien and 
      A.tipo_ppto        = B.tipo_ppto and 
      A.tipo_transaccion = @vi_tipo_transaccion 

if @cuenta = 0 
begin
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
   	      @vi_tipo_transaccion,
	      (select (isnull(max(A.nro_origen),0)+1)
	       from sig_seguimiento A
	       where (A.ano_eje 	   = B.ano_eje ) and
		     (A.sec_ejec 	   = B.sec_ejec) and
		     (A.tipo_transaccion   = @vi_tipo_transaccion)),
	      B.nro_orden,		
	      B.fecha_orden, --Fecha de la Orden
	      null,
	      null,	
	      B.estado,
	      B.tipo_ppto,
	      B.tipo_bien,
	      null,	
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
	      A.tipo_transaccion = @vi_tipo_transaccion

	-- Inserta Secuencia 	
	select @vi_nro_destino = nro_origen
	 from sig_seguimiento
	where ano_eje   	= @anio and
	      sec_ejec  	= @ejecutora and
	      tipo_bien  	= @tipo_bien   and
	      nro_transaccion   = @vi_sec_cuadro  and
	      tipo_transaccion  = @vi_tipo_trans_ant

	if @vi_nro_destino is not null
	begin
		insert into sig_seguimiento_secuencia(ano_eje, sec_ejec, tipo_transaccion,
			nro_origen, tipo_transaccion_destino, nro_destino)
		values(@anio, @ejecutora, @vi_tipo_transaccion,
			@vi_nro_origen, @vi_tipo_trans_ant, @vi_nro_destino)
	end


end 
else
begin
	select	@vi_nro_origen = A.nro_origen 
	from sig_seguimiento A, 
	     inserted B 
	where A.ano_eje 	 = B.ano_eje   and 
	      A.sec_ejec 	 = B.sec_ejec  and 
	      A.nro_transaccion	 = B.nro_orden and 
	      A.tipo_bien        = B.tipo_bien and 
	      A.tipo_ppto        = B.tipo_ppto and 
	      A.tipo_transaccion = @vi_tipo_transaccion 
end 


select @estado_seg = 'x'

if @estado = '0' --and @estado_siaf 
 select @estado_seg = '0' -- Pendiente

if @estado = '1' and @estado_siaf = '0'
select @estado_seg = '1' -- Comprometido

if @estado = '1' and @estado_siaf = '1'
begin
select @estado_seg = '1' -- Comprometido en Proceso (No genera seguimiento)
Goto salida
end 

if @estado = '1' and @estado_siaf = '2'
select @estado_seg = '2' -- Comprometido SIAF

if @estado = '1' and @estado_siaf = '3'
select @estado_seg = '3' -- Comprometido / SIAF Rechazado

if @estado = '4' and @estado_siaf = '0'
select @estado_seg = '4' -- Anulado

if @estado = '4' and @estado_siaf = '2'
select @estado_seg = '5' -- Anulado / SIAF

if @estado = '5' and @estado_siaf = '2'
select @estado_seg = '6' -- Anulado x Error / SIAF

if @estado_seg = 'x'
begin
-- No ingresa a ningun caso
Goto salida
end 

	-- Actualiza el seguimiento
	update sig_seguimiento 
	 set estado_transaccion = @estado_seg         
	where  ano_eje       	= @anio         and
	       sec_ejec      	= @ejecutora   and	 
	       tipo_transaccion	= @vi_tipo_transaccion   and
	       nro_origen	= @vi_nro_origen

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
	       @vi_tipo_transaccion,
	       @vi_nro_origen,
	       (select isnull(max(sec_estado),0) +1 
		from sig_seguimiento_estado
		where ano_eje  	       = A.ano_eje	and               
		      sec_ejec	       = A.sec_ejec 	and 
		      tipo_transaccion = @vi_tipo_transaccion and
		      nro_origen       = @vi_nro_origen ) ,
		getdate(),
		@estado_seg,
		getdate(),
		@vis_cuser_id,
		@vis_equipo_reg
	from inserted A  	

end

salida:
return

