import type { ColumnDef } from '@tanstack/react-table';
import type { EjecucionDetalleItem } from '../types';
import Semaforo from '../../../components/Semaforo';
import { calcularSemaforo } from '../../../lib/semaforo';
import { parseMonto, formatearMoneda } from '../../../lib/formatters';

export const ejecucionDetalleColumnas: ColumnDef<EjecucionDetalleItem>[] = [
  {
    accessorKey: 'sec_func',
    header: 'Meta',
    cell: ({ row }) => (
      <div className="font-medium text-center">
        {row.original.sec_func.toString().padStart(4, '0')}
      </div>
    ),
    size: 80,
  },
  {
    accessorKey: 'meta_nombre',
    header: 'Descripción de la Meta',
    cell: ({ row }) => (
      <div className="flex flex-col gap-1 max-w-[400px]">
        <span className="font-semibold text-xs text-muted-foreground">
          {row.original.funcion_nombre}
        </span>
        <span className="text-sm line-clamp-3" title={row.original.meta_nombre}>
          {row.original.meta_nombre}
        </span>
        {row.original.producto_proyecto && (
          <span className="text-xs text-muted-foreground/80 font-mono">
            Prod/Proy: {row.original.producto_proyecto}
          </span>
        )}
      </div>
    ),
  },
  {
    accessorKey: 'pim',
    header: () => <div className="text-right">PIM</div>,
    cell: ({ row }) => (
      <div className="text-right font-medium">
        {formatearMoneda(parseMonto(row.original.pim))}
      </div>
    ),
  },
  {
    accessorKey: 'certificado',
    header: () => <div className="text-right">Certificado</div>,
    cell: ({ row }) => (
      <div className="text-right">
        {formatearMoneda(parseMonto(row.original.certificado))}
      </div>
    ),
  },
  {
    accessorKey: 'devengado',
    header: () => <div className="text-right">Devengado</div>,
    cell: ({ row }) => (
      <div className="text-right">
        {formatearMoneda(parseMonto(row.original.devengado))}
      </div>
    ),
  },
  {
    accessorKey: 'girado',
    header: () => <div className="text-right">Girado</div>,
    cell: ({ row }) => (
      <div className="text-right">
        {formatearMoneda(parseMonto(row.original.girado))}
      </div>
    ),
  },
  {
    accessorKey: 'porcentaje_ejecucion',
    header: () => <div className="text-center">% Ejec.</div>,
    cell: ({ row }) => {
      const val = row.original.porcentaje_ejecucion;
      if (val === null || val === undefined) {
        return <div className="text-center text-xs text-muted-foreground">Sin datos</div>;
      }
      const numVal = Number(val);
      const estado = calcularSemaforo(numVal, 80, 50, 'mayor');
      return (
        <div className="flex justify-center">
          <Semaforo estado={estado} texto={`${numVal.toFixed(1)}%`} />
        </div>
      );
    },
    size: 120,
  }
];
