"""Job: detectar resoluciones manuales pedido<->CCMN obsoletas (§5.1).

Riesgo que cubre: si SIGA agrega un CCMN a la bolsa DESPUES de que un
funcionario resolvio, la resolucion sigue ahi sin avisar. El funcionario eligio
entre 3 candidatos; ahora hay 4 y puede que el nuevo sea el correcto.

Que hace: por cada resolucion activa, compara los candidatos guardados al
crearla (`candidatos_al_crear`) contra los candidatos actuales de la bolsa en
SIGA. Si cambiaron, sella `revision_pendiente_desde` y guarda los candidatos
nuevos en `candidatos_en_revision`.

Que NO hace: nunca revoca sola. Quitar el juicio de un humano sin avisar seria
exactamente el fallo silencioso que toda esta refactorizacion evita (§2, §7).
Solo marca; el funcionario decide.

Solo lectura sobre SIGA (regla 2). Escribe en Postgres.

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5.1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.repositories import pipeline_repo

logger = logging.getLogger(__name__)


@dataclass
class ResultadoRevision:
    """Resumen de una corrida, para el endpoint admin y el log."""

    revisadas: int = 0
    marcadas: int = 0
    resueltas: int = 0        # la bolsa volvio a coincidir -> se desmarcan
    errores: int = 0
    detalle: list[dict] = field(default_factory=list)


def revisar_resoluciones_obsoletas(
    ano: int | None = None,
) -> ResultadoRevision:
    """Recorre las resoluciones activas y marca las que quedaron obsoletas.

    Idempotente: correrlo dos veces seguidas no cambia nada la segunda vez.
    Si la bolsa vuelve a coincidir con lo guardado (p.ej. SIGA revirtio un
    cambio), se limpia la marca — el aviso no debe quedar pegado.
    """
    res = ResultadoRevision()
    ano_eje = ano or settings.ANO_VIGENTE
    sec_ejec = int(settings.SEC_EJEC)

    with SessionLocal() as db:
        activas = db.execute(
            text(
                """
                SELECT id, tipo_bien, tipo_pedido, nro_pedido,
                       nro_consolid, candidatos_al_crear,
                       revision_pendiente_desde
                  FROM sistema.resolucion_pedido_ccmn
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                   AND revocado_en IS NULL
                """
            ),
            {"ano": ano_eje, "sec_ejec": sec_ejec},
        ).mappings().all()

        for r in activas:
            res.revisadas += 1
            try:
                _revisar_una(db, r, ano_eje, res)
            except Exception:  # noqa: BLE001 — una fila mala no frena el job
                res.errores += 1
                logger.exception(
                    "revisar_resoluciones: fallo en resolucion %s", r["id"]
                )

        db.commit()

    logger.info(
        "revisar_resoluciones: %d revisadas, %d marcadas, %d resueltas, %d errores",
        res.revisadas, res.marcadas, res.resueltas, res.errores,
    )
    return res


def _revisar_una(db, r, ano_eje: int, res: ResultadoRevision) -> None:
    """Compara una resolucion contra los candidatos actuales de su bolsa."""
    guardados = sorted(r["candidatos_al_crear"] or [])

    ctx = pipeline_repo.contexto_pedido_bolsa(
        ano_eje,
        str(r["tipo_bien"]).strip(),
        str(r["tipo_pedido"]).strip(),
        int(r["nro_pedido"]),
    )
    actuales = sorted((ctx or {}).get("candidatos") or [])

    ya_marcada = r["revision_pendiente_desde"] is not None
    cambio = actuales != guardados

    # Foto vacia al crear (resoluciones previas a esta migracion): no hay con
    # que comparar, se siembra sin marcar para no generar avisos falsos.
    if not guardados:
        db.execute(
            text(
                """
                UPDATE sistema.resolucion_pedido_ccmn
                   SET candidatos_al_crear = :actuales
                 WHERE id = :id
                """
            ),
            {"id": r["id"], "actuales": actuales},
        )
        return

    if cambio and not ya_marcada:
        db.execute(
            text(
                """
                UPDATE sistema.resolucion_pedido_ccmn
                   SET revision_pendiente_desde = now(),
                       candidatos_en_revision = :actuales
                 WHERE id = :id
                """
            ),
            {"id": r["id"], "actuales": actuales},
        )
        res.marcadas += 1
        res.detalle.append({
            "id": str(r["id"]),
            "nro_pedido": int(r["nro_pedido"]),
            "tipo_bien": str(r["tipo_bien"]).strip(),
            "antes": guardados,
            "ahora": actuales,
            "aparecieron": sorted(set(actuales) - set(guardados)),
            "desaparecieron": sorted(set(guardados) - set(actuales)),
        })
    elif cambio and ya_marcada:
        # Sigue obsoleta pero la bolsa cambio otra vez: refrescar la foto.
        db.execute(
            text(
                "UPDATE sistema.resolucion_pedido_ccmn "
                "SET candidatos_en_revision = :actuales WHERE id = :id"
            ),
            {"id": r["id"], "actuales": actuales},
        )
    elif not cambio and ya_marcada:
        # La bolsa volvio a coincidir: el aviso ya no aplica, se limpia.
        db.execute(
            text(
                """
                UPDATE sistema.resolucion_pedido_ccmn
                   SET revision_pendiente_desde = NULL,
                       candidatos_en_revision = NULL
                 WHERE id = :id
                """
            ),
            {"id": r["id"]},
        )
        res.resueltas += 1
