// Detalle SIAF por fase de un expediente (Formato A · carga provisional).
// Reutilizable por el modal de expediente, el modal de la orden y la vista de
// Cruce SIAF↔SIGA: rompe la ceguera del pipeline mostrando el monto real por
// fase (Certificado/Devengado/Girado/Pagado), el proveedor, la caja de
// tesorería (girado/pagado/en tránsito) y los documentos sustento por fase.
//
// Es SOLO trazabilidad: nunca un total de tablero (RN §3). Toda la información
// se rotula como carga provisional con los meses cargados del Formato A.

import { formatearMoneda, formatFecha } from '@/lib/formatters';
import type { DetalleExpedienteSiaf, FaseExpedienteSiaf } from '@/features/pipeline/types';
import { avisoHistoriaIncompleta } from '@/features/pipeline/siaf-cobertura';
import { TileFase } from '@/features/panel/ui/primitivas';
import { BarrasFaseMonto } from './Fases';
import { ordenarFases } from './detalle-fases-siaf-lib';

// ─── Caja de tesorería del expediente (girado / pagado / en tránsito) ─────

export function CajaTesoreria({ detalle }: { detalle: DetalleExpedienteSiaf }) {
  const { fases, porCod } = ordenarFases(detalle);
  const devengado = porCod.get('D')?.monto_neto ?? null;
  const girado = porCod.get('G')?.monto_neto ?? null;
  const pagado = porCod.get('P')?.monto_neto ?? null;
  const enTransito = devengado != null && pagado != null ? devengado - pagado : null;
  const nDocs = fases.reduce((n, f) => n + f.n_documentos, 0);
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <TileFase label="Girado" valor={girado == null ? '—' : formatearMoneda(girado)} />
      <TileFase label="Pagado" valor={pagado == null ? '—' : formatearMoneda(pagado)} />
      <TileFase
        label="En tránsito"
        valor={enTransito == null ? '—' : formatearMoneda(enTransito)}
        ayuda="devengado − pagado"
        resaltar={enTransito != null && enTransito > 0}
      />
      <TileFase label="Documentos" valor={nDocs} />
    </div>
  );
}

// ─── Barras de monto por fase (comparación visual entre fases) ────────────

export function BarrasFasesSiaf({ detalle }: { detalle: DetalleExpedienteSiaf }) {
  const { fases, porCod, presentes } = ordenarFases(detalle);
  // Ancho proporcional al mayor neto de las fases presentes (no contra el PIM).
  const maxNeto = Math.max(1, ...fases.map((f) => Math.abs(f.monto_neto)));
  const barras = presentes.map((f) => {
    const fase = porCod.get(f.cod)!;
    return {
      label: f.label,
      valor: formatearMoneda(fase.monto_neto),
      ancho: (Math.abs(fase.monto_neto) / maxNeto) * 100,
      barraClass: f.barraClass,
    };
  });
  const aviso = avisoHistoriaIncompleta(fases);
  return (
    <div className="flex flex-col gap-2">
      <BarrasFaseMonto filas={barras} />
      {aviso ? (
        <p className="rounded-md border border-accent/40 bg-accent/10 px-2.5 py-1.5 text-[10.5px] leading-relaxed text-accent-foreground">
          {aviso}
        </p>
      ) : null}
    </div>
  );
}

// ─── Documentos sustento por fase ─────────────────────────────────────────

export function DocumentosPorFase({ detalle }: { detalle: DetalleExpedienteSiaf }) {
  const { porCod, presentes } = ordenarFases(detalle);
  return (
    <div className="grid grid-cols-1 gap-x-6 gap-y-3 lg:grid-cols-2">
      {presentes.map((f) => (
        <FaseDocumentos key={f.cod} label={f.label} fase={porCod.get(f.cod)!} />
      ))}
    </div>
  );
}

// Lista de documentos de una fase (cod/num + fecha + monto). El funcionario usa
// estos números para verificar el gasto en el SIAF.
function FaseDocumentos({ label, fase }: { label: string; fase: FaseExpedienteSiaf }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11.5px] font-semibold text-foreground">{label}</span>
        <span className="font-mono text-[11.5px] tabular-nums text-foreground">
          {formatearMoneda(fase.monto_neto)}
        </span>
      </div>
      <div className="flex flex-col gap-0.5 pl-2">
        {fase.documentos.map((d, i) => (
          <div
            key={`${d.cod_doc ?? ''}-${d.num_doc ?? ''}-${i}`}
            className="flex items-center gap-2 text-[11px] text-muted-foreground"
          >
            <span className="font-mono text-foreground">
              {d.cod_doc ? `${d.cod_doc} ` : ''}
              {d.num_doc ?? '—'}
            </span>
            <span>· {formatFecha(d.fecha_doc)}</span>
            <span className="ml-auto font-mono tabular-nums">{formatearMoneda(d.monto_soles)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
