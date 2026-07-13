import { useState } from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import { Link } from 'react-router-dom';
import { AlertCircle, MapPin, Filter } from 'lucide-react';
import WrapperMapa from '@/components/mapa/WrapperMapa';
import { SectionCard } from '@/components/layout/SectionCard';
import { ErrorState } from '@/components/layout/ErrorState';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { useObrasMapa } from './hooks';
import { ZOOM_DEFAULT_MAPA_GENERAL } from './constants';
import { semaforoToIconClass } from './utils';

const ANO_TODOS = 'todos';

const createCustomIcon = (semaforo: string) => {
  const cssClass = semaforoToIconClass(semaforo);
  const html = `
    <div class="relative flex h-6 w-6 items-center justify-center rounded-full ${cssClass} shadow-md border-2 border-white">
      <div class="h-2 w-2 rounded-full bg-white opacity-75"></div>
    </div>
  `;
  return L.divIcon({
    html,
    className: 'custom-leaflet-icon',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
};

export default function MapaObras() {
  const [filtros, setFiltros] = useState<{ ano: number | ''; funcion: string }>({
    ano: '',
    funcion: '',
  });
  const { data, isLoading, isError, refetch } = useObrasMapa(
    filtros.ano ? { ano: filtros.ano, funcion: filtros.funcion } : { funcion: filtros.funcion },
  );

  if (isError) {
    return (
      <ErrorState
        titulo="No se pudo cargar el mapa"
        descripcion="Ocurrió un error al consultar la ubicación de las obras."
        onReintentar={() => refetch()}
      />
    );
  }

  const itemsValidos =
    data?.items.filter(
      (obra) =>
        obra.latitud != null &&
        obra.longitud != null &&
        !(obra.latitud === 0 && obra.longitud === 0),
    ) ?? [];

  const itemsInvalidos =
    data?.items.filter(
      (obra) =>
        obra.latitud == null ||
        obra.longitud == null ||
        (obra.latitud === 0 && obra.longitud === 0),
    ) ?? [];

  const totalSinCoords = (data?.total_sin_coords ?? 0) + itemsInvalidos.length;
  const invalidosMapped = itemsInvalidos.map((obra) => ({
    codigo_unico: obra.codigo_unico,
    nombre_inversion: obra.nombre_inversion,
    funcion: obra.funcion,
    avance_fisico: obra.avance_fisico?.toString() ?? null,
    pim_anio_actual: obra.pim_anio_actual?.toString() ?? null,
  }));
  const todasSinCoords = [...(data?.sin_coordenadas ?? []), ...invalidosMapped];

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-14rem)] min-h-[600px]">
      {/* Panel lateral */}
      <div className="w-full lg:w-1/3 flex flex-col gap-4 min-h-0">
        <SectionCard titulo="Filtros" icono={Filter} padding="md">
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Año Fiscal
          </label>
          <Select
            value={filtros.ano ? String(filtros.ano) : ANO_TODOS}
            onValueChange={(val) =>
              setFiltros((prev) => ({
                ...prev,
                ano: val === ANO_TODOS ? '' : Number(val),
              }))
            }
          >
            <SelectTrigger aria-label="Filtrar por año">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANO_TODOS}>Todos los años</SelectItem>
              <SelectItem value="2026">2026</SelectItem>
              <SelectItem value="2025">2025</SelectItem>
              <SelectItem value="2024">2024</SelectItem>
            </SelectContent>
          </Select>
        </SectionCard>

        <SectionCard titulo="Leyenda" padding="md">
          <ul className="space-y-2 text-sm">
            <LeyendaItem color="bg-semaforo-ok" label="Avance ≥ 70% — al día" />
            <LeyendaItem color="bg-semaforo-alerta" label="Entre 40% y 70% — alerta" />
            <LeyendaItem color="bg-semaforo-critico" label="Menor a 40% — crítico" />
            <LeyendaItem color="bg-muted border border-border" label="Sin datos de avance" />
          </ul>
        </SectionCard>

        <SectionCard
          titulo={`En el mapa (${itemsValidos.length})`}
          icono={MapPin}
          padding="md"
          className="flex-1 min-h-0 flex flex-col"
          bodyClassName="flex-1 overflow-y-auto"
        >
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Cargando obras…</p>
          ) : totalSinCoords === 0 ? (
            <p className="text-sm text-muted-foreground">
              Todas las obras tienen ubicación válida.
            </p>
          ) : (
            <div>
              <div className="flex items-center gap-2 mb-3 text-xs text-muted-foreground">
                <AlertCircle className="w-4 h-4 text-[var(--semaforo-alerta)]" aria-hidden="true" />
                <span>Sin coordenadas registradas ({totalSinCoords})</span>
              </div>
              <ul className="space-y-3">
                {todasSinCoords.map((obra) => (
                  <li
                    key={obra.codigo_unico}
                    className="p-3 border border-border rounded-md bg-muted/30"
                  >
                    <div className="flex justify-between items-start mb-1 gap-2">
                      <span className="font-mono text-xs text-muted-foreground">
                        {obra.codigo_unico}
                      </span>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">
                        {obra.avance_fisico ? `${obra.avance_fisico}%` : 'S/D'}
                      </span>
                    </div>
                    <p
                      className="text-sm font-medium text-foreground line-clamp-2"
                      title={obra.nombre_inversion ?? ''}
                    >
                      {obra.nombre_inversion || 'Sin nombre'}
                    </p>
                    <Link
                      to={`/obras/${obra.codigo_unico}`}
                      className="text-xs text-primary hover:underline mt-2 inline-block"
                    >
                      Ver ficha →
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </SectionCard>
      </div>

      {/* Mapa principal */}
      <div className="w-full lg:w-2/3 h-full">
        {isLoading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground border border-border rounded-md">
            Cargando mapa…
          </div>
        ) : (
          <WrapperMapa height="100%" zoom={ZOOM_DEFAULT_MAPA_GENERAL}>
            {itemsValidos.map((obra) => (
              <Marker
                key={obra.codigo_unico}
                position={[obra.latitud!, obra.longitud!]}
                icon={createCustomIcon(obra.semaforo)}
              >
                <Popup>
                  <div className="max-w-[250px]">
                    <span className="font-mono text-xs text-muted-foreground">
                      {obra.codigo_unico}
                    </span>
                    <h4 className="font-semibold text-sm leading-tight mt-1 line-clamp-3 text-foreground">
                      {obra.nombre_inversion}
                    </h4>
                    <div className="flex items-center justify-between text-xs my-3 bg-muted/50 p-2 rounded">
                      <span className="text-muted-foreground">Avance físico:</span>
                      <span className="font-bold text-foreground">
                        {obra.avance_fisico != null ? `${obra.avance_fisico}%` : 'Sin datos'}
                      </span>
                    </div>
                    <Button asChild size="sm" className="w-full">
                      <Link to={`/obras/${obra.codigo_unico}`}>Ver ficha</Link>
                    </Button>
                  </div>
                </Popup>
              </Marker>
            ))}
          </WrapperMapa>
        )}
      </div>
    </div>
  );
}

function LeyendaItem({ color, label }: { color: string; label: string }) {
  return (
    <li className="flex items-center gap-2">
      <span className={`inline-block h-3 w-3 rounded-full ${color}`} aria-hidden="true" />
      <span className="text-muted-foreground">{label}</span>
    </li>
  );
}
