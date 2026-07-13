import { Link } from 'react-router-dom';
import {
  Building2,
  BarChart3,
  Users,
  MapPin,
  Wallet,
  TrendingUp,
  ShieldCheck,
  Database,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useEjecucionResumen } from '@/features/ejecucion/hooks';
import { useObras, useObrasMapa } from '@/features/obras/hooks';
import { useProveedoresPublico } from '@/features/proveedores/hooks';
import { PublicHero } from '@/components/publico/PublicHero';
import { SectionBand } from '@/components/publico/SectionBand';
import { SectionHeader } from '@/components/publico/SectionHeader';
import { StatBig } from '@/components/publico/StatBig';
import { ProgresoAnillo } from '@/components/publico/ProgresoAnillo';
import { FeatureCard } from '@/components/publico/FeatureCard';
import { BarraEjecucion } from '@/components/publico/BarraEjecucion';

const ANIO_VIGENTE = 2026;

function parseMonto(valor: string | number | null | undefined): number | null {
  if (valor === null || valor === undefined) return null;
  const n = typeof valor === 'string' ? parseFloat(valor) : valor;
  return Number.isNaN(n) ? null : n;
}

function formatoMillones(valor: string | number | null | undefined): string {
  const n = parseMonto(valor);
  if (n === null) return '—';
  if (n >= 1_000_000) return `S/ ${(n / 1_000_000).toFixed(1)} M`;
  if (n >= 1_000) return `S/ ${(n / 1_000).toFixed(0)} mil`;
  return `S/ ${n.toFixed(0)}`;
}

function formatoEntero(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return '—';
  return new Intl.NumberFormat('es-PE').format(valor);
}

function formatoPorcentaje(valor: string | number | null | undefined): string {
  const n = parseMonto(valor);
  if (n === null) return '—';
  return `${n.toFixed(1)}%`;
}

export default function Home() {
  const { data: resumen, isLoading: cargandoResumen } = useEjecucionResumen({ ano: ANIO_VIGENTE });
  const { data: obras, isLoading: cargandoObras } = useObras({ ano: ANIO_VIGENTE, page: 1, size: 1 });
  const { data: proveedores, isLoading: cargandoProveedores } = useProveedoresPublico({
    ano: ANIO_VIGENTE,
    page: 1,
    size: 1,
  });
  const { data: mapa, isLoading: cargandoMapa } = useObrasMapa({ ano: ANIO_VIGENTE });

  const pim = parseMonto(resumen?.pim);
  const devengado = parseMonto(resumen?.devengado);
  const porcentajeEjecucion =
    resumen?.porcentaje_ejecucion !== undefined && resumen?.porcentaje_ejecucion !== null
      ? parseMonto(resumen.porcentaje_ejecucion)
      : pim && devengado
        ? (devengado / pim) * 100
        : null;

  const kpiHomeCargando = cargandoResumen;

  return (
    <div className="bg-background">
      {/* HERO */}
      <PublicHero
        eyebrow={<>Portal de Transparencia · Año {ANIO_VIGENTE}</>}
        titulo={
          <>
            Así se invierte el presupuesto de{' '}
            <span className="text-primary">San Jerónimo</span>
          </>
        }
        subtitulo="Consulta obras públicas, ejecución del presupuesto distrital y proveedores. Los datos provienen directamente de SIAF, SIGA e Invierte.pe."
        acciones={
          <>
            <Button asChild size="lg">
              <Link to="/obras">
                <Building2 className="w-4 h-4" aria-hidden="true" />
                Ver obras públicas
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/ejecucion">
                <BarChart3 className="w-4 h-4" aria-hidden="true" />
                Ver presupuesto
              </Link>
            </Button>
          </>
        }
        destacado={
          <DestacadoAnillo
            porcentaje={porcentajeEjecucion}
            devengado={devengado}
            pim={pim}
            cargando={kpiHomeCargando}
            formatoMonto={formatoMillones}
          />
        }
      />

      {/* BANDA DE RESUMEN — stats grandes horizontales */}
      <SectionBand tono="muted" denso>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-10">
          <StatBig
            icono={Wallet}
            acento="primary"
            label="Presupuesto asignado"
            valor={formatoMillones(resumen?.pim)}
            ayuda={`PIM del ejercicio ${ANIO_VIGENTE}`}
            cargando={kpiHomeCargando}
          />
          <StatBig
            icono={TrendingUp}
            acento="secondary"
            label="Ejecutado (devengado)"
            valor={formatoMillones(resumen?.devengado)}
            ayuda={
              porcentajeEjecucion !== null
                ? `${porcentajeEjecucion.toFixed(1)}% del PIM ejecutado`
                : 'Acumulado del año'
            }
            cargando={kpiHomeCargando}
          />
          <StatBig
            icono={Building2}
            acento="accent"
            label="Obras del distrito"
            valor={formatoEntero(obras?.total)}
            ayuda="Proyectos de inversión registrados"
            cargando={cargandoObras}
          />
        </div>
      </SectionBand>

      {/* BARRA DE EJECUCIÓN — pieza pedagógica */}
      {resumen && pim && pim > 0 ? (
        <SectionBand tono="background">
          <SectionHeader
            eyebrow="Ejecución Presupuestal"
            titulo="Cómo se está usando el presupuesto"
            descripcion="Cada peso del presupuesto atraviesa cuatro etapas antes de ser pagado. Aquí puedes ver cuánto ha avanzado cada una en lo que va del año."
            accion={
              <Button asChild variant="outline">
                <Link to="/ejecucion">
                  Ver dashboard completo
                </Link>
              </Button>
            }
          />

          <div className="rounded-2xl border border-border bg-card p-6 md:p-10">
            <BarraEjecucion
              pim={pim}
              certificado={parseMonto(resumen.certificado)}
              comprometido={parseMonto(resumen.comprometido_anual)}
              devengado={devengado}
              girado={parseMonto(resumen.girado)}
              formatoMonto={formatoMillones}
            />
          </div>

          {/* Nota pedagógica */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <NotaEtapa
              titulo="Certificado"
              descripcion="El dinero está reservado para un fin específico."
            />
            <NotaEtapa
              titulo="Comprometido"
              descripcion="Se firmó un contrato u orden de compra."
            />
            <NotaEtapa
              titulo="Devengado"
              descripcion="La entidad reconoce la obligación de pago."
            />
            <NotaEtapa
              titulo="Girado"
              descripcion="El pago fue efectivamente realizado."
            />
          </div>
        </SectionBand>
      ) : null}

      {/* MÓDULOS PRINCIPALES */}
      <SectionBand tono="muted">
        <SectionHeader
          eyebrow="Explora el portal"
          titulo="¿Qué información encontrarás aquí?"
          descripcion="Cuatro secciones para explorar la gestión de recursos y proyectos de la municipalidad."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <FeatureCard
            to="/ejecucion"
            icono={BarChart3}
            acento="primary"
            destacado
            titulo="Ejecución Presupuestal"
            descripcion={`Explora cómo se distribuye y ejecuta el presupuesto del distrito durante ${ANIO_VIGENTE}, por función, fuente de financiamiento y mes.`}
            kpi={
              porcentajeEjecucion !== null
                ? formatoPorcentaje(porcentajeEjecucion)
                : null
            }
            kpiLabel="del PIM devengado"
            cargando={cargandoResumen}
            cta="Abrir dashboard"
          />

          <FeatureCard
            to="/obras"
            icono={Building2}
            acento="secondary"
            titulo="Obras Públicas"
            descripcion="Directorio de proyectos de inversión con presupuesto, avance físico y semáforo de ejecución."
            kpi={obras?.total !== undefined ? formatoEntero(obras.total) : null}
            kpiLabel="proyectos"
            cargando={cargandoObras}
            cta="Ver directorio"
          />

          <FeatureCard
            to="/proveedores"
            icono={Users}
            acento="accent"
            titulo="Proveedores"
            descripcion="Padrón de empresas y personas que brindan bienes y servicios a la municipalidad."
            kpi={proveedores?.total !== undefined ? formatoEntero(proveedores.total) : null}
            kpiLabel="proveedores con órdenes"
            cargando={cargandoProveedores}
            cta="Ver padrón"
          />

          <FeatureCard
            to="/mapa"
            icono={MapPin}
            acento="primary"
            titulo="Mapa del distrito"
            descripcion="Ubica visualmente las obras en curso a lo largo de San Jerónimo."
            kpi={mapa?.total_con_coords !== undefined ? formatoEntero(mapa.total_con_coords) : null}
            kpiLabel="obras geolocalizadas"
            cargando={cargandoMapa}
            cta="Abrir mapa"
          />
        </div>
      </SectionBand>

      {/* SELLO INSTITUCIONAL */}
      <section className="border-t border-border bg-card">
        <div className="mx-auto max-w-6xl px-4 md:px-6 py-8 grid grid-cols-1 md:grid-cols-3 gap-6">
          <SelloItem
            icono={ShieldCheck}
            titulo="Datos oficiales"
            descripcion={`Ejercicio fiscal ${ANIO_VIGENTE}, provenientes de fuentes autoritativas del MEF.`}
          />
          <SelloItem
            icono={Database}
            titulo="Sincronización diaria"
            descripcion="Los datos se actualizan automáticamente cada día desde SIAF, SIGA e Invierte.pe."
          />
          <SelloItem
            icono={Users}
            titulo="Transparencia activa"
            descripcion="Cumple con la Ley de Transparencia y Acceso a la Información Pública."
          />
        </div>
      </section>
    </div>
  );
}

/* ----- Subcomponentes locales de Home ----- */

interface DestacadoAnilloProps {
  porcentaje: number | null;
  devengado: number | null;
  pim: number | null;
  cargando: boolean;
  formatoMonto: (v: number | null) => string;
}

function DestacadoAnillo({
  porcentaje,
  devengado,
  pim,
  cargando,
  formatoMonto,
}: DestacadoAnilloProps) {
  return (
    <div className="relative rounded-2xl bg-card border border-border p-8 shadow-sm">
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-primary" aria-hidden="true" />
        <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          Ejecución del año
        </span>
      </div>

      <div className="flex items-center justify-center py-4">
        {cargando ? (
          <div
            className="w-[200px] h-[200px] rounded-full bg-muted animate-pulse"
            aria-hidden="true"
          />
        ) : (
          <ProgresoAnillo
            valor={porcentaje ?? 0}
            size={200}
            grosor={14}
            color="primary"
            centro={porcentaje !== null ? `${porcentaje.toFixed(1)}%` : '—'}
            etiqueta="PIM Ejecutado"
          />
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-border grid grid-cols-2 gap-4 text-center">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Devengado
          </p>
          <p className="mt-1 text-base font-bold text-foreground tabular-nums">
            {cargando ? '—' : formatoMonto(devengado)}
          </p>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            De un PIM de
          </p>
          <p className="mt-1 text-base font-bold text-foreground tabular-nums">
            {cargando ? '—' : formatoMonto(pim)}
          </p>
        </div>
      </div>
    </div>
  );
}

function NotaEtapa({ titulo, descripcion }: { titulo: string; descripcion: string }) {
  return (
    <div className="rounded-lg bg-muted/30 border border-border p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-foreground">{titulo}</p>
      <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{descripcion}</p>
    </div>
  );
}

interface SelloItemProps {
  icono: typeof ShieldCheck;
  titulo: string;
  descripcion: string;
}

function SelloItem({ icono: Icono, titulo, descripcion }: SelloItemProps) {
  return (
    <div className="flex items-start gap-3">
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
        <Icono className="w-4 h-4" aria-hidden="true" />
      </span>
      <div>
        <p className="text-sm font-semibold text-foreground">{titulo}</p>
        <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">{descripcion}</p>
      </div>
    </div>
  );
}
