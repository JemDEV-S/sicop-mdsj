import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

const VITE_API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_BASE_URL = `${VITE_API_URL}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Estado en memoria para proteger contra XSS (sin localStorage)
let accessToken: string | null = null;
let refreshPromise: Promise<string> | null = null;

export function getAccessToken() {
  return accessToken;
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

let resetSessionCallback: (() => void) | null = null;

export function setResetSessionCallback(cb: () => void) {
  resetSessionCallback = cb;
}

// Reseteo silencioso de la sesión (sin navegación). Llamado al fallar el interceptor.
export function triggerResetSession() {
  setAccessToken(null);
  if (resetSessionCallback) {
    resetSessionCallback();
  }
}

/**
 * Rehidrata la sesión solicitando un nuevo access_token mediante la cookie HttpOnly.
 * Maneja condiciones de carrera (múltiples llamadas) mediante un Promise lock.
 */
export function refreshAuthToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = axios.post(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true })
      .then((res) => {
        const newToken = res.data.access_token;
        setAccessToken(newToken);
        return newToken;
      })
      .catch((error) => {
        triggerResetSession();
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

// Interceptor de peticiones: Inyecta el token si existe
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Extender el tipado interno para nuestro flag _retry
interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// Interceptor de respuestas: Captura 401 y orquesta el reintento
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig;

    if (!originalRequest) return Promise.reject(error);

    // Evitar interceptar los propios requests de refresh para no hacer loops infinitos
    const isRefreshRoute = originalRequest.url?.includes('/auth/refresh');

    if (error.response?.status === 401 && !originalRequest._retry && !isRefreshRoute) {
      originalRequest._retry = true;

      try {
        const newToken = await refreshAuthToken();
        // Reintentar la solicitud original con el nuevo token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        // El refresh falló, la sesión está completamente muerta. 
        // triggerResetSession() ya fue llamado por refreshAuthToken().
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
