"""Endpoints del buzon ciudadano (HU-24).

- `POST /publico/obras/{codigo}/observaciones` (con captcha, rate-limit 5/hora/IP).
- `GET /admin/observaciones-ciudadanas` (revision por Admin).
- `PATCH /admin/observaciones-ciudadanas/{id}` (marcar estado / responder).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import CodigoRol
from app.schemas.observaciones import (
    ObservacionAdminItem,
    ObservacionCreate,
    ObservacionResponse,
    ObservacionUpdate,
)
from app.security.deps import (
    CurrentUser,
    get_client_ip,
    require_role,
)
from app.services import auditoria_service, rate_limit
from app.services.recaptcha_service import CaptchaInvalido, verificar

publico_router = APIRouter(prefix="/publico/obras", tags=["publico-obras"])
admin_router = APIRouter(
    prefix="/admin/observaciones-ciudadanas", tags=["admin-observaciones"]
)

# HU-24 §4.7: 5 posts por hora por IP.
_MAX_HITS = 5
_VENTANA = 3600


@publico_router.post(
    "/{codigo_unico}/observaciones",
    response_model=ObservacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_observacion(
    codigo_unico: str,
    payload: ObservacionCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> ObservacionResponse:
    ip = get_client_ip(request) or "sin-ip"
    if not rate_limit.permitir(
        f"obs:{ip}", max_hits=_MAX_HITS, ventana_seg=_VENTANA
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="demasiadas observaciones desde esta IP, intente mas tarde",
        )

    # Validar captcha (o saltar en dev sin secret).
    try:
        score = verificar(payload.captcha_token or "", ip=ip if ip != "sin-ip" else None)
    except CaptchaInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"captcha invalido: {exc}",
        ) from exc

    # Verificar que la obra exista.
    obra = db.execute(
        text(
            "SELECT 1 FROM siaf.inversiones WHERE codigo_unico = :c LIMIT 1"
        ),
        {"c": codigo_unico},
    ).first()
    if obra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"obra {codigo_unico} no encontrada",
        )

    row = db.execute(
        text(
            """
            INSERT INTO sistema.observaciones_ciudadanas (
                codigo_unico_obra, nombre_ciudadano, email_ciudadano,
                texto, ip_origen, captcha_score
            ) VALUES (
                :codigo, :nombre, :email, :texto, CAST(:ip AS inet), :score
            )
            RETURNING id, codigo_unico_obra, estado, creado_en
            """
        ),
        {
            "codigo": codigo_unico,
            "nombre": payload.nombre,
            "email": payload.email,
            "texto": payload.texto,
            "ip": ip if ip != "sin-ip" else None,
            "score": score,
        },
    ).mappings().first()

    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="observacion_publicada",
        detalle={
            "codigo_unico_obra": codigo_unico,
            "observacion_id": str(row["id"]),
        },
    )
    db.commit()

    return ObservacionResponse(
        id=row["id"],
        codigo_unico_obra=row["codigo_unico_obra"],
        estado=row["estado"],
        creado_en=row["creado_en"],
    )


# ─── Admin ────────────────────────────────────────────────────────────────

@admin_router.get("", response_model=list[ObservacionAdminItem])
def listar_observaciones(
    estado: str | None = None,
    codigo_unico: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _: CurrentUser = Depends(require_role(CodigoRol.admin, CodigoRol.decisor)),
    db: Session = Depends(get_db),
) -> list[ObservacionAdminItem]:
    where = []
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if estado:
        where.append("estado = CAST(:estado AS estado_observacion)")
        params["estado"] = estado
    if codigo_unico:
        where.append("codigo_unico_obra = :codigo")
        params["codigo"] = codigo_unico
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    rows = db.execute(
        text(
            f"""
            SELECT id, codigo_unico_obra, nombre_ciudadano, email_ciudadano,
                   texto, estado, creado_en, revisado_en, respuesta_interna
              FROM sistema.observaciones_ciudadanas
              {where_sql}
             ORDER BY creado_en DESC
             LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()
    return [ObservacionAdminItem.model_validate(dict(r)) for r in rows]


@admin_router.patch("/{obs_id}", response_model=ObservacionAdminItem)
def actualizar_observacion(
    obs_id: UUID,
    payload: ObservacionUpdate,
    request: Request,
    user: CurrentUser = Depends(require_role(CodigoRol.admin, CodigoRol.decisor)),
    db: Session = Depends(get_db),
) -> ObservacionAdminItem:
    row = db.execute(
        text(
            """
            UPDATE sistema.observaciones_ciudadanas
               SET estado = CAST(:estado AS estado_observacion),
                   respuesta_interna = COALESCE(:respuesta, respuesta_interna),
                   revisado_por = :usuario,
                   revisado_en = now()
             WHERE id = :id
             RETURNING id, codigo_unico_obra, nombre_ciudadano, email_ciudadano,
                       texto, estado, creado_en, revisado_en, respuesta_interna
            """
        ),
        {
            "id": str(obs_id),
            "estado": payload.estado,
            "respuesta": payload.respuesta_interna,
            "usuario": str(user.id),
        },
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="observacion no encontrada"
        )

    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="revision_alerta",
        usuario_id=user.id,
        detalle={"observacion_id": str(obs_id), "estado": payload.estado},
    )
    db.commit()
    return ObservacionAdminItem.model_validate(dict(row))
