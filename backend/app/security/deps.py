"""Dependencies FastAPI de autenticación/autorización.

Versión mínima (T-08): solo `get_current_user_id` que valida el access
token y devuelve el UUID del usuario.

T-09 ampliará este módulo con:
- `get_current_user` completo (con rol + CC resueltos por jerarquía)
- `require_role(*roles)` factory
- `get_centros_permitidos(user)`
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.jwt import TokenInvalido, decodificar_access_token

bearer_scheme = HTTPBearer(auto_error=False)


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


def get_client_ip(request: Request) -> str | None:
    """Extrae la IP del cliente. Respeta X-Forwarded-For si viene del proxy.

    Valida que sea IPv4/IPv6 válida antes de devolverla (columna `logs.auditoria.ip`
    es de tipo `inet`). Devuelve None si no lo es (ej. TestClient usa "testclient").
    """
    import ipaddress

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
