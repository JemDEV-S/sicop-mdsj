// Helpers puros del detalle SIAF por fase (Formato A). Separados de los
// componentes para que el módulo de UI exporte solo componentes (fast refresh).

import type { DetalleExpedienteSiaf } from '@/features/pipeline/types';
import { selloDetalleSiaf } from '@/features/pipeline/siaf-cobertura';

// Fases del ciclo de gasto en orden, con su color de barra. Solo se muestran
// las que el Formato A trae para el expediente (no se inventan las faltantes).
//
// Los colores CODIFICAN la fase por PASOS DE LUMINOSIDAD (no por opacidad, que
// da contraste bajo sobre bg-muted en modo claro): azul = fase presupuestal
// (Certificado), verde = ejecución en caja aclarándose de Devengado a Pagado
// usando la escala --chart-* ya validada para daltonismo en globals.css.
export const FASES_ORDEN: { cod: string; label: string; barraClass: string }[] = [
  { cod: 'C', label: 'Certificado', barraClass: 'bg-primary' },
  { cod: 'D', label: 'Devengado', barraClass: 'bg-secondary' },
  { cod: 'G', label: 'Girado', barraClass: 'bg-chart-2' },
  { cod: 'P', label: 'Pagado', barraClass: 'bg-chart-5' },
  { cod: 'R', label: 'Regularización', barraClass: 'bg-chart-4' },
];

/** Fase neta por código, en orden de ciclo (solo las presentes). */
export function ordenarFases(detalle: DetalleExpedienteSiaf | null | undefined) {
  const fases = detalle?.fases ?? [];
  const porCod = new Map(fases.map((f) => [f.fase, f]));
  const presentes = FASES_ORDEN.filter((f) => porCod.has(f.cod));
  return { fases, porCod, presentes };
}

/** Proveedor dominante del expediente (el primero que lo trae en cualquier fase). */
export function proveedorDeExpediente(detalle: DetalleExpedienteSiaf | null | undefined) {
  const fases = detalle?.fases ?? [];
  return {
    nombre: fases.find((f) => f.proveedor_nombre)?.proveedor_nombre ?? null,
    ruc: fases.find((f) => f.proveedor_ruc)?.proveedor_ruc ?? null,
  };
}

/** Sello "Detalle SIAF · carga provisional · meses cargados: …" del detalle. */
export function selloDeDetalle(detalle: DetalleExpedienteSiaf | null | undefined): string {
  return selloDetalleSiaf(detalle?.meses_cargados ?? []);
}
