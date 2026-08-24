// Modal · Expediente SIAF. Rompe la ceguera SIAF del pipeline: muestra el
// detalle por fase (Certificado/Devengado/Girado/Pagado) con monto real,
// proveedor y documentos sustento, desde el Formato A (carga provisional).
// La cadena programática y los ligados siguen saliendo del detalle SIGA.

import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { useDetalleExpedienteSiaf, useDetallePedido } from '@/features/pipeline/api';
import { useModales, type EntradaModal } from '../ModalesContext';
import { CargandoModal, ErrorModal } from '../EstadoModal';
import { FilaDato, ModalBloque, ModalHead } from '../ui';
import {
  BarrasFasesSiaf,
  CajaTesoreria,
  DocumentosPorFase,
} from '../componentes/DetalleFasesSiaf';
import {
  ordenarFases,
  proveedorDeExpediente,
  selloDeDetalle,
} from '../componentes/detalle-fases-siaf-lib';
import { ListaLigados, type Ligado } from '../componentes/FilaLigado';

type Entrada = Extract<EntradaModal, { tipo: 'siaf' }>;

export function ModalSiaf({ entrada }: { entrada: Entrada }) {
  const { nroPedido, tipoBien, tipoPedido, expSiaf } = entrada;
  const pedido = useDetallePedido({ nroPedido, tipoBien, tipoPedido });
  const siaf = useDetalleExpedienteSiaf(expSiaf);
  const { abrir } = useModales();

  if (pedido.isLoading) return <CargandoModal texto={`Cargando expediente ${expSiaf}…`} />;
  if (pedido.isError || !pedido.data) {
    return (
      <ErrorModal
        texto={
          pedido.error instanceof Error
            ? pedido.error.message
            : 'No se pudo cargar el expediente. Puede ser un corte temporal del SIGA.'
        }
        onReintentar={() => pedido.refetch()}
      />
    );
  }

  const data = pedido.data;
  const exp = data.expedientes.find((x) => x.exp_siaf === expSiaf);
  const orden = data.ordenes.find((o) => o.exp_siaf === expSiaf);
  const cert = data.certificaciones[0] ?? null;

  const detalle = siaf.data;
  const { fases, porCod } = ordenarFases(detalle);
  const tieneFases = Boolean(detalle?.tiene_datos) && fases.length > 0;

  // El "devengado" que rotula la cabecera: el neto de la fase D del Formato A.
  const devengado = porCod.get('D')?.monto_neto ?? null;
  const { nombre: proveedor, ruc: proveedorRuc } = proveedorDeExpediente(detalle);

  const ligados: Ligado[] = [
    ...(orden
      ? [
          {
            tipo: orden.tipo_bien === 'S' ? 'O/S' : 'O/C',
            id: orden.nro_orden,
            nota: orden.proveedor_nombre ?? orden.concepto ?? undefined,
            onClick: () =>
              abrir({ tipo: 'orden', nroPedido, tipoBien, tipoPedido, nroOrden: orden.nro_orden }),
          },
        ]
      : []),
    {
      tipo: 'Requerim.',
      id: data.nro_pedido,
      nota: 'pedido de origen en SIGA',
      onClick: () => abrir({ tipo: 'pedido', nroPedido, tipoBien, tipoPedido }),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <ModalHead
        overline="Expediente SIAF"
        titulo={String(expSiaf)}
        mono
        aside={
          <>
            <span className="font-mono text-2xl font-semibold tabular-nums text-primary">
              {devengado != null ? formatearMoneda(devengado) : '—'}
            </span>
            <span className="text-[10.5px] text-muted-foreground">devengado del expediente</span>
          </>
        }
      />

      {tieneFases ? <CajaTesoreria detalle={detalle!} /> : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ModalBloque titulo="Cadena programática">
          <div className="flex flex-col">
            <FilaDato label="Meta" mono>
              {data.sec_func ?? '—'}
              {data.nombre_meta ? (
                <span className="ml-1 font-sans text-muted-foreground">· {data.nombre_meta}</span>
              ) : null}
            </FilaDato>
            <FilaDato label="Act./Proy." mono>{data.act_proy ?? '—'}</FilaDato>
            <FilaDato label="Fuente">{data.fuente_financ_nombre ?? data.fuente_financ ?? '—'}</FilaDato>
            <FilaDato label="Centro de costo">{data.centro_costo_nombre ?? data.centro_costo ?? '—'}</FilaDato>
            {proveedor ? (
              <FilaDato label="Proveedor">
                {proveedor}
                {proveedorRuc ? <span className="ml-1 font-mono text-muted-foreground">· {proveedorRuc}</span> : null}
              </FilaDato>
            ) : null}
            {cert ? <FilaDato label="Certificación" mono>{cert.nro_certifica_siaf ?? cert.nro_certifica}</FilaDato> : null}
            {exp ? <FilaDato label="Fecha SIAF" mono>{formatFecha(exp.fecha_siaf ?? exp.fecha_documento)}</FilaDato> : null}
          </div>
        </ModalBloque>

        <ModalBloque titulo="Montos por fase" nota={selloDeDetalle(detalle)}>
          {siaf.isLoading ? (
            <p className="text-[12px] text-muted-foreground">Cargando detalle SIAF…</p>
          ) : !detalle?.tiene_datos ? (
            <p className="text-[12px] leading-relaxed text-muted-foreground">
              Aún no se ha cargado el Formato A del SIAF para este año. Un
              administrador puede subirlo para ver el monto real por fase.
            </p>
          ) : fases.length === 0 ? (
            <p className="text-[12px] leading-relaxed text-muted-foreground">
              El expediente aún no registra fases de gasto en el detalle SIAF.
            </p>
          ) : (
            <BarrasFasesSiaf detalle={detalle} />
          )}
        </ModalBloque>
      </div>

      {tieneFases ? (
        <ModalBloque titulo="Documentos sustento por fase">
          <DocumentosPorFase detalle={detalle!} />
        </ModalBloque>
      ) : null}

      <ModalBloque titulo="Órdenes y trámite SIGA ligados a este expediente">
        <ListaLigados ligados={ligados} />
      </ModalBloque>
    </div>
  );
}
