import { useState } from 'react';
import { Eye, EyeOff, KeyRound, Loader2, Lock, LogOut, ShieldAlert } from 'lucide-react';
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
      if (obligatorio) return; // No permitir cerrar si es obligatorio
      resetCampos();
      onClose?.();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!passwordActual) {
      setErrorMsg('Ingresa tu contraseña actual.');
      return;
    }

    if (passwordNueva.length < 8) {
      setErrorMsg('La nueva contraseña debe tener al menos 8 caracteres.');
      return;
    }

    if (passwordNueva === passwordActual) {
      setErrorMsg('La nueva contraseña no puede ser idéntica a la actual.');
      return;
    }

    if (passwordNueva !== passwordConfirm) {
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
        className="sm:max-w-md p-6"
      >
        <DialogHeader className="space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            {obligatorio ? (
              <ShieldAlert className="h-6 w-6 text-amber-500" />
            ) : (
              <KeyRound className="h-6 w-6 text-primary" />
            )}
          </div>
          <DialogTitle className="text-center text-xl font-bold tracking-tight">
            {obligatorio ? 'Actualización obligatoria de contraseña' : 'Cambiar contraseña'}
          </DialogTitle>
          <DialogDescription className="text-center text-sm text-muted-foreground leading-relaxed">
            {obligatorio
              ? 'Por políticas de seguridad institucional, debes actualizar tu contraseña antes de ingresar al sistema.'
              : 'Ingresa tu contraseña actual y define una nueva clave de acceso de al menos 8 caracteres.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-2 space-y-4">
          {errorMsg ? (
            <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-xs font-medium text-destructive">
              {errorMsg}
            </div>
          ) : null}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {obligatorio ? 'Contraseña actual (tu DNI inicial)' : 'Contraseña actual'}
            </label>
            <div className="relative">
              <Input
                type={verActual ? 'text' : 'password'}
                value={passwordActual}
                onChange={(e) => setPasswordActual(e.target.value)}
                placeholder="••••••••"
                className="pr-10"
                disabled={enviando}
                autoFocus
              />
              <button
                type="button"
                onClick={() => setVerActual(!verActual)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={verActual ? 'Ocultar contraseña' : 'Ver contraseña'}
              >
                {verActual ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Nueva contraseña
            </label>
            <div className="relative">
              <Input
                type={verNueva ? 'text' : 'password'}
                value={passwordNueva}
                onChange={(e) => setPasswordNueva(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="pr-10"
                disabled={enviando}
              />
              <button
                type="button"
                onClick={() => setVerNueva(!verNueva)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={verNueva ? 'Ocultar contraseña' : 'Ver contraseña'}
              >
                {verNueva ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Confirmar nueva contraseña
            </label>
            <div className="relative">
              <Input
                type={verConfirm ? 'text' : 'password'}
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="Repite la nueva contraseña"
                className="pr-10"
                disabled={enviando}
              />
              <button
                type="button"
                onClick={() => setVerConfirm(!verConfirm)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={verConfirm ? 'Ocultar contraseña' : 'Ver contraseña'}
              >
                {verConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div className="pt-2 flex flex-col gap-2">
            <Button
              type="submit"
              disabled={enviando || !passwordActual || !passwordNueva || !passwordConfirm}
              className="w-full gap-2"
            >
              {enviando ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Actualizando...
                </>
              ) : (
                <>
                  <Lock className="h-4 w-4" />
                  {obligatorio ? 'Establecer contraseña y continuar' : 'Actualizar contraseña'}
                </>
              )}
            </Button>

            {obligatorio ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => void logout()}
                disabled={enviando}
                className="text-xs text-muted-foreground hover:text-destructive gap-1.5"
              >
                <LogOut className="h-3.5 w-3.5" />
                Cerrar sesión e intentar más tarde
              </Button>
            ) : (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  resetCampos();
                  onClose?.();
                }}
                disabled={enviando}
                className="w-full"
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
