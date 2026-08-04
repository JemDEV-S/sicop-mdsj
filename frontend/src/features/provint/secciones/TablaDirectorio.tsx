import { Link } from 'react-router-dom';
import { ArrowRight, Mail, Phone, Building2, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatearMoneda } from '@/lib/formatters';
import { EmptyState } from '@/components/layout/EmptyState';
import { Button } from '@/components/ui/button';
import { esPersonaJuridica, esFlagVerdad } from '../lib';
import type { ProveedorInterno } from '../types';

interface TablaDirectorioProps {
  items: ProveedorInterno[];
  total: number;
  page: number;
  size: number;
  onPageChange: (page: number) => void;
  hayBusqueda: boolean;
  isFetching?: boolean;
}

export function TablaDirectorio({
  items,
  total,
  page,
  size,
  onPageChange,
  hayBusqueda,
  isFetching,
}: TablaDirectorioProps) {
  const totalPaginas = Math.max(1, Math.ceil(total / size));
  const desde = total === 0 ? 0 : (page - 1) * size + 1;
  const hasta = Math.min(page * size, total);

  if (total === 0) {
    return (
      <EmptyState
        titulo={hayBusqueda ? 'Sin proveedores para esa búsqueda' : 'Sin proveedores'}
        descripcion={
          hayBusqueda
            ? 'No hay proveedores que coincidan con el texto ingresado. Prueba con otro nombre o RUC.'
            : 'No hay proveedores registrados para el año seleccionado.'
        }
      />
    );
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3 text-sm text-muted-foreground">
        <span>
          Mostrando <span className="font-semibold tabular-nums text-foreground">{desde}</span>–
          <span className="font-semibold tabular-nums text-foreground">{hasta}</span> de{' '}
          <span className="font-semibold tabular-nums text-foreground">
            {total.toLocaleString('es-PE')}
          </span>{' '}
          proveedores
        </span>
        {isFetching ? <span className="text-xs">Actualizando…</span> : null}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2.5 text-left">Proveedor</th>
              <th className="px-4 py-2.5 text-left">Contacto</th>
              <th className="px-4 py-2.5 text-right">Ejecutado (órdenes)</th>
              <th className="px-4 py-2.5 text-right">Órdenes</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {items.map((p, i) => {
              const juridica = esPersonaJuridica(p.tipo_persona, p.ruc);
              const Icono = juridica ? Building2 : User;
              return (
                <tr
                  key={p.ruc ?? i}
                  className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-start gap-2">
                      <Icono
                        className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                        aria-hidden="true"
                      />
                      <div className="min-w-0">
                        <p className="font-medium text-foreground">{p.nombre ?? 'Sin nombre'}</p>
                        <p className="font-mono text-[11px] text-muted-foreground">
                          RUC {p.ruc ?? '—'}
                        </p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          {esFlagVerdad(p.flag_mype) ? <Badge>MYPE</Badge> : null}
                          {p.flag_rnp === 'S' ? <Badge>RNP</Badge> : null}
                          {p.flag_consorcio === 'S' ? <Badge>Consorcio</Badge> : null}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1 text-xs text-muted-foreground">
                      {p.email ? (
                        <span className="inline-flex items-center gap-1.5">
                          <Mail className="h-3.5 w-3.5" aria-hidden="true" />
                          <span className="truncate" title={p.email}>{p.email}</span>
                        </span>
                      ) : null}
                      {p.telefonos ? (
                        <span className="inline-flex items-center gap-1.5">
                          <Phone className="h-3.5 w-3.5" aria-hidden="true" />
                          {p.telefonos}
                        </span>
                      ) : null}
                      {!p.email && !p.telefonos ? <span>Sin contacto</span> : null}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-medium tabular-nums text-foreground">
                    {p.monto_acumulado != null ? formatearMoneda(p.monto_acumulado, true) : '—'}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                    {p.nro_ordenes}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {p.ruc ? (
                      <Link
                        to={`/interno/proveedores/${p.ruc}`}
                        className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        Ver perfil <ArrowRight className="h-3 w-3" aria-hidden="true" />
                      </Link>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <span className="text-sm text-muted-foreground">
          Página {page} de {totalPaginas}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPaginas}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  );
}

export default TablaDirectorio;
