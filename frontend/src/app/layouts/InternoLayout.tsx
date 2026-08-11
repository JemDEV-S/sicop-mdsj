import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { SidebarInterno } from '@/components/nav/SidebarInterno';
import { TopbarInterno } from '@/components/nav/TopbarInterno';
import { useContextoInterno } from '@/store/contexto-interno';
import { cn } from '@/lib/utils';

export default function InternoLayout() {
  const drawerAbierto = useContextoInterno((s) => s.drawerAbierto);
  const cerrarDrawer = useContextoInterno((s) => s.cerrarDrawer);

  // Cerrar el drawer con Escape y bloquear el scroll del fondo mientras está abierto.
  useEffect(() => {
    if (!drawerAbierto) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') cerrarDrawer();
    }
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [drawerAbierto, cerrarDrawer]);

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar fijo — solo escritorio/tablet ancho */}
      <div className="hidden lg:flex">
        <SidebarInterno variante="fijo" />
      </div>

      {/* Drawer móvil: overlay + panel deslizante */}
      <div
        className={cn(
          'fixed inset-0 z-50 lg:hidden',
          drawerAbierto ? 'pointer-events-auto' : 'pointer-events-none',
        )}
        aria-hidden={!drawerAbierto}
      >
        {/* Fondo oscuro */}
        <div
          className={cn(
            'absolute inset-0 bg-foreground/40 transition-opacity duration-200',
            drawerAbierto ? 'opacity-100' : 'opacity-0',
          )}
          onClick={cerrarDrawer}
        />
        {/* Panel */}
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Menú de navegación"
          className={cn(
            'absolute inset-y-0 left-0 h-full transition-transform duration-200 ease-out',
            drawerAbierto ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <SidebarInterno variante="drawer" />
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <TopbarInterno />
        <main className="flex-1 p-4 md:p-6 overflow-x-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
