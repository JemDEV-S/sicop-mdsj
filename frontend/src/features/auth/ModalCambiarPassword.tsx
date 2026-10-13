import { useState } from 'react';
import { Check, Eye, EyeOff, Loader2, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/auth';
import { handleApiError } from '@/lib/api-errors';
import { cn } from '@/lib/utils';

interface ModalCambiarPasswordProps {
  abierto: boolean;
  obligatorio?: boolean;
  onClose?: () => void;
}

export function ModalCambiarPassword({
  abierto,
  obligatorio = false,
  onClose,
}: ModalCambiarPasswordProps) {
  const cambiarPassword = useAuthStore((s) => s.cambiarPassword);
  const logout = useAuthStore((s) => s.logout);

  const [passwordActual, setPasswordActual] = useState('');
  const [passwordNueva, setPasswordNueva] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');

  const [verActual, setVerActual] = useState(false);
  const [verNueva, setVerNueva] = useState(false);
  const [verConfirm, setVerConfirm] = useState(false);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const resetCampos = () => {
    setPasswordActual('');
    setPasswordNueva('');
    setPasswordConfirm('');
    setErrorMsg(null);
    setVerActual(false);
    setVerNueva(false);
    setVerConfirm(false);
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      if (obligatorio) return;
      resetCampos();
      onClose?.();
    }
  };

  const longitudValida = passwordNueva.length >= 8;
  const coinciden = passwordConfirm.length > 0 && passwordNueva === passwordConfirm;
  const formularioValido = passwordActual.length > 0 && longitudValida && coinciden;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!passwordActual) {
      setErrorMsg('Ingresa tu contraseña actual.');
      return;
    }

    if (!longitudValida) {
      setErrorMsg('La nueva contraseña debe tener al menos 8 caracteres.');
      return;
    }

    if (passwordNueva === passwordActual) {
      setErrorMsg('La nueva contraseña no puede ser idéntica a la actual.');
      return;
    }

    if (!coinciden) {
      setErrorMsg('La confirmación de la contraseña no coincide.');
      return;
    }

    setEnviando(true);
    try {
      await cambiarPassword(passwordActual, passwordNueva);
      toast.success('Contraseña actualizada correctamente.');
      resetCampos();
      onClose?.();
    } catch (err) {
      const errorObj = handleApiError(err);
      setErrorMsg(errorObj.message || 'No se pudo actualizar la contraseña.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Dialog open={abierto} onOpenChange={handleOpenChange}>
      <DialogContent
        showCloseButton={!obligatorio}
        onPointerDownOutside={(e) => {
          if (obligatorio) e.preventDefault();
        }}
        onEscapeKeyDown={(e) => {
          if (obligatorio) e.preventDefault();
        }}
        className="sm:max-w-[390px] rounded-2xl border border-border/50 bg-background/98 p-6 shadow-2xl backdrop-blur-md"
      >
        <DialogHeader className="space-y-1.5 text-left">
          <DialogTitle className="text-lg font-semibold tracking-tight text-foreground">
            {obligatorio ? 'Actualizar contraseña' : 'Cambiar contraseña'}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground leading-relaxed">
            {obligatorio
              ? 'Por seguridad, define una nueva contraseña personal para tu cuenta.'
              : 'Ingresa tu clave actual y define tu nueva contraseña de acceso.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          {errorMsg ? (
            <div className="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-xs font-medium text-destructive">
              {errorMsg}
            </div>
          ) : null}

          {/* Contraseña actual */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs font-medium text-foreground/90">
              <label htmlFor="pwd-actual">Contraseña actual</label>
              {obligatorio ? (
                <span className="text-[10px] text-muted-foreground/70 font-normal">
                  (DNI inicial)
                </span>
              ) : null}
            </div>
            <div className="relative">
              <Input
                id="pwd-actual"
                type={verActual ? 'text' : 'password'}
                value={passwordActual}
                onChange={(e) => setPasswordActual(e.target.value)}
                placeholder="••••••••"
                className="h-10 pr-9 rounded-lg bg-muted/20 border-border/70 text-sm focus:bg-background transition-colors"
                disabled={enviando}
                autoFocus
              />
              <button
                type="button"
                onClick={() => setVerActual(!verActual)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-muted-foreground/50 hover:text-foreground transition-colors"
                aria-label={verActual ? 'Ocultar contraseña' : 'Ver contraseña'}
                tabIndex={-1}
              >
                {verActual ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Nueva contraseña */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs font-medium text-foreground/90">
              <label htmlFor="pwd-nueva">Nueva contraseña</label>
              {passwordNueva.length > 0 ? (
                <span
                  className={cn(
                    'text-[10px] flex items-center gap-1 transition-colors',
                    longitudValida
                      ? 'text-emerald-600 dark:text-emerald-400 font-medium'
                      : 'text-muted-foreground/70',
                  )}
                >
                  {longitudValida ? <Check className="h-3 w-3" /> : null}
                  Mín. 8 caracteres
                </span>
              ) : null}
            </div>
            <div className="relative">
              <Input
                id="pwd-nueva"
                type={verNueva ? 'text' : 'password'}
                value={passwordNueva}
                onChange={(e) => setPasswordNueva(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="h-10 pr-9 rounded-lg bg-muted/20 border-border/70 text-sm focus:bg-background transition-colors"
                disabled={enviando}
              />
              <button
                type="button"
                onClick={() => setVerNueva(!verNueva)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-muted-foreground/50 hover:text-foreground transition-colors"
                aria-label={verNueva ? 'Ocultar contraseña' : 'Ver contraseña'}
                tabIndex={-1}
              >
                {verNueva ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Confirmar contraseña */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs font-medium text-foreground/90">
              <label htmlFor="pwd-confirm">Confirmar contraseña</label>
              {passwordConfirm.length > 0 && coinciden ? (
                <span className="text-[10px] flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                  <Check className="h-3 w-3" /> Coinciden
                </span>
              ) : null}
            </div>
            <div className="relative">
              <Input
                id="pwd-confirm"
                type={verConfirm ? 'text' : 'password'}
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="Repite la contraseña"
                className="h-10 pr-9 rounded-lg bg-muted/20 border-border/70 text-sm focus:bg-background transition-colors"
                disabled={enviando}
              />
              <button
                type="button"
                onClick={() => setVerConfirm(!verConfirm)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-muted-foreground/50 hover:text-foreground transition-colors"
                aria-label={verConfirm ? 'Ocultar contraseña' : 'Ver contraseña'}
                tabIndex={-1}
              >
                {verConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Botones de acción */}
          <div className="pt-2 flex flex-col gap-2">
            <Button
              type="submit"
              disabled={enviando || !formularioValido}
              className="w-full h-10 rounded-lg text-sm font-medium shadow-xs transition-all"
            >
              {enviando ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                  Actualizando...
                </>
              ) : (
                'Guardar y continuar'
              )}
            </Button>

            {obligatorio ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => void logout()}
                disabled={enviando}
                className="w-full h-9 rounded-lg text-xs font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/5 hover:border-destructive/30 border-border/80 transition-all flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" />
                Cerrar sesión e intentar más tarde
              </Button>
            ) : (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  resetCampos();
                  onClose?.();
                }}
                disabled={enviando}
                className="w-full h-9 rounded-lg text-xs text-muted-foreground hover:text-foreground"
              >
                Cancelar
              </Button>
            )}
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
