import { useState, useCallback, useEffect } from 'react';
import { Camera, X, ChevronLeft, ChevronRight, Image as ImageIcon } from 'lucide-react';
import { useFotosObra } from '../media/hooks';
import { urlDescargaMedia } from '../media/api';
import { cn } from '@/lib/utils';
import { formatFecha } from '@/lib/formatters';

interface GaleriaProps {
  codigoUnico: string;
}

export function Galeria({ codigoUnico }: GaleriaProps) {
  const { data: fotos, isLoading, isError } = useFotosObra(codigoUnico);
  const [seleccionada, setSeleccionada] = useState<number | null>(null);

  const cerrar = useCallback(() => setSeleccionada(null), []);
  const anterior = useCallback(() => {
    if (!fotos) return;
    setSeleccionada((idx) => (idx === null ? null : (idx - 1 + fotos.length) % fotos.length));
  }, [fotos]);
  const siguiente = useCallback(() => {
    if (!fotos) return;
    setSeleccionada((idx) => (idx === null ? null : (idx + 1) % fotos.length));
  }, [fotos]);

  useEffect(() => {
    if (seleccionada === null) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') cerrar();
      else if (e.key === 'ArrowLeft') anterior();
      else if (e.key === 'ArrowRight') siguiente();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [seleccionada, cerrar, anterior, siguiente]);

  // Loading
  if (isLoading) {
    return (
      <ContenedorGaleria total={0}>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="aspect-[4/3] bg-muted animate-pulse rounded-lg"
              aria-hidden="true"
            />
          ))}
        </div>
      </ContenedorGaleria>
    );
  }

  // Error o vacío: no rompemos la ficha, mostramos empty state discreto
  if (isError || !fotos || fotos.length === 0) {
    return (
      <ContenedorGaleria total={0}>
        <div className="rounded-xl border border-dashed border-border bg-muted/30 p-10 text-center">
          <ImageIcon
            className="w-8 h-8 text-muted-foreground mx-auto mb-3"
            aria-hidden="true"
          />
          <p className="text-sm font-medium text-foreground">
            {isError ? 'No se pudieron cargar las fotos' : 'Aún no hay fotos publicadas'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
            {isError
              ? 'Intenta recargar la página en unos minutos.'
              : 'La municipalidad publica el avance visual de las obras cuando está disponible.'}
          </p>
        </div>
      </ContenedorGaleria>
    );
  }

  return (
    <>
      <ContenedorGaleria total={fotos.length}>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {fotos.map((foto, idx) => (
            <button
              key={foto.id}
              type="button"
              onClick={() => setSeleccionada(idx)}
              className={cn(
                'group relative aspect-[4/3] overflow-hidden rounded-lg bg-muted border border-border',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
              )}
              aria-label={`Ver foto: ${foto.nombre_original}`}
            >
              <img
                src={urlDescargaMedia(foto.ruta_relativa)}
                alt={foto.nombre_original}
                loading="lazy"
                className="absolute inset-0 h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
              />
              <span
                className="absolute inset-0 bg-foreground/0 group-hover:bg-foreground/10 transition-colors"
                aria-hidden="true"
              />
              <span className="absolute bottom-0 left-0 right-0 px-2 py-1.5 bg-gradient-to-t from-foreground/70 to-transparent text-primary-foreground text-[10px] font-medium truncate opacity-0 group-hover:opacity-100 transition-opacity">
                {formatFecha(foto.subido_en)}
              </span>
            </button>
          ))}
        </div>
      </ContenedorGaleria>

      {/* Lightbox */}
      {seleccionada !== null ? (
        <div
          className="fixed inset-0 z-50 bg-foreground/85 backdrop-blur-sm flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Vista de foto ampliada"
          onClick={cerrar}
        >
          <button
            type="button"
            onClick={cerrar}
            className="absolute top-4 right-4 inline-flex items-center justify-center h-10 w-10 rounded-full bg-card/10 text-primary-foreground hover:bg-card/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
            aria-label="Cerrar"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>

          {fotos.length > 1 ? (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  anterior();
                }}
                className="absolute left-4 top-1/2 -translate-y-1/2 inline-flex items-center justify-center h-10 w-10 rounded-full bg-card/10 text-primary-foreground hover:bg-card/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
                aria-label="Foto anterior"
              >
                <ChevronLeft className="w-5 h-5" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  siguiente();
                }}
                className="absolute right-4 top-1/2 -translate-y-1/2 inline-flex items-center justify-center h-10 w-10 rounded-full bg-card/10 text-primary-foreground hover:bg-card/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground"
                aria-label="Foto siguiente"
              >
                <ChevronRight className="w-5 h-5" aria-hidden="true" />
              </button>
            </>
          ) : null}

          {(() => {
            const foto = fotos[seleccionada];
            if (!foto) return null;
            return (
              <div
                className="relative max-w-5xl w-full max-h-full flex flex-col items-center"
                onClick={(e) => e.stopPropagation()}
              >
                <img
                  src={urlDescargaMedia(foto.ruta_relativa)}
                  alt={foto.nombre_original}
                  className="max-h-[80vh] max-w-full object-contain rounded-lg"
                />
                <div className="mt-4 text-center text-primary-foreground">
                  <p className="text-sm font-medium">{foto.nombre_original}</p>
                  <p className="text-xs text-primary-foreground/70 mt-1">
                    {formatFecha(foto.subido_en)} · Foto {seleccionada + 1} de {fotos.length}
                  </p>
                </div>
              </div>
            );
          })()}
        </div>
      ) : null}
    </>
  );
}

interface ContenedorGaleriaProps {
  total: number;
  children: React.ReactNode;
}

function ContenedorGaleria({ total, children }: ContenedorGaleriaProps) {
  return (
    <div className="rounded-2xl bg-card border border-border overflow-hidden">
      <header className="flex items-center gap-2 px-6 py-4 border-b border-border bg-muted/40">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Camera className="w-4 h-4" aria-hidden="true" />
        </span>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-foreground">Fotos de la obra</h3>
          <p className="text-xs text-muted-foreground">
            Registro visual del avance publicado por la municipalidad
          </p>
        </div>
        {total > 0 ? (
          <span className="text-xs font-medium text-muted-foreground tabular-nums">
            {total} {total === 1 ? 'foto' : 'fotos'}
          </span>
        ) : null}
      </header>
      <div className="p-6">{children}</div>
    </div>
  );
}
