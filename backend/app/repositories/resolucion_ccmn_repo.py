"""Resoluciones manuales pedido <-> CCMN (Postgres).

SIGA no vincula pedido y CCMN (§1 del doc de refactorizacion) y la cascada
automatica no siempre desambigua: quedan 158 `ambiguo` + 4 `conflicto` en 2026.
Esta es la via para que un funcionario los resuelva.

Principio de diseno (§5): la resolucion es **referencial y opcional**. El
sistema funciona sin ninguna fila aqui; si se borran todas, solo se pierde
precision en los `ambiguo`. Por eso este repo nunca falla la carga del
pipeline: si la tabla no responde, el pipeline sigue con la cascada.

Escribe en PostgreSQL, jamas en SIGA (regla 2 del proyecto).

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

# Llave del pedido: TIPO_BIEN + TIPO_PEDIDO + NRO_PEDIDO (doc §6).
# NRO_PEDIDO solo no es unico -- 446 colisiones en 2026.
ClavePedido = tuple[str, str, int]


def _clave(tipo_bien: Any, tipo_pedido: Any, nro_pedido: Any) -> ClavePedido:
    return (
        str(tipo_bien or "").strip(),
        str(tipo_pedido or "").strip(),
        int(nro_pedido),
    )


def resoluciones_activas(
    db: Session, *, ano: int, sec_ejec: int
) -> dict[ClavePedido, list[int]]:
    """Mapping pedido -> CCMN asociados manualmente (solo los no revocados).

    Devuelve una LISTA por pedido: la relacion es N:M (§5), un pedido puede
    tener varios CCMN asociados. El orden es por antiguedad de la resolucion.
    """
    rows = db.execute(
        text(
            """
            SELECT tipo_bien, tipo_pedido, nro_pedido, nro_consolid
              FROM sistema.resolucion_pedido_ccmn
             WHERE ano_eje = :ano
               AND sec_ejec = :sec_ejec
               AND revocado_en IS NULL
             ORDER BY creado_en
            """
        ),
        {"ano": ano, "sec_ejec": sec_ejec},
    ).all()

    out: dict[ClavePedido, list[int]] = defaultdict(list)
    for tb, tp, nped, ccmn in rows:
        out[_clave(tb, tp, nped)].append(int(ccmn))
    return dict(out)


def resoluciones_de_pedido(
    db: Session,
    *,
    ano: int,
    sec_ejec: int,
    tipo_bien: str,
    tipo_pedido: str,
    nro_pedido: int,
    incluir_revocadas: bool = False,
) -> list[dict[str, Any]]:
    """Resoluciones de UN pedido, con autoria — para el panel de trazabilidad.

    Con `incluir_revocadas` devuelve tambien el historial: la tabla nunca
    borra, revoca (§5), y la UI debe poder mostrar quien deshizo que.
    """
    filtro = "" if incluir_revocadas else "AND r.revocado_en IS NULL"
    rows = db.execute(
        text(
            f"""
            SELECT r.id, r.nro_consolid, r.sec_cua_mod_sal, r.nota,
                   r.usuario_id, u.nombre_completo AS usuario_nombre,
                   r.creado_en, r.revocado_en, r.revocado_por,
                   ur.nombre_completo AS revocado_por_nombre
              FROM sistema.resolucion_pedido_ccmn r
              LEFT JOIN auth.usuarios u  ON u.id  = r.usuario_id
              LEFT JOIN auth.usuarios ur ON ur.id = r.revocado_por
             WHERE r.ano_eje = :ano
               AND r.sec_ejec = :sec_ejec
               AND r.tipo_bien = :tipo_bien
               AND r.tipo_pedido = :tipo_pedido
               AND r.nro_pedido = :nro_pedido
               {filtro}
             ORDER BY r.creado_en DESC
            """
        ),
        {
            "ano": ano,
            "sec_ejec": sec_ejec,
            "tipo_bien": tipo_bien,
            "tipo_pedido": tipo_pedido,
            "nro_pedido": nro_pedido,
        },
    ).mappings().all()
    return [dict(r) for r in rows]


def obtener_resolucion(
    db: Session, *, resolucion_id: UUID
) -> dict[str, Any] | None:
    """Una resolucion por id, revocada o no.

    Se usa antes de revocar: el alcance de CC (RN-04) se valida contra el
    pedido al que pertenece, y para eso hay que leerla primero.
    """
    row = db.execute(
        text(
            """
            SELECT id, ano_eje, sec_ejec, tipo_bien, tipo_pedido, nro_pedido,
                   nro_consolid, sec_cua_mod_sal, nota, usuario_id,
                   creado_en, revocado_en, revocado_por
              FROM sistema.resolucion_pedido_ccmn
             WHERE id = :id
            """
        ),
        {"id": resolucion_id},
    ).mappings().first()
    return dict(row) if row else None


def crear_resolucion(
    db: Session,
    *,
    ano: int,
    sec_ejec: int,
    tipo_bien: str,
    tipo_pedido: str,
    nro_pedido: int,
    nro_consolid: int,
    sec_cua_mod_sal: int,
    usuario_id: UUID,
    nota: str | None = None,
) -> dict[str, Any]:
    """Asocia un CCMN a un pedido. Idempotente sobre el par activo.

    Si el par ya existe activo devuelve el existente en vez de reventar contra
    `uq_par_activo`: asociar dos veces lo mismo es una accion inocua, no un
    error que deba interrumpir al funcionario.
    """
    row = db.execute(
        text(
            """
            INSERT INTO sistema.resolucion_pedido_ccmn
                (ano_eje, sec_ejec, tipo_bien, tipo_pedido, nro_pedido,
                 nro_consolid, sec_cua_mod_sal, nota, usuario_id)
            VALUES
                (:ano, :sec_ejec, :tipo_bien, :tipo_pedido, :nro_pedido,
                 :nro_consolid, :sec_cua_mod_sal, :nota, :usuario_id)
            ON CONFLICT ON CONSTRAINT uq_par_activo DO NOTHING
            RETURNING id, nro_consolid, creado_en
            """
        ),
        {
            "ano": ano,
            "sec_ejec": sec_ejec,
            "tipo_bien": tipo_bien,
            "tipo_pedido": tipo_pedido,
            "nro_pedido": nro_pedido,
            "nro_consolid": nro_consolid,
            "sec_cua_mod_sal": sec_cua_mod_sal,
            "nota": nota,
            "usuario_id": usuario_id,
        },
    ).mappings().first()

    if row is None:
        # Ya existia activo: lo devolvemos para que el caller responda 200.
        row = db.execute(
            text(
                """
                SELECT id, nro_consolid, creado_en
                  FROM sistema.resolucion_pedido_ccmn
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                   AND tipo_bien = :tipo_bien AND tipo_pedido = :tipo_pedido
                   AND nro_pedido = :nro_pedido AND nro_consolid = :nro_consolid
                   AND revocado_en IS NULL
                """
            ),
            {
                "ano": ano,
                "sec_ejec": sec_ejec,
                "tipo_bien": tipo_bien,
                "tipo_pedido": tipo_pedido,
                "nro_pedido": nro_pedido,
                "nro_consolid": nro_consolid,
            },
        ).mappings().first()

    return dict(row) if row else {}


def revocar_resolucion(
    db: Session, *, resolucion_id: UUID, usuario_id: UUID
) -> bool:
    """Revoca (no borra) una resolucion. Devuelve False si ya estaba revocada.

    La tabla nunca pierde historial: `revocado_en`/`revocado_por` preservan
    quien deshizo que y cuando (§5).
    """
    row = db.execute(
        text(
            """
            UPDATE sistema.resolucion_pedido_ccmn
               SET revocado_en = now(), revocado_por = :usuario_id
             WHERE id = :id AND revocado_en IS NULL
            RETURNING id
            """
        ),
        {"id": resolucion_id, "usuario_id": usuario_id},
    ).first()
    return row is not None
