import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Wallet,
  TrendingUp,
  Target,
  Percent,
  Table as TableIcon,
  Coins,
  Package,
} from 'lucide-react';
import {
  useEjecucionResumen,
  useEjecucionPorRubro,
  useEjecucionPorGenerica,
  useEjecucionMensualAcumulado,
} from '@/features/ejecucion/hooks';
import { PublicHero } from '@/components/publico/PublicHero';
import { SectionBand } from '@/components/publico/SectionBand';
import { SectionHeader } from '@/components/publico/SectionHeader';
import { StatBig } from '@/components/publico/StatBig';
import { ProgresoAnillo } from '@/components/publico/ProgresoAnillo';
import { BarraEjecucion } from '@/components/publico/BarraEjecucion';
import { NavegadorJerarquia } from '@/components/publico/NavegadorJerarquia';
import { GraficoAcumulado } from '@/components/publico/GraficoAcumulado';
import { ListaDistribucion } from '@/components/publico/ListaDistribucion';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { parseMonto, formatearMoneda } from '@/lib/formatters';

const ANIO_VIGENTE = 2026;
const ANOS_DISPONIBLES = [ANIO_VIGENTE, ANIO_VIGENTE - 1, ANIO_VIGENTE - 2, ANIO_VIGENTE - 3];

function formatoMillones(valor: number | null): string {
  if (valor === null) return '—';
  if (valor >= 1_000_000) return `S/ ${(valor / 1_000_000).toFixed(1)} M`;
  if (valor >= 1_000) return `S/ ${(valor / 1_000).toFixed(0)} mil`;
  return `S/ ${valor.toFixed(0)}`;
}

function formatoEntero(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return '—';
  return new Intl.NumberFormat('es-PE').format(valor);
}

export default function EjecucionDashboard() {
  const [ano, setAno] = useState<number>(ANIO_VIGENTE);

  const { data: resumen, isLoading: cargandoResumen } = useEjecucionResumen({ ano });
  const { data: rubros, isLoading: cargandoRubros } = useEjecucionPorRubro({ ano });
  const { data: genericas, isLoading: cargandoGenericas } = useEjecucionPorGenerica({ ano });
  const { data: mensual, isLoading: cargandoMensual } = useEjecucionMensualAcumulado({ ano });

  const pim = parseMonto(resumen?.pim ?? null);
  const devengado = parseMonto(resumen?.devengado ?? null);
  const certificado = parseMonto(resumen?.certificado ?? null);
  const comprometido = parseMonto(resumen?.comprometido_anual ?? null);
  const girado = parseMonto(resumen?.girado ?? null);
  const porcentajeEjecucion =
    resumen?.porcentaje_ejecucion != null
      ? parseMonto(resumen.porcentaje_ejecucion)
      : pim && devengado
        ? (devengado / pim) * 100
        : null;

  return (
    <div className="bg-background">
      {/* HERO */}
      <PublicHero
        eyebrow={<>Ejecución Presupuestal · Año {ano}</>}
        titulo={
          <>
            ¿En qué gasta la muni <span className="text-primary">tu dinero</span>?
          </>
        }
        subtitulo="Explora cómo se distribuye y ejecuta el presupuesto de San Jerónimo. Los datos provienen directamente del SIAF del MEF y se actualizan diariamente."
        acciones={
          <>
            <Select value={ano.toString()} onValueChange={(v) => setAno(parseInt(v, 10))}>
              <SelectTrigger className="w-40" aria-label="Año fiscal">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ANOS_DISPONIBLES.map((a) => (
                  <SelectItem key={a} value={a.toString()}>
                    Ejercicio {a}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button asChild variant="outline">
              <Link to="/ejecucion/detalle">
                <TableIcon className="w-4 h-4" aria-hidden="true" />
                Ver detalle por meta
              </Link>
            </Button>
          </>
        }
        destacado={
          <div className="relative rounded-2xl bg-card border border-border p-8 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <span
                className="inline-block w-1.5 h-1.5 rounded-full bg-primary"
                aria-hidden="true"
              />
              <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                Ejecución del año
              </span>
            </div>
            <div className="flex items-center justify-center py-4">
              {cargandoResumen ? (
                <div
                  className="w-[200px] h-[200px] rounded-full bg-muted animate-pulse"
                  aria-hidden="true"
                />
              ) : (
                <ProgresoAnillo
                  valor={porcentajeEjecucion ?? 0}
                  size={200}
                  grosor={14}
                  color="primary"
                  centro={porcentajeEjecucion !== null ? `${porcentajeEjecucion.toFixed(1)}%` : '—'}
                  etiqueta="PIM ejecutado"
                />
              )}
            </div>
            <div className="mt-4 pt-4 border-t border-border grid grid-cols-2 gap-4 text-center">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Devengado
                </p>
                <p className="mt-1 text-base font-bold text-foreground tabular-nums">
                  {cargandoResumen ? '—' : formatoMillones(devengado)}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  De un PIM de
                </p>
                <p className="mt-1 text-base font-bold text-foreground tabular-nums">
                  {cargandoResumen ? '—' : formatoMillones(pim)}
                </p>
              </div>
            </div>
          </div>
        }
      />

      {/* KPIs */}
      <SectionBand tono="muted" denso>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-10">
          <StatBig
            icono={Wallet}
            acento="primary"
            label="Presupuesto asignado"
            valor={formatoMillones(pim)}
            ayuda={`PIM ${ano} · ${formatoEntero(resumen?.metas)} metas`}
            cargando={cargandoResumen}
          />
          <StatBig
            icono={TrendingUp}
            acento="secondary"
            label="Ejecutado (devengado)"
            valor={formatoMillones(devengado)}
            ayuda={
              porcentajeEjecucion !== null
                ? `${porcentajeEjecucion.toFixed(1)}% del PIM ejecutado`
                : 'Acumulado del año'
            }
            cargando={cargandoResumen}
          />
          <StatBig
            icono={Target}
            acento="accent"
            label="Certificado"
            valor={formatoMillones(certificado)}
            ayuda="Presupuesto reservado para uso específico"
            cargando={cargandoResumen}
          />
          <StatBig
            icono={Percent}
            acento="primary"
            label="Girado"
            valor={formatoMillones(girado)}
            ayuda="Pagos efectivamente realizados"
            cargando={cargandoResumen}
          />
        </div>
      </SectionBand>

      {/* BARRA PEDAGÓGICA */}
      {pim && pim > 0 ? (
        <SectionBand tono="background">
          <SectionHeader
            eyebrow="Cómo se gasta el presupuesto"
            titulo="Las 4 etapas de la ejecución"
            descripcion="Cada peso del presupuesto atraviesa cuatro etapas antes de ser pagado. Aquí puedes ver cuánto ha avanzado cada una."
          />
          <div className="rounded-2xl border border-border bg-card p-6 md:p-10">
            <BarraEjecucion
              pim={pim}
              certificado={certificado}
              comprometido={comprometido}
              devengado={devengado}
              girado={girado}
              formatoMonto={(v) => formatearMoneda(v, true)}
            />
          </div>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <NotaEtapa titulo="Certificado" descripcion="El dinero está reservado para un fin específico." />
            <NotaEtapa titulo="Comprometido" descripcion="Se firmó un contrato u orden de compra." />
            <NotaEtapa titulo="Devengado" descripcion="La entidad reconoce la obligación de pago." />
            <NotaEtapa titulo="Girado" descripcion="El pago fue efectivamente realizado." />
          </div>
        </SectionBand>
      ) : null}

      {/* NAVEGADOR JERÁRQUICO */}
      <SectionBand tono="muted">
        <SectionHeader
          eyebrow="Explora el gasto"
          titulo="¿En qué se está gastando el presupuesto?"
          descripcion="Empieza por el sector, luego elige la obra o servicio, y baja hasta la meta ejecutable. Puedes volver en cualquier momento."
          accion={
            <Button asChild variant="outline">
              <Link to="/ejecucion/detalle">
                <TableIcon className="w-4 h-4" aria-hidden="true" />
                Tabla completa de metas
              </Link>
            </Button>
          }
        />
        <NavegadorJerarquia ano={ano} />
      </SectionBand>

      {/* DISTRIBUCIONES: RUBROS Y GENÉRICAS */}
      <SectionBand tono="background">
        <SectionHeader
          eyebrow="Análisis del dinero"
          titulo="¿De dónde viene y en qué tipo de gasto se usa?"
          descripcion="El presupuesto tiene dos caras: el origen del dinero (rubro) y el tipo de gasto en que se emplea (genérica). Ambas se aplican en simultáneo a todo el presupuesto."
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Rubros */}
          <div className="rounded-2xl border border-border bg-card p-6 md:p-8">
            <div className="flex items-center gap-2.5 mb-6">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Coins className="w-4 h-4" aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm font-semibold text-foreground">¿De dónde viene el dinero?</p>
                <p className="text-xs text-muted-foreground">
                  Rubros de financiamiento — origen específico del presupuesto
                </p>
              </div>
            </div>
            <ListaDistribucion
              items={rubros?.map((r) => ({
                codigo: r.rubro_codigo,
                nombre: r.rubro_nombre,
                pim: r.pim,
                devengado: r.devengado,
                participacion_pim: r.participacion_pim,
              }))}
              isLoading={cargandoRubros}
              acento="primary"
              vacio="No hay información de rubros para este año."
            />
          </div>

          {/* Genéricas */}
          <div className="rounded-2xl border border-border bg-card p-6 md:p-8">
            <div className="flex items-center gap-2.5 mb-6">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-secondary/10 text-secondary">
                <Package className="w-4 h-4" aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm font-semibold text-foreground">¿En qué tipo de gasto?</p>
                <p className="text-xs text-muted-foreground">
                  Genérica — categoría económica de uso del dinero
                </p>
              </div>
            </div>
            <ListaDistribucion
              items={genericas?.map((g) => ({
                codigo: g.generica_codigo,
                nombre: g.generica_nombre,
                pim: g.pim,
                devengado: g.devengado,
                participacion_pim: g.participacion_pim,
              }))}
              isLoading={cargandoGenericas}
              acento="secondary"
              vacio="No hay información de genéricas para este año."
            />
          </div>
        </div>
      </SectionBand>

      {/* EVOLUCIÓN MENSUAL */}
      <SectionBand tono="muted">
        <SectionHeader
          eyebrow="Ritmo del año"
          titulo="Evolución de la ejecución mes a mes"
          descripcion="Cómo va creciendo el gasto acumulado durante el año. La línea muestra el total pagado hasta cada mes, no el gasto de ese mes."
        />
        <GraficoAcumulado data={mensual} isLoading={cargandoMensual} />
      </SectionBand>
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
