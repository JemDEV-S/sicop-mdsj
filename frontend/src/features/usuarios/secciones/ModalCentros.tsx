/**
 * Modal de asignación de centros de costo a un usuario (HU-17 · T-54).
 *
 * Muestra los CC ya asignados (con opción de quitar) y un buscador del árbol
 * completo de la entidad para añadir (input + lista filtrable, para no navegar
 * un <select> de ~89 opciones). El flag "cabeza de jerarquía" marca que ese CC
 * es la raíz desde la que un decisor ve toda su rama (RN-04).
 */
import { useMemo, useState } from 'react';
import { Trash2, Plus, Search, Check } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { EmptyState } from '@/components/layout/EmptyState';
import { cn } from '@/lib/utils';
import {
  useAsignarCentro,
  useCentrosCostoDisponibles,
  useQuitarCentro,
  useUsuarioDetalle,
} from '../api';
import type { CentroCostoBreve, UsuarioItem } from '../types';

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  usuario: UsuarioItem;
}

export function ModalCentros({ abierto, onCerrar, usuario }: Props) {
  const detalleQ = useUsuarioDetalle(abierto ? usuario.id : null);
  const centrosQ = useCentrosCostoDisponibles(abierto);
  const asignar = useAsignarCentro();
  const quitar = useQuitarCentro();

  const [busqueda, setBusqueda] = useState('');
  const [ccElegido, setCcElegido] = useState<CentroCostoBreve | null>(null);
  const [esRaiz, setEsRaiz] = useState(false);

  const asignados = detalleQ.data?.centros ?? [];
  const codigosAsignados = useMemo(
    () => new Set(asignados.map((c) => c.codigo)),
    [asignados],
  );

  // Disponibles = todos menos los ya asignados. Filtrados por la búsqueda
  // (código o nombre, sin distinguir tildes/mayúsculas). Limitado a 50 para no
  // renderizar una lista gigante; si hay más, se pide afinar la búsqueda.
  const disponibles = useMemo(() => {
    const norm = (s: string) =>
      s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    const q = norm(busqueda.trim());
    return (centrosQ.data ?? [])
      .filter((c) => !codigosAsignados.has(c.codigo))
      .filter((c) => !q || norm(c.codigo).includes(q) || norm(c.nombre).includes(q));
  }, [centrosQ.data, codigosAsignados, busqueda]);

  const totalDisponibles = disponibles.length;
  const visibles = disponibles.slice(0, 50);

  async function onAgregar() {
    if (!ccElegido) return;
    await asignar.mutateAsync({
      id: usuario.id,
      centro_costo: ccElegido.codigo,
      es_raiz_jerarquia: esRaiz,
    });
    setCcElegido(null);
    setEsRaiz(false);
    setBusqueda('');
  }

  return (
    <Dialog open={abierto} onOpenChange={(o) => (!o ? onCerrar() : undefined)}>
      <DialogContent className="flex max-h-[85vh] flex-col overflow-hidden sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="truncate">Centros de costo · {usuario.nombre_completo}</DialogTitle>
          <DialogDescription>
            Define qué dependencias puede ver este usuario. Un decisor ve su
            centro y toda la rama debajo; un operativo solo los centros asignados.
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
          {/* Asignados */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Asignados ({asignados.length})
            </p>
            {detalleQ.isLoading ? (
              <p className="text-sm text-muted-foreground">Cargando…</p>
            ) : asignados.length === 0 ? (
              <EmptyState
                titulo="Sin centros asignados"
                descripcion="Este usuario aún no ve ninguna dependencia. Añade al menos una abajo."
              />
            ) : (
              <ul className="divide-y divide-border rounded-md border border-border">
                {asignados.map((c) => (
                  <li key={c.codigo} className="flex items-center justify-between gap-2 px-3 py-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-foreground">{c.codigo}</span>
                        {c.es_raiz_jerarquia ? (
                          <Badge variant="secondary" className="shrink-0">Cabeza de jerarquía</Badge>
                        ) : null}
                      </div>
                      <p className="truncate text-sm text-foreground" title={c.nombre}>
                        {c.nombre}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0"
                      onClick={() => quitar.mutate({ id: usuario.id, centro_costo: c.codigo })}
                      disabled={quitar.isPending}
                      aria-label={`Quitar ${c.codigo}`}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Añadir: buscador + lista filtrable */}
          <div className="rounded-md border border-dashed border-border p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Añadir centro
            </p>

            <div className="relative">
              <Search
                className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                value={busqueda}
                onChange={(e) => {
                  setBusqueda(e.target.value);
                  setCcElegido(null);
                }}
                placeholder="Buscar por código o nombre…"
                className="pl-8"
                disabled={centrosQ.isLoading}
              />
            </div>

            {/* Lista de resultados (scroll propio, no desborda el modal) */}
            <div className="mt-2 max-h-52 overflow-y-auto rounded-md border border-border">
              {centrosQ.isLoading ? (
                <p className="px-3 py-4 text-sm text-muted-foreground">Cargando dependencias…</p>
              ) : visibles.length === 0 ? (
                <p className="px-3 py-4 text-sm text-muted-foreground">
                  {busqueda ? 'Sin coincidencias.' : 'No hay dependencias por asignar.'}
                </p>
              ) : (
                <ul className="divide-y divide-border">
                  {visibles.map((c) => {
                    const seleccionado = ccElegido?.codigo === c.codigo;
                    return (
                      <li key={c.codigo}>
                        <button
                          type="button"
                          onClick={() => setCcElegido(seleccionado ? null : c)}
                          className={cn(
                            'flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-muted/60',
                            seleccionado && 'bg-primary/10',
                          )}
                          aria-pressed={seleccionado}
                        >
                          <Check
                            className={cn(
                              'h-4 w-4 shrink-0',
                              seleccionado ? 'text-primary' : 'text-transparent',
                            )}
                            aria-hidden="true"
                          />
                          <span className="w-24 shrink-0 font-mono text-xs font-semibold text-foreground">
                            {c.codigo}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-sm text-foreground" title={c.nombre}>
                            {c.nombre}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            {totalDisponibles > visibles.length ? (
              <p className="mt-1 text-[11px] text-muted-foreground">
                Mostrando {visibles.length} de {totalDisponibles}. Afina la búsqueda para ver más.
              </p>
            ) : null}

            {/* Fila de acción: elegido + flag + botón */}
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-1.5 text-xs text-foreground">
                <input
                  type="checkbox"
                  checked={esRaiz}
                  onChange={(e) => setEsRaiz(e.target.checked)}
                />
                Cabeza de jerarquía
              </label>
              <Button size="sm" onClick={onAgregar} disabled={!ccElegido || asignar.isPending}>
                <Plus className="mr-1 h-4 w-4" aria-hidden="true" />
                {ccElegido ? `Añadir ${ccElegido.codigo}` : 'Añadir'}
              </Button>
            </div>

            <p className="mt-2 text-[11px] text-muted-foreground">
              Marca "cabeza de jerarquía" si este centro es la raíz desde la que
              un decisor debe ver toda su rama de dependencias.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCerrar}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
