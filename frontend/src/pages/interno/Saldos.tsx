/**
 * Saldos presupuestales (HU-15 · T-48).
 *
 * Ruta: /interno/saldos — protegida por RequireAuth.
 *
 * Tabla dual por meta (SIGA operativo | MEF oficial). El devengado y el % de
 * ejecución salen SIEMPRE del MEF real (Docs/consolidacion-backend-presupuestal.md
 * §0.1) — el mismo número que ve el ciudadano en el portal público.
 */
import { useState } from 'react';
import { toast } from 'sonner';
import { Wallet, FileSpreadsheet, FileText } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { ErrorState } from '@/components/layout/ErrorState';
import {
  SkeletonKPI,
  SkeletonTable,
} from '@/components/layout/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { useContextoInterno } from '@/store/contexto-interno';
import { descargarSaldos, useResumenSaldos, useSaldos } from '@/features/saldos/api';
import { KpisSaldos } from '@/features/saldos/secciones/KpisSaldos';
import { FiltrosSaldos } from '@/features/saldos/secciones/FiltrosSaldos';
import { TablaSaldos } from '@/features/saldos/secciones/TablaSaldos';
import { FILTROS_SALDOS_VACIO, type FiltrosSaldos as TFiltrosSaldos } from '@/features/saldos/types';

const PAGE_SIZE = 25;

export default function Saldos() {
  const año = useContextoInterno((s) => s.añoActivo);
  const cc = useContextoInterno((s) => s.ccActivo);

  const [filtros, setFiltros] = useState<TFiltrosSaldos>(FILTROS_SALDOS_VACIO);
  const [page, setPage] = useState(1);
  const [descargando, setDescargando] = useState<'excel' | 'pdf' | null>(null);

  const resumenQ = useResumenSaldos();
  const listadoQ = useSaldos({ page, size: PAGE_SIZE, secFunc: filtros.secFunc });

  // Al cambiar el filtro de meta se vuelve a la primera página.
  const actualizarFiltros = (nuevos: TFiltrosSaldos) => {
    if (nuevos.secFunc !== filtros.secFunc) setPage(1);
    setFiltros(nuevos);
  };

  const exportar = async (formato: 'excel' | 'pdf') => {
    setDescargando(formato);
    try {
      await descargarSaldos(formato, {
        ano: año,
        ...(cc?.codigo ? { centro_costo: cc.codigo } : {}),
        ...(filtros.secFunc != null ? { sec_func: filtros.secFunc } : {}),
      });
      toast.success(`Reporte ${formato === 'excel' ? 'Excel' : 'PDF'} generado`);
    } catch {
      toast.error('No se pudo generar el reporte. Intenta de nuevo.');
    } finally {
      setDescargando(null);
    }
  };

  const acciones = (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => exportar('excel')}
        disabled={descargando !== null}
      >
        <FileSpreadsheet aria-hidden="true" />
        {descargando === 'excel' ? 'Generando…' : 'Excel'}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => exportar('pdf')}
        disabled={descargando !== null}
      >
        <FileText aria-hidden="true" />
        {descargando === 'pdf' ? 'Generando…' : 'PDF'}
      </Button>
    </>
  );

  const contexto = cc
    ? `${cc.nombre} · Año ${año}`
    : `Todas mis unidades · Año ${año}`;

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Saldos presupuestales"
        descripcion={
          <>
            Saldo y ejecución de cada meta.{' '}
            <span className="text-muted-foreground">{contexto}</span>
          </>
        }
        acciones={acciones}
      />

      {/* KPIs de resumen */}
      {resumenQ.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonKPI key={i} />
          ))}
        </div>
      ) : resumenQ.isError ? (
        <ErrorState
          titulo="No se pudo cargar el resumen de saldos"
          descripcion="Puede ser un corte temporal del servicio. Vuelve a intentarlo."
          onReintentar={() => resumenQ.refetch()}
        />
      ) : resumenQ.data ? (
        <KpisSaldos resumen={resumenQ.data} />
      ) : null}

      {/* Filtros */}
      <SectionCard titulo="Filtros" padding="md">
        <FiltrosSaldos
          filtros={filtros}
          onChange={actualizarFiltros}
          ccNombre={cc?.nombre ?? null}
        />
      </SectionCard>

      {/* Tabla dual */}
      <SectionCard titulo="Metas presupuestales" icono={Wallet} padding="sm" bodyClassName="p-0">
        {listadoQ.isLoading ? (
          <div className="p-4">
            <SkeletonTable rows={8} cols={7} />
          </div>
        ) : listadoQ.isError ? (
          <div className="p-4">
            <ErrorState
              titulo="No se pudieron cargar los saldos"
              descripcion="Puede ser un corte temporal del SIGA. Vuelve a intentarlo."
              onReintentar={() => listadoQ.refetch()}
            />
          </div>
        ) : listadoQ.data ? (
          <TablaSaldos
            items={listadoQ.data.items}
            total={listadoQ.data.total}
            page={page}
            size={PAGE_SIZE}
            onPageChange={setPage}
            filtroSemaforo={filtros.semaforo}
            onLimpiarSemaforo={() => setFiltros({ ...filtros, semaforo: null })}
            isFetching={listadoQ.isFetching}
          />
        ) : null}
      </SectionCard>
    </div>
  );
}
