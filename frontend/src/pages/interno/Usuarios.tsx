/**
 * Gestión de usuarios — admin-only (HU-17 · T-54).
 *
 * Ruta: /admin/usuarios — protegida por RequireRole="admin".
 *
 * Es la pantalla que hace operable la jerarquía de acceso (T-56): el admin crea
 * usuarios, les asigna rol y centros de costo, y resetea contraseñas. La
 * contraseña inicial de un usuario nuevo es su DNI.
 */
import { useEffect, useState } from 'react';
import { UserCog, UserPlus, KeyRound, Pencil, Building2 } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import { ErrorState } from '@/components/layout/ErrorState';
import { SkeletonTable } from '@/components/layout/LoadingSkeleton';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { formatFecha } from '@/lib/formatters';
import { useAuthStore } from '@/store/auth';
import { useResetPassword, useUsuarios, useUsuarioDetalle } from '@/features/usuarios/api';
import {
  ROLES,
  ESTADOS,
  estadoLabel,
  estadoVariant,
  rolLabel,
  rolVariant,
} from '@/features/usuarios/lib';
import { ModalUsuario } from '@/features/usuarios/secciones/ModalUsuario';
import { ModalCentros } from '@/features/usuarios/secciones/ModalCentros';
import type { EstadoUsuario, Rol, UsuarioItem } from '@/features/usuarios/types';

const PAGE_SIZE = 25;

export default function Usuarios() {
  const actorId = useAuthStore((s) => s.user?.id ?? '');

  const [qInput, setQInput] = useState('');
  const [q, setQ] = useState('');
  const [rol, setRol] = useState<Rol | null>(null);
  const [estado, setEstado] = useState<EstadoUsuario | null>(null);
  const [page, setPage] = useState(1);

  // Debounce de la búsqueda (350ms), mismo patrón que provint.
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(qInput.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(t);
  }, [qInput]);

  const listadoQ = useUsuarios({ q: q || null, rol, estado, page, size: PAGE_SIZE });

  // Modales.
  const [modalUsuario, setModalUsuario] = useState<{ abierto: boolean; usuarioId: string | null }>({
    abierto: false,
    usuarioId: null,
  });
  const [ccUsuario, setCcUsuario] = useState<UsuarioItem | null>(null);

  const editandoQ = useUsuarioDetalle(modalUsuario.usuarioId);

  return (
    <div className="space-y-6">
      <PageHeader
        titulo="Gestión de usuarios"
        descripcion="Crea funcionarios, asigna su rol y sus centros de costo. La contraseña inicial es el DNI."
        acciones={
          <Button onClick={() => setModalUsuario({ abierto: true, usuarioId: null })}>
            <UserPlus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            Nuevo usuario
          </Button>
        }
      />

      <SectionCard titulo="Filtros" icono={UserCog} padding="sm">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-foreground">Buscar</span>
            <Input
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
              placeholder="Nombre, usuario o DNI"
              className="w-64"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-foreground">Rol</span>
            <select
              className="h-9 rounded-md border border-border bg-background px-2 text-sm"
              value={rol ?? ''}
              onChange={(e) => {
                setRol((e.target.value || null) as Rol | null);
                setPage(1);
              }}
            >
              <option value="">Todos</option>
              {ROLES.map((r) => (
                <option key={r.valor} value={r.valor}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-foreground">Estado</span>
            <select
              className="h-9 rounded-md border border-border bg-background px-2 text-sm"
              value={estado ?? ''}
              onChange={(e) => {
                setEstado((e.target.value || null) as EstadoUsuario | null);
                setPage(1);
              }}
            >
              <option value="">Todos</option>
              {ESTADOS.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </SectionCard>

      <SectionCard titulo="Usuarios" icono={UserCog} padding="sm" bodyClassName="p-0">
        {listadoQ.isLoading ? (
          <div className="p-4">
            <SkeletonTable rows={8} cols={5} />
          </div>
        ) : listadoQ.isError ? (
          <div className="p-4">
            <ErrorState
              titulo="No se pudieron cargar los usuarios"
              onReintentar={() => listadoQ.refetch()}
            />
          </div>
        ) : listadoQ.data ? (
          <TablaUsuarios
            items={listadoQ.data.items}
            total={listadoQ.data.total}
            page={page}
            size={PAGE_SIZE}
            onPageChange={setPage}
            isFetching={listadoQ.isFetching}
            actorId={actorId}
            onEditar={(u) => setModalUsuario({ abierto: true, usuarioId: u.id })}
            onCentros={(u) => setCcUsuario(u)}
          />
        ) : null}
      </SectionCard>

      <ModalUsuario
        abierto={modalUsuario.abierto}
        onCerrar={() => setModalUsuario({ abierto: false, usuarioId: null })}
        usuario={modalUsuario.usuarioId ? editandoQ.data ?? null : null}
        actorId={actorId}
      />

      {ccUsuario ? (
        <ModalCentros abierto onCerrar={() => setCcUsuario(null)} usuario={ccUsuario} />
      ) : null}
    </div>
  );
}

interface TablaProps {
  items: UsuarioItem[];
  total: number;
  page: number;
  size: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
  actorId: string;
  onEditar: (u: UsuarioItem) => void;
  onCentros: (u: UsuarioItem) => void;
}

function TablaUsuarios({
  items,
  total,
  page,
  size,
  onPageChange,
  isFetching,
  actorId,
  onEditar,
  onCentros,
}: TablaProps) {
  const reset = useResetPassword();
  const totalPaginas = Math.max(1, Math.ceil(total / size));

  if (total === 0) {
    return (
      <EmptyState
        titulo="Sin usuarios"
        descripcion="No hay usuarios que coincidan con los filtros. Crea uno con el botón «Nuevo usuario»."
      />
    );
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3 text-sm text-muted-foreground">
        <span>
          <span className="font-semibold tabular-nums text-foreground">
            {total.toLocaleString('es-PE')}
          </span>{' '}
          usuarios
        </span>
        {isFetching ? <span className="text-xs">Actualizando…</span> : null}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2.5 text-left">Usuario</th>
              <th className="px-4 py-2.5 text-left">Rol</th>
              <th className="px-4 py-2.5 text-left">Estado</th>
              <th className="px-4 py-2.5 text-right">Centros</th>
              <th className="px-4 py-2.5 text-left">Alta</th>
              <th className="px-4 py-2.5 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((u, i) => (
              <tr
                key={u.id}
                className={cn('border-t border-border align-middle', i % 2 === 1 && 'bg-muted/20')}
              >
                <td className="px-4 py-3">
                  <p className="font-medium text-foreground">{u.nombre_completo}</p>
                  <p className="text-[11px] text-muted-foreground">
                    @{u.usuario}
                    {u.dni ? ` · DNI ${u.dni}` : ''}
                    {u.id === actorId ? ' · tú' : ''}
                  </p>
                </td>
                <td className="px-4 py-3">
                  <Badge variant={rolVariant(u.rol)}>{rolLabel(u.rol)}</Badge>
                </td>
                <td className="px-4 py-3">
                  <Badge variant={estadoVariant(u.estado)}>{estadoLabel(u.estado)}</Badge>
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-foreground">{u.nro_centros}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{formatFecha(u.creado_en)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" onClick={() => onCentros(u)} aria-label="Centros de costo">
                      <Building2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => onEditar(u)} aria-label="Editar">
                      <Pencil className="h-4 w-4" aria-hidden="true" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={!u.dni || reset.isPending}
                      onClick={() => {
                        if (
                          window.confirm(
                            `¿Restablecer la contraseña de ${u.nombre_completo} a su DNI (${u.dni})?`,
                          )
                        ) {
                          reset.mutate(u.id);
                        }
                      }}
                      aria-label="Restablecer contraseña al DNI"
                      title={u.dni ? 'Restablecer contraseña al DNI' : 'Sin DNI registrado'}
                    >
                      <KeyRound className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-border px-4 py-3">
        <span className="text-sm text-muted-foreground">
          Página {page} de {totalPaginas}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPaginas}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </div>
  );
}
