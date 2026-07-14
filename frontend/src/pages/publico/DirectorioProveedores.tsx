import { useState, useMemo } from 'react';
import { useDebounce } from 'use-debounce';
import { Search, Users, X } from 'lucide-react';
import { useProveedoresPublico } from '@/features/proveedores/hooks';
import { TablaProveedores, type SortKey } from '@/features/proveedores/secciones/TablaProveedores';
import { PublicHero } from '@/components/publico/PublicHero';
import { SectionBand } from '@/components/publico/SectionBand';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const ANIO_VIGENTE = 2026;
const ANOS_DISPONIBLES = [ANIO_VIGENTE, ANIO_VIGENTE - 1, ANIO_VIGENTE - 2];

export default function DirectorioProveedores() {
  const [q, setQ] = useState('');
  const [debouncedQ] = useDebounce(q, 300);
  const [ano, setAno] = useState<number>(ANIO_VIGENTE);
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 25 });
  const [sortKey, setSortKey] = useState<SortKey>('monto');

  const { data, isLoading, isError, refetch } = useProveedoresPublico({
    ano,
    q: debouncedQ || undefined,
    page: pagination.pageIndex + 1,
    size: pagination.pageSize,
  });

  const total = data?.total ?? 0;
  const pageCount = data ? Math.ceil(data.total / data.size) : -1;

  // Cantidad de proveedores con al menos una orden en el año (sobre la página actual — no
  // hay endpoint de agregados; damos una lectura honesta de "en esta página, cuántos tienen").
  const conOrdenesPagina = useMemo(
    () => (data?.items ?? []).filter((p) => (p.nro_ordenes ?? 0) > 0).length,
    [data],
  );

  const limpiarBusqueda = () => {
    setQ('');
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  };

  return (
    <div className="bg-background">
      {/* HERO */}
      <PublicHero
        eyebrow={<>Directorio de Proveedores · Año {ano}</>}
        titulo={
          <>
            ¿Quién le vende <span className="text-primary">a la muni</span>?
          </>
        }
        subtitulo="Empresas y personas que brindan bienes y servicios a la Municipalidad Distrital de San Jerónimo. Excluye datos de contacto según la Ley de Transparencia."
        acciones={
          <Select value={ano.toString()} onValueChange={(v) => setAno(parseInt(v, 10))}>
            <SelectTrigger className="w-40" aria-label="Año fiscal">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ANOS_DISPONIBLES.map((y) => (
                <SelectItem key={y} value={y.toString()}>
                  Ejercicio {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
        destacado={
          <div className="relative rounded-2xl bg-card border border-border p-8 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <span
                className="inline-block w-1.5 h-1.5 rounded-full bg-primary"
                aria-hidden="true"
              />
              <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                Padrón vigente
              </span>
            </div>

            <div className="flex items-baseline gap-3">
              <span className="inline-flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary shrink-0">
                <Users className="w-7 h-7" aria-hidden="true" />
              </span>
              <div>
                {isLoading ? (
                  <div
                    className="h-10 w-32 bg-muted animate-pulse rounded-md"
                    aria-hidden="true"
                  />
                ) : (
                  <p className="text-4xl md:text-5xl font-bold text-foreground leading-none tabular-nums">
                    {total.toLocaleString('es-PE')}
                  </p>
                )}
                <p className="mt-2 text-sm text-muted-foreground">
                  {total === 1 ? 'proveedor registrado' : 'proveedores registrados'}
                </p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-border">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Fuente: SIGA · Datos actualizados automáticamente. La ley excluye
                datos de contacto (email, teléfono) del ámbito público.
              </p>
            </div>
          </div>
        }
      />

      {/* BUSCADOR + CONTADOR */}
      <SectionBand tono="muted" denso>
        <div className="mb-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-primary mb-1">
            Encuentra un proveedor
          </p>
          <p className="text-sm text-muted-foreground">
            Busca por RUC o Razón Social. La búsqueda se aplica a todo el año seleccionado.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 min-w-0">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none"
              aria-hidden="true"
            />
            <Input
              type="search"
              placeholder="Buscar por RUC (ej: 20501234567) o razón social..."
              className="pl-10 h-11 text-base"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPagination((p) => ({ ...p, pageIndex: 0 }));
              }}
              aria-label="Buscar proveedor"
            />
            {q ? (
              <button
                type="button"
                onClick={limpiarBusqueda}
                className="absolute right-3 top-1/2 -translate-y-1/2 inline-flex items-center justify-center h-6 w-6 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                aria-label="Limpiar búsqueda"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>
            ) : null}
          </div>
        </div>

        {debouncedQ ? (
          <div className="mt-4 flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Resultados para:</span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 text-primary px-3 py-1 text-xs font-semibold">
              "{debouncedQ}"
              <button
                type="button"
                onClick={limpiarBusqueda}
                className="hover:opacity-70"
                aria-label="Quitar filtro de búsqueda"
              >
                <X className="w-3 h-3" aria-hidden="true" />
              </button>
            </span>
            <span className="text-xs text-muted-foreground ml-1">
              · {total.toLocaleString('es-PE')} {total === 1 ? 'resultado' : 'resultados'}
            </span>
          </div>
        ) : null}
      </SectionBand>

      {/* TABLA */}
      <SectionBand tono="background">
        <div className="mb-4 flex items-baseline justify-between">
          <div>
            <p className="text-sm font-semibold text-foreground">
              {isLoading
                ? 'Cargando proveedores...'
                : `${total.toLocaleString('es-PE')} proveedores en el padrón`}
            </p>
            {!isLoading && data ? (
              <p className="text-xs text-muted-foreground mt-0.5">
                En esta página, {conOrdenesPagina}{' '}
                {conOrdenesPagina === 1 ? 'tiene' : 'tienen'} al menos una orden en {ano}.
              </p>
            ) : null}
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          {isError ? (
            <div className="p-10 text-center">
              <p className="text-sm text-destructive mb-3">
                No se pudo cargar el directorio.
              </p>
              <Button variant="outline" onClick={() => refetch()}>
                Reintentar
              </Button>
            </div>
          ) : (
            <TablaProveedores
              items={data?.items ?? []}
              isLoading={isLoading}
              pageIndex={pagination.pageIndex}
              pageSize={pagination.pageSize}
              pageCount={pageCount}
              totalItems={total}
              onPageChange={(p) => setPagination((prev) => ({ ...prev, pageIndex: p }))}
              onPageSizeChange={(s) =>
                setPagination(() => ({ pageIndex: 0, pageSize: s }))
              }
              sortKey={sortKey}
              onSortChange={setSortKey}
            />
          )}
        </div>
      </SectionBand>
    </div>
  );
}
