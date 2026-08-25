import { useEffect, useMemo, useState } from 'react';
import { Marker, Popup, Polyline, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { Link } from 'react-router-dom';
import { Camera, ChevronLeft, ChevronRight, ArrowRight, Wallet, Navigation } from 'lucide-react';
import WrapperMapa from '@/components/mapa/WrapperMapa';
import { Button } from '@/components/ui/button';
import { ZOOM_DEFAULT_MAPA_GENERAL } from './constants';
import { useFotosObra } from './media/hooks';
import { urlDescargaMedia } from './media/api';
import { etiquetaEtapaAvance } from './utils';
import { formatearMoneda } from '@/lib/formatters';
import type { ObraMapaItem } from './types';

interface MapaObrasProps {
  items: ObraMapaItem[];
  isLoading?: boolean;
  height?: string | number;
  onSeleccionarMarcador?: () => void;
}

// --- Estilos globales del marcador (inyectados una sola vez por módulo) ---
const MARKER_STYLES = `
  .leaflet-marker-icon.custom-leaflet-icon { background: none !important; border: none !important; }
  .mapa-marker-obra {
    position: relative;
    width: 44px;
    height: 54px;
    filter: drop-shadow(0 4px 6px rgba(15, 23, 42, 0.25));
    transition: transform .18s ease, filter .18s ease;
    transform-origin: 50% 100%;
    cursor: pointer;
  }
  .mapa-marker-obra:hover {
    transform: translateY(-2px) scale(1.08);
    filter: drop-shadow(0 8px 12px rgba(15, 23, 42, 0.35));
    z-index: 1000 !important;
  }
  .mapa-marker-obra.is-selected {
    transform: translateY(-3px) scale(1.12);
    filter:
      drop-shadow(0 0 0 rgba(255,255,255,1))
      drop-shadow(0 10px 16px rgba(15, 23, 42, 0.38));
  }
  .mapa-marker-obra.is-selected::before {
    content: "";
    position: absolute;
    left: 50%;
    bottom: -1px;
    width: 18px;
    height: 8px;
    border-radius: 999px;
    border: 2px solid white;
    background: color-mix(in srgb, var(--primary) 70%, transparent);
    transform: translateX(-50%);
    box-shadow: 0 0 0 5px color-mix(in srgb, var(--primary) 18%, transparent);
  }
  .mapa-marker-obra .marker-inner-icon {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 8px;
    color: white;
    pointer-events: none;
  }
  .mapa-marker-obra .marker-inner-icon svg { width: 18px; height: 18px; }
  .mapa-marker-obra .marker-pct {
    position: absolute;
    top: -6px;
    right: -6px;
    background: white;
    color: var(--foreground);
    border: 1.5px solid var(--border);
    border-radius: 999px;
    font-size: 9.5px;
    font-weight: 700;
    padding: 1px 5px;
    line-height: 1.2;
    font-family: ui-sans-serif, system-ui, sans-serif;
    box-shadow: 0 1px 2px rgba(0,0,0,.12);
    letter-spacing: -0.02em;
  }
  /* Popup — compacto, sin saltos ni placeholders vacíos */
  .leaflet-popup.mapa-popup-obra .leaflet-popup-content-wrapper {
    border-radius: 12px;
    padding: 0;
    box-shadow: 0 10px 30px rgba(15,23,42,.18), 0 2px 6px rgba(15,23,42,.08);
    overflow: hidden;
  }
  .leaflet-popup.mapa-popup-obra .leaflet-popup-content {
    margin: 10px;
    line-height: 1.35;
    max-height: min(420px, 70vh);
    overflow-y: auto;
  }
  .leaflet-popup.mapa-popup-obra .leaflet-popup-tip {
    box-shadow: 0 2px 6px rgba(15,23,42,.12);
  }
  .leaflet-popup.mapa-popup-obra .leaflet-popup-close-button {
    top: 6px;
    right: 6px;
    z-index: 2;
    color: var(--muted-foreground);
    font-size: 18px;
    padding: 2px 6px;
  }
  .mapa-marker-obra .marker-spread-dot {
    position: absolute;
    left: 50%;
    bottom: -9px;
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: white;
    border: 2px solid color-mix(in srgb, var(--primary) 72%, transparent);
    transform: translateX(-50%);
    box-shadow: 0 1px 4px rgba(15,23,42,.25);
  }
  .mapa-marker-obra.is-spread::after {
    content: "";
    position: absolute;
    left: 50%;
    bottom: -18px;
    width: 1.5px;
    height: 14px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--primary) 42%, transparent);
    transform: translateX(-50%);
  }
  /* Cluster: varias obras en el mismo punto → un solo bubble */
  .mapa-cluster-obra {
    width: var(--cluster-size, 44px);
    height: var(--cluster-size, 44px);
    border-radius: 999px;
    background: var(--cluster-bg, var(--primary));
    border: 3px solid #fff;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.28);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-family: ui-sans-serif, system-ui, sans-serif;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    user-select: none;
  }
  .mapa-cluster-obra:hover {
    transform: scale(1.08);
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.34);
  }
  .mapa-cluster-obra__count {
    font-size: 15px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.02em;
  }
  .mapa-cluster-obra__label {
    font-size: 8px;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    opacity: 0.92;
    line-height: 1;
    margin-top: 2px;
  }
  .leaflet-tooltip.mapa-tooltip-obra {
    width: 220px;
    max-width: min(220px, calc(100vw - 48px));
    white-space: normal;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--card);
    color: var(--foreground);
    box-shadow: 0 8px 20px rgba(15,23,42,.16), 0 2px 5px rgba(15,23,42,.08);
    padding: 8px 10px;
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.25;
    text-align: left;
    pointer-events: none;
  }
  .leaflet-tooltip.mapa-tooltip-obra .mapa-tooltip-obra__texto {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    overflow: hidden;
  }
  .leaflet-tooltip-top.mapa-tooltip-obra::before {
    border-top-color: var(--card);
  }
`;

if (typeof document !== 'undefined' && !document.getElementById('mapa-obras-styles')) {
  const style = document.createElement('style');
  style.id = 'mapa-obras-styles';
  style.textContent = MARKER_STYLES;
  document.head.appendChild(style);
}

// --- Utilidades visuales del pin ---

/**
 * Interpola color del pin entre dos tonos primarios (claro → oscuro).
 * Sin rojos ni amarillos: solo intensidad. Avance nulo = neutro (slate).
 */
function obtenerNombreTooltip(nombre: string | null | undefined): string {
  const texto = nombre?.trim();
  if (!texto) return 'Obra sin nombre registrado';

  const limite = 72;
  if (texto.length <= limite) return texto;

  const recorte = texto.slice(0, limite).trimEnd();
  const ultimoEspacio = recorte.lastIndexOf(' ');
  const base = ultimoEspacio >= 42 ? recorte.slice(0, ultimoEspacio) : recorte;

  return `${base.trimEnd()}...`;
}

interface CategoriaPin {
  id: string;
  etiqueta: string;
  color: string;
  patrones: RegExp[];
}

const CATEGORIAS_PIN: CategoriaPin[] = [
  {
    id: 'transporte',
    etiqueta: 'Transporte',
    color: '#1d4ed8',
    patrones: [/transporte|vial|v[ií]a|pista|calle|puente|carret|transitabilidad/],
  },
  {
    id: 'saneamiento',
    etiqueta: 'Agua',
    color: '#0ea5e9',
    patrones: [/saneamiento|agua|desag|alcantar|drenaje|potable|canaliz/],
  },
  {
    id: 'educacion',
    etiqueta: 'Educación',
    color: '#7e22ce',
    patrones: [/educaci|escolar|escuela|colegio|instituci[oó]n educativa|i\.e\./],
  },
  {
    id: 'salud',
    etiqueta: 'Salud',
    color: '#e11d48',
    patrones: [/salud|hospital|posta|m[eé]dic|centro de salud/],
  },
  {
    id: 'recreacion',
    etiqueta: 'Recreación',
    color: '#f97316',
    patrones: [/deporte|recre|parque|plaza|estadio|losa/],
  },
  {
    id: 'ambiente',
    etiqueta: 'Ambiente',
    color: '#16a34a',
    patrones: [/ambient|residuo|ecol|forestal|limpieza/],
  },
  {
    id: 'agropecuaria',
    etiqueta: 'Riego rural',
    color: '#a16207',
    patrones: [/agr[ií]|riego|pecuari|rural/],
  },
  {
    id: 'seguridad',
    etiqueta: 'Seguridad',
    color: '#111827',
    patrones: [/seguridad|orden|serenaz|polic/],
  },
  {
    id: 'cultura',
    etiqueta: 'Cultura',
    color: '#db2777',
    patrones: [/cultura|patrimonio|turism/],
  },
];

const CATEGORIA_PIN_DEFAULT: CategoriaPin = {
  id: 'otros',
  etiqueta: 'Otros',
  color: '#64748b',
  patrones: [],
};

const CATEGORIAS_LEYENDA_PIN = [...CATEGORIAS_PIN, CATEGORIA_PIN_DEFAULT];

function categoriaPinPorObra(obra: ObraMapaItem): CategoriaPin {
  const key = `${obra.funcion ?? ''} ${obra.nombre_inversion ?? ''}`.toLowerCase();
  return CATEGORIAS_PIN.find((categoria) =>
    categoria.patrones.some((patron) => patron.test(key)),
  ) ?? CATEGORIA_PIN_DEFAULT;
}

/**
 * Devuelve un path SVG (viewBox 24x24) con un ícono representativo del sector.
 */
function iconoSectorSvg(funcion: string | null | undefined): string {
  const key = (funcion ?? '').toLowerCase();
  if (/educaci|escolar|escuela|colegio/.test(key)) {
    // Graduation cap
    return '<path d="M22 10L12 5 2 10l10 5 10-5zM6 12v5c0 1 3 3 6 3s6-2 6-3v-5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>';
  }
  if (/salud|hospital|posta|m[eé]dic/.test(key)) {
    return '<path d="M12 3v18M3 12h18" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>';
  }
  if (/transporte|vial|v[ií]a|pista|calle|puente|carret/.test(key)) {
    // Road
    return '<path d="M4 21l4-18M20 21l-4-18M12 4v3M12 11v3M12 18v3" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>';
  }
  if (/saneamiento|agua|desag|alcantar/.test(key)) {
    // Droplet
    return '<path d="M12 2s6 7 6 12a6 6 0 11-12 0c0-5 6-12 6-12z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/deporte|recre|parque|plaza|estadio/.test(key)) {
    // Tree/park
    return '<circle cx="12" cy="9" r="6" stroke="currentColor" stroke-width="2" fill="none"/><path d="M12 15v6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>';
  }
  if (/cultura|patrimonio|turism/.test(key)) {
    // Landmark/museum
    return '<path d="M3 21h18M4 21V9m4 12V9m4 12V9m4 12V9m4 12V9M12 3l9 6H3l9-6z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/seguridad|orden|serenaz|polic/.test(key)) {
    // Shield
    return '<path d="M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6l8-3z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/ambient|residuo|ecol/.test(key)) {
    // Leaf
    return '<path d="M4 20c8-2 14-8 16-16-8 0-14 6-16 14v2z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round"/>';
  }
  if (/agr[ií]|riego|pecuari|rural/.test(key)) {
    // Wheat / sprout
    return '<path d="M12 22V11M8 15c0-3 4-4 4-4s4 1 4 4M6 10c0-3 6-5 6-5s6 2 6 5" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>';
  }
  // Default: building
  return '<path d="M4 21V6l8-3 8 3v15M9 21V12h6v9M4 21h16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>';
}

/**
 * Construye el HTML del marcador tipo pin: el color identifica el tipo
 * de proyecto y el número conserva el avance físico.
 */
function crearIconoPin(obra: ObraMapaItem, seleccionado = false, separado = false): L.DivIcon {
  const avance =
    obra.avance_fisico != null ? Math.min(100, Math.max(0, Number(obra.avance_fisico))) : null;
  const color = categoriaPinPorObra(obra).color;
  const iconoSector = iconoSectorSvg(`${obra.funcion ?? ''} ${obra.nombre_inversion ?? ''}`);

  // Trazamos el pin con su color de categoría y dejamos el avance como aro blanco.
  // Path del contorno del pin (mismo path, viewBox 44x54).
  // Longitud aproximada del path para stroke-dasharray dinámico.
  const pathPin =
    'M22 2 C10 2 3 10.5 3 20.5 C3 33 22 51 22 51 C22 51 41 33 41 20.5 C41 10.5 34 2 22 2 Z';
  const perimetro = 138; // longitud aproximada del path
  const dashLen = avance != null ? (perimetro * avance) / 100 : 0;
  const dashGap = perimetro - dashLen;
  const badgePct = avance != null ? `<span class="marker-pct">${avance.toFixed(0)}%</span>` : '';

  return L.divIcon({
    html: `
      <div class="mapa-marker-obra${seleccionado ? ' is-selected' : ''}${separado ? ' is-spread' : ''}" role="button" tabindex="-1">
        <svg viewBox="0 0 44 54" width="44" height="54" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <defs>
            <linearGradient id="glow-${obra.codigo_unico}" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stop-color="${color}" stop-opacity="1"/>
              <stop offset="100%" stop-color="${color}" stop-opacity="0.85"/>
            </linearGradient>
          </defs>
          <!-- Sombra base clara del pin -->
          <path d="${pathPin}" fill="url(#glow-${obra.codigo_unico})" stroke="white" stroke-width="2"/>
          <!-- Aro de progreso: recorre el contorno del pin -->
          ${
            avance != null
              ? `<path d="${pathPin}" fill="none" stroke="white" stroke-width="2.5"
                   stroke-dasharray="${dashLen} ${dashGap}"
                   stroke-dashoffset="0"
                   stroke-linecap="round" opacity="0.95"/>`
              : ''
          }
        </svg>
        <div class="marker-inner-icon">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            ${iconoSector}
          </svg>
        </div>
        ${badgePct}
        ${separado ? '<span class="marker-spread-dot" aria-hidden="true"></span>' : ''}
      </div>
    `,
    className: 'custom-leaflet-icon',
    iconSize: [44, 54],
    iconAnchor: [22, 52],
    popupAnchor: [0, -46],
  });
}

interface MarcadorObraVista {
  tipo: 'obra';
  obra: ObraMapaItem;
  icon: L.DivIcon;
  position: L.LatLngExpression;
  posicionReal: L.LatLngExpression;
  separado: boolean;
  zIndexOffset: number;
}

interface MarcadorClusterVista {
  tipo: 'cluster';
  id: string;
  count: number;
  position: L.LatLngExpression;
  icon: L.DivIcon;
  obras: ObraMapaItem[];
}

type VistaMarcador = MarcadorObraVista | MarcadorClusterVista;

interface ClusterTemporal {
  indices: number[];
  centro: L.Point;
}

/** Distancia en px para considerar obras "en el mismo sitio". */
const DISTANCIA_COLISION_PX = 48;

function idDeCluster(obras: ObraMapaItem[]): string {
  return obras
    .map((o) => o.codigo_unico)
    .sort()
    .join('|');
}

function fondoClusterPorObras(obras: ObraMapaItem[]): string {
  const colores = Array.from(new Set(obras.map((obra) => categoriaPinPorObra(obra).color)));

  if (colores.length === 0) return 'var(--primary)';
  if (colores.length === 1) return colores[0]!;

  const visibles = colores.slice(0, 5);
  const paso = 100 / visibles.length;
  return `conic-gradient(${visibles
    .map((color, index) => `${color} ${index * paso}% ${(index + 1) * paso}%`)
    .join(', ')})`;
}

function crearIconoCluster(count: number, obras: ObraMapaItem[]): L.DivIcon {
  const size = count >= 10 ? 52 : count >= 5 ? 46 : 42;
  const fondo = fondoClusterPorObras(obras);
  return L.divIcon({
    html: `
      <div class="mapa-cluster-obra" style="--cluster-size:${size}px;--cluster-bg:${fondo}" role="button" tabindex="-1"
           aria-label="${count} obras en esta zona. Clic para separarlas.">
        <span class="mapa-cluster-obra__count">${count}</span>
        <span class="mapa-cluster-obra__label">obras</span>
      </div>
    `,
    className: 'custom-leaflet-icon',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/** Radio de spiderfy generoso: al expandir, los pines no deben solaparse. */
function obtenerOffsetMarcador(index: number, total: number): [number, number] {
  if (total <= 1) return [0, 0];

  const radio =
    total <= 2 ? 42 :
      total <= 4 ? 56 :
        total <= 7 ? 72 :
          total <= 10 ? 88 :
            100;
  const anguloInicial = total === 2 ? Math.PI : -Math.PI / 2;
  const angulo = anguloInicial + (index * 2 * Math.PI) / total;

  return [
    Math.round(Math.cos(angulo) * radio),
    Math.round(Math.sin(angulo) * radio),
  ];
}

function agruparPorProximidad(
  items: ObraMapaItem[],
  map: L.Map,
): { puntos: { obra: ObraMapaItem; latLng: L.LatLng; punto: L.Point }[]; clusters: ClusterTemporal[] } {
  const puntos = items.map((obra) => {
    const latLng = L.latLng(obra.latitud!, obra.longitud!);
    return {
      obra,
      latLng,
      punto: map.latLngToLayerPoint(latLng),
    };
  });

  const clusters: ClusterTemporal[] = [];

  puntos.forEach((item, index) => {
    const cluster = clusters.find((c) => c.centro.distanceTo(item.punto) < DISTANCIA_COLISION_PX);

    if (!cluster) {
      clusters.push({
        indices: [index],
        centro: item.punto,
      });
      return;
    }

    cluster.indices.push(index);
    const total = cluster.indices.length;
    cluster.centro = L.point(
      (cluster.centro.x * (total - 1) + item.punto.x) / total,
      (cluster.centro.y * (total - 1) + item.punto.y) / total,
    );
  });

  return { puntos, clusters };
}

/**
 * Si varias obras caen cerca: un bubble con el conteo.
 * Solo al expandir (clic) se spiderfían en círculo con líneas al punto real.
 */
function calcularVistasMarcadores(
  items: ObraMapaItem[],
  map: L.Map,
  codigoSeleccionado: string | null,
  clusterExpandidoId: string | null,
): VistaMarcador[] {
  const { puntos, clusters } = agruparPorProximidad(items, map);
  const vistas: VistaMarcador[] = [];

  clusters.forEach((cluster) => {
    const obrasGrupo = cluster.indices.map((i) => puntos[i]!.obra);
    const id = idDeCluster(obrasGrupo);

    if (cluster.indices.length === 1) {
      const item = puntos[cluster.indices[0]!]!;
      const seleccionado = item.obra.codigo_unico === codigoSeleccionado;
      vistas.push({
        tipo: 'obra',
        obra: item.obra,
        icon: crearIconoPin(item.obra, seleccionado, false),
        position: item.latLng,
        posicionReal: item.latLng,
        separado: false,
        zIndexOffset: seleccionado ? 1200 : 0,
      });
      return;
    }

    const expandido = clusterExpandidoId === id;

    if (!expandido) {
      vistas.push({
        tipo: 'cluster',
        id,
        count: obrasGrupo.length,
        position: map.layerPointToLatLng(cluster.centro),
        icon: crearIconoCluster(obrasGrupo.length, obrasGrupo),
        obras: obrasGrupo,
      });
      return;
    }

    cluster.indices.forEach((itemIndex, indexEnGrupo) => {
      const item = puntos[itemIndex]!;
      const offset = obtenerOffsetMarcador(indexEnGrupo, cluster.indices.length);
      const puntoSeparado = cluster.centro.add(L.point(offset[0], offset[1]));
      const position = map.layerPointToLatLng(puntoSeparado);
      const seleccionado = item.obra.codigo_unico === codigoSeleccionado;

      vistas.push({
        tipo: 'obra',
        obra: item.obra,
        icon: crearIconoPin(item.obra, seleccionado, true),
        position,
        posicionReal: item.latLng,
        separado: true,
        zIndexOffset: seleccionado ? 1200 : 800 + indexEnGrupo,
      });
    });
  });

  return vistas;
}

type PopupConMapa = L.Popup & { _map?: L.Map };

function ajustarPopupAlAbrir(event: L.LeafletEvent) {
  const popup = event.target as L.Popup;
  window.setTimeout(() => {
    popup.update();

    const map = (popup as PopupConMapa)._map;
    const popupEl = popup.getElement();
    const mapEl = map?.getContainer();
    if (!map || !popupEl || !mapEl) return;

    const popupRect = popupEl.getBoundingClientRect();
    const mapRect = mapEl.getBoundingClientRect();
    const latLng = popup.getLatLng();
    if (!latLng) return;

    const marcador = map.latLngToContainerPoint(latLng);
    const marcadorRect = {
      left: mapRect.left + marcador.x - 28,
      right: mapRect.left + marcador.x + 28,
      top: mapRect.top + marcador.y - 66,
      bottom: mapRect.top + marcador.y + 10,
    };
    const margen = 18;
    const margenInferior = 24;
    const umbralMovimiento = 18;
    const areaVisible = {
      left: Math.min(popupRect.left, marcadorRect.left),
      right: Math.max(popupRect.right, marcadorRect.right),
      top: Math.min(popupRect.top, marcadorRect.top),
      bottom: Math.max(popupRect.bottom, marcadorRect.bottom),
    };

    let dx = 0;
    let dy = 0;

    if (areaVisible.left < mapRect.left + margen) {
      dx = areaVisible.left - mapRect.left - margen;
    } else if (areaVisible.right > mapRect.right - margen) {
      dx = areaVisible.right - mapRect.right + margen;
    }

    if (areaVisible.top < mapRect.top + margen) {
      dy = areaVisible.top - mapRect.top - margen;
    } else if (areaVisible.bottom > mapRect.bottom - margenInferior) {
      dy = areaVisible.bottom - mapRect.bottom + margenInferior;
    }

    const distancia = Math.hypot(dx, dy);
    if (distancia > umbralMovimiento) {
      map.stop();
      map.panBy([dx, dy], {
        animate: distancia > 90,
        duration: 0.18,
        easeLinearity: 0.75,
      });
    }
  }, 80);
}

export default function MapaObras({
  items,
  isLoading = false,
  height = '100%',
  onSeleccionarMarcador,
}: MapaObrasProps) {
  const [codigoSeleccionado, setCodigoSeleccionado] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div
        className="flex h-full w-full items-center justify-center rounded-2xl border border-border bg-gradient-to-br from-muted/45 to-primary/10 text-sm text-muted-foreground"
        style={{ height }}
      >
        Cargando mapa…
      </div>
    );
  }

  return (
    <div className="relative h-full w-full overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-card via-card to-primary/5 shadow-lg ring-1 ring-black/5">
      <WrapperMapa
        height={height}
        zoom={ZOOM_DEFAULT_MAPA_GENERAL}
        estilo="voyager"
        scrollWheelZoom
      >
        <MarcadoresObras
          items={items}
          codigoSeleccionado={codigoSeleccionado}
          onSeleccionar={(obra) => {
            setCodigoSeleccionado(obra.codigo_unico);
            onSeleccionarMarcador?.();
          }}
          onCerrar={() => setCodigoSeleccionado(null)}
        />
      </WrapperMapa>

      {/* Leyenda flotante — color = tipo de proyecto */}
      <div className="pointer-events-none absolute bottom-4 left-4 z-[500] w-[300px] max-w-[calc(100%-2rem)] rounded-xl border border-border bg-card/95 px-3 py-2.5 shadow-md backdrop-blur">
        <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          Tipo de proyecto
        </p>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
          {CATEGORIAS_LEYENDA_PIN.map((categoria) => (
            <span
              key={categoria.id}
              className="flex min-w-0 items-center gap-1.5 text-[10px] font-medium text-muted-foreground"
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-white"
                style={{ backgroundColor: categoria.color }}
                aria-hidden="true"
              />
              <span className="truncate">{categoria.etiqueta}</span>
            </span>
          ))}
        </div>
        <p className="mt-2 text-[10px] leading-tight text-muted-foreground">
          El número muestra el avance físico. Los grupos reúnen obras cercanas.
        </p>
      </div>
    </div>
  );
}

interface MarcadoresObrasProps {
  items: ObraMapaItem[];
  codigoSeleccionado: string | null;
  onSeleccionar: (obra: ObraMapaItem) => void;
  onCerrar: () => void;
}

function MarcadoresObras({
  items,
  codigoSeleccionado,
  onSeleccionar,
  onCerrar,
}: MarcadoresObrasProps) {
  const map = useMap();
  const [revisionMapa, setRevisionMapa] = useState(0);
  const [clusterExpandidoId, setClusterExpandidoId] = useState<string | null>(null);

  useMapEvents({
    zoomend: () => {
      setClusterExpandidoId(null);
      setRevisionMapa((v) => v + 1);
    },
    moveend: () => setRevisionMapa((v) => v + 1),
    click: () => setClusterExpandidoId(null),
  });

  const vistas = useMemo(
    () => {
      void revisionMapa;
      return calcularVistasMarcadores(items, map, codigoSeleccionado, clusterExpandidoId);
    },
    [items, map, codigoSeleccionado, clusterExpandidoId, revisionMapa],
  );

  // Si el grupo expandido ya no aplica (filtro / zoom), limpiar.
  useEffect(() => {
    if (!clusterExpandidoId) return;
    const haySpiderfy = vistas.some((v) => v.tipo === 'obra' && v.separado);
    const hayCluster = vistas.some(
      (v) => v.tipo === 'cluster' && v.id === clusterExpandidoId,
    );
    if (!haySpiderfy && !hayCluster) setClusterExpandidoId(null);
  }, [vistas, clusterExpandidoId]);

  const obrasSeparadas = vistas.filter(
    (v): v is MarcadorObraVista => v.tipo === 'obra' && v.separado,
  );

  return (
    <>
      {obrasSeparadas.map(({ obra, position, posicionReal }) => (
        <Polyline
          key={`linea-${obra.codigo_unico}`}
          positions={[posicionReal, position]}
          pathOptions={{
            color: 'var(--primary)',
            opacity: 0.35,
            weight: 1.5,
            dashArray: '3 5',
          }}
          interactive={false}
        />
      ))}

      {vistas.map((vista) => {
        if (vista.tipo === 'cluster') {
          return (
            <Marker
              key={`cluster-${vista.id}`}
              position={vista.position}
              icon={vista.icon}
              zIndexOffset={900}
              eventHandlers={{
                click: (e) => {
                  L.DomEvent.stopPropagation(e);
                  setClusterExpandidoId(vista.id);
                },
              }}
            >
              <Tooltip
                className="mapa-tooltip-obra"
                direction="top"
                offset={[0, -28]}
                opacity={1}
              >
                <span className="mapa-tooltip-obra__texto">
                  {vista.count} obras en esta zona — clic para verlas
                </span>
              </Tooltip>
            </Marker>
          );
        }

        const { obra, icon, position, zIndexOffset } = vista;
        return (
          <Marker
            key={obra.codigo_unico}
            position={position}
            icon={icon}
            zIndexOffset={zIndexOffset}
            eventHandlers={{
              popupopen: () => onSeleccionar(obra),
              popupclose: onCerrar,
              click: (e) => L.DomEvent.stopPropagation(e),
            }}
          >
            <Tooltip
              className="mapa-tooltip-obra"
              direction="top"
              offset={[0, -56]}
              opacity={1}
            >
              <span className="mapa-tooltip-obra__texto">
                {obtenerNombreTooltip(obra.nombre_inversion)}
              </span>
            </Tooltip>
            <Popup
              maxWidth={300}
              minWidth={260}
              className="mapa-popup-obra"
              autoPan={false}
              eventHandlers={{
                add: ajustarPopupAlAbrir,
              }}
              closeButton
            >
              <PopupContenido obra={obra} />
            </Popup>
          </Marker>
        );
      })}
    </>
  );
}

// --- Popup enriquecido ---

function PopupContenido({ obra }: { obra: ObraMapaItem }) {
  const map = useMap();
  const { data: fotos } = useFotosObra(obra.codigo_unico);
  const [idxFoto, setIdxFoto] = useState(0);

  const fotosDisponibles = fotos && fotos.length > 0 ? fotos.slice(0, 5) : [];
  const fotoActual = fotosDisponibles[idxFoto];
  const totalFotos = fotosDisponibles.length;
  const tieneFotos = totalFotos > 0;

  const etapa = etiquetaEtapaAvance(obra.avance_fisico);
  const monto = obra.pim_anio_actual != null ? Number(obra.pim_anio_actual) : null;
  const tieneAvance = obra.avance_fisico != null;

  const urlNavegacion =
    obra.latitud != null && obra.longitud != null
      ? `https://www.google.com/maps/dir/?api=1&destination=${obra.latitud},${obra.longitud}`
      : null;

  // Recalcular tamaño del popup cuando llegan fotos (sin reservar placeholder vacío).
  useEffect(() => {
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker && layer.isPopupOpen()) {
        layer.getPopup()?.update();
      }
    });
  }, [map, tieneFotos, idxFoto]);

  return (
    <div className="w-[276px] font-sans">
      {/* Carrusel solo con fotos reales — sin skeleton azul si no hay imagen */}
      {tieneFotos && fotoActual ? (
        <div className="relative -mx-2.5 -mt-2.5 mb-2 overflow-hidden bg-muted">
          <div className="aspect-[2/1] w-full max-h-[120px]">
            <img
              src={urlDescargaMedia(fotoActual.ruta_relativa)}
              alt={fotoActual.nombre_original}
              className="h-full w-full object-cover"
              loading="lazy"
            />
          </div>

          {totalFotos > 1 ? (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIdxFoto((idx) => (idx - 1 + totalFotos) % totalFotos);
                }}
                className="absolute left-1.5 top-1/2 -translate-y-1/2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black/40 text-white transition hover:bg-black/60"
                aria-label="Foto anterior"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIdxFoto((idx) => (idx + 1) % totalFotos);
                }}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black/40 text-white transition hover:bg-black/60"
                aria-label="Foto siguiente"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
              <div className="absolute bottom-1.5 left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-full bg-black/50 px-1.5 py-0.5 text-[10px] font-medium text-white">
                <Camera className="h-3 w-3" aria-hidden="true" />
                <span>
                  {idxFoto + 1} / {totalFotos}
                </span>
              </div>
            </>
          ) : null}
        </div>
      ) : null}

      <div className="px-0.5 pb-0.5">
        <span className="font-mono text-[10px] tracking-tight text-muted-foreground">
          {obra.codigo_unico}
        </span>
        <h4 className="mt-0.5 line-clamp-3 break-words text-[13px] font-semibold leading-snug text-foreground">
          {obra.nombre_inversion ?? 'Obra sin nombre registrado'}
        </h4>

        {obra.funcion ? (
          <p className="mt-0.5 line-clamp-1 text-[11px] text-muted-foreground">{obra.funcion}</p>
        ) : null}

        {tieneAvance ? (
          <div className="mt-2 rounded-md border border-border bg-muted/40 px-2 py-1.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {etapa.titulo}
              </span>
              <span className="text-[11px] font-bold tabular-nums text-foreground">
                {Number(obra.avance_fisico).toFixed(0)}%
              </span>
            </div>
            <div
              className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted"
              aria-hidden="true"
            >
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(100, Math.max(0, Number(obra.avance_fisico)))}%` }}
              />
            </div>
          </div>
        ) : (
          <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
            Avance físico aún no reportado
          </p>
        )}

        <div className="mt-2 grid grid-cols-2 gap-1.5">
          <div className="rounded-md border border-border px-2 py-1.5">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Wallet className="h-3 w-3" aria-hidden="true" />
              <span className="text-[9px] font-semibold uppercase tracking-wide">
                Presupuesto
              </span>
            </div>
            <p className="mt-0.5 text-[12px] font-bold tabular-nums text-foreground">
              {monto != null ? formatearMoneda(monto, true) : 'Sin dato'}
            </p>
          </div>

          <div className="rounded-md border border-border px-2 py-1.5">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Navigation className="h-3 w-3" aria-hidden="true" />
              <span className="text-[9px] font-semibold uppercase tracking-wide">
                Ubicación
              </span>
            </div>
            {urlNavegacion ? (
              <a
                href={urlNavegacion}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-0.5 inline-flex items-center gap-0.5 text-[11.5px] font-semibold text-primary hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                Cómo llegar
                <ArrowRight className="h-3 w-3" aria-hidden="true" />
              </a>
            ) : (
              <p className="mt-0.5 text-[11px] text-muted-foreground">No disponible</p>
            )}
          </div>
        </div>

        <Button
          asChild
          size="sm"
          variant="outline"
          className="mt-2 h-8 w-full border-primary/40 text-primary hover:bg-primary hover:text-primary-foreground"
        >
          <Link to={`/obras/${obra.codigo_unico}`}>
            Ver ficha completa
            <ArrowRight className="ml-1 h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </Button>
      </div>
    </div>
  );
}
