import * as React from 'react';
import { cn } from '@/lib/utils';
import { PiedraInca } from '@/components/decor/PiedraInca';
import { GrecaAndina } from '@/components/decor/GrecaAndina';

interface PublicHeroProps {
  eyebrow?: React.ReactNode;
  titulo: React.ReactNode;
  subtitulo?: React.ReactNode;
  acciones?: React.ReactNode;
  taglineDerecha?: React.ReactNode;
  /** Contenido lateral opcional a la derecha (KPI destacado, ilustración, etc). */
  destacado?: React.ReactNode;
  /** Área superior interactiva (ej: galería de fotos flotantes con animación) */
  areaSuperior?: React.ReactNode;
  /** Franja decorativa inferior. Default true. */
  conGreca?: boolean;
  /** Compacto = padding reducido para páginas internas de listado/detalle. */
  compacto?: boolean;
  /** Distribución horizontal amplia estilo Motion (título a la izquierda, acciones a la derecha). */
  distribuido?: boolean;
  /** Fondo blanco limpio (#ffffff). Default true para mantener fondo blanco institucional. */
  fondoBlanco?: boolean;
  className?: string;
}

/**
 * Hero canónico del portal público. Estructura asimétrica con muro inca
 * como enmarque decorativo en el borde derecho. Se usa en Home, ObrasListado,
 * EjecucionDashboard, Mapa y Obra.
 */
export function PublicHero({
  eyebrow,
  titulo,
  subtitulo,
  acciones,
  taglineDerecha,
  destacado,
  areaSuperior,
  conGreca = true,
  compacto = false,
  distribuido = false,
  fondoBlanco = true,
  className,
}: PublicHeroProps) {
  return (
    <section
      className={cn(
        'relative overflow-hidden border-b border-border/60',
        fondoBlanco
          ? 'bg-white'
          : 'bg-gradient-to-br from-card via-background to-primary/10',
        distribuido && 'min-h-[calc(100vh-72px)] md:min-h-[calc(100vh-80px)] flex flex-col justify-between',
        className,
      )}
    >
      {/* Muro inca — enmarque sutil a la derecha */}
      <div
        className="pointer-events-none absolute inset-y-0 right-0 w-[42%] hidden md:block overflow-hidden"
        aria-hidden="true"
      >
        <PiedraInca
          color="primary"
          opacidad={fondoBlanco ? 0.03 : 0.06}
          className="absolute inset-0 h-full w-full"
        />
        {/* Gradiente suave para fundir el muro con el fondo blanco */}
        <div
          className="absolute inset-0"
          style={{
            background: fondoBlanco
              ? 'linear-gradient(to right, #ffffff 0%, rgba(255,255,255,0.7) 35%, transparent 100%)'
              : 'linear-gradient(to right, var(--card) 0%, transparent 40%, transparent 100%)',
          }}
        />
      </div>

      <div
        className={cn(
          'relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 w-full',
          distribuido
            ? 'flex-1 flex flex-col justify-center py-6 sm:py-8 lg:py-10'
            : compacto
              ? 'py-8 md:py-10'
              : 'py-12 md:py-16',
        )}
      >
        {distribuido ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 xl:gap-12 items-center w-full my-auto">
            {/* Columna Izquierda: Eyebrow + Título + Subtítulo + Tagline + Acciones */}
            <div className="lg:col-span-6 xl:col-span-6 flex flex-col justify-center z-10 pr-0 lg:pr-2">
              {eyebrow ? (
                <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-border/80 bg-zinc-50/90 dark:bg-muted/40 px-3.5 py-1.5 text-xs sm:text-sm font-medium text-zinc-600 dark:text-muted-foreground shadow-2xs w-fit">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </span>
                  <span>{eyebrow}</span>
                </div>
              ) : null}

              <h1 className="font-display text-4xl sm:text-5xl md:text-[3.25rem] lg:text-[3.75rem] xl:text-[4.25rem] font-bold sm:font-extrabold tracking-[-0.035em] leading-[1.06] text-foreground text-balance">
                {titulo}
              </h1>

              {subtitulo ? (
                <p className="mt-4 sm:mt-5 text-base sm:text-lg text-muted-foreground/85 leading-relaxed max-w-lg text-pretty font-normal">
                  {subtitulo}
                </p>
              ) : null}

              {taglineDerecha ? (
                <div className="mt-7 text-xs sm:text-sm font-medium text-muted-foreground/80 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary/60 inline-block" />
                  <span>{taglineDerecha}</span>
                </div>
              ) : null}

              {acciones ? (
                <div className="mt-6 w-full flex flex-wrap items-center gap-3.5">
                  {acciones}
                </div>
              ) : null}
            </div>

            {/* Columna Derecha: Animación de Imágenes Cuadradas en Baraja y Dispersión */}
            <div className="lg:col-span-6 xl:col-span-6 relative w-full h-[380px] sm:h-[450px] md:h-[500px] lg:h-[560px] xl:h-[600px] flex items-center justify-center">
              {areaSuperior}
            </div>
          </div>
        ) : (
          <div
            className={cn(
              'grid gap-8 items-center',
              destacado ? 'md:grid-cols-[1.4fr_1fr]' : 'md:grid-cols-1',
            )}
          >
            {/* Columna principal */}
            <div className="max-w-2xl">
              {eyebrow ? (
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border/80 bg-zinc-50/90 dark:bg-muted/40 px-3 py-1 text-xs font-medium text-zinc-600 dark:text-muted-foreground shadow-2xs">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                  </span>
                  <span>{eyebrow}</span>
                </div>
              ) : null}

              <h1
                className={cn(
                  'font-bold text-foreground leading-[1.12] tracking-tight text-balance',
                  compacto
                    ? 'text-2xl md:text-3xl'
                    : 'text-3xl sm:text-4xl md:text-[2.75rem] lg:text-[3.25rem]',
                )}
              >
                {titulo}
              </h1>

              {subtitulo ? (
                <p
                  className={cn(
                    'mt-3.5 sm:mt-4 text-muted-foreground max-w-xl text-pretty font-normal leading-relaxed',
                    compacto ? 'text-sm md:text-base' : 'text-base sm:text-lg',
                  )}
                >
                  {subtitulo}
                </p>
              ) : null}

              {acciones ? (
                <div className="mt-7 flex flex-wrap items-center gap-3">{acciones}</div>
              ) : null}
            </div>

            {/* Columna destacada (opcional) */}
            {destacado ? (
              <div className="relative md:justify-self-end w-full max-w-md">{destacado}</div>
            ) : null}
          </div>
        )}
      </div>

      {conGreca ? (
        <GrecaAndina
          color="accent"
          variante="escalonada"
          altura={4}
          className="opacity-40"
        />
      ) : null}
    </section>
  );
}

export default PublicHero;
