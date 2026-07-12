/**
 * @vitest-environment jsdom
 *
 * Tests del Dashboard Interno (HU-22, T-44).
 *
 * Estrategia: vi.mock sobre el hook useDashboard y el store de auth
 * para validar los tres estados (carga, error, éxito) sin necesidad
 * de backend real.
 */

import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { DashboardResponse } from '../types';

// ─── Mocks ────────────────────────────────────────────────────────────

vi.mock('../api', () => ({
  useDashboard: vi.fn(),
}));

vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('../../../lib/formatters', () => ({
  parseMonto: (v: unknown) => {
    if (v == null || v === '') return null;
    const n = typeof v === 'number' ? v : parseFloat(String(v));
    return isNaN(n) ? null : n;
  },
  formatearMoneda: (v: number | null) => {
    if (v === null) return 'ND';
    return `S/ ${v.toLocaleString('es-PE', { minimumFractionDigits: 2 })}`;
  },
  formatPorcentaje: (v: number | null | undefined) => {
    if (v == null) return '0%';
    return `${v.toFixed(1)}%`;
  },
  formatFecha: (v: string | null | undefined) => {
    if (!v) return '-';
    return v;
  },
}));

// Stub de Semaforo para evitar dependencia de estilos
vi.mock('../../../components/Semaforo', () => ({
  default: ({ estado, texto }: { estado: string; texto: string }) => (
    <span data-testid="semaforo">{estado}: {texto}</span>
  ),
}));

// Stub de mapSemaforoApiToEstado
vi.mock('../../obras/api', () => ({
  mapSemaforoApiToEstado: (s: string | null) => s === 'ok' || s === 'alerta' || s === 'critico' ? s : null,
}));

// ─── Imports que usan los mocks ───────────────────────────────────────

import { useDashboard } from '../api';
import { useAuthStore } from '../../../store/auth';
import DashboardWidgets from './DashboardWidgets';

const mockUseDashboard = useDashboard as ReturnType<typeof vi.fn>;
const mockUseAuthStore = useAuthStore as unknown as ReturnType<typeof vi.fn>;

// ─── Fixtures ─────────────────────────────────────────────────────────

const MOCK_DASHBOARD: DashboardResponse = {
  alertas: {
    pedidos_estancados: 3,
    contratos_por_vencer: 1,
    metas_rezagadas: 2,
  },
  pipeline: {
    solicitados: 8,
    con_orden: 15,
    conformidad: 5,
    devengado: 3,
    cerrado: 12,
  },
  saldos: {
    saldo_disponible: 87540.50,
    pim_total: 500000,
    devengado_total: 412459.50,
    porcentaje_ejecucion: 82.5,
    semaforo: 'alerta',
  },
  ultimos_pedidos: [
    {
      nro_pedido: '234-2026',
      monto: 12450,
      descripcion: 'Cemento Portland',
      estado: 'Solicitado',
      fecha: '2026-07-10',
    },
    {
      nro_pedido: '235-2026',
      monto: 8900,
      descripcion: 'Consultoría técnica',
      estado: 'Con orden',
      fecha: '2026-07-09',
    },
    {
      nro_pedido: '236-2026',
      monto: 3200,
      descripcion: 'Papelería',
      estado: 'Conformidad',
      fecha: null,
    },
  ],
};

// ─── Helpers ──────────────────────────────────────────────────────────

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardWidgets />
    </MemoryRouter>
  );
}

// ─── Tests ────────────────────────────────────────────────────────────

describe('DashboardWidgets (T-44)', () => {
  beforeEach(() => {
    mockUseAuthStore.mockImplementation((selector: (state: Record<string, unknown>) => unknown) =>
      selector({
        user: {
          id: '1',
          usuario: 'jperez',
          nombre_completo: 'José Pérez',
          email: null,
          rol: { codigo: 'operativo', nombre: 'Sub. Obras Públicas' },
        },
      })
    );
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('muestra skeletons durante la carga', () => {
    mockUseDashboard.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    });

    renderDashboard();

    expect(screen.getByText(/Bienvenido, José Pérez/)).toBeTruthy();
    expect(screen.getByText('Sub. Obras Públicas')).toBeTruthy();
    // Los skeleton divs se renderizan (3 widgets)
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBe(3);
  });

  it('muestra mensaje de error si el fetch falla', () => {
    mockUseDashboard.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('SIGA no disponible'),
    });

    renderDashboard();

    expect(screen.getByText('Error')).toBeTruthy();
    expect(screen.getByText('SIGA no disponible')).toBeTruthy();
  });

  it('renderiza los 3 widgets y la tabla con datos exitosos', () => {
    mockUseDashboard.mockReturnValue({
      data: MOCK_DASHBOARD,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderDashboard();

    // Widget Alertas
    const alertasWidget = screen.getByTestId('widget-alertas');
    expect(alertasWidget).toBeTruthy();
    expect(alertasWidget.textContent).toContain('3'); // pedidos_estancados
    expect(screen.getByText('Pedidos estancados')).toBeTruthy();

    // Widget Pipeline
    expect(screen.getByTestId('widget-pipeline')).toBeTruthy();
    expect(screen.getByText('43 pedidos')).toBeTruthy(); // 8+15+5+3+12

    // Widget Saldos
    expect(screen.getByTestId('widget-saldos')).toBeTruthy();
    // Semáforo alerta renderizado
    expect(screen.getByTestId('semaforo')).toBeTruthy();
    expect(screen.getByText(/alerta: Atención/)).toBeTruthy();

    // Tabla de pedidos
    expect(screen.getByTestId('tabla-pedidos')).toBeTruthy();
    expect(screen.getByText('234-2026')).toBeTruthy();
    expect(screen.getByText('Cemento Portland')).toBeTruthy();
    expect(screen.getByText('235-2026')).toBeTruthy();
    expect(screen.getByText('236-2026')).toBeTruthy();

    // Accesos rápidos
    expect(screen.getByTestId('accesos-rapidos')).toBeTruthy();
  });

  it('formatea montos con formatearMoneda y no produce NaN', () => {
    mockUseDashboard.mockReturnValue({
      data: MOCK_DASHBOARD,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderDashboard();

    // El saldo de 87540.50 debe estar formateado, NO como "S/ NaN"
    const bodyText = document.body.textContent || '';
    expect(bodyText).not.toContain('NaN');
  });

  it('muestra "Sin alertas pendientes" cuando todas las alertas son 0', () => {
    const dashSinAlertas = {
      ...MOCK_DASHBOARD,
      alertas: {
        pedidos_estancados: 0,
        contratos_por_vencer: 0,
        metas_rezagadas: 0,
      },
    };

    mockUseDashboard.mockReturnValue({
      data: dashSinAlertas,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderDashboard();
    expect(screen.getByText('Sin alertas pendientes')).toBeTruthy();
  });

  it('muestra "No hay pedidos recientes" cuando la lista está vacía', () => {
    const dashSinPedidos = {
      ...MOCK_DASHBOARD,
      ultimos_pedidos: [],
    };

    mockUseDashboard.mockReturnValue({
      data: dashSinPedidos,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderDashboard();
    expect(screen.getByText('No hay pedidos recientes.')).toBeTruthy();
  });

  it('muestra fecha como "-" para pedidos con fecha null', () => {
    mockUseDashboard.mockReturnValue({
      data: MOCK_DASHBOARD,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderDashboard();

    // El pedido 236-2026 tiene fecha: null → formatFecha devuelve '-'
    const rows = screen.getByTestId('tabla-pedidos').querySelectorAll('tbody tr');
    const lastRow = rows[rows.length - 1]!;
    const cells = lastRow.querySelectorAll('td');
    const fechaCell = cells[cells.length - 1]!;
    expect(fechaCell.textContent).toBe('-');
  });
});
