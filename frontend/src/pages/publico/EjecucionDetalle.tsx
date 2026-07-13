import React, { useState, useEffect } from 'react';
import { useEjecucionDetalle, useExportarEjecucionPublico, useEjecucionPorFuncion, useEjecucionPorFuente } from '../../features/ejecucion/hooks';
import { ejecucionDetalleColumnas } from '../../features/ejecucion/secciones/EjecucionDetalleColumnas';
import { DataTable } from '../../components/tabla/DataTable';
import { Button } from '../../components/ui/button';
import { Download } from 'lucide-react';

export default function EjecucionDetalle() {
  // Filtros locales (input del usuario)
  const [localFiltros, setLocalFiltros] = useState({
    ano: 2026,
    funcion: '',
    fuente: '',
    categoria_gasto: ''
  });

  // Filtros debounced (para despachar al backend)
  const [debouncedFiltros, setDebouncedFiltros] = useState(localFiltros);

  // Paginación (estado unificado para TanStack Table)
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 10
  });

  // Debounce effect
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedFiltros(localFiltros);
      // Resetear paginacion al cambiar filtros
      setPagination(prev => ({ ...prev, pageIndex: 0 }));
    }, 300);
    return () => clearTimeout(handler);
  }, [localFiltros]);

  // Obtener datos para Selects
  const { data: funciones } = useEjecucionPorFuncion({ ano: localFiltros.ano });
  const { data: fuentes } = useEjecucionPorFuente({ ano: localFiltros.ano });

  // Query principal
  const { data, isLoading, isError } = useEjecucionDetalle({
    ano: debouncedFiltros.ano,
    funcion: debouncedFiltros.funcion || undefined,
    fuente: debouncedFiltros.fuente || undefined,
    categoria_gasto: debouncedFiltros.categoria_gasto || undefined,
    page: pagination.pageIndex + 1, // backend usa 1-based
    size: pagination.pageSize
  });

  // Mutación de exportación
  const { exportar } = useExportarEjecucionPublico();

  const handleExport = () => {
    exportar({
      ano: debouncedFiltros.ano,
      funcion: debouncedFiltros.funcion || undefined,
      fuente: debouncedFiltros.fuente || undefined,
      categoria_gasto: debouncedFiltros.categoria_gasto || undefined
    });
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    const { name, value } = e.target;
    setLocalFiltros(prev => ({ ...prev, [name]: value }));
  };

  const pageCount = data ? Math.ceil(data.total / data.size) : -1;

  // Clases compartidas para selects (Tailwind - matches Shadcn Input)
  const selectClassName = "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Ejecución a Nivel de Meta</h1>
          <p className="text-muted-foreground mt-1">
            Explore el detalle del gasto público por cada meta presupuestal.
          </p>
        </div>
        <Button onClick={handleExport} variant="outline" className="shrink-0 gap-2">
          <Download className="w-4 h-4" />
          Exportar a Excel
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 p-4 border rounded-lg bg-card text-card-foreground shadow-sm">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Año Fiscal</label>
          <select 
            name="ano" 
            value={localFiltros.ano} 
            onChange={handleFilterChange}
            className={selectClassName}
          >
            <option value="2026">2026</option>
            <option value="2025">2025</option>
          </select>
        </div>
        
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Función</label>
          <select 
            name="funcion" 
            value={localFiltros.funcion} 
            onChange={handleFilterChange}
            className={selectClassName}
          >
            <option value="">Todas las funciones</option>
            {funciones?.map((f: any) => (
              <option key={f.funcion_codigo} value={f.funcion_codigo}>
                {f.funcion_nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Fuente de Financiamiento</label>
          <select 
            name="fuente" 
            value={localFiltros.fuente} 
            onChange={handleFilterChange}
            className={selectClassName}
          >
            <option value="">Todas las fuentes</option>
            {fuentes?.map((f: any) => (
              <option key={f.fuente_codigo} value={f.fuente_codigo}>
                {f.fuente_nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">Categoría de Gasto</label>
          <select 
            name="categoria_gasto" 
            value={localFiltros.categoria_gasto} 
            onChange={handleFilterChange}
            className={selectClassName}
          >
            <option value="">Todas las categorías</option>
            <option value="5">Gasto Corriente</option>
            <option value="6">Gasto de Capital</option>
          </select>
        </div>
      </div>

      <div className="bg-card border rounded-lg shadow-sm">
        {isError ? (
          <div className="p-8 text-center text-destructive">
            Ocurrió un error al cargar los datos. Por favor, intente nuevamente.
          </div>
        ) : isLoading ? (
          <div className="p-8 text-center text-muted-foreground">
            Cargando datos...
          </div>
        ) : (
          <DataTable
            columns={ejecucionDetalleColumnas}
            data={data?.items ?? []}
            pageCount={pageCount}
            pagination={pagination}
            onPaginationChange={setPagination}
          />
        )}
      </div>
    </div>
  );
}
