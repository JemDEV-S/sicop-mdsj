import { useState } from 'react';
import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/auth';
import { formatFecha } from '@/lib/formatters';
import {
  useAnotacionesPedido,
  useCrearAnotacionPedido,
  useEliminarAnotacionPedido,
} from './api';
import type { Anotacion } from './types';

interface AnotacionesProps {
  nroPedido: number;
  tipoBien: string;
}

// AC-10.4: registrar y ver observaciones internas persistidas en
// sistema.anotaciones_internas. Solo el autor o admin pueden borrar.
export function Anotaciones({ nroPedido, tipoBien }: AnotacionesProps) {
  const [texto, setTexto] = useState('');
  const [abierto, setAbierto] = useState(false);
  const listaQ = useAnotacionesPedido({ nroPedido, tipoBien });
  const crearM = useCrearAnotacionPedido({ nroPedido, tipoBien });

  const usuarioId = useAuthStore((s) => s.user?.id) ?? null;
  const esAdmin = useAuthStore((s) => s.user?.rol) === 'admin';

  const enviar = async () => {
    const valor = texto.trim();
    if (!valor) return;
    try {
      await crearM.mutateAsync(valor);
      setTexto('');
      setAbierto(false);
    } catch {
      // El error se refleja en crearM.isError abajo; no rompemos el flujo.
    }
  };

  return (
    <SectionCard
      titulo="Observaciones internas"
      icono={MessageSquare}
      padding="md"
      accion={
        !abierto ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAbierto(true)}
            className="text-xs"
          >
            <Plus className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
            Nueva observación
          </Button>
        ) : null
      }
    >
      {abierto ? (
        <div className="mb-4 space-y-2">
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Escribe una observación interna para este pedido…"
            className="w-full min-h-[80px] rounded-md border border-border bg-background p-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            maxLength={2000}
            aria-label="Texto de la observación interna"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground tabular-nums">
              {texto.length}/2000
            </span>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setTexto('');
                  setAbierto(false);
                }}
                disabled={crearM.isPending}
              >
                Cancelar
              </Button>
              <Button
                size="sm"
                onClick={enviar}
                disabled={!texto.trim() || crearM.isPending}
              >
                {crearM.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
            </div>
          </div>
          {crearM.isError ? (
            <p className="text-xs text-destructive">
              No se pudo guardar. Reintenta en unos segundos.
            </p>
          ) : null}
        </div>
      ) : null}

      {listaQ.isLoading ? (
        <p className="text-sm text-muted-foreground">Cargando observaciones…</p>
      ) : listaQ.isError ? (
        <p className="text-sm text-destructive">
          No se pudieron cargar las observaciones.
        </p>
      ) : listaQ.data && listaQ.data.length > 0 ? (
        <ul className="space-y-3">
          {listaQ.data.map((a) => (
            <ItemAnotacion
              key={a.id}
              anotacion={a}
              usuarioActual={usuarioId}
              esAdmin={esAdmin}
              nroPedido={nroPedido}
              tipoBien={tipoBien}
            />
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          Aún no hay observaciones para este pedido.
        </p>
      )}
    </SectionCard>
  );
}

interface ItemAnotacionProps {
  anotacion: Anotacion;
  usuarioActual: string | null;
  esAdmin: boolean;
  nroPedido: number;
  tipoBien: string;
}

function ItemAnotacion({
  anotacion,
  usuarioActual,
  esAdmin,
  nroPedido,
  tipoBien,
}: ItemAnotacionProps) {
  const eliminarM = useEliminarAnotacionPedido({ nroPedido, tipoBien });
  const puedeBorrar = esAdmin || anotacion.usuario_id === usuarioActual;

  return (
    <li className="border-l-2 border-border pl-3 py-1">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <div className="flex items-baseline gap-2 flex-wrap min-w-0">
          <span className="text-sm font-medium text-foreground truncate">
            {anotacion.usuario_nombre ?? 'Usuario desconocido'}
          </span>
          <span className="text-xs text-muted-foreground tabular-nums">
            {formatFecha(anotacion.creado_en)}
          </span>
        </div>
        {puedeBorrar ? (
          <button
            type="button"
            onClick={() => eliminarM.mutate(anotacion.id)}
            disabled={eliminarM.isPending}
            className="text-xs text-muted-foreground hover:text-destructive inline-flex items-center gap-1 focus-visible:outline-none focus-visible:underline disabled:opacity-50"
            aria-label="Eliminar observación"
          >
            <Trash2 className="w-3 h-3" aria-hidden="true" />
            Eliminar
          </button>
        ) : null}
      </div>
      <p className="mt-1 text-sm text-foreground whitespace-pre-wrap">
        {anotacion.texto}
      </p>
    </li>
  );
}

export default Anotaciones;
