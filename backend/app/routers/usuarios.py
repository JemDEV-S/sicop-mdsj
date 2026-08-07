"""Gestión de usuarios — admin-only (HU-17 · T-08/T-54).

CRUD de usuarios internos + asignación de centros de costo. Es la pantalla que
hace operable la jerarquía de acceso (T-56): sin ella, asignar CC se haría a
mano en la BD.

Todo protegido con `require_role(admin)` y auditado. La contraseña inicial de un
usuario nuevo es su DNI; el cambio posterior es opcional (ver usuarios_service).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import CodigoRol, EstadoUsuario
from app.repositories import centros_costo_repo
from app.schemas.auth import CentroCostoBreve
from app.schemas.usuarios import (
    AsignacionCentroCrear,
    ResetPasswordResponse,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioDetalle,
    UsuarioItem,
    UsuariosListado,
)
from app.security.deps import CurrentUser, require_role
from app.services import auditoria_service, usuarios_service
from app.services.usuarios_service import UsuarioError

router = APIRouter(prefix="/interno/admin/usuarios", tags=["admin-usuarios"])

# Dependency reutilizable: exige admin y expone el usuario actual (para las
# salvaguardas de auto-gestión y la auditoría).
_admin = require_role(CodigoRol.admin)


def _raise(exc: UsuarioError) -> HTTPException:
    return HTTPException(status_code=exc.codigo, detail=exc.mensaje)


@router.get("", response_model=UsuariosListado)
def listar(
    q: str | None = Query(None, description="Busca en nombre, usuario o DNI."),
    rol: CodigoRol | None = None,
    estado: EstadoUsuario | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    _: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> UsuariosListado:
    items, total = usuarios_service.listar_usuarios(
        db, q=q, rol=rol, estado=estado, limit=size, offset=(page - 1) * size
    )
    return UsuariosListado(
        items=[UsuarioItem.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/centros-costo", response_model=list[CentroCostoBreve])
def centros_costo_disponibles(
    _: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> list[CentroCostoBreve]:
    """Árbol de CC de la entidad para el selector de asignación (todos, activos).

    El admin ve toda la municipalidad, así que no se filtra por alcance.
    """
    filas = centros_costo_repo.listar_centros_costo(db, solo_activos=True)
    return [
        CentroCostoBreve(codigo=f["codigo"], nombre=f["nombre"], abreviado=f["abreviado"])
        for f in filas
    ]


@router.get("/{usuario_id}", response_model=UsuarioDetalle)
def obtener(
    usuario_id: UUID,
    _: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> UsuarioDetalle:
    detalle = usuarios_service.obtener_usuario(db, usuario_id)
    if detalle is None:
        raise HTTPException(status_code=404, detail="usuario no encontrado")
    return UsuarioDetalle.model_validate(detalle)


@router.post("", response_model=UsuarioDetalle, status_code=status.HTTP_201_CREATED)
def crear(
    payload: UsuarioCrear,
    request: Request,
    user: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> UsuarioDetalle:
    try:
        uid = usuarios_service.crear_usuario(
            db,
            usuario=payload.usuario,
            nombre_completo=payload.nombre_completo,
            dni=payload.dni,
            rol=payload.rol,
            email=payload.email,
        )
    except UsuarioError as exc:
        raise _raise(exc) from exc
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion=auditoria_service.Accion.USUARIO_CREADO,
        usuario_id=user.id,
        detalle={"objetivo_id": str(uid), "usuario": payload.usuario, "rol": payload.rol.value},
    )
    db.commit()
    return UsuarioDetalle.model_validate(usuarios_service.obtener_usuario(db, uid))


@router.patch("/{usuario_id}", response_model=UsuarioDetalle)
def actualizar(
    usuario_id: UUID,
    payload: UsuarioActualizar,
    request: Request,
    user: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> UsuarioDetalle:
    try:
        usuarios_service.actualizar_usuario(
            db,
            objetivo_id=usuario_id,
            actor_id=user.id,
            nombre_completo=payload.nombre_completo,
            email=payload.email,
            rol=payload.rol,
            estado=payload.estado,
        )
    except UsuarioError as exc:
        raise _raise(exc) from exc
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion=auditoria_service.Accion.USUARIO_ACTUALIZADO,
        usuario_id=user.id,
        detalle={
            "objetivo_id": str(usuario_id),
            "cambios": payload.model_dump(exclude_none=True, mode="json"),
        },
    )
    db.commit()
    detalle = usuarios_service.obtener_usuario(db, usuario_id)
    if detalle is None:
        raise HTTPException(status_code=404, detail="usuario no encontrado")
    return UsuarioDetalle.model_validate(detalle)


@router.post("/{usuario_id}/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    usuario_id: UUID,
    request: Request,
    user: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> ResetPasswordResponse:
    try:
        usuarios_service.resetear_password_a_dni(db, usuario_id)
    except UsuarioError as exc:
        raise _raise(exc) from exc
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion=auditoria_service.Accion.USUARIO_PASSWORD_RESET,
        usuario_id=user.id,
        detalle={"objetivo_id": str(usuario_id)},
    )
    db.commit()
    return ResetPasswordResponse(
        ok=True, mensaje="Contraseña restablecida al DNI del usuario."
    )


@router.post(
    "/{usuario_id}/centros", response_model=UsuarioDetalle, status_code=status.HTTP_201_CREATED
)
def asignar_centro(
    usuario_id: UUID,
    payload: AsignacionCentroCrear,
    request: Request,
    user: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> UsuarioDetalle:
    try:
        usuarios_service.asignar_centro(
            db,
            usuario_id=usuario_id,
            centro_costo=payload.centro_costo,
            es_raiz_jerarquia=payload.es_raiz_jerarquia,
        )
    except UsuarioError as exc:
        raise _raise(exc) from exc
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion=auditoria_service.Accion.USUARIO_CC_ASIGNADO,
        usuario_id=user.id,
        detalle={
            "objetivo_id": str(usuario_id),
            "centro_costo": payload.centro_costo,
            "es_raiz_jerarquia": payload.es_raiz_jerarquia,
        },
    )
    db.commit()
    return UsuarioDetalle.model_validate(usuarios_service.obtener_usuario(db, usuario_id))


@router.delete(
    "/{usuario_id}/centros/{centro_costo}", response_model=UsuarioDetalle
)
def quitar_centro(
    usuario_id: UUID,
    centro_costo: str,
    request: Request,
    user: CurrentUser = Depends(_admin),
    db: Session = Depends(get_db),
) -> UsuarioDetalle:
    usuarios_service.quitar_centro(db, usuario_id=usuario_id, centro_costo=centro_costo)
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion=auditoria_service.Accion.USUARIO_CC_QUITADO,
        usuario_id=user.id,
        detalle={"objetivo_id": str(usuario_id), "centro_costo": centro_costo},
    )
    db.commit()
    detalle = usuarios_service.obtener_usuario(db, usuario_id)
    if detalle is None:
        raise HTTPException(status_code=404, detail="usuario no encontrado")
    return UsuarioDetalle.model_validate(detalle)
