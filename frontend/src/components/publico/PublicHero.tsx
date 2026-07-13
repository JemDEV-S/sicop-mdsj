import * as React from 'react';
import { cn } from '@/lib/utils';
import { PiedraInca } from '@/components/decor/PiedraInca';
import { GrecaAndina } from '@/components/decor/GrecaAndina';

interface PublicHeroProps {
  eyebrow?: React.ReactNode;
  titulo: React.ReactNode;
  subtitulo?: React.ReactNode;
  acciones?: React.ReactNode;
  /** Contenido lateral opcional a la derecha (KPI destacado, ilustración, etc). */
  destacado?: React.ReactNode;
  /** Franja decorativa inferior. Default true. */
  conGreca?: boolean;
  /** Compacto = padding reducido para páginas internas de listado/detalle. */
  compacto?: boolean;
  className?: string;
}

/**
 * Hero canónico del portal público. Estructura asimétrica con muro inca
 * como enmarque decorativo en el borde derecho. Se usa en Home, ObrasListado,
 * EjecucionDashboard, DirectorioProveedores, Mapa y Obra.
 */
export function PublicHero({
  eyebrow,
  titulo,
  subtitulo,
  acciones,
  destacado,
  conGreca = true,
  compacto = false,
  className,
}: PublicHeroProps) {
  return (
    <section
      className={cn(
        'relative overflow-hidden bg-card border-b border-border',
        className,
      )}
    >
      {/* Muro inca — enmarque a la derecha, saliendo por el borde */}
      <div
        className="pointer-events-none absolute inset-y-0 right-0 w-[45%] hidden md:block"
        aria-hidden="true"
      >
        <PiedraInca
          color="primary"
          opacidad={0.07}
          className="absolute inset-0 h-full w-full"
        />
        {/* Gradiente suave para fundir el muro con el card (única "gradiente" tolerada:
            mask puro que va de bg-card a transparente, no color) */}
        <div
          className="absolute inset-0"
          style={{
            background:
              'linear-gradient(to right, var(--card) 0%, transparent 40%, transparent 100%)',
          }}
        />
      </div>

      <div
        className={cn(
          'relative mx-auto max-w-6xl px-4 md:px-6',
          compacto ? 'py-8 md:py-10' : 'py-12 md:py-20',
        )}
      >
        <div
          className={cn(
            'grid gap-10 items-center',
            destacado ? 'md:grid-cols-[1.4fr_1fr]' : 'md:grid-cols-1',
          )}
        >
          {/* Columna principal */}
          <div className="max-w-2xl">
            {eyebrow ? (
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
                {eyebrow}
              </div>
            ) : null}

            <h1
              className={cn(
                'font-bold text-foreground leading-[1.1] tracking-tight',
                compacto
                  ? 'text-2xl md:text-3xl'
                  : 'text-4xl md:text-5xl lg:text-6xl',
              )}
            >
              {titulo}
            </h1>

            {subtitulo ? (
              <div
                className={cn(
                  'mt-5 text-muted-foreground max-w-xl',
                  compacto ? 'text-sm md:text-base' : 'text-base md:text-lg',
                )}
              >
                {subtitulo}
              </div>
            ) : null}

            {acciones ? (
              <div className="mt-8 flex flex-col sm:flex-row gap-3">{acciones}</div>
            ) : null}
          </div>

          {/* Columna destacada (opcional) */}
          {destacado ? (
            <div className="relative md:justify-self-end w-full max-w-md">{destacado}</div>
          ) : null}
        </div>
      </div>

      {conGreca ? (
        <GrecaAndina
          color="accent"
          variante="escalonada"
          altura={6}
          className="opacity-70"
        />
      ) : null}
    </section>
  );
}

export default PublicHero;
