/**
 * Directorio interno de proveedores (HU-19 · T-53).
 *
 * Ruta: /interno/proveedores — protegida por RequireAuth.
 *
 * Lista con datos de contacto (email/teléfono) y ejecución por órdenes; enlaza
 * al perfil detallado de cada proveedor. `monto_acumulado` es EJECUCIÓN real
 * (órdenes), no el valor de contratos (orden ≠ contrato).
 */
import { useEffect, useState } from 'react';
import { Search, X, Users } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonTable } from '@/components/layout/LoadingSkeleton';
import { useContextoInterno } from '@/store/contexto-interno';
import { useProveedores } from '@/features/provint/api';
import { TablaDirectorio } from '@/features/provint/secciones/TablaDirectorio';

const PAGE_SIZE = 25;

export default function Proveedores() {
  const año = useContextoInterno((s) => s.añoActivo);
  const [texto, setTexto] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);

  // Debounce de la búsqueda (350ms) para no golpear el backend en cada tecla.
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(texto);
      setPage(1);
    }, 350);
    return () => clearTimeout(t);
  }, [texto]);

  const { data, isLoading, isError, isFetching, refetch } = useProveedores({
    q,
    page,
    size: PAGE_SIZE,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Directorio de proveedores"
        descripcion={
          <>
            Proveedores con órdenes en <span className="text-muted-foreground">el año {año}</span>,
            con datos de contacto e historial.
          </>
        }
      />

      <SectionCard titulo="Buscar" padding="md">
        <div className="relative max-w-md">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Nombre o RUC del proveedor"
            aria-label="Buscar proveedor por nombre o RUC"
            className="h-9 w-full rounded-md border border-input bg-background pl-9 pr-9 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {texto ? (
            <button
              type="button"
              onClick={() => setTexto('')}
              aria-label="Limpiar búsqueda"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard titulo="Proveedores" icono={Users} padding="sm" bodyClassName="p-0">
        {isLoading ? (
          <div className="p-4">
            <SkeletonTable rows={8} cols={5} />
          </div>
        ) : isError ? (
          <div className="p-4">
            <ErrorState
              titulo="No se pudo cargar el directorio"
              descripcion="Puede ser un corte temporal del SIGA. Vuelve a intentarlo."
              onReintentar={() => refetch()}
            />
          </div>
        ) : data ? (
          <TablaDirectorio
            items={data.items}
            total={data.total}
            page={page}
            size={PAGE_SIZE}
            onPageChange={setPage}
            hayBusqueda={q.trim().length > 0}
            isFetching={isFetching}
          />
        ) : null}
      </SectionCard>
    </div>
  );
}
