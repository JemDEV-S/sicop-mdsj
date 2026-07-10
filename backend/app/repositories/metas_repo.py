"""Repositorio: `ref.metas` (espejo local del catalogo META de SIGA).

Se lee de PostgreSQL — no se golpea SIGA en cada request. Ver CLAUDE.md §9:
"Los datos maestros de SIGA NO se consultan contra SIGA en cada request.
Se leen de ref.* (poblado por sync_catalogos_siga)."
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def listar_metas(
    db: Session,
    *,
    ano: int,
    tipo_meta: str | None = None,
    funcion: str | None = None,
    programa: str | None = None,
    solo_activas: bool = True,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Devuelve metas del ano, con filtros opcionales."""
    where = ["ano_eje = :ano"]
    params: dict[str, Any] = {"ano": ano}
    if tipo_meta is not None:
        where.append("tipo_meta = :tipo")
        params["tipo"] = tipo_meta
    if funcion is not None:
        where.append("funcion = :funcion")
        params["funcion"] = funcion
    if programa is not None:
        where.append("programa = :programa")
        params["programa"] = programa
    if solo_activas:
        where.append("activo = true")

    sql = f"""
        SELECT sec_func, ano_eje, meta, nombre, funcion, programa,
               sub_programa, act_proy, componente, finalidad, tipo_meta,
               unidad_med, activo
          FROM ref.metas
         WHERE {" AND ".join(where)}
      ORDER BY sec_func
    """
    if limit is not None:
        sql += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def obtener_meta(db: Session, *, sec_func: int) -> dict[str, Any] | None:
    row = (
        db.execute(
            text(
                """
                SELECT sec_func, ano_eje, meta, nombre, funcion, programa,
                       sub_programa, act_proy, componente, finalidad, tipo_meta,
                       unidad_med, activo
                  FROM ref.metas
                 WHERE sec_func = :sec_func
                """
            ),
            {"sec_func": sec_func},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def contar_metas(db: Session, *, ano: int, solo_activas: bool = True) -> int:
    sql = "SELECT COUNT(*) FROM ref.metas WHERE ano_eje = :ano"
    if solo_activas:
        sql += " AND activo = true"
    return int(db.execute(text(sql), {"ano": ano}).scalar_one())
