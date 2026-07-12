import { type ColumnDef } from '@tanstack/react-table';
import { Badge } from '../../../components/ui/badge';
import { parseMonto, formatearMoneda } from '../../ejecucion/utils';
import type { ProveedorPublicoItem } from '../types';

export const columnasProveedoresPublico: ColumnDef<ProveedorPublicoItem>[] = [
  {
    accessorKey: 'ruc',
    header: 'RUC',
    cell: ({ row }) => (
      <div className="font-medium">{row.getValue('ruc') || 'S/N'}</div>
    ),
  },
  {
    accessorKey: 'nombre',
    header: 'Razón Social / Nombre',
    cell: ({ row }) => (
      <div className="max-w-[300px] truncate" title={row.getValue('nombre')}>
        {row.getValue('nombre') || 'Desconocido'}
      </div>
    ),
  },
  {
    accessorKey: 'giro',
    header: 'Giro / Rubro',
    cell: ({ row }) => {
      const giro = row.getValue<string | null>('giro');
      return (
        <div className="max-w-[200px] truncate text-muted-foreground" title={giro || ''}>
          {giro || '-'}
        </div>
      );
    },
  },
  {
    id: 'insignias',
    header: 'Condición',
    cell: ({ row }) => {
      const isMype = row.original.flag_mype === 'S' || row.original.flag_mype === '1' || row.original.flag_mype === 'Y';
      const isRnp = row.original.flag_rnp === 'S' || row.original.flag_rnp === '1' || row.original.flag_rnp === 'Y';
      
      return (
        <div className="flex gap-2">
          {isMype && <Badge variant="secondary" className="bg-blue-100 text-blue-800 hover:bg-blue-200">MYPE</Badge>}
          {isRnp && <Badge variant="secondary" className="bg-green-100 text-green-800 hover:bg-green-200">RNP</Badge>}
          {!isMype && !isRnp && <span className="text-muted-foreground text-sm">-</span>}
        </div>
      );
    },
  },
  {
    accessorKey: 'nro_ordenes',
    header: 'Órdenes',
    cell: ({ row }) => (
      <div className="text-right tabular-nums">
        {row.getValue('nro_ordenes')}
      </div>
    ),
  },
  {
    accessorKey: 'monto_acumulado',
    header: 'Monto Acumulado (S/)',
    cell: ({ row }) => {
      return (
        <div className="text-right font-medium tabular-nums">
          {formatearMoneda(parseMonto(row.getValue('monto_acumulado')))}
        </div>
      );
    },
  },
];
