import { Landmark, TrendingUp, Wallet } from 'lucide-react';
import { KpiCard } from '@/components/KpiCard';
import Semaforo from '@/components/Semaforo';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import {
  semaforoDesdePorcentaje,
  mapSemaforo,
  etiquetaSemaforo,
} from '../lib';
import type { PresupuestoMeta as TPresupuestoMeta } from '../types';

interface KpisMetaProps {
  presupuesto: TPresupuestoMeta;
}

/**
 * Fila de KPIs del consolidado de meta. Protagonista: el DEVENGADO OFICIAL
 * (MEF) — el mismo número del portal público. El % y el semáforo salen de
 * `devengado_mef / pim_mef`, nunca de cert+compr.
 */
export function KpisMeta({ presupuesto: p }: KpisMetaProps) {
  const sem = semaforoDesdePorcentaje(p.porcentaje_devengado);
  const semEstado = mapSemaforo(sem);
  const tieneMef = p.devengado_mef != null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        label="PIM oficial (MEF)"
        valor={p.pim_mef != null ? formatearMoneda(p.pim_mef) : 'ND'}
        tono="neutro"
        icono={Landmark}
        ayuda={
          <span title="PIM del SIGA a nivel meta (puede diferir del MEF).">
            PIM SIGA: {formatearMoneda(p.pim)}
          </span>
        }
      />

      <KpiCard
        label="Devengado oficial (MEF)"
        valor={tieneMef ? formatearMoneda(p.devengado_mef) : 'ND'}
        tono="primario"
        icono={TrendingUp}
        ayuda={
          tieneMef
            ? `${formatPorcentaje(p.porcentaje_devengado)} del PIM oficial`
            : 'La meta no cruza con el snapshot MEF'
        }
        semaforo={
          semEstado ? (
            <Semaforo estado={semEstado} texto={etiquetaSemaforo(sem, p.porcentaje_devengado)} />
          ) : undefined
        }
      />

      <KpiCard
        label="Girado (MEF)"
        valor={p.girado_mef != null ? formatearMoneda(p.girado_mef) : 'ND'}
        tono="secundario"
        icono={Wallet}
        ayuda="Pagos efectivamente girados"
      />

      <KpiCard
        label="Saldo disponible (MEF)"
        valor={p.saldo_disponible_mef != null ? formatearMoneda(p.saldo_disponible_mef) : 'ND'}
        tono="neutro"
        icono={Wallet}
        ayuda={
          <span title="Saldo del SIGA a nivel meta.">
            Saldo SIGA: {formatearMoneda(p.saldo_disponible)}
          </span>
        }
      />
    </div>
  );
}

/**
 * Detalle presupuestal dual dentro del acordeón: la cadena de ejecución
 * (Certificado → Comprometido → Devengado → Girado) en dos columnas —
 * SIGA operativo (fases previas) vs. MEF oficial (número del ciudadano).
 *
 * SIGA no tiene devengado ni girado a este nivel: se marca "—" para no
 * inventar el dato ni presentar cert/compr como devengado.
 */
export function DetallePresupuesto({ presupuesto: p }: KpisMetaProps) {
  const filas: { fase: string; nota?: string; siga: number | null; mef: number | null }[] = [
    { fase: 'PIA', siga: p.pia, mef: null },
    { fase: 'PIM', siga: p.pim, mef: p.pim_mef },
    { fase: 'Certificado', nota: 'Crédito reservado', siga: p.certificado, mef: p.certificado_mef },
    { fase: 'Comprometido', nota: 'Obligación adquirida', siga: p.comprometido, mef: p.comprometido_mef },
    { fase: 'Devengado', nota: 'Bien/servicio recibido', siga: null, mef: p.devengado_mef },
    { fase: 'Girado', nota: 'Pago efectuado', siga: null, mef: p.girado_mef },
    { fase: 'Saldo disponible', siga: p.saldo_disponible, mef: p.saldo_disponible_mef },
  ];

  return (
    <div className="p-5">
      <p className="mb-4 text-xs text-muted-foreground">
        La cadena del gasto es secuencial: Certificación → Compromiso → Devengado → Girado.
        El <span className="font-medium text-foreground">devengado real</span> es el del MEF;
        certificación y compromiso son fases previas.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-3 py-2 text-left">Fase del gasto</th>
              <th className="bg-muted/40 px-3 py-2 text-right" title="Fases previas según el SIGA de la muni.">
                SIGA operativo
              </th>
              <th className="bg-primary/5 px-3 py-2 text-right" title="Snapshot oficial del portal MEF.">
                MEF oficial
              </th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.fase} className="border-t border-border">
                <td className="px-3 py-2.5">
                  <span className="font-medium text-foreground">{f.fase}</span>
                  {f.nota ? (
                    <span className="ml-2 text-xs text-muted-foreground">{f.nota}</span>
                  ) : null}
                </td>
                <td className="bg-muted/20 px-3 py-2.5 text-right tabular-nums text-muted-foreground">
                  {f.siga != null ? formatearMoneda(f.siga, true) : '—'}
                </td>
                <td className="bg-primary/[0.03] px-3 py-2.5 text-right font-medium tabular-nums text-foreground">
                  {f.mef != null ? formatearMoneda(f.mef, true) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
