import { useState, useMemo } from 'react';
import type { ColumnDef, PaginationState } from '@tanstack/react-table';
import { DataTable } from '../../components/tabla/DataTable';
import { useObras, useFunciones, useTipologias } from '../../features/obras/hooks';
import type { ObraCardResponse } from '../../features/obras/types';
import { mapSemaforoApiToEstado } from '../../features/obras/api';
import Semaforo from '../../components/Semaforo';
import { formatSoles } from '../../lib/formatters';

export default function ObrasListado() {
  const [q, setQ] = useState('');
  const [funcion, setFuncion] = useState('');
  const [tipologia, setTipologia] = useState('');
  
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 25,
  });

  const { data, isLoading, isError } = useObras({
    page: pagination.pageIndex + 1,
    size: pagination.pageSize,
    q: q || undefined,
    funcion: funcion || undefined,
    tipologia: tipologia || undefined,
  });

  const { data: funciones } = useFunciones();
  const { data: tipologias } = useTipologias();

  const columns = useMemo<ColumnDef<ObraCardResponse>[]>(() => [
    {
      accessorKey: 'codigo_unico',
      header: 'CUI',
      cell: ({ row }) => (
        <span className="font-mono text-sm text-gray-600">
          {row.getValue('codigo_unico')}
        </span>
      ),
    },
    {
      accessorKey: 'nombre_inversion',
      header: 'Proyecto',
      cell: ({ row }) => {
        const nombre = row.getValue('nombre_inversion') as string;
        return (
          <div className="max-w-md truncate" title={nombre || ''}>
            {nombre || 'Sin nombre'}
          </div>
        );
      },
    },
    {
      accessorKey: 'pim_anio_actual',
      header: 'Presupuesto (PIM)',
      cell: ({ row }) => (
        <span className="font-medium text-gray-900">
          {formatSoles(row.getValue('pim_anio_actual') as number || 0)}
        </span>
      ),
    },
    {
      id: 'semaforo',
      header: 'Avance',
      cell: ({ row }) => {
        const rawSemaforo = row.original.semaforo;
        const estado = mapSemaforoApiToEstado(rawSemaforo);
        
        if (!estado) {
          return <span className="text-gray-500 text-sm">Sin datos de avance</span>;
        }

        const fisico = row.original.avance_fisico;
        const texto = fisico !== null && fisico !== undefined 
          ? `${fisico.toFixed(1)}%` 
          : 'Desconocido';

        return <Semaforo estado={estado} texto={texto} />;
      },
    },
  ], []);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pagination.pageSize)) : 1;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Directorio de Obras Públicas</h1>
          <p className="text-gray-600 mt-2">
            Consulta el estado, avance físico y financiero de los proyectos de inversión en el distrito.
          </p>
        </header>

        {/* Filtros */}
        <section className="bg-white p-4 border border-gray-200 shadow-sm flex flex-col md:flex-row gap-4 items-end rounded-sm">
          <div className="flex-1 w-full">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Buscar
            </label>
            <input
              type="text"
              placeholder="Nombre o CUI..."
              className="w-full border border-gray-300 rounded-none px-3 py-2 text-gray-900 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPagination(prev => ({ ...prev, pageIndex: 0 }));
              }}
            />
          </div>

          <div className="w-full md:w-64">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Función
            </label>
            <select
              className="w-full border border-gray-300 rounded-none px-3 py-2 text-gray-900 bg-white focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
              value={funcion}
              onChange={(e) => {
                setFuncion(e.target.value);
                setPagination(prev => ({ ...prev, pageIndex: 0 }));
              }}
            >
              <option value="">Todas</option>
              {funciones?.map(f => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>

          <div className="w-full md:w-64">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipología
            </label>
            <select
              className="w-full border border-gray-300 rounded-none px-3 py-2 text-gray-900 bg-white focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
              value={tipologia}
              onChange={(e) => {
                setTipologia(e.target.value);
                setPagination(prev => ({ ...prev, pageIndex: 0 }));
              }}
            >
              <option value="">Todas</option>
              {tipologias?.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </section>

        {/* Tabla */}
        <section>
          {isError ? (
            <div className="p-4 bg-red-50 text-red-900 border border-red-200">
              Ocurrió un error al cargar las obras. Por favor intente más tarde.
            </div>
          ) : (
            <div className="opacity-100 transition-opacity" style={{ opacity: isLoading ? 0.6 : 1 }}>
              <DataTable 
                columns={columns} 
                data={data?.items || []} 
                pageCount={totalPages}
                pagination={pagination}
                onPaginationChange={setPagination}
              />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
