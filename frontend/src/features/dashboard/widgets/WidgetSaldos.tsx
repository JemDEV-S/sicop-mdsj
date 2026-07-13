import { Wallet } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import Semaforo from '@/components/Semaforo';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import { mapSemaforoApiToEstado } from '@/features/obras/api';
import type { SaldosResumen } from '../types';

interface WidgetSaldosProps {
  saldos: SaldosResumen;
}

export function WidgetSaldos({ saldos }: WidgetSaldosProps) {
  const semaforoEstado = mapSemaforoApiToEstado(saldos.semaforo ?? 'desconocido');
  const saldoFormateado = formatearMoneda(saldos.saldo_disponible);
  const porcentaje = formatPorcentaje(saldos.porcentaje_ejecucion);

  return (
    <SectionCard
      titulo="Saldo de la unidad"
      icono={Wallet}
      padding="md"
      className="h-full"
    >
      <div data-testid="widget-saldos">
        <p className="text-2xl font-bold text-foreground mb-1">{saldoFormateado}</p>
        <p className="text-sm text-muted-foreground mb-3">
          Ejecución: {porcentaje}
        </p>

        {semaforoEstado ? (
          <Semaforo
            estado={semaforoEstado}
            texto={
              semaforoEstado === 'ok'
                ? 'Normal'
                : semaforoEstado === 'alerta'
                  ? 'Atención'
                  : 'Crítico'
            }
          />
        ) : null}
      </div>
    </SectionCard>
  );
}

export default WidgetSaldos;
