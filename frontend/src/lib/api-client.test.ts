import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import axios from 'axios';
import { apiClient, setAccessToken, getAccessToken } from './api-client';

describe('apiClient concurrency lock', () => {
  let mockGlobal: MockAdapter;
  let mockApi: MockAdapter;

  beforeEach(() => {
    mockGlobal = new MockAdapter(axios);
    mockApi = new MockAdapter(apiClient);
    setAccessToken(null);
    // Mock window.location
    globalThis.window = { location: { href: '' } } as any;
  });

  afterEach(() => {
    mockGlobal.restore();
    mockApi.restore();
    vi.clearAllMocks();
  });

  it('debe llamar a /auth/refresh EXACTAMENTE UNA VEZ cuando fallan 5 requests concurrentes y redirigir si el refresh falla', async () => {
    let refreshCalls = 0;

    // Mock del refresh endpoint para que falle también (cookie expirada)
    mockGlobal.onPost(/\/auth\/refresh/).reply(() => {
      refreshCalls++;
      return [401, { detail: 'Cookie expired' }];
    });

    // Mock de un endpoint protegido que devuelve 401
    mockApi.onGet(/\/protegido/).reply(401, { detail: 'Unauthorized' });

    // Disparamos 5 requests concurrentes al mismo tiempo
    const requests = Array.from({ length: 5 }).map(() => 
      apiClient.get('/protegido').catch(() => 'error esperado')
    );

    // Esperamos que todos resuelvan (fallando controladamente)
    await Promise.all(requests);

    // Verificaciones críticas exigidas por el supervisor:
    
    // 1. ¿Cuántas veces se llamó al refresh? Exactamente 1.
    expect(refreshCalls).toBe(1);

    // 2. ¿Terminó en triggerResetSession? (token en null, sin navegación)
    expect(window.location.href).toBe('');
    expect(getAccessToken()).toBeNull();
  });

  it('debe llamar a /auth/refresh EXACTAMENTE UNA VEZ cuando fallan 5 requests concurrentes y reintentarlas con éxito si el refresh funciona', async () => {
    let refreshCalls = 0;
    let protectedCallsWithNewToken = 0;

    // Mock del refresh endpoint para que DEVUELVA UN NUEVO TOKEN
    mockGlobal.onPost(/\/auth\/refresh/).reply(() => {
      refreshCalls++;
      return [200, { access_token: 'new-valid-token' }];
    });

    // Mock de un endpoint protegido. 
    // Primera vez devuelve 401. Si viene con el nuevo token, devuelve 200.
    mockApi.onGet(/\/protegido/).reply((config) => {
      if (config.headers?.Authorization === 'Bearer new-valid-token') {
        protectedCallsWithNewToken++;
        return [200, { data: 'ok' }];
      }
      return [401, { detail: 'Unauthorized' }];
    });

    // Disparamos 5 requests concurrentes al mismo tiempo
    const requests = Array.from({ length: 5 }).map(() => apiClient.get('/protegido'));

    // Esperamos que todos resuelvan CON ÉXITO
    const responses = await Promise.all(requests);

    // Verificaciones:
    
    // 1. ¿Se llamó exactamente 1 vez al refresh a pesar de las 5 fallas iniciales?
    expect(refreshCalls).toBe(1);

    // 2. ¿Las 5 peticiones originales se reintentaron exitosamente usando el token nuevo?
    expect(protectedCallsWithNewToken).toBe(5);

    // 3. ¿Resolvieron correctamente?
    expect(responses[0]!.status).toBe(200);
    expect(responses[0]!.data.data).toBe('ok');
    
    // 4. ¿Mantuvo la sesión?
    expect(window.location.href).toBe('');
  });
});
