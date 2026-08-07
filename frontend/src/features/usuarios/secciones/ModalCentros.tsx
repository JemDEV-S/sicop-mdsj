/**
 * Modal de asignación de centros de costo a un usuario (HU-17 · T-54).
 *
 * Muestra los CC ya asignados (con opción de quitar) y un selector del árbol
 * completo de la entidad para añadir. El flag "cabeza de jerarquía" marca que
 * ese CC es la raíz desde la que un decisor ve toda su rama (RN-04).
 */
import { useState } from 'react';
import { Trash2, Plus } from 'lucide-react';
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
import { EmptyState } from '@/components/layout/EmptyState';
import {
  useAsignarCentro,
  useCentrosCostoDisponibles,
  useQuitarCentro,
  useUsuarioDetalle,
} from '../api';
import type { UsuarioItem } from '../types';

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  usuario: UsuarioItem;
}

const CAMPO = 'h-9 flex-1 rounded-md border border-border bg-background px-2 text-sm';

export function ModalCentros({ abierto, onCerrar, usuario }: Props) {
  const detalleQ = useUsuarioDetalle(abierto ? usuario.id : null);
  const centrosQ = useCentrosCostoDisponibles(abierto);
  const asignar = useAsignarCentro();
  const quitar = useQuitarCentro();

  const [ccElegido, setCcElegido] = useState('');
  const [esRaiz, setEsRaiz] = useState(false);

  const asignados = detalleQ.data?.centros ?? [];
  const codigosAsignados = new Set(asignados.map((c) => c.codigo));
  const disponibles = (centrosQ.data ?? []).filter((c) => !codigosAsignados.has(c.codigo));

  async function onAgregar() {
    if (!ccElegido) return;
    await asignar.mutateAsync({
      id: usuario.id,
      centro_costo: ccElegido,
      es_raiz_jerarquia: esRaiz,
    });
    setCcElegido('');
    setEsRaiz(false);
  }

  return (
    <Dialog open={abierto} onOpenChange={(o) => (!o ? onCerrar() : undefined)}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Centros de costo · {usuario.nombre_completo}</DialogTitle>
          <DialogDescription>
            Define qué dependencias puede ver este usuario. Un decisor ve su
            centro y toda la rama debajo; un operativo solo los centros asignados.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
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
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-foreground">{c.codigo}</span>
                        {c.es_raiz_jerarquia ? (
                          <Badge variant="secondary">Cabeza de jerarquía</Badge>
                        ) : null}
                      </div>
                      <p className="truncate text-sm text-foreground" title={c.nombre}>
                        {c.nombre}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
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

          {/* Añadir */}
          <div className="rounded-md border border-dashed border-border p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Añadir centro
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <select
                className={CAMPO}
                value={ccElegido}
                onChange={(e) => setCcElegido(e.target.value)}
                disabled={centrosQ.isLoading}
              >
                <option value="">Selecciona una dependencia…</option>
                {disponibles.map((c) => (
                  <option key={c.codigo} value={c.codigo}>
                    {c.codigo} · {c.nombre}
                  </option>
                ))}
              </select>
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
                Añadir
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
