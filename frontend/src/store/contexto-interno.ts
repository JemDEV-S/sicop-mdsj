import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { CentroCostoBreve } from './auth';

const AÑO_VIGENTE = 2026;
const AÑOS_COBERTURA = [2023, 2024, 2025, 2026] as const;

export type AñoActivo = (typeof AÑOS_COBERTURA)[number];

interface ContextoInternoState {
  añoActivo: AñoActivo;
  ccActivo: CentroCostoBreve | null;
  sidebarColapsado: boolean;
  /** Estado del drawer de navegación en móvil. Efímero — no se persiste. */
  drawerAbierto: boolean;
  setAño: (año: AñoActivo) => void;
  setCc: (cc: CentroCostoBreve | null) => void;
  toggleSidebar: () => void;
  setSidebarColapsado: (colapsado: boolean) => void;
  abrirDrawer: () => void;
  cerrarDrawer: () => void;
  hidratarDesdePerfil: (centros: CentroCostoBreve[]) => void;
  reset: () => void;
}

export const AÑOS_DISPONIBLES: readonly AñoActivo[] = AÑOS_COBERTURA;
export const AÑO_DEFAULT: AñoActivo = AÑO_VIGENTE;

export const useContextoInterno = create<ContextoInternoState>()(
  persist(
    (set, get) => ({
      añoActivo: AÑO_DEFAULT,
      ccActivo: null,
      sidebarColapsado: false,
      drawerAbierto: false,
      setAño: (año) => set({ añoActivo: año }),
      setCc: (cc) => set({ ccActivo: cc }),
      toggleSidebar: () => set((s) => ({ sidebarColapsado: !s.sidebarColapsado })),
      setSidebarColapsado: (colapsado) => set({ sidebarColapsado: colapsado }),
      abrirDrawer: () => set({ drawerAbierto: true }),
      cerrarDrawer: () => set({ drawerAbierto: false }),
      hidratarDesdePerfil: (centros) => {
        const actual = get().ccActivo;
        const sigueDisponible =
          actual && centros.some((c) => c.codigo === actual.codigo);
        if (sigueDisponible) return;
        set({ ccActivo: centros[0] ?? null });
      },
      reset: () => set({ añoActivo: AÑO_DEFAULT, ccActivo: null }),
    }),
    {
      name: 'presupuesto:contexto-interno',
      storage: createJSONStorage(() => localStorage),
      // El drawer es estado efímero de la vista: nunca debe rehidratarse abierto.
      partialize: ({ drawerAbierto: _drawer, ...resto }) => resto,
    },
  ),
);
