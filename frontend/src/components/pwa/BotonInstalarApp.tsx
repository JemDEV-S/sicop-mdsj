import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * Evento no estándar de Chromium para instalar PWAs. No está en los tipos DOM,
 * así que lo declaramos localmente.
 */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

interface BotonInstalarAppProps {
  className?: string;
  /** Se llama tras aceptar la instalación (útil para cerrar el menú móvil). */
  onInstalado?: () => void;
}

/**
 * Botón "Instalar app" para el portal público.
 * Sólo aparece cuando el navegador ofrece instalar la PWA (evento
 * `beforeinstallprompt`) y la app no está ya instalada / corriendo en standalone.
 * En navegadores que no soportan instalación (p. ej. iOS Safari) no se renderiza.
 */
export function BotonInstalarApp({ className, onInstalado }: BotonInstalarAppProps) {
  const [promptEvent, setPromptEvent] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    // Si ya se abre como app instalada, no ofrecemos instalar.
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      // iOS expone este flag no estándar.
      (window.navigator as { standalone?: boolean }).standalone === true;
    if (standalone) return;

    function onBeforeInstall(e: Event) {
      // Evitamos el mini-infobar automático para controlar el momento del prompt.
      e.preventDefault();
      setPromptEvent(e as BeforeInstallPromptEvent);
    }
    function onInstalledEvent() {
      setPromptEvent(null);
    }

    window.addEventListener('beforeinstallprompt', onBeforeInstall);
    window.addEventListener('appinstalled', onInstalledEvent);
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall);
      window.removeEventListener('appinstalled', onInstalledEvent);
    };
  }, []);

  if (!promptEvent) return null;

  async function instalar() {
    if (!promptEvent) return;
    await promptEvent.prompt();
    const { outcome } = await promptEvent.userChoice;
    // El evento sólo puede usarse una vez.
    setPromptEvent(null);
    if (outcome === 'accepted') onInstalado?.();
  }

  return (
    <button
      type="button"
      onClick={instalar}
      className={cn(
        'inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md',
        'bg-accent text-accent-foreground hover:bg-accent/90',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-foreground',
        className,
      )}
    >
      <Download className="w-4 h-4" aria-hidden="true" />
      Instalar app
    </button>
  );
}

export default BotonInstalarApp;
