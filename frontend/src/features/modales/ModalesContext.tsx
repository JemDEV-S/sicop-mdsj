// Contexto de modales apilables (Panel Interno v2).
//
// Los modales son la base de las tres vistas: desde el Panel, el Análisis y el
// Cruce se abre un pedido, y desde ahí se navega en cascada a su orden, su
// expediente SIAF, su PECOSA o el reporte de su meta — cada uno apilado sobre
// el anterior, sin perder el hilo. Este contexto mantiene la PILA y expone
// `abrir`, `volver` y `cerrar`. El render de la pila lo hace <ModalesHost/>.

import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

/** Cada tipo de modal y las llaves que necesita para cargar sus datos reales. */
export type EntradaModal =
  | { tipo: 'pedido'; nroPedido: number; tipoBien: string; tipoPedido: string }
  | { tipo: 'orden'; nroPedido: number; tipoBien: string; tipoPedido: string; nroOrden: number }
  | { tipo: 'siaf'; nroPedido: number; tipoBien: string; tipoPedido: string; expSiaf: number }
  | { tipo: 'pecosa'; nroPedido: number; tipoBien: string; tipoPedido: string; nroMovimiento: number }
  // El reporte agrega una meta puntual (secFunc) o el ámbito completo. Cuando
  // no hay meta, `categoria` respeta el filtro Producto/Proyecto de la vista:
  // 'proyecto' | 'producto' agregan solo esa naturaleza; 'todas' (o ausente),
  // el universo visible.
  | { tipo: 'reporte'; secFunc: number | null; categoria?: 'todas' | 'producto' | 'proyecto' };

export type TipoModal = EntradaModal['tipo'];

interface ModalesContextValue {
  pila: EntradaModal[];
  abrir: (entrada: EntradaModal) => void;
  volver: (indice: number) => void;
  cerrar: () => void;
}

const ModalesContext = createContext<ModalesContextValue | null>(null);

export function ModalesProvider({ children }: { children: ReactNode }) {
  const [pila, setPila] = useState<EntradaModal[]>([]);

  const abrir = useCallback((entrada: EntradaModal) => {
    setPila((prev) => [...prev, entrada]);
  }, []);

  // Vuelve al modal en `indice`, descartando los apilados encima.
  const volver = useCallback((indice: number) => {
    setPila((prev) => prev.slice(0, indice + 1));
  }, []);

  const cerrar = useCallback(() => setPila([]), []);

  const value = useMemo(
    () => ({ pila, abrir, volver, cerrar }),
    [pila, abrir, volver, cerrar],
  );

  return <ModalesContext.Provider value={value}>{children}</ModalesContext.Provider>;
}

/** Acceso a la pila de modales. Lanza si se usa fuera del provider. */
export function useModales(): ModalesContextValue {
  const ctx = useContext(ModalesContext);
  if (!ctx) {
    throw new Error('useModales debe usarse dentro de <ModalesProvider>');
  }
  return ctx;
}

/**
 * Variante segura: no lanza si no hay provider (devuelve un abridor inerte).
 * Útil para componentes reutilizables que pueden renderizarse fuera de una
 * pantalla con modales (p. ej. en pruebas o en la vista pública).
 */
export function useModalesOpcional(): Pick<ModalesContextValue, 'abrir'> {
  const ctx = useContext(ModalesContext);
  return ctx ?? { abrir: () => {} };
}
