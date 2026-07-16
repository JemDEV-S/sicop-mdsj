import { create } from 'zustand';
import { apiClient, setAccessToken, refreshAuthToken, setResetSessionCallback } from '../lib/api-client';
import { useContextoInterno } from './contexto-interno';

export interface CentroCostoBreve {
  codigo: string;
  nombre: string;
  abreviado: string | null;
}

export interface UserProfile {
  id: string;
  usuario: string;
  nombre_completo: string;
  email: string | null;
  rol: string;
  centros_costo: CentroCostoBreve[];
  debe_cambiar_password: boolean;
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
    useContextoInterno.getState().reset();
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  login: async (usuario, password) => {
    const res = await apiClient.post('/auth/login', { usuario, password });
    setAccessToken(res.data.access_token);

    const userRes = await apiClient.get<UserProfile>('/auth/me');
    useContextoInterno.getState().hidratarDesdePerfil(userRes.data.centros_costo);
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
      await refreshAuthToken();
      const userRes = await apiClient.get<UserProfile>('/auth/me');
      useContextoInterno.getState().hidratarDesdePerfil(userRes.data.centros_costo);
      set({ user: userRes.data, isAuthenticated: true, isLoading: false });
    } catch (error) {
      useAuthStore.getState().resetSession();
    }
  }
}));

// Inyección de la dependencia de reseteo hacia el api-client
setResetSessionCallback(() => {
  useAuthStore.getState().resetSession();
});
