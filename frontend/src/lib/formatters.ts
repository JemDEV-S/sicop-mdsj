/**
 * Convierte un string numérico de la API a un number primitivo.
 * Si el valor es null, undefined, vacío o inválido, devuelve null.
 * Esto diferencia explícitamente "cero legítimo" ('0') de "dato faltante" (null/''),
 * permitiendo a la UI y a Recharts manejar los casos nulos de forma correcta.
 */
export function parseMonto(valor: string | number | null | undefined): number | null {
  if (valor == null || valor === '') return null;
  if (typeof valor === 'number') return isNaN(valor) ? null : valor;
  
  const parsed = parseFloat(valor);
  return isNaN(parsed) ? null : parsed;
}

/**
 * Formatea un monto en Soles (ej. S/ 1,234,567.89).
 * Soporta montos acortados si se pide (ej. 1.2M).
 */
export function formatearMoneda(valor: number | null, compact = false): string {
  if (valor === null) return 'ND'; // No disponible
  
  if (compact) {
    if (valor >= 1_000_000) return `S/ ${(valor / 1_000_000).toFixed(1)}M`;
    if (valor >= 1_000) return `S/ ${(valor / 1_000).toFixed(1)}K`;
  }
  
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN',
  }).format(valor);
}

/**
 * Calcula un porcentaje de forma segura evitando división por cero o resultados NaN/Infinity.
 * Devuelve el porcentaje redondeado a 2 decimales (ej. 45.23).
 * Si alguna parte de la división es null o total es 0, devuelve null.
 */
export function calcularPorcentaje(parte: string | number | null, total: string | number | null): number | null {
  const p = parseMonto(parte);
  const t = parseMonto(total);
  if (t === null || t === 0 || p === null) return null;
  
  const pct = (p / t) * 100;
  return Math.round(pct * 100) / 100;
}

/**
 * Formatea un número como porcentaje
 */
export function formatPorcentaje(amount: number | null | undefined, decimals = 1): string {
  if (amount == null) return '0%';
  
  return new Intl.NumberFormat('es-PE', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(amount / 100);
}

/**
 * Formatea una fecha ISO o Date a un string local
 */
export function formatFecha(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return '-';
  
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  
  // Evitar invalid date
  if (isNaN(date.getTime())) return '-';
  
  return new Intl.DateTimeFormat('es-PE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}
