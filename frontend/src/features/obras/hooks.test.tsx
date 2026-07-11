/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useObras } from './hooks';
import { apiClient } from '../../lib/query-client';

// Mockeamos el apiClient base
vi.mock('../../lib/query-client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/query-client')>();
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
    },
  };
});

describe('useObras hook', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  it('procesa correctamente una respuesta con semaforo "desconocido" sin romper el data flow', async () => {
    const mockResponse = {
      data: {
        items: [
          {
            codigo_unico: '2000000',
            nombre_inversion: 'Obra de prueba',
            funcion: 'SALUD',
            tipologia: 'HOSPITAL',
            modalidad: 'CONTRATA',
            estado: 'ACTIVO',
            etapa_f8: null,
            avance_fisico: 50,
            avance_ejecucion: 40,
            pim_anio_actual: 1000000,
            dev_anio_actual: 400000,
            tiene_avan_fisico: 'S',
            latitud: -13.5,
            longitud: -71.9,
            semaforo: 'desconocido', // El caso defensivo
          }
        ],
        total: 1,
        page: 1,
        size: 25,
      }
    };

    // Simulamos la respuesta de Axios
    vi.mocked(apiClient.get).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useObras({ page: 1, size: 25 }), { wrapper });

    // Esperamos a que la petición finalice exitosamente
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verificamos que los parámetros viajaron correctamente a apiClient.get
    expect(apiClient.get).toHaveBeenCalledWith('/publico/obras', {
      params: { page: 1, size: 25 }
    });

    // Verificamos que el hook no explotó y propagó los datos intactos (incluyendo "desconocido")
    expect(result.current.data).toBeDefined();
    expect(result.current.data?.items[0].semaforo).toBe('desconocido');
  });
});
