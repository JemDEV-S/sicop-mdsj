// Constantes compartidas de la vista profesional del pipeline.

import type { Macrofase } from '@/features/dashboard/types';
import type { CampoAgrupacion, CampoOrden } from './tipos';

/** Las 6 macrofases en orden de avance, con sigla y etiqueta. */
export const MACROFASES: { macrofase: Macrofase; sigla: string; label: string }[] = [
  { macrofase: 'solicitud', sigla: 'SOL', label: 'Solicitud' },
  { macrofase: 'programacion', sigla: 'PRO', label: 'Programación' },
  { macrofase: 'certificacion', sigla: 'CER', label: 'Certificación' },
  { macrofase: 'contratacion', sigla: 'CON', label: 'Contratación' },
  { macrofase: 'ejecucion', sigla: 'EJE', label: 'Ejecución' },
  { macrofase: 'cierre', sigla: 'CIE', label: 'Cierre' },
];

export const ORDEN_MACROFASE: Record<Macrofase, number> = {
  solicitud: 0,
  programacion: 1,
  certificacion: 2,
  contratacion: 3,
  ejecucion: 4,
  cierre: 5,
};

export const LABEL_MACROFASE: Record<Macrofase, string> = Object.fromEntries(
  MACROFASES.map((m) => [m.macrofase, m.label]),
) as Record<Macrofase, string>;

/** Opciones del selector "Agrupar por". */
export const OPCIONES_AGRUPACION: { valor: CampoAgrupacion; label: string }[] = [
  { valor: 'macrofase', label: 'Fase del pipeline' },
  { valor: 'centro_costo', label: 'Centro de costo' },
  { valor: 'meta', label: 'Meta' },
  { valor: 'estado', label: 'Estado (estancado / en curso)' },
  { valor: 'ninguno', label: 'Sin agrupar (lista plana)' },
];

/** Opciones del selector de orden dentro de cada grupo. */
export const OPCIONES_ORDEN: { valor: CampoOrden; label: string }[] = [
  { valor: 'monto_siga', label: 'Monto SIGA' },
  { valor: 'dias_en_etapa', label: 'Días en etapa' },
  { valor: 'devengado_estimado', label: 'Devengado (est.)' },
  { valor: 'nro_pedido', label: 'N° de pedido' },
  { valor: 'macrofase', label: 'Fase del pipeline' },
];

/**
 * Color del acento de cada macrofase para chips/bordes. Usa tokens del sistema
 * de diseño (no hex crudos) para respetar claro/oscuro.
 */
export const ACENTO_MACROFASE: Record<Macrofase, string> = {
  solicitud: 'border-l-muted-foreground',
  programacion: 'border-l-muted-foreground',
  certificacion: 'border-l-accent',
  contratacion: 'border-l-accent',
  ejecucion: 'border-l-primary',
  cierre: 'border-l-secondary',
};
