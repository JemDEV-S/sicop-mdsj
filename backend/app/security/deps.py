"""Dependencies FastAPI de autenticación/autorización.

- `get_current_user_id`  → valida JWT y devuelve solo el UUID (barato, sin DB).
- `get_current_user`     → valida JWT + carga usuario, rol y CC permitidos.
- `require_role(*roles)` → factory de dependencies que exige rol específico.
- `get_client_ip` / `get_user_agent` → helpers para auditoría.

El `CurrentUser` es un dataclass inmutable que viaja por el request y expone:
- id, usuario, rol (CodigoRol), nombre_completo
- centros_permitidos: list[str] | None    (None = admin ve todo)

La resolución de CC se hace en cada request (no se confía en el claim `cc` del
JWT) para que los cambios de asignación surtan efecto sin re-login.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import Usuario
from app.models.enums import CodigoRol, EstadoUsuario
from app.security.jwt import TokenInvalido, decodificar_access_token
from app.services import permisos_service

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Snapshot del usuario autenticado + permisos resueltos para este request."""

    id: UUID
    usuario: str
    nombre_completo: str
    rol: CodigoRol
    centros_permitidos: list[str] | None  # None = admin (sin filtro)

    @property
    def es_admin(self) -> bool:
        return self.rol == CodigoRol.admin

    def puede_ver_centro(self, codigo_cc: str) -> bool:
        """True si el usuario puede consultar datos del CC indicado."""
        if self.centros_permitidos is None:
            return True
        return codigo_cc in self.centros_permitidos


def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UUID:
    """Valida el header Authorization: Bearer <token> y devuelve `sub` como UUID."""
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decodificar_access_token(creds.credentials)
    except TokenInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"token invalido: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token sin sub valido",
        ) from exc


def get_current_user(
    usuario_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Carga el usuario desde DB y resuelve rol + CC permitidos.

    Se ejecuta en cada request protegido. Rechaza usuarios inactivos/bloqueados
    aunque el JWT sea válido (evita usar tokens de sesiones ya revocadas por
    admin).
    """
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="usuario no encontrado",
        )
    if usuario.estado != EstadoUsuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="usuario inactivo",
        )

    # Rol: convertir el CodigoRol del ORM a valor puro.
    rol = usuario.rol.codigo if hasattr(usuario, "rol") and usuario.rol else None
    if rol is None:
        # Sin relationship precargada, consultar por rol_id.
        from app.models.auth import Rol  # import local para evitar ciclos

        rol_row = db.get(Rol, usuario.rol_id)
        if rol_row is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="rol no encontrado",
            )
        rol = rol_row.codigo

    rol_enum = rol if isinstance(rol, CodigoRol) else CodigoRol(str(rol))

    centros = permisos_service.resolver_centros_permitidos(db, usuario.id, rol_enum)

    return CurrentUser(
        id=usuario.id,
        usuario=usuario.usuario,
        nombre_completo=usuario.nombre_completo,
        rol=rol_enum,
        centros_permitidos=centros,
    )


def require_role(*roles_permitidos: CodigoRol):
    """Factory de dependency que exige que el usuario tenga uno de los roles dados.

    Uso:
        @router.get("/admin/algo", dependencies=[Depends(require_role(CodigoRol.admin))])
        def endpoint(user: CurrentUser = Depends(get_current_user)): ...
    """
    if not roles_permitidos:
        raise ValueError("require_role necesita al menos un rol")

    permitidos = frozenset(roles_permitidos)

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.rol not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "rol_insuficiente",
                    "detail": f"rol {user.rol.value} no autorizado",
                    "roles_requeridos": [r.value for r in permitidos],
                },
            )
        return user

    return _dependency


def get_client_ip(request: Request) -> str | None:
    """Extrae la IP del cliente. Respeta X-Forwarded-For si viene del proxy.

    Valida que sea IPv4/IPv6 válida antes de devolverla (columna `logs.auditoria.ip`
    es de tipo `inet`). Devuelve None si no lo es (ej. TestClient usa "testclient").
    """
    candidato: str | None = None
    xff = request.headers.get("x-forwarded-for")
    if xff:
        candidato = xff.split(",")[0].strip()
    elif request.client:
        candidato = request.client.host

    if not candidato:
        return None
    try:
        ipaddress.ip_address(candidato)
    except ValueError:
        return None
    return candidato


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")
