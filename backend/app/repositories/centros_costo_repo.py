"""Repositorio: `ref.centros_costo` con jerarquia ltree.

RN-04 (jerarquia CC): decisores ven todos los descendientes; el ltree operador
`<@ 'root.<codigo>'` resuelve la subarbol con el indice GIST — no queries
recursivas manuales (CLAUDE.md §11).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def listar_centros_costo(
    db: Session,
    *,
    solo_activos: bool = True,
    solo_con_presupuesto: bool = False,
) -> list[dict[str, Any]]:
    where = []
    if solo_activos:
        where.append("activo = true")
    if solo_con_presupuesto:
        where.append("flag_presupuesto = true")
    where_sql = " AND ".join(where) or "true"
    rows = (
        db.execute(
            text(
                f"""
                SELECT codigo, nombre, abreviado, centro_padre,
                       ruta::text AS ruta, nivel, activo, flag_presupuesto
                  FROM ref.centros_costo
                 WHERE {where_sql}
              ORDER BY ruta
                """
            )
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def obtener_centro_costo(db: Session, *, codigo: str) -> dict[str, Any] | None:
    row = (
        db.execute(
            text(
                """
                SELECT codigo, nombre, abreviado, centro_padre,
                       ruta::text AS ruta, nivel, activo, flag_presupuesto,
                       flag_cn, flag_ppr, tipo_dependencia, nro_personal, sede
                  FROM ref.centros_costo
                 WHERE codigo = :codigo
                """
            ),
            {"codigo": codigo},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def descendientes_cc(
    db: Session, *, codigo_raiz: str, solo_activos: bool = True
) -> list[str]:
    """Devuelve todos los codigos de CC descendientes de `codigo_raiz` (incluido el).

    Usa el indice GIST sobre `ruta` (ltree) — una sola query, sin recursion
    manual. Se compone `root.<codigo>` porque la raiz del arbol es `root` (ver
    `ltree_builder.py`).
    """
    where_activo = " AND activo = true" if solo_activos else ""
    sql = f"""
        SELECT codigo
          FROM ref.centros_costo
         WHERE ruta <@ CAST(:raiz AS ltree){where_activo}
      ORDER BY ruta
    """
    rows = db.execute(text(sql), {"raiz": f"root.{codigo_raiz}"}).all()
    return [r.codigo for r in rows]


def ancestros_cc(db: Session, *, codigo: str) -> list[dict[str, Any]]:
    """Devuelve la cadena desde la raiz hasta el CC, ordenada por nivel."""
    rows = (
        db.execute(
            text(
                """
                WITH me AS (
                    SELECT ruta FROM ref.centros_costo WHERE codigo = :codigo
                )
                SELECT c.codigo, c.nombre, c.nivel, c.ruta::text AS ruta
                  FROM ref.centros_costo c, me
                 WHERE me.ruta <@ c.ruta  -- c es ancestro (o el mismo) de me
              ORDER BY c.nivel
                """
            ),
            {"codigo": codigo},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def metas_de_centro(
    db: Session, *, codigo_cc: str, ano: int
) -> list[dict[str, Any]]:
    """Devuelve las metas asignadas a un CC en un ano, via `ref.metas_centro_costo`."""
    rows = (
        db.execute(
            text(
                """
                SELECT DISTINCT m.sec_func, m.meta, m.nombre, m.tipo_meta,
                                m.funcion, m.programa, m.act_proy
                  FROM ref.metas m
                  JOIN ref.metas_centro_costo mcc USING (sec_func)
                 WHERE mcc.centro_costo = :cc
                   AND m.ano_eje = :ano
                   AND m.activo = true
              ORDER BY m.sec_func
                """
            ),
            {"cc": codigo_cc, "ano": ano},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]
