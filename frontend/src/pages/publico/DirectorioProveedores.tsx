import { useState } from 'react';
import { useDebounce } from 'use-debounce';
import { Search, Filter, Users } from 'lucide-react';
import { useProveedoresPublico } from '@/features/proveedores/hooks';
import { columnasProveedoresPublico } from '@/features/proveedores/secciones/ProveedoresColumnas';
import { DataTable } from '@/components/tabla/DataTable';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { ErrorState } from '@/components/layout/ErrorState';

const ANO_VIGENTE = 2026;

export default function DirectorioProveedores() {
  const [q, setQ] = useState('');
  const [debouncedQ] = useDebounce(q, 300);
  const [ano, setAno] = useState<number>(ANO_VIGENTE);

  const [{ pageIndex, pageSize }, setPagination] = useState({
    pageIndex: 0,
    pageSize: 25,
  });

  const { data, isLoading, isError, refetch } = useProveedoresPublico({
    ano,
    q: debouncedQ || undefined,
    page: pageIndex + 1,
    size: pageSize,
  });

  return (
    <div className="mx-auto max-w-6xl px-4 md:px-6 py-8">
      <PageHeader
        titulo="Directorio de Proveedores"
        descripcion="Empresas y personas que brindan bienes y servicios a la Municipalidad Distrital de San Jerónimo. Excluye datos de contacto según la Ley de Transparencia."
        densidad="publico"
      />

      <div className="space-y-6">
        <SectionCard titulo="Filtros" icono={Filter} padding="md">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 min-w-0">
              <Search
                className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                type="search"
                placeholder="Buscar por RUC o Razón Social..."
                className="pl-8"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                aria-label="Buscar proveedor"
              />
            </div>

            <div className="w-full sm:w-48">
              <Select
                value={ano.toString()}
                onValueChange={(val) => setAno(parseInt(val, 10))}
              >
                <SelectTrigger aria-label="Año de ejecución">
                  <SelectValue placeholder="Año de Ejecución" />
                </SelectTrigger>
                <SelectContent>
                  {[ANO_VIGENTE, ANO_VIGENTE - 1, ANO_VIGENTE - 2].map((y) => (
                    <SelectItem key={y} value={y.toString()}>
                      Año {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </SectionCard>

        {isError ? (
          <ErrorState
            titulo="No se pudo cargar el directorio"
            descripcion="Ocurrió un error al consultar el listado de proveedores. Intenta de nuevo."
            onReintentar={() => refetch()}
          />
        ) : (
          <SectionCard
            titulo="Proveedores registrados"
            icono={Users}
            padding="sm"
            bodyClassName="p-0"
          >
            <DataTable
              columns={columnasProveedoresPublico}
              data={data?.items || []}
              pageCount={data?.total ? Math.ceil(data.total / pageSize) : -1}
              manualPagination={true}
              isLoading={isLoading}
              pagination={{ pageIndex, pageSize }}
              onPaginationChange={setPagination}
            />
          </SectionCard>
        )}
      </div>
    </div>
  );
}
