import { useState } from 'react';
import { useDebounce } from 'use-debounce';
import { useProveedoresPublico } from '../../features/proveedores/hooks';
import { columnasProveedoresPublico } from '../../features/proveedores/secciones/ProveedoresColumnas';
import { DataTable } from '../../components/tabla/DataTable';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Search } from 'lucide-react';

const ANO_VIGENTE = 2026;

export default function DirectorioProveedores() {
  const [q, setQ] = useState('');
  const [debouncedQ] = useDebounce(q, 300);
  const [ano, setAno] = useState<number>(ANO_VIGENTE);
  
  const [{ pageIndex, pageSize }, setPagination] = useState({
    pageIndex: 0,
    pageSize: 25,
  });

  const { data, isError } = useProveedoresPublico({
    ano,
    q: debouncedQ || undefined,
    page: pageIndex + 1,
    size: pageSize,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Directorio de Proveedores</h1>
        <p className="text-muted-foreground">
          Directorio de proveedores registrados en la entidad, excluyendo datos de contacto según Ley de Transparencia.
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Buscar por RUC o Razón Social..."
            className="pl-8"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        
        <div className="w-full sm:w-48">
          <Select value={ano.toString()} onValueChange={(val) => setAno(parseInt(val, 10))}>
            <SelectTrigger>
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

      {isError ? (
        <div className="rounded-md bg-destructive/15 p-4 text-sm text-destructive">
          Ocurrió un error al cargar el directorio de proveedores. Por favor, intente nuevamente.
        </div>
      ) : (
        <div className="rounded-md border bg-card">
          <DataTable
            columns={columnasProveedoresPublico}
            data={data?.items || []}
            pageCount={data?.total ? Math.ceil(data.total / pageSize) : -1}
            pagination={{ pageIndex, pageSize }}
            onPaginationChange={setPagination}
          />
        </div>
      )}
    </div>
  );
}
