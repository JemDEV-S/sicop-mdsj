import { create } from 'zustand';
import { apiClient, setAccessToken, refreshAuthToken, setResetSessionCallback } from '../lib/api-client';

export interface UserProfile {
  id: string;
  usuario: string;
  nombre_completo: string;
  email: string | null;
  rol: string;
}

interface AuthState {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (usuario: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  resetSession: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true, // Empieza cargando para la rehidratación inicial

  resetSession: () => {
    setAccessToken(null);
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  login: async (usuario, password) => {
    // 1. Llamada a la API para loguear
    const res = await apiClient.post('/auth/login', { usuario, password });
    
    // 2. Inyectar el token en memoria antes de la siguiente petición
    setAccessToken(res.data.access_token);

    // 3. Obtener el perfil
    const userRes = await apiClient.get<UserProfile>('/auth/me');
    
    // 4. Actualizar estado global
    set({ user: userRes.data, isAuthenticated: true });
  },

  logout: async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch (error) {
      // Ignoramos si la API de logout falla (e.g. token ya expiró),
      // lo importante es que limpie localmente.
      console.warn('Fallo al avisar logout al servidor', error);
    } finally {
      useAuthStore.getState().resetSession();
      // En este caso, al ser un logout explícito, sí navegamos
      window.location.href = '/login';
    }
  },

  checkAuth: async () => {
    try {
      // Intentar refrescar token. Usa la misma Promise de api-client si hay concurrencia.
      await refreshAuthToken();
      // Si tuvo éxito, la memoria ya tiene token, ahora traemos perfil.
      const userRes = await apiClient.get<UserProfile>('/auth/me');
      set({ user: userRes.data, isAuthenticated: true, isLoading: false });
    } catch (error) {
      // Fallo de hidratación. Reseteo silencioso. No expulsa a nadie a /login.
      useAuthStore.getState().resetSession();
    }
  }
}));

// Inyección de la dependencia de reseteo hacia el api-client
setResetSessionCallback(() => {
  useAuthStore.getState().resetSession();
});
