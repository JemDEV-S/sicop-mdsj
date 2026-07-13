import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Wallet,
  TrendingUp,
  Activity,
  FileText,
  Building2,
  Info,
} from 'lucide-react';
import { useObra } from '@/features/obras/hooks';
import { mapSemaforoApiToEstado } from '@/features/obras/api';
import { Identificacion } from '@/features/obras/secciones/Identificacion';
import { AvancePresupuesto } from '@/features/obras/secciones/AvancePresupuesto';
import { Cronograma } from '@/features/obras/secciones/Cronograma';
import { UbicacionMapa } from '@/features/obras/secciones/UbicacionMapa';
import { Contratista, Documentos } from '@/features/obras/secciones/ContratistaDocumentos';
import { Galeria } from '@/features/obras/secciones/Galeria';
import { DocumentosPublicos } from '@/features/obras/secciones/DocumentosPublicos';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonCard } from '@/components/layout/LoadingSkeleton';
import { PublicHero } from '@/components/publico/PublicHero';
import { SectionBand } from '@/components/publico/SectionBand';
import { SectionHeader } from '@/components/publico/SectionHeader';
import { ProgresoAnillo } from '@/components/publico/ProgresoAnillo';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import type { ObraDetalleResponse } from '@/features/obras/types';

const ANIO_VIGENTE = 2026;

export default function Obra() {
  const { codigo } = useParams<{ codigo: string }>();
  const { data: obra, isLoading, isError, refetch } = useObra(codigo || '');

  if (!codigo) {
    return (
      <div className="mx-auto max-w-5xl px-4 md:px-6 py-10">
        <ErrorState
          titulo="Código no especificado"
          descripcion="La URL no incluye el CUI de la obra."
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-background">
        <div className="bg-card border-b border-border">
          <div className="mx-auto max-w-6xl px-4 md:px-6 py-10">
            <div className="h-4 w-40 bg-muted animate-pulse rounded mb-6" aria-hidden="true" />
            <div className="grid md:grid-cols-[1.4fr_1fr] gap-10">
              <div className="space-y-4">
                <div className="h-6 w-32 bg-muted animate-pulse rounded" aria-hidden="true" />
                <div className="h-12 w-full bg-muted animate-pulse rounded" aria-hidden="true" />
                <div className="h-12 w-3/4 bg-muted animate-pulse rounded" aria-hidden="true" />
              </div>
              <div className="h-64 bg-muted animate-pulse rounded-2xl" aria-hidden="true" />
            </div>
          </div>
        </div>
        <div className="mx-auto max-w-6xl px-4 md:px-6 py-10 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SkeletonCard className="h-56" />
            <SkeletonCard className="h-56" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SkeletonCard className="h-64" />
            <SkeletonCard className="h-64" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !obra) {
    return (
      <div className="mx-auto max-w-5xl px-4 md:px-6 py-10">
        <ErrorState
          titulo={`No encontramos la obra ${codigo}`}
          descripcion="El código puede ser incorrecto o el servidor no está disponible. Intenta de nuevo o vuelve al directorio."
          onReintentar={() => refetch()}
        />
      </div>
    );
  }

  const estado = mapSemaforoApiToEstado(obra.semaforo);
  const tieneAvanceFisico =
    obra.avance_fisico !== null && obra.avance_fisico !== undefined;
  const tienePresupuesto = obra.montos_ejecucion.pim > 0;
  const tieneEjecucion = obra.montos_ejecucion.devengado > 0;
  const enPreEjecucion = !tienePresupuesto && !tieneEjecucion;

  return (
    <div className="bg-background">
      {/* HERO — ficha de la obra */}
      <PublicHero
        compacto
        conGreca
        eyebrow={
          <>
            <Building2 className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Obra pública · CUI {obra.codigo_unico}</span>
          </>
        }
        titulo={obra.nombre_inversion || 'Sin nombre de proyecto'}
        subtitulo={<MetadataObra obra={obra} />}
        acciones={
          <Link
            to="/obras"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary focus-visible:outline-none focus-visible:underline"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Volver al directorio
          </Link>
        }
        destacado={
          <DestacadoAvance
            obra={obra}
            tieneAvanceFisico={tieneAvanceFisico}
            tienePresupuesto={tienePresupuesto}
          />
        }
      />

      {/* AVISO — pre-ejecución */}
      {enPreEjecucion ? (
        <div className="bg-accent/15 border-b border-accent/40">
          <div className="mx-auto max-w-6xl px-4 md:px-6 py-4 flex items-start gap-3">
            <Info className="w-5 h-5 text-accent-foreground shrink-0 mt-0.5" aria-hidden="true" />
            <div className="text-sm">
              <p className="font-semibold text-foreground">
                Esta obra aún no tiene ejecución presupuestal en {ANIO_VIGENTE}.
              </p>
              <p className="mt-1 text-muted-foreground">
                Es posible que se encuentre en fase de formulación, viabilidad o pendiente de
                asignación de presupuesto. La información técnica del proyecto se muestra a
                continuación.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {/* SECCIÓN — Avance físico + estado del ciclo */}
      <SectionBand tono="muted" denso>
        <SectionHeader
          eyebrow="Cómo va la obra"
          titulo="Avance y estado"
          descripcion="Indicadores clave de ejecución física y financiera de este proyecto."
        />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KpiCompacto
            icono={Activity}
            label="Avance físico"
            valor={tieneAvanceFisico ? `${obra.avance_fisico!.toFixed(1)}%` : 'Sin dato'}
            ayuda={
              tieneAvanceFisico
                ? estado === 'ok'
                  ? 'En avance'
                  : estado === 'alerta'
                    ? 'Con demoras'
                    : estado === 'critico'
                      ? 'Crítica'
                      : '—'
                : 'No registrado aún'
            }
            acento={
              !tieneAvanceFisico
                ? 'neutro'
                : estado === 'critico'
                  ? 'destructive'
                  : estado === 'alerta'
                    ? 'accent'
                    : 'primary'
            }
          />
          <KpiCompacto
            icono={TrendingUp}
            label="Avance financiero"
            valor={
              obra.montos_ejecucion.porcentaje_devengado !== null &&
              obra.montos_ejecucion.porcentaje_devengado !== undefined
                ? `${obra.montos_ejecucion.porcentaje_devengado.toFixed(1)}%`
                : tienePresupuesto
                  ? '0%'
                  : 'Sin dato'
            }
            ayuda={tienePresupuesto ? 'Devengado sobre PIM' : 'Sin PIM asignado'}
            acento={tienePresupuesto ? 'secondary' : 'neutro'}
          />
          <KpiCompacto
            icono={Wallet}
            label="Presupuesto (PIM)"
            valor={
              tienePresupuesto ? formatearMoneda(obra.montos_ejecucion.pim) : 'Sin asignar'
            }
            ayuda={
              tienePresupuesto
                ? 'Institucional Modificado'
                : 'Pendiente de asignación'
            }
            acento={tienePresupuesto ? 'primary' : 'neutro'}
          />
          <KpiCompacto
            icono={FileText}
            label="Etapa actual"
            valor={obra.etapa_f8 || obra.estado || '—'}
            ayuda={obra.marco || 'Marco no registrado'}
            acento="accent"
          />
        </div>
      </SectionBand>

      {/* SECCIÓN — Ejecución presupuestal detallada (solo si hay presupuesto) */}
      {tienePresupuesto ? (
        <SectionBand tono="background">
          <SectionHeader
            eyebrow="Presupuesto"
            titulo="Cómo se ejecuta el dinero de esta obra"
            descripcion={`Desglose de las etapas de ejecución presupuestal del año ${ANIO_VIGENTE}.`}
          />
          <AvancePresupuesto obra={obra} />
        </SectionBand>
      ) : null}

      {/* SECCIÓN — Registro visual */}
      <SectionBand tono="background">
        <SectionHeader
          eyebrow="Registro visual"
          titulo="Fotos y documentos de la obra"
          descripcion="Material publicado por la municipalidad para dar seguimiento visual y documental al avance del proyecto."
        />
        <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-6">
          <Galeria codigoUnico={obra.codigo_unico} />
          <DocumentosPublicos codigoUnico={obra.codigo_unico} />
        </div>
      </SectionBand>

      {/* SECCIÓN — Ficha técnica + cronograma + ubicación */}
      <SectionBand tono="muted">
        <SectionHeader
          eyebrow="Ficha técnica"
          titulo="Datos del proyecto"
          descripcion="Información oficial registrada en Invierte.pe y en la administración municipal."
        />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Identificacion obra={obra} />
          <Cronograma obra={obra} />
        </div>
        <div className="mt-6">
          <UbicacionMapa obra={obra} />
        </div>
      </SectionBand>

      {/* Contratista y documentos internos legacy (aún null en backend) */}
      <Contratista obra={obra} />
      <Documentos obra={obra} />
    </div>
  );
}

/* ----- Subcomponentes locales ----- */

function MetadataObra({ obra }: { obra: ObraDetalleResponse }) {
  const meta: { label: string; valor: string }[] = [];
  if (obra.funcion) meta.push({ label: 'Función', valor: obra.funcion });
  if (obra.tipologia) meta.push({ label: 'Tipología', valor: obra.tipologia });
  if (obra.modalidad) meta.push({ label: 'Modalidad', valor: obra.modalidad });

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
      {meta.map((m) => (
        <span key={m.label} className="text-muted-foreground">
          <span className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground/80">
            {m.label}:
          </span>{' '}
          <span className="text-foreground font-medium">{m.valor}</span>
        </span>
      ))}
      {meta.length === 0 ? (
        <span className="text-muted-foreground">Proyecto de inversión pública del distrito.</span>
      ) : null}
    </div>
  );
}

interface DestacadoAvanceProps {
  obra: ObraDetalleResponse;
  tieneAvanceFisico: boolean;
  tienePresupuesto: boolean;
}

function DestacadoAvance({ obra, tieneAvanceFisico, tienePresupuesto }: DestacadoAvanceProps) {
  const estado = mapSemaforoApiToEstado(obra.semaforo);
  const financiero = obra.montos_ejecucion.porcentaje_devengado ?? 0;

  // Si no hay avance físico ni presupuesto: tarjeta de estado del ciclo
  if (!tieneAvanceFisico && !tienePresupuesto) {
    return (
      <div className="relative rounded-2xl bg-card border border-border p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent" aria-hidden="true" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
            Estado del proyecto
          </span>
        </div>

        <p className="text-2xl font-bold text-foreground leading-tight">
          {obra.estado || obra.etapa_f8 || 'En formulación'}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Este proyecto de inversión aún no registra ejecución presupuestal ni avance físico
          en el año {ANIO_VIGENTE}.
        </p>

        <div className="mt-5 pt-4 border-t border-border grid grid-cols-2 gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Situación
            </p>
            <p className="mt-1 text-sm font-semibold text-foreground">
              {obra.situacion || '—'}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Etapa
            </p>
            <p className="mt-1 text-sm font-semibold text-foreground">
              {obra.etapa_f8 || '—'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const fisico = obra.avance_fisico ?? 0;
  const colorAnillo =
    estado === 'critico' ? 'primary' : estado === 'alerta' ? 'accent' : 'secondary';

  return (
    <div className="relative rounded-2xl bg-card border border-border p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <span
          className={cn(
            'inline-block w-1.5 h-1.5 rounded-full',
            estado === 'ok'
              ? 'bg-[var(--semaforo-ok)]'
              : estado === 'alerta'
                ? 'bg-[var(--semaforo-alerta)]'
                : estado === 'critico'
                  ? 'bg-[var(--semaforo-critico)]'
                  : 'bg-muted-foreground',
          )}
          aria-hidden="true"
        />
        <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Avance físico
        </span>
      </div>

      <div className="flex items-center justify-center py-2">
        <ProgresoAnillo
          valor={fisico}
          size={180}
          grosor={12}
          color={colorAnillo}
          centro={tieneAvanceFisico ? `${fisico.toFixed(1)}%` : '—'}
          etiqueta="Ejecutado"
        />
      </div>

      <div className="mt-4 pt-4 border-t border-border grid grid-cols-2 gap-4 text-center">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Devengado
          </p>
          <p className="mt-1 text-base font-bold text-foreground tabular-nums">
            {tienePresupuesto ? formatearMoneda(obra.montos_ejecucion.devengado) : '—'}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {tienePresupuesto ? `${financiero.toFixed(1)}% del PIM` : 'PIM sin asignar'}
          </p>
          <p className="mt-1 text-base font-bold text-foreground tabular-nums">
            {tienePresupuesto ? formatearMoneda(obra.montos_ejecucion.pim) : '—'}
          </p>
        </div>
      </div>
    </div>
  );
}

interface KpiCompactoProps {
  icono: typeof Wallet;
  label: string;
  valor: string;
  ayuda: string;
  acento: 'primary' | 'secondary' | 'accent' | 'destructive' | 'neutro';
}

const acentoBar: Record<KpiCompactoProps['acento'], string> = {
  primary: 'before:bg-primary',
  secondary: 'before:bg-secondary',
  accent: 'before:bg-accent',
  destructive: 'before:bg-destructive',
  neutro: 'before:bg-muted-foreground/30',
};

const acentoIconoColor: Record<KpiCompactoProps['acento'], string> = {
  primary: 'text-primary',
  secondary: 'text-secondary',
  accent: 'text-accent-foreground',
  destructive: 'text-destructive',
  neutro: 'text-muted-foreground',
};

function KpiCompacto({ icono: Icono, label, valor, ayuda, acento }: KpiCompactoProps) {
  const esNeutro = acento === 'neutro';
  return (
    <div
      className={cn(
        'relative rounded-xl bg-card border border-border p-5 pl-6',
        'before:absolute before:left-0 before:top-4 before:bottom-4 before:w-1 before:rounded-r-full',
        acentoBar[acento],
      )}
    >
      <div className="flex items-center gap-2">
        <Icono className={cn('w-4 h-4 shrink-0', acentoIconoColor[acento])} aria-hidden="true" />
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
      </div>
      <p
        className={cn(
          'mt-2 text-2xl font-bold tabular-nums leading-none truncate',
          esNeutro ? 'text-muted-foreground' : 'text-foreground',
        )}
      >
        {valor}
      </p>
      <p className="mt-1.5 text-xs text-muted-foreground truncate">{ayuda}</p>
    </div>
  );
}
