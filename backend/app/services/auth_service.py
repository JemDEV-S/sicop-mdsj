"""Servicio de autenticación.

Reglas (HU-08 + §7 arquitectura):
- Hash bcrypt en `auth.usuarios.password_hash`.
- Login exitoso resetea `intentos_fallidos` y `bloqueado_hasta`.
- Login fallido incrementa `intentos_fallidos`. Al llegar a 5 → bloqueo
  por `BLOQUEO_MINUTOS` (15 min).
- Cada intento (exitoso o fallido) queda en `logs.auditoria` con IP + UA.
- Refresh token se guarda hasheado (SHA-256) en `auth.refresh_tokens`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.auth import Rol, Usuario, UsuarioCentroCosto
from app.models.enums import EstadoUsuario
from app.security.jwt import (
    TokenInvalido,
    crear_access_token,
    crear_refresh_token,
    decodificar_refresh_token,
    sha256_hex,
)
from app.security.passwords import hash_password, verify_password
from app.services import auditoria_service
from app.services.auditoria_service import Accion

logger = logging.getLogger(__name__)

MAX_INTENTOS_FALLIDOS = 5
BLOQUEO_MINUTOS = 15


# ─── Excepciones ────────────────────────────────────────────────────────

class AuthError(Exception):
    """Base para errores de auth. El router los mapea a 401/403."""

    codigo: str = "auth_error"


class CredencialesInvalidas(AuthError):
    codigo = "credenciales_invalidas"


class UsuarioBloqueado(AuthError):
    codigo = "usuario_bloqueado"

    def __init__(self, hasta: datetime):
        super().__init__(f"Usuario bloqueado hasta {hasta.isoformat()}")
        self.hasta = hasta


class UsuarioInactivo(AuthError):
    codigo = "usuario_inactivo"


class RefreshInvalido(AuthError):
    codigo = "refresh_invalido"


class PasswordActualIncorrecta(AuthError):
    codigo = "password_actual_incorrecta"


# ─── Resultados ─────────────────────────────────────────────────────────

@dataclass
class ResultadoLogin:
    usuario_id: UUID
    rol: str
    access_token: str
    access_expira_en_segundos: int
    refresh_token: str
    refresh_expira_en: datetime
    debe_cambiar_password: bool


@dataclass
class ResultadoRefresh:
    access_token: str
    access_expira_en_segundos: int


# ─── Helpers ────────────────────────────────────────────────────────────

def _ahora() -> datetime:
    return datetime.now(UTC)


def _centros_costo_directos(db: Session, usuario_id: UUID) -> list[str]:
    """Devuelve solo los CC asignados directamente al usuario.

    La expansión por jerarquía (decisor → descendientes) se hace en T-09
    en el middleware `get_centros_permitidos`.
    """
    rows = db.execute(
        select(UsuarioCentroCosto.centro_costo).where(
            UsuarioCentroCosto.usuario_id == usuario_id
        )
    ).all()
    return [r[0] for r in rows]


def _rol_codigo(db: Session, rol_id: int) -> str:
    row = db.execute(select(Rol.codigo).where(Rol.id == rol_id)).first()
    if row is None:
        raise AuthError("rol no encontrado")
    codigo = row[0]
    return codigo.value if hasattr(codigo, "value") else str(codigo)


def _registrar_auditoria(
    db: Session,
    accion: str,
    usuario_id: UUID | None,
    detalle: dict[str, Any] | None,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """Wrapper delgado sobre `auditoria_service.registrar` (T-10)."""
    auditoria_service.registrar(
        db,
        accion=accion,
        usuario_id=usuario_id,
        detalle=detalle,
        ip=ip,
        user_agent=user_agent,
    )


def _guardar_refresh(
    db: Session,
    usuario_id: UUID,
    token_hash: str,
    expira_en: datetime,
    ip: str | None,
    user_agent: str | None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO auth.refresh_tokens
                   (usuario_id, token_hash, expira_en, user_agent, ip_origen)
            VALUES (:usuario_id, :hash, :expira, :ua, :ip)
            """
        ),
        {
            "usuario_id": str(usuario_id),
            "hash": token_hash,
            "expira": expira_en,
            "ua": user_agent,
            "ip": ip,
        },
    )


# ─── API pública del servicio ───────────────────────────────────────────

def login(
    db: Session,
    usuario_input: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> ResultadoLogin:
    """Valida credenciales, aplica bloqueo, emite tokens y audita.

    Lanza `CredencialesInvalidas`, `UsuarioBloqueado` o `UsuarioInactivo`.
    Todos los caminos hacen commit (para persistir intentos_fallidos y
    entradas de auditoría).
    """
    usuario = db.execute(
        select(Usuario).where(Usuario.usuario == usuario_input)
    ).scalar_one_or_none()

    if usuario is None:
        # Registrar intento contra usuario inexistente sin exponerlo.
        _registrar_auditoria(
            db, Accion.LOGIN_FALLIDO, None,
            {"usuario_intento": usuario_input, "motivo": "usuario_no_existe"},
            ip, user_agent,
        )
        db.commit()
        raise CredencialesInvalidas()

    # Bloqueo activo
    if usuario.bloqueado_hasta and usuario.bloqueado_hasta > _ahora():
        _registrar_auditoria(
            db, Accion.LOGIN_FALLIDO, usuario.id,
            {"motivo": "bloqueado", "hasta": usuario.bloqueado_hasta.isoformat()},
            ip, user_agent,
        )
        db.commit()
        raise UsuarioBloqueado(usuario.bloqueado_hasta)

    # Estado inactivo/bloqueado permanente
    if usuario.estado != EstadoUsuario.activo:
        _registrar_auditoria(
            db, Accion.LOGIN_FALLIDO, usuario.id,
            {"motivo": "estado", "estado": usuario.estado.value},
            ip, user_agent,
        )
        db.commit()
        raise UsuarioInactivo()

    if not verify_password(password, usuario.password_hash):
        usuario.intentos_fallidos = int(usuario.intentos_fallidos or 0) + 1
        motivo = {"motivo": "password_incorrecto", "intentos": usuario.intentos_fallidos}
        if usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
            usuario.bloqueado_hasta = _ahora() + timedelta(minutes=BLOQUEO_MINUTOS)
            usuario.intentos_fallidos = 0
            motivo["bloqueado_hasta"] = usuario.bloqueado_hasta.isoformat()
        _registrar_auditoria(db, Accion.LOGIN_FALLIDO, usuario.id, motivo, ip, user_agent)
        db.commit()
        if "bloqueado_hasta" in motivo:
            raise UsuarioBloqueado(usuario.bloqueado_hasta)  # type: ignore[arg-type]
        raise CredencialesInvalidas()

    # ── Éxito ──
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None

    rol_codigo = _rol_codigo(db, usuario.rol_id)
    centros = _centros_costo_directos(db, usuario.id)

    access_token, access_exp = crear_access_token(usuario.id, rol_codigo, centros)
    refresh_plain, refresh_hash, refresh_exp = crear_refresh_token(usuario.id)
    _guardar_refresh(db, usuario.id, refresh_hash, refresh_exp, ip, user_agent)

    _registrar_auditoria(
        db, Accion.LOGIN_EXITOSO, usuario.id,
        {"rol": rol_codigo, "centros_costo_directos": len(centros)},
        ip, user_agent,
    )
    db.commit()

    return ResultadoLogin(
        usuario_id=usuario.id,
        rol=rol_codigo,
        access_token=access_token,
        access_expira_en_segundos=int((access_exp - _ahora()).total_seconds()),
        refresh_token=refresh_plain,
        refresh_expira_en=refresh_exp,
        debe_cambiar_password=bool(usuario.debe_cambiar_password),
    )


def refresh_access(
    db: Session,
    refresh_token: str,
) -> ResultadoRefresh:
    """Emite un nuevo access token a partir de un refresh válido y no revocado."""
    try:
        payload = decodificar_refresh_token(refresh_token)
    except TokenInvalido as exc:
        raise RefreshInvalido(str(exc)) from exc

    token_hash = sha256_hex(refresh_token)
    row = db.execute(
        text(
            """
            SELECT usuario_id, revocado, expira_en
              FROM auth.refresh_tokens
             WHERE token_hash = :hash
            """
        ),
        {"hash": token_hash},
    ).first()
    if row is None or row.revocado or row.expira_en <= _ahora():
        raise RefreshInvalido("token no encontrado, revocado o expirado")

    usuario_id = UUID(payload["sub"])
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or usuario.estado != EstadoUsuario.activo:
        raise RefreshInvalido("usuario no valido")

    rol_codigo = _rol_codigo(db, usuario.rol_id)
    centros = _centros_costo_directos(db, usuario.id)
    access_token, access_exp = crear_access_token(usuario.id, rol_codigo, centros)
    return ResultadoRefresh(
        access_token=access_token,
        access_expira_en_segundos=int((access_exp - _ahora()).total_seconds()),
    )


def logout(db: Session, refresh_token: str, ip: str | None, user_agent: str | None) -> None:
    """Revoca el refresh token (marca `revocado=true`). Idempotente."""
    token_hash = sha256_hex(refresh_token)
    row = db.execute(
        text(
            "UPDATE auth.refresh_tokens SET revocado = true "
            "WHERE token_hash = :hash AND revocado = false "
            "RETURNING usuario_id"
        ),
        {"hash": token_hash},
    ).first()
    if row is not None:
        _registrar_auditoria(
            db, Accion.LOGOUT, row.usuario_id, None, ip, user_agent
        )
    db.commit()


def cambiar_password(
    db: Session,
    usuario_id: UUID,
    password_actual: str,
    password_nueva: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or usuario.estado != EstadoUsuario.activo:
        raise UsuarioInactivo()
    if not verify_password(password_actual, usuario.password_hash):
        _registrar_auditoria(
            db, Accion.CAMBIO_PASSWORD_FALLIDO, usuario_id, None, ip, user_agent
        )
        db.commit()
        raise PasswordActualIncorrecta()
    usuario.password_hash = hash_password(password_nueva)
    usuario.debe_cambiar_password = False
    _registrar_auditoria(db, Accion.CAMBIO_PASSWORD, usuario_id, None, ip, user_agent)
    # Revocar todos los refresh existentes: fuerza re-login en otras sesiones.
    db.execute(
        text(
            "UPDATE auth.refresh_tokens SET revocado = true "
            "WHERE usuario_id = :id AND revocado = false"
        ),
        {"id": str(usuario_id)},
    )
    db.commit()


def obtener_perfil(db: Session, usuario_id: UUID) -> dict[str, Any]:
    """Devuelve datos para `/auth/me`."""
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise AuthError("usuario no encontrado")
    return {
        "id": usuario.id,
        "usuario": usuario.usuario,
        "nombre_completo": usuario.nombre_completo,
        "email": usuario.email,
        "rol": _rol_codigo(db, usuario.rol_id),
        "centros_costo": _centros_costo_directos(db, usuario.id),
        "debe_cambiar_password": bool(usuario.debe_cambiar_password),
    }
