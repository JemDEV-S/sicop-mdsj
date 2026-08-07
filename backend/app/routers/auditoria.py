"""Consulta de auditoría — admin-only (idea-principal §8, actividad-3 §3.6).

Expone `logs.auditoria` como una vista filtrable para el administrador: quién
hizo qué, cuándo, desde dónde. Complementa la ESCRITURA de auditoría (que ocurre
en todo el sistema vía `auditoria_service`) con su LECTURA controlada.

Protegido con `require_role(admin)`: la traza de accesos es información sensible;
solo el administrador la consulta.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import CodigoRol
from app.schemas.auditoria import AccionCatalogo, AuditoriaItem, AuditoriaListado
from app.security.deps import require_role

router = APIRouter(prefix="/interno/admin/auditoria", tags=["admin-auditoria"])


@router.get("", response_model=AuditoriaListado)
def listar_auditoria(
    response: Response,
    accion: str | None = Query(None, description="Filtra por código de acción exacto."),
    usuario_id: UUID | None = Query(None, description="Filtra por usuario."),
    desde: datetime | None = Query(None, description="Límite inferior de creado_en."),
    hasta: datetime | None = Query(None, description="Límite superior de creado_en."),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _=Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> AuditoriaListado:
    """Listado paginado de eventos, más reciente primero.

    Los filtros se combinan con AND. El índice `ix_auditoria_accion_creado` y
    `ix_auditoria_usuario_creado` cubren los dos filtros más comunes.
    """
    where = ["1 = 1"]
    params: dict = {}
    if accion:
        where.append("a.accion = :accion")
        params["accion"] = accion
    if usuario_id:
        where.append("a.usuario_id = :usuario_id")
        params["usuario_id"] = str(usuario_id)
    if desde:
        where.append("a.creado_en >= :desde")
        params["desde"] = desde
    if hasta:
        where.append("a.creado_en <= :hasta")
        params["hasta"] = hasta
    where_sql = " AND ".join(where)

    total = db.execute(
        text(f"SELECT COUNT(*) FROM logs.auditoria a WHERE {where_sql}"),
        params,
    ).scalar_one()

    offset = (page - 1) * size
    rows = db.execute(
        text(
            f"""
            SELECT a.id, a.usuario_id, u.nombre_completo AS usuario_nombre,
                   a.accion, a.detalle, host(a.ip) AS ip, a.user_agent,
                   a.creado_en
              FROM logs.auditoria a
              LEFT JOIN auth.usuarios u ON u.id = a.usuario_id
             WHERE {where_sql}
             ORDER BY a.creado_en DESC, a.id DESC
             LIMIT :limit OFFSET :offset
            """
        ),
        {**params, "limit": size, "offset": offset},
    ).mappings().all()

    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Total-Pages"] = str(max(1, (total + size - 1) // size))
    return AuditoriaListado(
        items=[AuditoriaItem.model_validate(dict(r)) for r in rows],
        total=total,
        page=page,
        size=size,
    )


@router.get("/acciones", response_model=list[AccionCatalogo])
def catalogo_acciones(
    _=Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> list[AccionCatalogo]:
    """Acciones distintas presentes en el log con su conteo — puebla el filtro.

    Es dinámico (lo que realmente ocurrió) en vez de una lista fija de códigos:
    así el filtro refleja el estado real del sistema sin mantenerlo a mano.
    """
    rows = db.execute(
        text(
            """
            SELECT accion, COUNT(*) AS total
              FROM logs.auditoria
             GROUP BY accion
             ORDER BY total DESC, accion
            """
        )
    ).mappings().all()
    return [AccionCatalogo.model_validate(dict(r)) for r in rows]
