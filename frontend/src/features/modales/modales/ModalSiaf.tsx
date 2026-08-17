// Modal · Expediente SIAF. Datos reales de useDetallePedido → Expediente.
// Estructura de la plantilla v2: cabecera con devengado a la derecha, "Cadena
// programática" + "Fases y montos" (barras), y órdenes/trámite ligados.

import { formatearMoneda, formatearNumero, formatFecha } from '@/lib/formatters';
import { useDetallePedido } from '@/features/pipeline/api';
import { useModales, type EntradaModal } from '../ModalesContext';
import { CargandoModal, ErrorModal } from '../EstadoModal';
import { FilaDato, ModalBloque, ModalHead } from '../ui';
import { BarrasFaseMonto } from '../componentes/Fases';
import { ListaLigados, type Ligado } from '../componentes/FilaLigado';
import { fasesDeEstadoSiaf } from '../lib/estados';

type Entrada = Extract<EntradaModal, { tipo: 'siaf' }>;

const BARRA_FASE: Record<string, string> = {
  Certificado: 'bg-primary/80',
  Comprometido: 'bg-primary/60',
  Devengado: 'bg-secondary',
  Girado: 'bg-secondary/70',
  Pagado: 'bg-secondary/50',
};

export function ModalSiaf({ entrada }: { entrada: Entrada }) {
  const { nroPedido, tipoBien, tipoPedido, expSiaf } = entrada;
  const { data, isLoading, isError, error, refetch } = useDetallePedido({ nroPedido, tipoBien, tipoPedido });
  const { abrir } = useModales();

  if (isLoading) return <CargandoModal texto={`Cargando expediente ${expSiaf}…`} />;
  if (isError || !data) {
    return (
      <ErrorModal
        texto={error instanceof Error ? error.message : 'No se pudo cargar el expediente. Puede ser un corte temporal del SIGA.'}
        onReintentar={() => refetch()}
      />
    );
  }

  const exp = data.expedientes.find((x) => x.exp_siaf === expSiaf);
  const orden = data.ordenes.find((o) => o.exp_siaf === expSiaf);
  const estadoSiaf = exp?.estado_siaf ?? orden?.estado_siaf ?? null;
  const cert = data.certificaciones[0] ?? null;
  const total = orden?.total_fact_soles ?? null;

  // "Fases y montos": ancho de barra 100% para fases alcanzadas, 0% para las que
  // no. El monto solo se muestra donde hay total real de la orden.
  const fasesEstado = fasesDeEstadoSiaf(estadoSiaf);
  const barras = fasesEstado.map((f) => ({
    label: f.label,
    valor: f.hecho && total != null ? formatearNumero(total, 0) : f.hecho ? 'alcanzada' : '—',
    ancho: f.hecho ? 100 : 0,
    barraClass: BARRA_FASE[f.label],
  }));

  const faseActual = [...fasesEstado].reverse().find((f) => f.hecho)?.label ?? 'sin fase confirmada';

  const ligados: Ligado[] = [
    ...(orden
      ? [{ tipo: orden.tipo_bien === 'S' ? 'O/S' : 'O/C', id: orden.nro_orden, nota: orden.proveedor_nombre ?? orden.concepto ?? undefined, onClick: () => abrir({ tipo: 'orden', nroPedido, tipoBien, tipoPedido, nroOrden: orden.nro_orden }) }]
      : []),
    { tipo: 'Requerim.', id: data.nro_pedido, nota: 'pedido de origen en SIGA', onClick: () => abrir({ tipo: 'pedido', nroPedido, tipoBien, tipoPedido }) },
  ];

  return (
    <div className="flex flex-col gap-4">
      <ModalHead
        overline="Expediente SIAF"
        titulo={String(expSiaf)}
        mono
        descripcion="Afectación presupuestal oficial. Las cifras provienen del SIAF/MEF."
        aside={
          <>
            <span className="font-mono text-xl font-semibold tabular-nums text-primary">
              {total != null && fasesEstado.find((f) => f.label === 'Devengado')?.hecho ? formatearMoneda(total) : '—'}
            </span>
            <span className="text-[10.5px] text-muted-foreground">devengado del expediente</span>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ModalBloque titulo="Cadena programática">
          <div className="flex flex-col">
            <FilaDato label="Meta" mono>
              {data.sec_func ?? '—'}
              {data.nombre_meta ? <span className="ml-1 font-sans text-muted-foreground">· {data.nombre_meta}</span> : null}
            </FilaDato>
            <FilaDato label="Act./Proy." mono>{data.act_proy ?? '—'}</FilaDato>
            <FilaDato label="Fuente">{data.fuente_financ_nombre ?? data.fuente_financ ?? '—'}</FilaDato>
            <FilaDato label="Centro de costo">{data.centro_costo_nombre ?? data.centro_costo ?? '—'}</FilaDato>
            {cert ? <FilaDato label="Certificación" mono>{cert.nro_certifica_siaf ?? cert.nro_certifica}</FilaDato> : null}
            {exp ? <FilaDato label="Fecha SIAF" mono>{formatFecha(exp.fecha_siaf ?? exp.fecha_documento)}</FilaDato> : null}
          </div>
        </ModalBloque>

        <ModalBloque titulo="Fases y montos" nota={`Fase actual: ${faseActual}. El SIGA no desglosa el monto por fase; la barra marca la fase alcanzada.`}>
          <BarrasFaseMonto filas={barras} />
        </ModalBloque>
      </div>

      <ModalBloque titulo="Órdenes y trámite SIGA ligados a este expediente">
        <ListaLigados ligados={ligados} />
      </ModalBloque>
    </div>
  );
}
