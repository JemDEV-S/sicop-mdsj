"""Emisión y validación de JWT (access y refresh).

- Access token: 15 min por defecto (`APP_JWT_ACCESS_MINUTES`), claims con
  sub/rol/cc según §7.2 del doc de arquitectura.
- Refresh token: 8h por defecto (`APP_JWT_REFRESH_HOURS`). No lleva rol/cc,
  solo `sub` + `jti` para poder revocarlo. El hash del token se guarda en
  `auth.refresh_tokens.token_hash`.

Se usa `python-jose[cryptography]` con algoritmo HS256 sobre `APP_SECRET_KEY`.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


class TokenInvalido(Exception):
    """Firma inválida, token expirado, o payload mal formado."""


# ─── Access token ───────────────────────────────────────────────────────

def crear_access_token(
    usuario_id: UUID,
    rol: str,
    centros_costo: list[str],
) -> tuple[str, datetime]:
    """Devuelve (token, expira_en).

    Args:
        usuario_id: PK de `auth.usuarios` (UUID).
        rol: código del rol (`ciudadano|operativo|decisor|admin`).
        centros_costo: lista de códigos de CC asignados directamente al usuario.
            La expansión por jerarquía se hace en T-09 (middleware).
    """
    ahora = datetime.now(UTC)
    expira = ahora + timedelta(minutes=settings.APP_JWT_ACCESS_MINUTES)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "cc": centros_costo,
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
        "typ": "access",
    }
    token = jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=ALGORITHM)
    return token, expira


def decodificar_access_token(token: str) -> dict[str, Any]:
    """Valida firma y expiración; devuelve el payload."""
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenInvalido(str(exc)) from exc
    if payload.get("typ") != "access":
        raise TokenInvalido("tipo de token invalido")
    return payload


# ─── Refresh token ──────────────────────────────────────────────────────

def crear_refresh_token(usuario_id: UUID) -> tuple[str, str, datetime]:
    """Emite un refresh token opaco (JWT firmado con jti único).

    Returns:
        (token_plaintext, token_hash_sha256, expira_en)

        - `token_plaintext`: se envía en la cookie httpOnly al cliente.
        - `token_hash_sha256`: se persiste en `auth.refresh_tokens.token_hash`.
          Al hacer refresh, buscamos por hash — nunca por plaintext.
    """
    ahora = datetime.now(UTC)
    expira = ahora + timedelta(hours=settings.APP_JWT_REFRESH_HOURS)
    jti = str(uuid4())
    payload = {
        "sub": str(usuario_id),
        "jti": jti,
        "iat": int(ahora.timestamp()),
        "exp": int(expira.timestamp()),
        "typ": "refresh",
    }
    token = jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=ALGORITHM)
    return token, sha256_hex(token), expira


def decodificar_refresh_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenInvalido(str(exc)) from exc
    if payload.get("typ") != "refresh":
        raise TokenInvalido("tipo de token invalido")
    return payload


def sha256_hex(texto: str) -> str:
    """SHA-256 hex — usado para el token_hash del refresh."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
