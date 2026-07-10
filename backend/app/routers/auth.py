"""Endpoints de autenticación.

- POST /auth/login             — usuario+password → access token + refresh cookie
- POST /auth/refresh           — cookie refresh   → nuevo access token
- POST /auth/logout            — cookie refresh   → revoca y borra cookie
- POST /auth/cambiar-password  — usuario autenticado
- GET  /auth/me                — perfil del usuario autenticado

Ver `Docs/actividad-3-arquitectura-tecnica.md` §4.3 y §7.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    CambiarPasswordRequest,
    LoginRequest,
    MeResponse,
    TokenResponse,
)
from app.security.deps import get_client_ip, get_current_user_id, get_user_agent
from app.services import auth_service as svc

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str, expira_en: datetime) -> None:
    max_age = max(0, int((expira_en - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=False,  # TODO: True en producción cuando haya TLS (T-59)
        samesite="lax",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/")


def _mapear_error(exc: svc.AuthError) -> HTTPException:
    """Traduce AuthError → HTTPException con status semántico."""
    if isinstance(exc, svc.UsuarioBloqueado):
        return HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "code": exc.codigo,
                "detail": "usuario bloqueado por intentos fallidos",
                "hasta": exc.hasta.isoformat(),
            },
        )
    if isinstance(exc, svc.UsuarioInactivo):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": exc.codigo, "detail": "usuario inactivo"},
        )
    if isinstance(exc, svc.RefreshInvalido):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.codigo, "detail": "refresh token invalido"},
        )
    if isinstance(exc, svc.PasswordActualIncorrecta):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.codigo, "detail": "contrasena actual incorrecta"},
        )
    # Fallback: credenciales inválidas y AuthError base
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": getattr(exc, "codigo", "auth_error"), "detail": "credenciales invalidas"},
    )


# ─── Endpoints ──────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    try:
        resultado = svc.login(db, payload.usuario, payload.password, ip, ua)
    except svc.AuthError as exc:
        raise _mapear_error(exc) from exc

    _set_refresh_cookie(response, resultado.refresh_token, resultado.refresh_expira_en)
    return TokenResponse(
        access_token=resultado.access_token,
        expira_en_segundos=resultado.access_expira_en_segundos,
        debe_cambiar_password=resultado.debe_cambiar_password,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "refresh_ausente", "detail": "cookie refresh no presente"},
        )
    try:
        resultado = svc.refresh_access(db, refresh_token)
    except svc.AuthError as exc:
        raise _mapear_error(exc) from exc
    return TokenResponse(
        access_token=resultado.access_token,
        expira_en_segundos=resultado.access_expira_en_segundos,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> Response:
    if refresh_token:
        svc.logout(db, refresh_token, get_client_ip(request), get_user_agent(request))
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/cambiar-password", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_password(
    payload: CambiarPasswordRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    usuario_id: UUID = Depends(get_current_user_id),
) -> Response:
    try:
        svc.cambiar_password(
            db,
            usuario_id,
            payload.password_actual,
            payload.password_nueva,
            get_client_ip(request),
            get_user_agent(request),
        )
    except svc.AuthError as exc:
        raise _mapear_error(exc) from exc
    # Fuerza re-login en el cliente al invalidar todos los refresh tokens.
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_db),
    usuario_id: UUID = Depends(get_current_user_id),
) -> Any:
    try:
        return svc.obtener_perfil(db, usuario_id)
    except svc.AuthError as exc:
        raise _mapear_error(exc) from exc
