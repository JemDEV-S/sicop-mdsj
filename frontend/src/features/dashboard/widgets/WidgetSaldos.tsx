import { Link } from 'react-router-dom';
import { ArrowRight, Wallet } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import Semaforo from '@/components/Semaforo';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import type { EjecucionMef, MetaCritica, SaldosResumen } from '../types';

interface WidgetSaldosProps {
  resumen: SaldosResumen;
}

// El backend de saldos devuelve 'verde' | 'amarillo' | 'rojo' | 'desconocido'
// (ver backend/app/services/semaforo_service.py), no el vocabulario 'ok/alerta/critico'
// que usa el módulo de obras.
function mapSemaforoSaldos(valor: string): 'ok' | 'alerta' | 'critico' | null {
  if (valor === 'verde') return 'ok';
  if (valor === 'amarillo') return 'alerta';
  if (valor === 'rojo') return 'critico';
  return null;
}

export function WidgetSaldos({ resumen }: WidgetSaldosProps) {
  const semaforoEstado = mapSemaforoSaldos(resumen.semaforo);
  const sinDatosSiga = resumen.pim <= 0;
  const mef = resumen.mef;

  return (
    <SectionCard
      titulo="Saldo de la unidad"
      icono={Wallet}
      padding="md"
      className="h-full flex flex-col"
      accion={
        <Link
          to="/interno/saldos"
          className="text-xs text-primary hover:underline inline-flex items-center gap-1"
        >
          Ver saldos <ArrowRight className="w-3 h-3" aria-hidden="true" />
        </Link>
      }
    >
      <div data-testid="widget-saldos" className="flex flex-col gap-4">
        {mef ? <BloqueMef mef={mef} /> : <BloqueSaldoDisponible pim={resumen.pim} saldo={resumen.saldo_disponible} />}

        {!sinDatosSiga ? (
          <BloqueSiga resumen={resumen} />
        ) : (
          <p className="text-sm text-muted-foreground">
            No hay presupuesto asignado a esta unidad.
          </p>
        )}

        {semaforoEstado ? (
          <Semaforo estado={semaforoEstado} texto={etiquetaSemaforo(semaforoEstado)} />
        ) : null}

        {resumen.top_metas_criticas.length > 0 ? (
          <TopMetasCriticas metas={resumen.top_metas_criticas} />
        ) : null}
      </div>
    </SectionCard>
  );
}

// Bloque principal cuando el usuario ve el pliego completo: número oficial
// que cuadra con el portal MEF público.
function BloqueMef({ mef }: { mef: EjecucionMef }) {
  return (
    <div>
      <p
        className="text-xs font-medium text-muted-foreground uppercase tracking-wide"
        title="Fuente: portal MEF (Consulta amigable). Es el mismo número que ve el ciudadano."
      >
        Devengado oficial (MEF)
      </p>
      <p className="text-2xl font-bold text-foreground leading-tight">
        {formatearMoneda(mef.devengado)}
      </p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-2">
        <dt className="text-muted-foreground">PIM</dt>
        <dd className="text-right font-medium text-foreground">
          {formatearMoneda(mef.pim)}
        </dd>
        <dt className="text-muted-foreground">% Devengado</dt>
        <dd className="text-right font-semibold text-foreground">
          {formatPorcentaje(mef.porcentaje_devengado)}
        </dd>
        <dt className="text-muted-foreground">Saldo disponible</dt>
        <dd className="text-right font-medium text-foreground">
          {formatearMoneda(mef.saldo_disponible)}
        </dd>
      </dl>
    </div>
  );
}

// Fallback cuando el usuario está restringido a un subárbol de CC y no tiene
// visión del pliego completo (por privacidad no exponemos el MEF entero).
function BloqueSaldoDisponible({ pim, saldo }: { pim: number; saldo: number }) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Saldo disponible
      </p>
      <p className="text-2xl font-bold text-foreground leading-tight">
        {formatearMoneda(saldo)}
      </p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs mt-2">
        <dt className="text-muted-foreground">PIM asignado</dt>
        <dd className="text-right font-medium text-foreground">
          {formatearMoneda(pim)}
        </dd>
      </dl>
    </div>
  );
}

// Bloque interno: lo que la unidad tiene asignado en el SIGA a nivel meta.
function BloqueSiga({ resumen }: { resumen: SaldosResumen }) {
  return (
    <div className="pt-3 border-t border-border">
      <p
        className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2"
        title="Datos del SIGA de la muni a nivel meta. Puede diferir del MEF porque no todo el techo del pliego está desagregado a metas ejecutables."
      >
        Ejecución interna (SIGA)
      </p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <dt className="text-muted-foreground">PIM asignado</dt>
        <dd className="text-right font-medium text-foreground">
          {formatearMoneda(resumen.pim)}
        </dd>
        <dt
          className="text-muted-foreground"
          title="Certificación: crédito presupuestal reservado. Fase previa al compromiso."
        >
          Certificado
        </dt>
        <dd className="text-right font-medium text-foreground">
          {formatearMoneda(resumen.certificado)}
        </dd>
        <dt
          className="text-muted-foreground"
          title="Compromiso: obligación adquirida. Fase previa al devengado (el devengado real es el del MEF, arriba)."
        >
          Comprometido
        </dt>
        <dd className="text-right font-medium text-foreground">
          {formatearMoneda(resumen.comprometido)}
        </dd>
        <dt className="text-muted-foreground">Metas activas</dt>
        <dd className="text-right font-medium text-foreground">
          {resumen.metas_total}
          {resumen.metas_criticas > 0 ? (
            <span className="text-destructive font-semibold ml-1">
              · {resumen.metas_criticas} críticas
            </span>
          ) : null}
        </dd>
      </dl>
    </div>
  );
}

function etiquetaSemaforo(estado: 'ok' | 'alerta' | 'critico'): string {
  if (estado === 'ok') return 'Ejecución normal';
  if (estado === 'alerta') return 'Ejecución en atención';
  return 'Ejecución crítica';
}

function TopMetasCriticas({ metas }: { metas: MetaCritica[] }) {
  return (
    <div className="pt-3 border-t border-border">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
        Top metas críticas
      </p>
      <ul className="space-y-1.5">
        {metas.map((m) => (
          <li key={m.sec_func} className="flex items-center justify-between gap-2 text-xs">
            <span className="text-foreground truncate" title={m.nombre_meta ?? ''}>
              <span className="font-mono text-muted-foreground mr-1">
                {String(m.sec_func).padStart(4, '0')}
              </span>
              {m.nombre_meta ?? 'Sin nombre'}
            </span>
            <span className="text-destructive font-semibold shrink-0">
              {formatPorcentaje(m.porcentaje_devengado)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default WidgetSaldos;
