/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DirectorioProveedores from './DirectorioProveedores';
import { apiClient } from '../../lib/api-client';
import type { ProveedorPublicoItem } from '../../features/proveedores/types';

vi.mock('../../lib/api-client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/api-client')>();
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
    },
  };
});

// Mock de contrato Pydantic confirmado en T-43, ver bitácora — pendiente de verificación E2E real hasta .bak de SIGA
const mockProveedores: ProveedorPublicoItem[] = [
  {
    ruc: '20123456789',
    nombre: 'CONSTRUCTORA LOS ANDES S.A.C.',
    tipo_persona: 'JURIDICA',
    giro: 'CONSTRUCCION DE EDIFICIOS',
    flag_mype: 'S',
    flag_rnp: 'S',
    flag_consorcio: 'N',
    monto_acumulado: 150000.5,
    nro_ordenes: 3,
  },
  {
    ruc: '10987654321',
    nombre: 'JUAN PEREZ CONSULTING',
    tipo_persona: 'NATURAL',
    giro: 'SERVICIOS PROFESIONALES',
    flag_mype: 'N',
    flag_rnp: 'S',
    flag_consorcio: 'N',
    monto_acumulado: 45000,
    nro_ordenes: 1,
  },
];

describe('DirectorioProveedores (Mock Pydantic T-43)', () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        items: mockProveedores,
        total: mockProveedores.length,
        page: 1,
        size: 25,
      }
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders table with mocked data successfully', async () => {
    render(<DirectorioProveedores />, { wrapper });

    // Esperar a que los mocks de MSW provean los datos a TanStack Query
    await waitFor(() => {
      expect(screen.getByText('CONSTRUCTORA LOS ANDES S.A.C.')).toBeDefined();
    });

    // Validar visualización de RUC
    expect(screen.getByText('20123456789')).toBeDefined();
    
    // Validar visualización de insignias
    expect(screen.getByText('MYPE')).toBeDefined();
    expect(screen.getAllByText('RNP').length).toBe(2);

    // Validar formato de moneda
    expect(screen.getByText('S/ 150,000.50')).toBeDefined();
  });

  it('filters table using mock logic', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        items: mockProveedores,
        total: mockProveedores.length,
        page: 1,
        size: 25,
      }
    });

    render(<DirectorioProveedores />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('CONSTRUCTORA LOS ANDES S.A.C.')).toBeDefined();
    });

    // Escribir en el buscador
    const searchInput = screen.getByPlaceholderText('Buscar por RUC o Razón Social...');
    
    // Al escribir, la UI debe hacer un nuevo fetch. 
    // Preparamos el mock para la respuesta filtrada.
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        items: [mockProveedores[1]],
        total: 1,
        page: 1,
        size: 25,
      }
    });

    fireEvent.change(searchInput, { target: { value: 'JUAN PEREZ' } });

    // Como usamos debounce de 300ms, esperamos un poco más
    await waitFor(() => {
      expect(screen.queryByText('CONSTRUCTORA LOS ANDES S.A.C.')).toBeNull();
      expect(screen.getByText('JUAN PEREZ CONSULTING')).toBeDefined();
    }, { timeout: 1000 });
  });
});
