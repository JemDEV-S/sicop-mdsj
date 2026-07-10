"""Endpoints de anotaciones internas (HU-10 AC-10.4).

Almacen: `sistema.anotaciones_internas` (PostgreSQL).
`entidad_tipo` es un ENUM: pedido | orden | meta | obra | contrato.
El `entidad_id` es el identificador logico (para pedido: "NRO_PEDIDO/TIPO_BIEN").
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.anotaciones import AnotacionCreate, AnotacionResponse
from app.security.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/interno/anotaciones", tags=["interno-anotaciones"])

_TIPOS_VALIDOS = {"pedido", "orden", "meta", "obra", "contrato"}


def _validar_tipo(tipo: str) -> None:
    if tipo not in _TIPOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"entidad_tipo invalido: {tipo}. Validos: {sorted(_TIPOS_VALIDOS)}",
        )


@router.get(
    "/{entidad_tipo}/{entidad_id}",
    response_model=list[AnotacionResponse],
)
def listar_anotaciones(
    entidad_tipo: str = Path(...),
    entidad_id: str = Path(...),
    _: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AnotacionResponse]:
    _validar_tipo(entidad_tipo)
    rows = db.execute(
        text(
            """
            SELECT a.id, a.entidad_tipo::text AS entidad_tipo,
                   a.entidad_id, a.usuario_id,
                   u.nombre_completo AS usuario_nombre,
                   a.texto, a.creado_en
              FROM sistema.anotaciones_internas a
              LEFT JOIN auth.usuarios u ON u.id = a.usuario_id
             WHERE a.entidad_tipo = CAST(:tipo AS tipo_entidad_anotacion)
               AND a.entidad_id = :id
             ORDER BY a.creado_en DESC
            """
        ),
        {"tipo": entidad_tipo, "id": entidad_id},
    ).mappings().all()
    return [AnotacionResponse.model_validate(dict(r)) for r in rows]


@router.post(
    "/{entidad_tipo}/{entidad_id}",
    response_model=AnotacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_anotacion(
    payload: AnotacionCreate,
    entidad_tipo: str = Path(...),
    entidad_id: str = Path(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnotacionResponse:
    _validar_tipo(entidad_tipo)
    row = db.execute(
        text(
            """
            INSERT INTO sistema.anotaciones_internas (
                entidad_tipo, entidad_id, usuario_id, texto
            )
            VALUES (CAST(:tipo AS tipo_entidad_anotacion), :id, :usr, :texto)
            RETURNING id, entidad_tipo::text AS entidad_tipo,
                      entidad_id, usuario_id, texto, creado_en
            """
        ),
        {
            "tipo": entidad_tipo,
            "id": entidad_id,
            "usr": str(user.id),
            "texto": payload.texto,
        },
    ).mappings().first()
    db.commit()
    return AnotacionResponse.model_validate(
        {**dict(row), "usuario_nombre": user.nombre_completo}
    )


@router.delete(
    "/{anotacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_anotacion(
    anotacion_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """El autor o un admin puede borrar. Otros roles: 403."""
    row = db.execute(
        text(
            "SELECT usuario_id FROM sistema.anotaciones_internas WHERE id = :id"
        ),
        {"id": anotacion_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="anotacion no encontrada")
    if str(row.usuario_id) != str(user.id) and not user.es_admin:
        raise HTTPException(
            status_code=403, detail="solo el autor o un admin pueden borrar"
        )
    db.execute(
        text("DELETE FROM sistema.anotaciones_internas WHERE id = :id"),
        {"id": anotacion_id},
    )
    db.commit()
