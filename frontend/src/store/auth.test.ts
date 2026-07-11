import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from './auth';
import { apiClient, getAccessToken } from '../lib/api-client';

// Mockeamos el axios apiClient
vi.mock('../lib/api-client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api-client')>();
  return {
    ...actual,
    apiClient: {
      post: vi.fn(),
      get: vi.fn()
    },
    refreshAuthToken: vi.fn()
  };
});

// Mock para window.location
const originalLocation = window.location;

describe('Auth Store (Zustand)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: true });
    useAuthStore.getState().resetSession();
    
    // Mock window location href
    delete (window as any).location;
    window.location = { ...originalLocation, href: '' } as any;
  });

  it('login() exitoso debe actualizar el estado y setear token en memoria', async () => {
    const mockToken = 'jwt-fake-token-123';
    const mockUser = {
      id: 'uuid-123',
      usuario: 'jperez',
      nombre_completo: 'Juan Perez',
      email: null,
      rol: { codigo: 'admin', nombre: 'Administrador' }
    };

    // Simulamos respuesta de /auth/login
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { access_token: mockToken } });
    
    // Simulamos respuesta de /auth/me
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockUser });

    await useAuthStore.getState().login('jperez', 'password123');

    // Verificaciones
    expect(getAccessToken()).toBe(mockToken);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().user).toEqual(mockUser);
  });

  it('checkAuth() con visitante anónimo falla silenciosamente sin forzar redirección', async () => {
    // Simulamos que el refreshAuthToken falla (ej. sin cookie de refresh)
    const { refreshAuthToken } = await import('../lib/api-client');
    vi.mocked(refreshAuthToken).mockRejectedValueOnce(new Error('No token'));

    await useAuthStore.getState().checkAuth();

    // Verificaciones
    expect(getAccessToken()).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(window.location.href).toBe(''); // NO debió redirigir a /login
    expect(apiClient.post).not.toHaveBeenCalledWith('/auth/logout'); // NO debió llamar a logout
  });

  it('logout() explícito limpia estado, llama a /auth/logout y redirige a /login', async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({});

    await useAuthStore.getState().logout();

    // Verificaciones
    expect(apiClient.post).toHaveBeenCalledWith('/auth/logout');
    expect(getAccessToken()).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(window.location.href).toBe('/login');
  });
});
