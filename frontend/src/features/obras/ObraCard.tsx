import { Link } from 'react-router-dom';
import { ArrowRight, MapPin } from 'lucide-react';
import { mapSemaforoApiToEstado } from './api';
import type { ObraCardResponse } from './types';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';

interface ObraCardProps {
  obra: ObraCardResponse;
}

const semaforoAcento: Record<'ok' | 'alerta' | 'critico', string> = {
  ok: 'bg-[var(--semaforo-ok)]',
  alerta: 'bg-[var(--semaforo-alerta)]',
  critico: 'bg-[var(--semaforo-critico)]',
};

const semaforoTexto: Record<'ok' | 'alerta' | 'critico', string> = {
  ok: 'text-[var(--semaforo-ok)]',
  alerta: 'text-[var(--semaforo-alerta)]',
  critico: 'text-[var(--semaforo-critico)]',
};

const semaforoLeyenda: Record<'ok' | 'alerta' | 'critico', string> = {
  ok: 'En avance',
  alerta: 'Con demoras',
  critico: 'Crítica',
};

export function ObraCard({ obra }: ObraCardProps) {
  const estado = mapSemaforoApiToEstado(obra.semaforo);
  const avance = obra.avance_fisico;
  const avancePct = avance !== null && avance !== undefined ? Math.max(0, Math.min(100, avance)) : null;
  const hayCoords = obra.latitud != null && obra.longitud != null && !(obra.latitud === 0 && obra.longitud === 0);

  return (
    <Link
      to={`/obras/${obra.codigo_unico}`}
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-xl bg-card border border-border',
        'transition-all duration-200',
        'hover:-translate-y-0.5 hover:shadow-sm hover:border-border/80',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      )}
      aria-label={`Ver ficha de la obra ${obra.nombre_inversion ?? obra.codigo_unico}`}
    >
      {/* Cinta superior con estado (semáforo) */}
      <div
        className={cn(
          'h-1 w-full',
          estado ? semaforoAcento[estado] : 'bg-muted',
        )}
        aria-hidden="true"
      />

      <div className="p-5 flex flex-col flex-1">
        {/* Fila superior: CUI + ubicación */}
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="font-mono text-muted-foreground">
            CUI {obra.codigo_unico}
          </span>
          {hayCoords ? (
            <span
              className="inline-flex items-center gap-1 text-muted-foreground"
              title="Con ubicación geográfica registrada"
            >
              <MapPin className="w-3 h-3" aria-hidden="true" />
              Ubicada
            </span>
          ) : null}
        </div>

        {/* Título */}
        <h3 className="mt-3 text-base font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors leading-snug">
          {obra.nombre_inversion ?? 'Sin nombre registrado'}
        </h3>

        {/* Función como etiqueta */}
        {obra.funcion ? (
          <p
            className="mt-2 text-xs text-muted-foreground line-clamp-1"
            title={obra.funcion}
          >
            {obra.funcion}
          </p>
        ) : null}

        {/* Bloque de datos */}
        <div className="mt-4 pt-4 border-t border-border space-y-4 flex-1">
          {/* Avance físico como barra */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Avance físico
              </span>
              <span
                className={cn(
                  'text-sm font-bold tabular-nums',
                  estado ? semaforoTexto[estado] : 'text-muted-foreground',
                )}
              >
                {avancePct !== null ? `${avancePct.toFixed(1)}%` : 'Sin dato'}
              </span>
            </div>
            <div
              className="relative h-1.5 w-full rounded-full bg-muted overflow-hidden"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={avancePct ?? 0}
              aria-label="Avance físico de la obra"
            >
              <div
                className={cn(
                  'absolute inset-y-0 left-0 transition-all',
                  estado ? semaforoAcento[estado] : 'bg-muted-foreground/30',
                )}
                style={{ width: `${avancePct ?? 0}%` }}
                aria-hidden="true"
              />
            </div>
            {estado ? (
              <p className="mt-1 text-[10px] text-muted-foreground">{semaforoLeyenda[estado]}</p>
            ) : null}
          </div>

          {/* Presupuesto */}
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Presupuesto (PIM)
            </p>
            <p className="mt-1 text-lg font-bold text-foreground tabular-nums leading-none">
              {obra.pim_anio_actual !== null && obra.pim_anio_actual !== undefined
                ? formatearMoneda(obra.pim_anio_actual)
                : '—'}
            </p>
          </div>
        </div>

        {/* CTA */}
        <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-primary group-hover:gap-2.5 transition-all">
          Ver ficha completa
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}

export default ObraCard;
