"""Servicio de permisos — resuelve centros de costo visibles por usuario.

Regla RN-04 (Docs/actividad-2-requerimientos-funcionales.md §2):
- Admin           → sin filtro (None = todos los CC).
- Operativo       → solo los CC directamente asignados en `auth.usuarios_centros_costo`.
- Decisor         → todos los CC bajo la jerarquía de cada CC asignado (usa ltree
                    `ruta <@ 'root.<codigo>'`). Los flags `es_raiz_jerarquia` de
                    la asignación indican que ese CC es "cabeza" de una gerencia.
- Ciudadano       → lista vacía (no debería consultar endpoints protegidos por CC).

Diseño clave:
- La expansión por jerarquía NO es recursiva manual: se apoya en el índice GIST
  sobre `ref.centros_costo.ruta` (ltree) creado en la migración inicial. Esto
  hace la resolución O(log n) y evita CTEs recursivos.
- Devuelve la lista *deduplicada y ordenada* de códigos de CC.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.enums import CodigoRol


def resolver_centros_permitidos(
    db: Session,
    usuario_id: UUID,
    rol: CodigoRol | str,
) -> list[str] | None:
    """Devuelve los CC visibles por el usuario según su rol.

    - `None` = sin filtro (admin ve todo).
    - `[]`   = sin CC (ciudadano o usuario sin asignaciones).
    - `[...]` = lista explícita ordenada y deduplicada.
    """
    rol_codigo = rol.value if isinstance(rol, CodigoRol) else str(rol)

    if rol_codigo == CodigoRol.admin.value:
        return None

    if rol_codigo == CodigoRol.ciudadano.value:
        return []

    if rol_codigo == CodigoRol.operativo.value:
        return _centros_directos(db, usuario_id)

    if rol_codigo == CodigoRol.decisor.value:
        return _centros_por_jerarquia(db, usuario_id)

    # Rol desconocido → tratar como sin acceso.
    return []


def _centros_directos(db: Session, usuario_id: UUID) -> list[str]:
    """CC asignados directamente al usuario (Operativo y fallback de Decisor)."""
    rows = db.execute(
        text(
            """
            SELECT centro_costo
              FROM auth.usuarios_centros_costo
             WHERE usuario_id = :uid
             ORDER BY centro_costo
            """
        ),
        {"uid": str(usuario_id)},
    ).all()
    return [r[0] for r in rows]


def _centros_por_jerarquia(db: Session, usuario_id: UUID) -> list[str]:
    """Expande la jerarquía ltree para cada CC asignado al decisor.

    Estrategia: por cada CC asignado, buscamos su `ruta` y luego traemos todos
    los CC cuya `ruta` es descendiente de esa (operador `<@` de ltree). Un
    único query hace ambas cosas con un self-join.
    """
    rows = db.execute(
        text(
            """
            SELECT DISTINCT descendientes.codigo
              FROM auth.usuarios_centros_costo asignados
              JOIN ref.centros_costo raiz
                ON raiz.codigo = asignados.centro_costo
              JOIN ref.centros_costo descendientes
                ON descendientes.ruta <@ raiz.ruta
             WHERE asignados.usuario_id = :uid
               AND descendientes.activo = true
             ORDER BY descendientes.codigo
            """
        ),
        {"uid": str(usuario_id)},
    ).all()
    return [r[0] for r in rows]
