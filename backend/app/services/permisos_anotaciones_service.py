"""Resolución de alcance por CC para anotaciones internas.

Las anotaciones se guardan por `entidad_tipo + entidad_id`, sin un CC propio
(ver `sistema.anotaciones_internas`). Para aplicar la regla municipal de que
"la dependencia trabaja como equipo" (alcance por unidad, no por usuario) hay
que resolver a qué centro de costo pertenece la entidad anotada y validar que
está dentro del alcance del usuario (RN-04).

Diseño:
- Solo `pedido` tiene un CC amarrado de forma directa y verificada en SIGA
  (`SIG_PEDIDOS.CENTRO_COSTO`, la misma columna que usa el pipeline). Se valida
  su alcance.
- `orden` NO tiene columna de CC en SIGA (verificado: SIG_ORDEN_ADQUISICION no
  expone CENTRO_COSTO ni SEC_FUNC directos). Derivar su CC exige recorrer la
  cadena orden→presupuesto→meta→CC, costosa y frágil; se difiere. Mientras
  tanto la orden se trata como transversal (no se bloquea), igual que
  meta/obra/contrato. No se inventa una llave que SIGA no expone (regla CLAUDE.md
  "no inventar"). Amarre orden↔CC: mejora futura, misma línea que contratos §5.2.
- La resolución de pedido consulta SIGA (solo lectura, SEC_EJEC fijo). Devuelve
  el código de CC ya trimmed o `None` si no se encuentra / no tiene CC.
- `verificar_alcance_entidad` es el punto de entrada del router: lanza 403 si la
  entidad cae fuera del alcance; no hace nada si el usuario es admin o si la
  entidad es de un tipo transversal.

Formato de `entidad_id` (lo fija el frontend, ver features/pipeline/api.ts):
- pedido: "{NRO_PEDIDO}-{TIPO_BIEN}"   (ej. "1234-S"). No trae TIPO_PEDIDO, así
  que basta el par (nro, tipo_bien) para ubicar el CC.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text

from app.config import settings
from app.security.deps import CurrentUser
from app.siga.conexion import get_connection

# Tipos de entidad con CC directo y verificado en SIGA → se validan por alcance.
# El resto (orden / meta / obra / contrato) son transversales aquí: no se
# bloquean (ver docstring del módulo para el porqué de `orden`).
_TIPOS_CON_CC = {"pedido"}


def _parsear_id(entidad_id: str) -> tuple[int, str] | None:
    """"{numero}-{TIPO_BIEN}" → (numero, tipo_bien). None si no parsea."""
    partes = entidad_id.rsplit("-", 1)
    if len(partes) != 2:
        return None
    numero_str, tipo_bien = partes[0].strip(), partes[1].strip().upper()
    if not numero_str.isdigit() or tipo_bien not in ("B", "S"):
        return None
    return int(numero_str), tipo_bien


def _cc_de_pedido(numero: int, tipo_bien: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            text(
                """
                SELECT TOP 1 LTRIM(RTRIM(p.CENTRO_COSTO)) AS cc
                  FROM SIG_PEDIDOS p
                 WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
                   AND p.TIPO_BIEN = :tipo AND p.NRO_PEDIDO = :nro
                   AND p.CENTRO_COSTO IS NOT NULL
                """
            ),
            {
                "ano": settings.ANO_VIGENTE,
                "sec_ejec": settings.SEC_EJEC,
                "tipo": tipo_bien,
                "nro": numero,
            },
        ).first()
    return row[0] if row and row[0] else None


def resolver_cc_entidad(entidad_tipo: str, entidad_id: str) -> str | None:
    """CC de la entidad anotada, o None si no aplica / no se encuentra."""
    if entidad_tipo not in _TIPOS_CON_CC:
        return None
    parsed = _parsear_id(entidad_id)
    if parsed is None:
        return None
    numero, tipo_bien = parsed
    return _cc_de_pedido(numero, tipo_bien)


def verificar_alcance_entidad(
    user: CurrentUser, entidad_tipo: str, entidad_id: str
) -> None:
    """Lanza 403 si la anotación cae fuera del alcance de CC del usuario.

    - Admin (centros_permitidos is None): siempre permitido.
    - Tipo transversal (meta/obra/contrato): permitido (no tiene CC propio).
    - Pedido/orden: se resuelve el CC contra SIGA y se exige que esté en el
      alcance. Si la entidad no se encuentra o no tiene CC, se niega a los
      usuarios restringidos (preferimos negar que asumir, igual que el pipeline).
    """
    if user.centros_permitidos is None:
        return
    if entidad_tipo not in _TIPOS_CON_CC:
        return
    cc = resolver_cc_entidad(entidad_tipo, entidad_id)
    if not cc or cc not in user.centros_permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="entidad fuera del alcance del usuario",
        )
