/**
 * Formatea un número como moneda (Soles Peruanos)
 */
export function formatSoles(amount: number | null | undefined): string {
  if (amount == null) return 'S/ 0.00';
  
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN',
  }).format(amount);
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
