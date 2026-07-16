CREATE   procedure sp_genera_seguimiento(@vi_anio numeric(4), @vi_ejecutora numeric(6),@tipo_ini numeric(2), @nro_nro_ini numeric(6))
as

begin

declare @existe int
declare @existe_sup int

create table #SIG_SEG_TRANS_TMP
(anio numeric(4), ejecutora numeric(6), tipo numeric(2), nro numeric(6))

create table #SIG_SEG_TRANS_ORIGEN
(anio numeric(4), ejecutora numeric(6), tipo numeric(2), nro numeric(6))

create table #SIG_SEG_TRANS_DESTINO
(anio numeric(4), ejecutora numeric(6), tipo numeric(2), nro numeric(6))
 
create table #SIG_SEG_TRANS_DOCUM
(anio numeric(4), ejecutora numeric(6),tipo numeric(2), nro numeric(6))

insert into #SIG_SEG_TRANS_DOCUM(anio, ejecutora, tipo, nro)
values(@vi_anio, @vi_ejecutora, @tipo_ini, @nro_nro_ini)

insert into #SIG_SEG_TRANS_TMP(anio, ejecutora, tipo, nro)
values(@vi_anio, @vi_ejecutora, @tipo_ini, @nro_nro_ini)

insert into #SIG_SEG_TRANS_ORIGEN(anio, ejecutora, tipo, nro)
values(@vi_anio, @vi_ejecutora, @tipo_ini, @nro_nro_ini)

insert into #SIG_SEG_TRANS_DESTINO(anio, ejecutora, tipo, nro)
select ano_eje, sec_ejec, tipo_transaccion, nro_origen
from sig_seguimiento_secuencia
where ano_eje 		       = @vi_anio      and
      sec_ejec		       = @vi_ejecutora and
      tipo_transaccion_destino = @tipo_ini     and	
      nro_destino 	       = @nro_nro_ini

insert into #SIG_SEG_TRANS_DOCUM(anio, ejecutora, tipo, nro)
select ano_eje, sec_ejec, tipo_transaccion, nro_origen
from sig_seguimiento_secuencia
where ano_eje 		       = @vi_anio      and
      sec_ejec		       = @vi_ejecutora and
      tipo_transaccion_destino = @tipo_ini     and	
      nro_destino 	       = @nro_nro_ini

/*
insert into aaa(anio, ejecutora, tipo, nro)
select ano_eje, sec_ejec, tipo_transaccion, nro_origen
from sig_seguimiento_secuencia
where ano_eje 		       = @vi_anio      and
      sec_ejec		       = @vi_ejecutora and
      tipo_transaccion_destino = @tipo_ini     and	
      nro_destino 	       = @nro_nro_ini
*/

select @existe = count(*) 
from sig_seguimiento_secuencia
where   ANO_EJE   = @vi_anio 	     and
	SEC_EJEC  = @vi_ejecutora    and
	TIPO_TRANSACCION = @tipo_ini and
        NRO_ORIGEN = @nro_nro_ini

select @existe_sup = count(*) 
from sig_seguimiento_secuencia
where   ANO_EJE  	 	 = @vi_anio 	     and
	SEC_EJEC  		 = @vi_ejecutora    and
	TIPO_TRANSACCION_DESTINO = @tipo_ini and
       	NRO_DESTINO		 = @nro_nro_ini

  while @existe > 0 
  begin
            delete from #SIG_SEG_TRANS_TMP

            insert into #SIG_SEG_TRANS_TMP(anio, ejecutora, tipo, nro)
            select ANO_EJE, SEC_EJEC, TIPO_TRANSACCION_DESTINO, NRO_DESTINO
            from sig_seguimiento_secuencia
            where exists
                        (select 1 from #SIG_SEG_TRANS_ORIGEN
                        where   anio 	  = ANO_EJE	     and
				ejecutora = SEC_EJEC 	     and
				tipo	  = TIPO_TRANSACCION and
	                        nro	  = NRO_ORIGEN)

            insert into #SIG_SEG_TRANS_DOCUM(anio, ejecutora, tipo, nro)
            select ANO_EJE, SEC_EJEC, TIPO_TRANSACCION_DESTINO, NRO_DESTINO
            from sig_seguimiento_secuencia
            where exists
                      (select 1 from #SIG_SEG_TRANS_ORIGEN
                	where  anio 	= ANO_EJE 	   and
			       ejecutora= SEC_EJEC         and
			       tipo 	= TIPO_TRANSACCION and
                      	       nro  	= NRO_ORIGEN)

            select @existe = count(*) 
            from sig_seguimiento_secuencia
            where exists
                        (select 1 from #SIG_SEG_TRANS_TMP
                        where anio 	= ANO_EJE 	   and
			      ejecutora	= SEC_EJEC 	   and
			      tipo 	= TIPO_TRANSACCION and
                              nro 	= NRO_ORIGEN)

            if @existe > 0 
            begin
                        delete from #SIG_SEG_TRANS_ORIGEN
                     
                        insert into #SIG_SEG_TRANS_ORIGEN
                        select * from #SIG_SEG_TRANS_TMP

            end      
  end

  while @existe_sup > 0
	begin
	    delete from #SIG_SEG_TRANS_TMP
	
	    insert into #SIG_SEG_TRANS_TMP(anio, ejecutora, tipo, nro)
            select ANO_EJE, SEC_EJEC, TIPO_TRANSACCION, NRO_ORIGEN
            from sig_seguimiento_secuencia
            where exists
                        (select 1 from #SIG_SEG_TRANS_DESTINO
                        where   anio 	  = ANO_EJE	     and
				ejecutora = SEC_EJEC 	     and
				tipo	  = TIPO_TRANSACCION_DESTINO and
	                        nro	  = NRO_DESTINO)	

	    insert into #SIG_SEG_TRANS_DOCUM(anio, ejecutora, tipo, nro)
            select ANO_EJE, SEC_EJEC, TIPO_TRANSACCION, NRO_ORIGEN
            from sig_seguimiento_secuencia
            where exists
                        (select 1 from #SIG_SEG_TRANS_DESTINO
                        where   anio 	  = ANO_EJE	     and
				ejecutora = SEC_EJEC 	     and
				tipo	  = TIPO_TRANSACCION_DESTINO and
	                        nro	  = NRO_DESTINO)	

            select @existe_sup = count(*) 
            from sig_seguimiento_secuencia
            where exists
                        (select 1 from #SIG_SEG_TRANS_TMP
                        where anio 	= ANO_EJE 	   and
			      ejecutora	= SEC_EJEC 	   and
			      tipo 	= TIPO_TRANSACCION_DESTINO and
                              nro 	= NRO_DESTINO)

            if @existe_sup > 0 
            begin
                        delete from #SIG_SEG_TRANS_DESTINO
                     
                        insert into #SIG_SEG_TRANS_DESTINO
                        select * from #SIG_SEG_TRANS_TMP

            end      	
		
	end		
		
	select B.fecha_reg, B.centro_costo, B.tipo_transaccion, B.nro_pedido, 
	       B.fecha_transaccion, B.estado_transaccion, B.ano_eje, B.sec_ejec,
	       B.nro_origen, C.nombre_depend as nombre_depend , D.nombre as nombre,
	       B.cuser_id
	from #SIG_SEG_TRANS_DOCUM A,
	     sig_seguimiento B
         LEFT OUTER JOIN sig_centro_costo C
         ON B.ano_eje      = C.ano_eje      and 
            B.sec_ejec     = C.sec_ejec     and 
            B.centro_costo = C.centro_costo,
         ejecutora D
   where A.anio      = B.ano_eje          and
	     A.ejecutora = B.sec_ejec         and
	     A.tipo      = B.tipo_transaccion and
	     A.nro       = B.nro_origen       and
	     B.sec_ejec  = D.sec_ejec

end

