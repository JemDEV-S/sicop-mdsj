// Bandeja de acción del Panel: las colas de trabajo del día, con filtros por
// grupo. Reúne tres fuentes reales:
//   - pedidos estancados (rojo)      → /interno/alertas/pedidos-estancados
//   - metas rezagadas (rojo)         → /interno/saldos/metas-rezagadas
//   - contratos por vencer (ámbar)   → /interno/alertas/contratos-por-vencer
// Cada ítem lleva su acción: abrir el pedido o analizar la meta.

import { useMemo, useState } from 'react';
import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type {
  ContratoPorVencer,
  MetaRezagada,
  PedidoCard,
} from '@/features/dashboard/types';
import { EstadoChip, PanelSection, bordeIzquierdo, type Tono } from '../ui/primitivas';

export interface AccionItem {
  clave: string;
  grupo: 'estancados' | 'metas' | 'contratos';
  tono: Extract<Tono, 'critico' | 'alerta'>;
  tipo: string;
  titulo: string;
  evidencia: string;
  ref: string;
  cta: string;
  onAccion: () => void;
}

const GRUPOS: { id: 'todas' | AccionItem['grupo']; label: string }[] = [
  { id: 'todas', label: 'Todas' },
  { id: 'estancados', label: 'Estancados' },
  { id: 'metas', label: 'Metas' },
  { id: 'contratos', label: 'Contratos' },
];

export function BandejaAccion({
  estancados,
  metasRezagadas,
  contratos,
  onAbrirPedido,
  onAnalizarMeta,
  onVerContrato,
}: {
  estancados: PedidoCard[];
  metasRezagadas: MetaRezagada[];
  contratos: ContratoPorVencer[];
  onAbrirPedido: (p: PedidoCard) => void;
  onAnalizarMeta: (secFunc: number) => void;
  onVerContrato: (ruc: string | null) => void;
}) {
  const [grupo, setGrupo] = useState<'todas' | AccionItem['grupo']>('todas');

  const items = useMemo<AccionItem[]>(() => {
    const out: AccionItem[] = [];

    [...estancados]
      .sort((a, b) => (b.dias_en_etapa ?? 0) - (a.dias_en_etapa ?? 0))
      .forEach((p) => {
        out.push({
          clave: `est-${p.nro_pedido}-${p.tipo_bien}`,
          grupo: 'estancados',
          tono: 'critico',
          tipo: 'Estancado',
          titulo: `Pedido ${p.nro_pedido} · ${p.dias_en_etapa ?? '?'} días en ${p.etapa_label}`,
          evidencia:
            p.alerta?.evidencia ?? 'Sin avance sobre el plazo esperado para su macrofase.',
          ref: `${p.macrofase_label} · ${formatearMoneda(p.monto_total, true)} SIGA`,
          cta: 'Abrir',
          onAccion: () => onAbrirPedido(p),
        });
      });

    [...metasRezagadas]
      .sort((a, b) => b.pim - a.pim)
      .forEach((m) => {
        out.push({
          clave: `meta-${m.sec_func}`,
          grupo: 'metas',
          tono: 'critico',
          tipo: 'Meta rezagada',
          titulo: `Meta ${m.act_proy ?? m.sec_func} · ${formatearNumero(m.porcentaje_devengado, 1)}% devengado`,
          evidencia: `PIM de ${formatearMoneda(m.pim, true)} con avance por debajo de lo esperado; saldo por ejecutar ${formatearMoneda(m.pim - m.devengado, true)}.`,
          ref: m.nombre_meta ?? `Meta ${m.sec_func}`,
          cta: 'Analizar',
          onAccion: () => onAnalizarMeta(m.sec_func),
        });
      });

    [...contratos]
      .sort((a, b) => a.dias_restantes - b.dias_restantes)
      .forEach((c) => {
        out.push({
          clave: `con-${c.sec_contrato}-${c.nro_contrato}`,
          grupo: 'contratos',
          tono: 'alerta',
          tipo: 'Contrato por vencer',
          titulo: `${c.tipo_contrato} ${c.nro_contrato} · vence en ${c.dias_restantes} día${c.dias_restantes === 1 ? '' : 's'}`,
          evidencia:
            c.objeto ?? 'Contrato próximo a vencer sin renovación registrada en el pipeline.',
          ref: `${c.proveedor_nombre ?? 'Proveedor'} · ${formatearMoneda(c.valor_soles, true)}`,
          cta: 'Ver',
          onAccion: () => onVerContrato(c.proveedor_ruc),
        });
      });

    return out;
  }, [estancados, metasRezagadas, contratos, onAbrirPedido, onAnalizarMeta, onVerContrato]);

  const visibles = grupo === 'todas' ? items : items.filter((i) => i.grupo === grupo);
  const conteo = (id: (typeof GRUPOS)[number]['id']) =>
    id === 'todas' ? items.length : items.filter((i) => i.grupo === id).length;

  return (
    <PanelSection
      titulo="Bandeja de acción"
      aside={
        <div className="flex flex-wrap gap-1.5">
          {GRUPOS.map((g) => {
            const activo = grupo === g.id;
            return (
              <button
                key={g.id}
                type="button"
                onClick={() => setGrupo(g.id)}
                aria-pressed={activo}
                className={cn(
                  'rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  activo
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-card text-muted-foreground hover:bg-muted',
                )}
              >
                {g.label} {conteo(g.id)}
              </button>
            );
          })}
        </div>
      }
      bodyClassName="max-h-[360px] overflow-y-auto"
    >
      {visibles.length === 0 ? (
        <p className="rounded border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
          Sin pendientes en este grupo para el ámbito visible.
        </p>
      ) : (
        visibles.map((a) => (
          <div
            key={a.clave}
            className={cn(
              'flex flex-wrap items-start gap-2.5 rounded-md border bg-card px-3 py-2.5',
              bordeIzquierdo(a.tono),
            )}
          >
            <div className="flex min-w-[200px] flex-1 flex-col gap-1">
              <div className="flex flex-wrap items-center gap-2">
                <EstadoChip tono={a.tono} tamano="xs" punto={false}>
                  {a.tipo}
                </EstadoChip>
                <span className="text-[12.5px] font-semibold text-foreground">{a.titulo}</span>
              </div>
              <span className="text-[11.5px] leading-snug text-muted-foreground">{a.evidencia}</span>
              <span className="font-mono text-[10.5px] text-muted-foreground/80">{a.ref}</span>
            </div>
            <button
              type="button"
              onClick={a.onAccion}
              className="shrink-0 rounded-md border border-primary bg-card px-2.5 py-1 text-[11.5px] font-medium text-primary transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {a.cta}
            </button>
          </div>
        ))
      )}
    </PanelSection>
  );
}

export default BandejaAccion;
