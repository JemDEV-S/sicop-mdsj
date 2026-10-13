import { registerSW } from 'virtual:pwa-register';

// Variable de control para evitar recargas infinitas en caso de eventos duplicados
let isRefreshing = false;

// Si el Service Worker cambia de controlador (nueva versión activada), recargar la página automáticamente
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!isRefreshing) {
      isRefreshing = true;
      window.location.reload();
    }
  });
}

// Escuchar error de chunks obsoletos tras un nuevo despliegue (Vite Dynamic Imports)
window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault();
  if (!isRefreshing) {
    isRefreshing = true;
    window.location.reload();
  }
});

// Registrar Service Worker con auto-actualización proactiva
export const updateSW = registerSW({
  immediate: true,
  onNeedRefresh() {
    console.info('[PWA] Nueva versión detectada en el servidor. Actualizando...');
    updateSW(true);
  },
  onOfflineReady() {
    console.info('[PWA] Aplicación lista para uso sin conexión.');
  },
  onRegisteredSW(_swUrl, registration) {
    if (!registration) return;

    // 1. Verificar actualizaciones periódicamente cada 15 minutos
    setInterval(() => {
      registration.update().catch((err) => {
        console.warn('[PWA] Error comprobando actualización periódica:', err);
      });
    }, 15 * 60 * 1000);

    // 2. Verificar actualización inmediata cuando el usuario vuelve a la pestaña
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        registration.update().catch(() => {});
      }
    });

    // 3. Verificar al reconectar red
    window.addEventListener('online', () => {
      registration.update().catch(() => {});
    });
  },
  onRegisterError(error) {
    console.error('[PWA] Error al registrar service worker:', error);
  },
});
