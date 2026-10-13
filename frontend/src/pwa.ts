import { registerSW } from 'virtual:pwa-register';

// Inyectado por Vite en build-time
declare const __APP_BUILD_ID__: string;

let isUpdating = false;

/**
 * Limpia todas las cachés y recarga a la versión más reciente del servidor
 */
export async function forceUpdateApp(reason: string) {
  if (isUpdating) return;
  isUpdating = true;
  console.info(`[SICOP Auto-Update] ${reason}. Actualizando a la última versión...`);

  try {
    // 1. Limpiar todas las cachés del navegador (CacheStorage)
    if ('caches' in window) {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    }

    // 2. Forzar actualización de Service Workers
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (const reg of registrations) {
        await reg.update().catch(() => {});
      }
    }
  } catch (err) {
    console.warn('[SICOP Auto-Update] Error limpiando caché:', err);
  }

  // 3. Recargar la página evitando cualquier caché HTTP residual
  const target = new URL(window.location.href);
  target.searchParams.set('_v', Date.now().toString());
  window.location.replace(target.toString());
}

/**
 * Consulta el archivo /version.json del servidor para detectar despliegues
 */
async function checkServerVersion() {
  if (isUpdating) return;
  try {
    const res = await fetch(`/version.json?_t=${Date.now()}`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
    });
    if (!res.ok) return;
    const data = await res.json();
    if (data?.version && typeof __APP_BUILD_ID__ !== 'undefined') {
      if (data.version !== __APP_BUILD_ID__) {
        await forceUpdateApp(`Nueva versión detectada en el servidor (${data.version})`);
      }
    }
  } catch {
    // Sin conexión o fallo transitorio, no interrumpir
  }
}

// 1. Detectar cambio de controlador del Service Worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    void forceUpdateApp('Nuevo Service Worker activado');
  });
}

// 2. Detectar error de chunks obsoletos tras nuevo despliegue (Vite Dynamic Imports)
window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault();
  void forceUpdateApp('Módulo dinámico obsoleto detectado');
});

// 3. Revisión periódica y por eventos de foco / visibilidad
setTimeout(() => void checkServerVersion(), 1500);
setInterval(() => void checkServerVersion(), 30 * 1000); // Cada 30 segundos

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    void checkServerVersion();
  }
});

window.addEventListener('focus', () => {
  void checkServerVersion();
});

window.addEventListener('online', () => {
  void checkServerVersion();
});

// 4. Registro del Service Worker
export const updateSW = registerSW({
  immediate: true,
  onNeedRefresh() {
    console.info('[PWA] Nueva versión lista en Service Worker.');
    void forceUpdateApp('Actualización de PWA lista');
  },
  onOfflineReady() {
    console.info('[PWA] Aplicación lista para operar.');
  },
  onRegisteredSW(_swUrl, registration) {
    if (!registration) return;
    setInterval(() => {
      registration.update().catch(() => {});
    }, 5 * 60 * 1000);
  },
});
