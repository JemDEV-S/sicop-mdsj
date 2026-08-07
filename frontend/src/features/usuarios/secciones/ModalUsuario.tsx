/**
 * Modal de alta / edición de usuario (HU-17 · T-54).
 *
 * En modo ALTA pide usuario, nombre, DNI, rol, email. La contraseña inicial es
 * el DNI (nota visible al usuario admin) — no se captura contraseña aquí.
 * En modo EDICIÓN sólo permite nombre, email, rol y estado (usuario y DNI son
 * identidad; no se cambian). El rol/estado propios se bloquean (salvaguarda que
 * el backend también aplica).
 */
import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useActualizarUsuario, useCrearUsuario } from '../api';
import { ROLES, ROL_AYUDA, ESTADOS } from '../lib';
import type { EstadoUsuario, Rol, UsuarioDetalle } from '../types';

interface Props {
  abierto: boolean;
  onCerrar: () => void;
  /** null = alta; objeto = edición. */
  usuario: UsuarioDetalle | null;
  /** id del admin en sesión, para bloquear la auto-gestión de rol/estado. */
  actorId: string;
}

const CAMPO = 'h-9 rounded-md border border-border bg-background px-2 text-sm';

export function ModalUsuario({ abierto, onCerrar, usuario, actorId }: Props) {
  const esEdicion = usuario != null;
  const esUnoMismo = esEdicion && usuario.id === actorId;

  const crear = useCrearUsuario();
  const actualizar = useActualizarUsuario();

  const [nombre, setNombre] = useState('');
  const [usuarioLogin, setUsuarioLogin] = useState('');
  const [dni, setDni] = useState('');
  const [email, setEmail] = useState('');
  const [rol, setRol] = useState<Rol>('operativo');
  const [estado, setEstado] = useState<EstadoUsuario>('activo');
  const [error, setError] = useState<string | null>(null);

  // Rehidratar el formulario al abrir / cambiar de usuario.
  useEffect(() => {
    if (!abierto) return;
    setError(null);
    setNombre(usuario?.nombre_completo ?? '');
    setUsuarioLogin(usuario?.usuario ?? '');
    setDni(usuario?.dni ?? '');
    setEmail(usuario?.email ?? '');
    setRol(usuario?.rol ?? 'operativo');
    setEstado(usuario?.estado ?? 'activo');
  }, [abierto, usuario]);

  const guardando = crear.isPending || actualizar.isPending;

  async function onGuardar() {
    setError(null);
    try {
      if (esEdicion) {
        await actualizar.mutateAsync({
          id: usuario.id,
          cambios: {
            nombre_completo: nombre.trim(),
            email: email.trim() || null,
            // No enviar rol/estado propios (el backend los rechazaría).
            ...(esUnoMismo ? {} : { rol, estado }),
          },
        });
      } else {
        await crear.mutateAsync({
          usuario: usuarioLogin.trim().toLowerCase(),
          nombre_completo: nombre.trim(),
          dni: dni.trim(),
          rol,
          email: email.trim() || null,
        });
      }
      onCerrar();
    } catch (e) {
      setError(mensajeError(e));
    }
  }

  return (
    <Dialog open={abierto} onOpenChange={(o) => (!o ? onCerrar() : undefined)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{esEdicion ? 'Editar usuario' : 'Nuevo usuario'}</DialogTitle>
          <DialogDescription>
            {esEdicion
              ? 'Actualiza los datos del funcionario. El usuario y el DNI no se modifican aquí.'
              : 'La contraseña inicial será el DNI del usuario. Podrá cambiarla luego si lo desea.'}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          <label className="grid gap-1 text-sm">
            <span className="font-medium text-foreground">Nombre completo</span>
            <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Ej. Juan Pérez Quispe" />
          </label>

          {!esEdicion ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1 text-sm">
                <span className="font-medium text-foreground">Usuario (para iniciar sesión)</span>
                <Input
                  value={usuarioLogin}
                  onChange={(e) => setUsuarioLogin(e.target.value)}
                  placeholder="jperez"
                  autoCapitalize="none"
                />
              </label>
              <label className="grid gap-1 text-sm">
                <span className="font-medium text-foreground">DNI</span>
                <Input
                  value={dni}
                  onChange={(e) => setDni(e.target.value.replace(/\D/g, ''))}
                  placeholder="12345678"
                  inputMode="numeric"
                  maxLength={12}
                />
              </label>
            </div>
          ) : null}

          <label className="grid gap-1 text-sm">
            <span className="font-medium text-foreground">
              Correo <span className="text-muted-foreground">(opcional)</span>
            </span>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jperez@munisanjeronimo.gob.pe" />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="font-medium text-foreground">Rol</span>
              <select
                className={CAMPO}
                value={rol}
                onChange={(e) => setRol(e.target.value as Rol)}
                disabled={esUnoMismo}
              >
                {ROLES.map((r) => (
                  <option key={r.valor} value={r.valor}>
                    {r.label}
                  </option>
                ))}
              </select>
              <span className="text-[11px] text-muted-foreground">{ROL_AYUDA[rol]}</span>
            </label>

            {esEdicion ? (
              <label className="grid gap-1 text-sm">
                <span className="font-medium text-foreground">Estado</span>
                <select
                  className={CAMPO}
                  value={estado}
                  onChange={(e) => setEstado(e.target.value as EstadoUsuario)}
                  disabled={esUnoMismo}
                >
                  {ESTADOS.map((s) => (
                    <option key={s.valor} value={s.valor}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>

          {esUnoMismo ? (
            <p className="rounded-md bg-muted px-3 py-2 text-[11px] text-muted-foreground">
              No puedes cambiar tu propio rol ni estado desde aquí.
            </p>
          ) : null}

          {error ? (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCerrar} disabled={guardando}>
            Cancelar
          </Button>
          <Button onClick={onGuardar} disabled={guardando}>
            {guardando ? 'Guardando…' : esEdicion ? 'Guardar cambios' : 'Crear usuario'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function mensajeError(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return 'No se pudo guardar. Revisa los datos e intenta de nuevo.';
}
