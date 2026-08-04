/**
 * Cruce SIAF-SIGA · Vista consolidada por meta (HU-13 · T-51).
 *
 * Ruta: /interno/cruce/meta/:secFunc — protegida por RequireAuth.
 *
 * Reúne en una pantalla todo lo ejecutado contra una meta: presupuesto dual
 * (SIGA operativo | MEF oficial), órdenes de adquisición, certificaciones y
 * pedidos de origen. El devengado y el % salen SIEMPRE del MEF real
 * (Docs/consolidacion-backend-presupuestal.md §0.1).
 */
import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ChevronRight, LayoutDashboard, Wallet, Package, FileCheck, FileText } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Acordeon } from '@/components/layout/Acordeon';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonKPI, SkeletonBloque } from '@/components/layout/LoadingSkeleton';
import { formatearMoneda } from '@/lib/formatters';
import { useConsolidadoMeta, esNoEncontrada } from '@/features/cruce/api';
import { formatSecFunc, totalOrdenes } from '@/features/cruce/lib';
import { KpisMeta, DetallePresupuesto } from '@/features/cruce/secciones/PresupuestoMeta';
import {
  TablaOrdenes,
  TablaCertificaciones,
  TablaPedidos,
} from '@/features/cruce/secciones/TablasCruce';

function Breadcrumbs({ secFunc }: { secFunc: number }) {
  return (
    <nav aria-label="Ubicación" className="flex items-center gap-1 text-sm text-muted-foreground">
      <Link to="/interno" className="inline-flex items-center gap-1 hover:text-primary">
        <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
      </Link>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" aria-hidden="true" />
      <Link to="/interno/saldos" className="hover:text-primary">
        Saldos
      </Link>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" aria-hidden="true" />
      <span className="font-medium text-foreground" aria-current="page">
        Meta {formatSecFunc(secFunc)}
      </span>
    </nav>
  );
}

export default function CruceMeta() {
  const { secFunc: secFuncParam } = useParams<{ secFunc: string }>();
  const secFunc = secFuncParam != null ? Number.parseInt(secFuncParam, 10) : null;
  const valido = secFunc != null && Number.isFinite(secFunc);

  const { data, isLoading, isError, error, refetch } = useConsolidadoMeta(valido ? secFunc : null);

  const totalOrd = useMemo(
    () => (data ? totalOrdenes(data.ordenes) : 0),
    [data],
  );

  if (!valido) {
    return (
      <div className="space-y-6">
        <PageHeader titulo="Vista consolidada de meta" />
        <EmptyState
          titulo="Meta no especificada"
          descripcion="La dirección no incluye un número de meta (SEC_FUNC) válido."
          accion={{ label: 'Ir a Saldos', href: '/interno/saldos' }}
        />
      </div>
    );
  }

  // 404: meta inexistente o fuera del alcance del usuario.
  if (isError && esNoEncontrada(error)) {
    return (
      <div className="space-y-6">
        <PageHeader
          titulo={`Meta ${formatSecFunc(secFunc)}`}
          breadcrumbs={<Breadcrumbs secFunc={secFunc} />}
        />
        <EmptyState
          titulo="Meta no encontrada"
          descripcion="Esta meta no existe en el año seleccionado o está fuera de tu alcance. Prueba cambiar el año desde el encabezado o vuelve a Saldos."
          accion={{ label: 'Volver a Saldos', href: '/interno/saldos' }}
        />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          titulo={`Meta ${formatSecFunc(secFunc)}`}
          breadcrumbs={<Breadcrumbs secFunc={secFunc} />}
        />
        <ErrorState
          titulo="No se pudo cargar el consolidado de la meta"
          descripcion="Puede ser un corte temporal del SIGA. Vuelve a intentarlo."
          onReintentar={() => refetch()}
        />
      </div>
    );
  }

  const nombreMeta = data?.meta.nombre ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        titulo={
          isLoading
            ? `Meta ${formatSecFunc(secFunc)}`
            : `Meta ${formatSecFunc(secFunc)} · ${nombreMeta ?? 'Sin nombre'}`
        }
        descripcion="Consolidado de presupuesto, órdenes, certificaciones y pedidos de la meta."
        breadcrumbs={<Breadcrumbs secFunc={secFunc} />}
      />

      {isLoading || !data ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonKPI key={i} />
            ))}
          </div>
          <SkeletonBloque className="h-14 w-full" />
          <SkeletonBloque className="h-14 w-full" />
        </>
      ) : (
        <>
          {/* Contexto de la meta */}
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted-foreground">
            {data.meta.act_proy ? (
              <span>
                Acto/Proyecto: <span className="font-medium text-foreground">{data.meta.act_proy}</span>
              </span>
            ) : null}
            {data.meta.funcion ? (
              <span>
                Función: <span className="font-medium text-foreground">{data.meta.funcion}</span>
              </span>
            ) : null}
            {data.meta.programa ? (
              <span>
                Programa: <span className="font-medium text-foreground">{data.meta.programa}</span>
              </span>
            ) : null}
          </div>

          {/* KPIs */}
          <KpisMeta presupuesto={data.presupuesto} />

          {/* Acordeón: Presupuesto (abierto) · Órdenes · Certificaciones · Pedidos */}
          <div className="space-y-3">
            <Acordeon titulo="Presupuesto (SIGA y MEF)" icono={Wallet} defaultOpen>
              <DetallePresupuesto presupuesto={data.presupuesto} />
            </Acordeon>

            <Acordeon
              titulo="Órdenes de adquisición"
              icono={Package}
              conteo={data.ordenes.length}
              resumen={data.ordenes.length > 0 ? formatearMoneda(totalOrd, true) : undefined}
              vacio={data.ordenes.length === 0}
            >
              <TablaOrdenes ordenes={data.ordenes} />
            </Acordeon>

            <Acordeon
              titulo="Certificaciones"
              icono={FileCheck}
              conteo={data.certificaciones.length}
              vacio={data.certificaciones.length === 0}
            >
              <TablaCertificaciones items={data.certificaciones} />
            </Acordeon>

            <Acordeon
              titulo="Pedidos de origen"
              icono={FileText}
              conteo={data.pedidos.length}
              vacio={data.pedidos.length === 0}
            >
              <TablaPedidos pedidos={data.pedidos} />
            </Acordeon>
          </div>
        </>
      )}
    </div>
  );
}
