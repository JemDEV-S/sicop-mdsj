/**
 * Perfil interno de proveedor (HU-19 · T-53).
 *
 * Ruta: /interno/proveedores/:ruc — protegida por RequireAuth.
 *
 * Identidad + contacto, KPIs de ejecución (calculados desde sus ÓRDENES —
 * el endpoint de detalle no agrega el monto), historial de órdenes y contratos
 * del proveedor. orden ≠ contrato: el monto ejecutado (órdenes) y el valor de
 * los contratos se muestran por separado, nunca sumados.
 */
import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ChevronRight,
  LayoutDashboard,
  Building2,
  User,
  Mail,
  Phone,
  MapPin,
  Package,
  FileSignature,
  CalendarClock,
  CheckCircle2,
  Ban,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { KpiCard } from '@/components/KpiCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonKPI, SkeletonBloque } from '@/components/layout/LoadingSkeleton';
import { cn } from '@/lib/utils';
import { formatearMoneda, formatFecha } from '@/lib/formatters';
import { useContextoInterno } from '@/store/contexto-interno';
import {
  useProveedor,
  useOrdenesProveedor,
  useContratosProveedor,
  esNoEncontrado,
} from '@/features/provint/api';
import {
  esPersonaJuridica,
  tipoPersonaLabel,
  esFlagVerdad,
  tipoBienLabel,
  ordenAnulada,
  ordenDevengadaSiaf,
  resumenOrdenes,
  refContrato,
} from '@/features/provint/lib';
import type { ContratoItem, OrdenProveedor } from '@/features/provint/types';

function Breadcrumbs({ nombre }: { nombre: string }) {
  return (
    <nav aria-label="Ubicación" className="flex items-center gap-1 text-sm text-muted-foreground">
      <Link to="/interno" className="inline-flex items-center gap-1 hover:text-primary">
        <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
      </Link>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" aria-hidden="true" />
      <Link to="/interno/proveedores" className="hover:text-primary">
        Proveedores
      </Link>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" aria-hidden="true" />
      <span className="max-w-[16rem] truncate font-medium text-foreground" aria-current="page">
        {nombre}
      </span>
    </nav>
  );
}

export default function PerfilProveedor() {
  const { ruc } = useParams<{ ruc: string }>();
  const año = useContextoInterno((s) => s.añoActivo);

  const provQ = useProveedor(ruc ?? null);
  const ordenesQ = useOrdenesProveedor(ruc ?? null);
  const contratosQ = useContratosProveedor(ruc ?? null);

  const ordenes = ordenesQ.data ?? [];
  const resumen = useMemo(() => resumenOrdenes(ordenesQ.data ?? []), [ordenesQ.data]);

  if (provQ.isError && esNoEncontrado(provQ.error)) {
    return (
      <div className="space-y-6">
        <PageHeader titulo="Proveedor" />
        <EmptyState
          titulo="Proveedor no encontrado"
          descripcion={`No existe un proveedor con RUC ${ruc} en el registro.`}
          accion={{ label: 'Volver al directorio', href: '/interno/proveedores' }}
        />
      </div>
    );
  }

  if (provQ.isError) {
    return (
      <div className="space-y-6">
        <PageHeader titulo="Proveedor" />
        <ErrorState
          titulo="No se pudo cargar el proveedor"
          descripcion="Puede ser un corte temporal del SIGA. Vuelve a intentarlo."
          onReintentar={() => provQ.refetch()}
        />
      </div>
    );
  }

  const prov = provQ.data;
  const juridica = prov ? esPersonaJuridica(prov.tipo_persona, prov.ruc) : true;
  const Icono = juridica ? Building2 : User;

  return (
    <div className="space-y-6">
      <PageHeader
        titulo={prov?.nombre ?? (provQ.isLoading ? 'Cargando…' : 'Proveedor')}
        descripcion={
          prov ? (
            <span className="inline-flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="inline-flex items-center gap-1.5">
                <Icono className="h-4 w-4" aria-hidden="true" />
                {tipoPersonaLabel(prov.tipo_persona, prov.ruc)}
              </span>
              <span className="font-mono">RUC {prov.ruc}</span>
              {prov.giro ? <span>· {prov.giro}</span> : null}
            </span>
          ) : undefined
        }
        breadcrumbs={prov ? <Breadcrumbs nombre={prov.nombre ?? prov.ruc ?? 'Proveedor'} /> : undefined}
      />

      {provQ.isLoading || !prov ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonKPI key={i} />
          ))}
        </div>
      ) : (
        <>
          {/* Contacto + flags */}
          <SectionCard titulo="Identificación y contacto" padding="md">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <dl className="grid grid-cols-1 gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
                <Contacto icono={Mail} label="Email" valor={prov.email} />
                <Contacto icono={Phone} label="Teléfono" valor={prov.telefonos} />
                <Contacto icono={MapPin} label="Dirección" valor={prov.direccion} />
                <Contacto label="RNP" valor={prov.nro_rnp} />
              </dl>
              <div className="flex flex-wrap gap-2">
                {esFlagVerdad(prov.flag_mype) ? <Flag>MYPE</Flag> : null}
                {prov.flag_rnp === 'S' ? <Flag>RNP</Flag> : null}
                {prov.flag_consorcio === 'S' ? <Flag>Consorcio</Flag> : null}
              </div>
            </div>
          </SectionCard>

          {/* KPIs (desde las órdenes, no del detalle que trae null) */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <KpiCard
              label={`Ejecutado en órdenes ${año}`}
              valor={formatearMoneda(resumen.montoTotal)}
              tono="primario"
              icono={Package}
              ayuda="Suma facturada en sus órdenes (ejecución real, no contratos)"
            />
            <KpiCard
              label="Órdenes vigentes"
              valor={ordenesQ.isLoading ? '…' : resumen.nroOrdenes.toLocaleString('es-PE')}
              tono="neutro"
              icono={Package}
              ayuda="Excluye órdenes anuladas"
            />
            <KpiCard
              label="Última orden"
              valor={resumen.ultimaFecha ? formatFecha(resumen.ultimaFecha) : '—'}
              tono="secundario"
              icono={CalendarClock}
            />
          </div>

          {/* Historial de órdenes */}
          <SectionCard titulo={`Órdenes ${año}`} icono={Package} padding="sm" bodyClassName="p-0">
            {ordenesQ.isLoading ? (
              <div className="p-4">
                <SkeletonBloque className="h-40 w-full" />
              </div>
            ) : ordenes.length === 0 ? (
              <EmptyState
                titulo="Sin órdenes en el año"
                descripcion={`Este proveedor no tiene órdenes registradas en ${año}. Prueba con otro año desde el encabezado.`}
              />
            ) : (
              <TablaOrdenes ordenes={ordenes} />
            )}
          </SectionCard>

          {/* Contratos del proveedor */}
          <SectionCard titulo="Contratos" icono={FileSignature} padding="sm" bodyClassName="p-0">
            {contratosQ.isLoading ? (
              <div className="p-4">
                <SkeletonBloque className="h-24 w-full" />
              </div>
            ) : (contratosQ.data?.length ?? 0) === 0 ? (
              <EmptyState
                titulo="Sin contratos"
                descripcion="Este proveedor no tiene contratos registrados. Puede operar por órdenes de compra directa."
              />
            ) : (
              <TablaContratos contratos={contratosQ.data ?? []} />
            )}
          </SectionCard>
        </>
      )}
    </div>
  );
}

function Contacto({
  icono: Icono,
  label,
  valor,
}: {
  icono?: typeof Mail;
  label: string;
  valor: string | null;
}) {
  return (
    <div className="flex items-start gap-2">
      {Icono ? <Icono className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" /> : null}
      <div className="min-w-0">
        <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
        <dd className="text-foreground">{valor ?? '—'}</dd>
      </div>
    </div>
  );
}

function Flag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </span>
  );
}

function TablaOrdenes({ ordenes }: { ordenes: OrdenProveedor[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2.5 text-left">Orden</th>
            <th className="px-4 py-2.5 text-left">Concepto</th>
            <th className="px-4 py-2.5 text-right">Importe</th>
            <th className="px-4 py-2.5 text-left">SIAF</th>
            <th className="px-4 py-2.5 text-left">Estado</th>
          </tr>
        </thead>
        <tbody>
          {ordenes.map((o, i) => {
            const anulada = ordenAnulada(o.estado);
            const devengada = ordenDevengadaSiaf(o.estado_siaf);
            return (
              <tr
                key={`${o.nro_orden}-${o.ano_eje}`}
                className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs font-semibold text-foreground">
                      {o.nro_orden}-{o.ano_eje}
                    </span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {tipoBienLabel(o.tipo_bien)}
                    </span>
                  </div>
                  {o.fecha_orden ? (
                    <p className="text-[11px] text-muted-foreground">{formatFecha(o.fecha_orden)}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <p className="line-clamp-2 max-w-md text-xs text-muted-foreground" title={o.concepto ?? ''}>
                    {o.concepto ?? '—'}
                  </p>
                </td>
                <td className="px-4 py-3 text-right font-medium tabular-nums text-foreground">
                  {o.total_fact_soles != null ? formatearMoneda(o.total_fact_soles, true) : '—'}
                </td>
                <td className="px-4 py-3">
                  {devengada ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-secondary">
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Devengado
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Pendiente</span>
                  )}
                  {o.exp_siaf ? (
                    <p className="font-mono text-[11px] text-muted-foreground">EXP {o.exp_siaf}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  {anulada ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">
                      <Ban className="h-3 w-3" aria-hidden="true" />
                      Anulada
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Vigente</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TablaContratos({ contratos }: { contratos: ContratoItem[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-2.5 text-left">Contrato</th>
            <th className="px-4 py-2.5 text-left">Documento</th>
            <th className="px-4 py-2.5 text-right">Valor (marco)</th>
            <th className="px-4 py-2.5 text-left">Vigencia</th>
          </tr>
        </thead>
        <tbody>
          {contratos.map((c, i) => (
            <tr
              key={`${c.nro_contrato}-${c.ano_eje}-${c.sec_contrato}`}
              className={cn('border-t border-border align-top', i % 2 === 1 && 'bg-muted/20')}
            >
              <td className="px-4 py-3 font-mono text-xs font-semibold text-foreground">
                {refContrato(c.nro_contrato, c.ano_eje)}
                <span className="ml-1.5 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {tipoBienLabel(c.tipo_bien)}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-muted-foreground">{c.nro_documento ?? '—'}</td>
              <td className="px-4 py-3 text-right font-medium tabular-nums text-foreground">
                {c.valor_soles != null ? formatearMoneda(c.valor_soles, true) : '—'}
              </td>
              <td className="px-4 py-3 text-xs text-muted-foreground">
                {formatFecha(c.fecha_inicial)} → {formatFecha(c.fecha_final)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
