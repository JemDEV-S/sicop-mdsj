"""Servicio de gestión de usuarios — admin-only (HU-17 · T-08/T-54).

Lógica de negocio del CRUD de usuarios y la asignación de centros de costo.
Reglas del proyecto:

- Contraseña inicial = DNI del usuario. El cambio posterior es OPCIONAL, así que
  el usuario nace con `debe_cambiar_password = false`.
- Salvaguarda de auto-gestión: un admin NO puede cambiarse el rol ni cambiar su
  propio estado desde esta pantalla (evita quedar sin acceso o dejar el sistema
  sin administradores). Sí puede editar su nombre/email.
- El rol 'ciudadano' no aplica a usuarios internos (se valida en el schema).

Errores de negocio se levantan como `UsuarioError` y el router los mapea a HTTP.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.enums import CodigoRol, EstadoUsuario
from app.security.passwords import hash_password


class UsuarioError(Exception):
    """Error de negocio en la gestión de usuarios. `codigo` mapea a HTTP status."""

    def __init__(self, mensaje: str, *, codigo: int = 400) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _rol_id(db: Session, rol: CodigoRol) -> int:
    rid = db.execute(
        text("SELECT id FROM auth.roles WHERE codigo = :c"),
        {"c": rol.value},
    ).scalar_one_or_none()
    if rid is None:
        raise UsuarioError(f"rol '{rol.value}' no existe", codigo=400)
    return rid


def listar_usuarios(
    db: Session,
    *,
    q: str | None = None,
    rol: CodigoRol | None = None,
    estado: EstadoUsuario | None = None,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Listado paginado con conteo de CC asignados. Excluye ciudadanos."""
    where = ["r.codigo <> 'ciudadano'"]
    params: dict[str, Any] = {}
    if q:
        where.append("(u.nombre_completo ILIKE :q OR u.usuario ILIKE :q OR u.dni ILIKE :q)")
        params["q"] = f"%{q}%"
    if rol:
        where.append("r.codigo = :rol")
        params["rol"] = rol.value
    if estado:
        where.append("u.estado = CAST(:estado AS estado_usuario)")
        params["estado"] = estado.value
    where_sql = " AND ".join(where)

    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
              FROM auth.usuarios u
              JOIN auth.roles r ON r.id = u.rol_id
             WHERE {where_sql}
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            f"""
            SELECT u.id, u.usuario, u.nombre_completo, u.dni, u.email,
                   r.codigo AS rol, u.estado::text AS estado,
                   u.debe_cambiar_password, u.creado_en,
                   (SELECT COUNT(*) FROM auth.usuarios_centros_costo ucc
                     WHERE ucc.usuario_id = u.id) AS nro_centros
              FROM auth.usuarios u
              JOIN auth.roles r ON r.id = u.rol_id
             WHERE {where_sql}
          ORDER BY u.creado_en DESC
             LIMIT :limit OFFSET :offset
            """
        ),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()
    return [dict(r) for r in rows], total


def obtener_usuario(db: Session, usuario_id: UUID) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT u.id, u.usuario, u.nombre_completo, u.dni, u.email,
                   r.codigo AS rol, u.estado::text AS estado,
                   u.debe_cambiar_password, u.creado_en,
                   (SELECT COUNT(*) FROM auth.usuarios_centros_costo ucc
                     WHERE ucc.usuario_id = u.id) AS nro_centros
              FROM auth.usuarios u
              JOIN auth.roles r ON r.id = u.rol_id
             WHERE u.id = :id AND r.codigo <> 'ciudadano'
            """
        ),
        {"id": str(usuario_id)},
    ).mappings().first()
    if row is None:
        return None
    detalle = dict(row)
    detalle["centros"] = _centros_de_usuario(db, usuario_id)
    return detalle


def _centros_de_usuario(db: Session, usuario_id: UUID) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT cc.codigo, cc.nombre, cc.abreviado, ucc.es_raiz_jerarquia
              FROM auth.usuarios_centros_costo ucc
              JOIN ref.centros_costo cc ON cc.codigo = ucc.centro_costo
             WHERE ucc.usuario_id = :id
          ORDER BY cc.ruta
            """
        ),
        {"id": str(usuario_id)},
    ).mappings().all()
    return [dict(r) for r in rows]


def crear_usuario(
    db: Session,
    *,
    usuario: str,
    nombre_completo: str,
    dni: str,
    rol: CodigoRol,
    email: str | None,
) -> UUID:
    """Crea el usuario con contraseña = DNI y `debe_cambiar_password = false`.

    No commitea — el caller decide la transacción (para agrupar con auditoría).
    """
    existe = db.execute(
        text("SELECT 1 FROM auth.usuarios WHERE usuario = :u"),
        {"u": usuario},
    ).first()
    if existe:
        raise UsuarioError(f"el usuario '{usuario}' ya existe", codigo=409)

    dni_existe = db.execute(
        text("SELECT 1 FROM auth.usuarios WHERE dni = :d"),
        {"d": dni},
    ).first()
    if dni_existe:
        raise UsuarioError(f"ya hay un usuario con DNI {dni}", codigo=409)

    rid = _rol_id(db, rol)
    uid = db.execute(
        text(
            """
            INSERT INTO auth.usuarios
                   (usuario, password_hash, nombre_completo, dni, email, rol_id,
                    debe_cambiar_password)
            VALUES (:u, :h, :n, :dni, :email, :r, false)
            RETURNING id
            """
        ),
        {
            "u": usuario,
            "h": hash_password(dni),
            "n": nombre_completo,
            "dni": dni,
            "email": email,
            "r": rid,
        },
    ).scalar_one()
    return uid


def actualizar_usuario(
    db: Session,
    *,
    objetivo_id: UUID,
    actor_id: UUID,
    nombre_completo: str | None,
    email: str | None,
    rol: CodigoRol | None,
    estado: EstadoUsuario | None,
) -> None:
    """Actualiza campos no nulos. Aplica la salvaguarda de auto-gestión.

    Un admin sobre su propia cuenta no puede cambiar `rol` ni `estado` (evita
    autobloqueo / quedarse sin admins). Nombre y email sí.
    """
    fila = db.execute(
        text(
            """
            SELECT u.id, r.codigo AS rol
              FROM auth.usuarios u
              JOIN auth.roles r ON r.id = u.rol_id
             WHERE u.id = :id
            """
        ),
        {"id": str(objetivo_id)},
    ).mappings().first()
    if fila is None:
        raise UsuarioError("usuario no encontrado", codigo=404)

    es_uno_mismo = str(objetivo_id) == str(actor_id)
    if es_uno_mismo and (rol is not None or estado is not None):
        raise UsuarioError(
            "no puedes cambiar tu propio rol ni estado", codigo=403
        )

    sets: list[str] = []
    params: dict[str, Any] = {"id": str(objetivo_id)}
    if nombre_completo is not None:
        sets.append("nombre_completo = :n")
        params["n"] = nombre_completo
    if email is not None:
        sets.append("email = :email")
        params["email"] = email
    if rol is not None:
        sets.append("rol_id = :rid")
        params["rid"] = _rol_id(db, rol)
    if estado is not None:
        sets.append("estado = CAST(:estado AS estado_usuario)")
        params["estado"] = estado.value

    if not sets:
        return  # nada que actualizar

    sets.append("actualizado_en = now()")
    db.execute(
        text(f"UPDATE auth.usuarios SET {', '.join(sets)} WHERE id = :id"),
        params,
    )


def resetear_password_a_dni(db: Session, usuario_id: UUID) -> None:
    """Restablece la contraseña al DNI del usuario. No commitea."""
    fila = db.execute(
        text("SELECT dni FROM auth.usuarios WHERE id = :id"),
        {"id": str(usuario_id)},
    ).first()
    if fila is None:
        raise UsuarioError("usuario no encontrado", codigo=404)
    if not fila.dni:
        raise UsuarioError(
            "el usuario no tiene DNI registrado; no se puede resetear al DNI",
            codigo=400,
        )
    db.execute(
        text(
            "UPDATE auth.usuarios SET password_hash = :h, debe_cambiar_password = false "
            "WHERE id = :id"
        ),
        {"h": hash_password(fila.dni), "id": str(usuario_id)},
    )


def asignar_centro(
    db: Session,
    *,
    usuario_id: UUID,
    centro_costo: str,
    es_raiz_jerarquia: bool,
) -> None:
    """Asigna un CC al usuario (idempotente: actualiza el flag si ya existía)."""
    existe_cc = db.execute(
        text("SELECT 1 FROM ref.centros_costo WHERE codigo = :c AND activo = true"),
        {"c": centro_costo},
    ).first()
    if not existe_cc:
        raise UsuarioError(f"centro de costo '{centro_costo}' inexistente o inactivo", codigo=400)

    existe_usr = db.execute(
        text("SELECT 1 FROM auth.usuarios WHERE id = :id"),
        {"id": str(usuario_id)},
    ).first()
    if not existe_usr:
        raise UsuarioError("usuario no encontrado", codigo=404)

    db.execute(
        text(
            """
            INSERT INTO auth.usuarios_centros_costo
                   (usuario_id, centro_costo, es_raiz_jerarquia)
            VALUES (:u, :c, :raiz)
            ON CONFLICT (usuario_id, centro_costo)
            DO UPDATE SET es_raiz_jerarquia = EXCLUDED.es_raiz_jerarquia
            """
        ),
        {"u": str(usuario_id), "c": centro_costo, "raiz": es_raiz_jerarquia},
    )


def quitar_centro(db: Session, *, usuario_id: UUID, centro_costo: str) -> None:
    db.execute(
        text(
            "DELETE FROM auth.usuarios_centros_costo "
            "WHERE usuario_id = :u AND centro_costo = :c"
        ),
        {"u": str(usuario_id), "c": centro_costo},
    )
