"""Servicio transversal de auditoría (RN-05).

Helper único para insertar en `logs.auditoria`. Uso desde routers y servicios
para dejar rastro de acciones sensibles:

  - login exitoso / fallido / bloqueo
  - logout, cambio de contraseña
  - exportación de reportes
  - cambio de umbrales / alertas
  - subida de documentos de obra
  - publicación de observaciones ciudadanas

Diseño:
- `registrar(...)` inserta en la sesión actual (no hace commit). El caller
  decide cuándo commitear — así se agrupan escrituras en la misma transacción
  que la acción auditada (patrón unit-of-work).
- `registrar_desde_request(...)` extrae automáticamente IP + user-agent del
  `Request` de FastAPI y llama a `registrar`.
- `_serializar_detalle(...)` convierte el `dict` a JSON con `default=str` para
  cubrir `datetime`, `UUID`, `Decimal`, etc. sin que el caller tenga que
  preocuparse.

Códigos de acción canónicos — mantener sincronizado con `Docs/actividad-3` §10.2:
    login_exitoso, login_fallido, logout,
    cambio_password, cambio_password_fallido,
    exportacion_reporte,
    cambio_umbral, cambio_alerta,
    subida_documento_obra,
    observacion_publicada,
    revision_alerta.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.security.deps import get_client_ip, get_user_agent

logger = logging.getLogger(__name__)


# Acciones canónicas — se exponen como constantes para autocompletado y para
# evitar typos en strings mágicas dispersas por el código.
class Accion:
    LOGIN_EXITOSO = "login_exitoso"
    LOGIN_FALLIDO = "login_fallido"
    LOGOUT = "logout"
    CAMBIO_PASSWORD = "cambio_password"
    CAMBIO_PASSWORD_FALLIDO = "cambio_password_fallido"
    EXPORTACION_REPORTE = "exportacion_reporte"
    CAMBIO_UMBRAL = "cambio_umbral"
    CAMBIO_ALERTA = "cambio_alerta"
    SUBIDA_DOCUMENTO_OBRA = "subida_documento_obra"
    OBSERVACION_PUBLICADA = "observacion_publicada"
    REVISION_ALERTA = "revision_alerta"


def registrar(
    db: Session,
    *,
    accion: str,
    usuario_id: UUID | None = None,
    detalle: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Inserta una fila en `logs.auditoria` en la sesión actual.

    No commitea — el caller es responsable de la transacción. Ideal para agrupar
    la auditoría con la acción auditada (login → intentos_fallidos + auditoría
    en el mismo commit).

    Si el INSERT falla, se loguea el error pero NO se propaga: nunca queremos
    que la falla en auditoría tumbe la operación principal.
    """
    try:
        db.execute(
            text(
                """
                INSERT INTO logs.auditoria
                       (usuario_id, accion, detalle, ip, user_agent)
                VALUES (:usuario_id, :accion, CAST(:detalle AS jsonb), :ip, :user_agent)
                """
            ),
            {
                "usuario_id": str(usuario_id) if usuario_id else None,
                "accion": accion,
                "detalle": _serializar_detalle(detalle),
                "ip": ip,
                "user_agent": user_agent,
            },
        )
    except Exception as exc:  # noqa: BLE001 — audit debe ser best-effort
        logger.warning(
            "no se pudo registrar auditoria (accion=%s usuario=%s): %s",
            accion,
            usuario_id,
            exc,
        )


def registrar_desde_request(
    db: Session,
    request: Request,
    *,
    accion: str,
    usuario_id: UUID | None = None,
    detalle: dict[str, Any] | None = None,
) -> None:
    """Igual que `registrar` pero extrae IP + user-agent del Request FastAPI."""
    registrar(
        db,
        accion=accion,
        usuario_id=usuario_id,
        detalle=detalle,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


def _serializar_detalle(detalle: dict[str, Any] | None) -> str | None:
    """Convierte `dict` → JSON string apto para CAST(... AS jsonb).

    `default=str` maneja `datetime`, `UUID`, `Decimal`, `Enum`, etc.
    """
    if detalle is None:
        return None
    return json.dumps(detalle, default=str)
