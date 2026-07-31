"""Job: reconciliacion del snapshot siga.* contra SIGA (§01.2 punto 3).

El sync incremental por watermark no ve updates que no tocan FECHA_REG ni
deletes/renumeraciones (SIGA a veces borra y renumera). Una vez al dia este
barrido compara COUNT(*) y MAX(FECHA_REG) por tabla en SIGA vs Postgres; si
difieren, recarga el año completo de esa tabla (para las de watermark, resetea
el watermark forzando un reload total; las de recarga completa ya se rehacen
enteras en cada corrida, asi que solo se recuentan).

Ejecucion:
    python -m app.jobs.reconciliacion_siga [--ano 2026]
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.jobs.siga_extractores import EXTRACTOR_SEGUIMIENTO, EXTRACTORES, Extractor
from app.jobs.sync_siga_pipeline import _correr
from app.siga.conexion import get_connection

logger = logging.getLogger(__name__)

# Tablas SIGA de origen por destino (para el COUNT en SIGA). Tupla:
#   (tabla_origen, columna_de_año, filtro_extra)
# El filtro_extra replica el WHERE del extractor cuando este no trae toda la
# tabla (p. ej. movimientos_almacen filtra tipos I/R/S y transac=1); sin el, el
# COUNT en SIGA es mayor que el snapshot y la reconciliacion recargaria en vano.
_ORIGEN: dict[str, tuple[str, str, str]] = {
    "pedidos": ("SIG_PEDIDOS", "ANO_EJE", ""),
    "pedido_items": ("SIG_DETALLE_PEDIDOS", "ANO_EJE", ""),
    "bolsas": ("SIG_CUADRO_MODIFICADO_CMN", "ANNO_EJEC", ""),
    "expedientes_ccmn": ("SIG_PAAC_CONSOLIDADO", "ANO_EJE", ""),
    "ordenes": ("SIG_ORDEN_ADQUISICION", "ANO_EJE", ""),
    "certificaciones": ("SIG_CERTIFICACION_FASE", "ANO_EJE", ""),
    "compromisos": ("SIG_EXP_SIGA_DOCU", "ANO_EJE", ""),
    "conformidades": ("SIG_MOVIM_CONFOR_SERVICIO", "ANO_ORDEN", ""),
    "movimientos_almacen": (
        "SIG_MOVIM_ALMACEN", "ANO_EJE",
        "AND TIPO_MOVIMTO IN ('I','R','S') AND TIPO_TRANSAC = 1",
    ),
    "seguimiento_estados": ("SIG_SEGUIMIENTO_ESTADO", "ANO_EJE", ""),
}


@dataclass
class ResultadoReconciliacion:
    ano: int
    revisadas: int = 0
    desfasadas: list[str] = field(default_factory=list)
    recargadas: list[str] = field(default_factory=list)


def _conteo_siga(
    siga: Any, tabla_origen: str, col_ano: str, filtro_extra: str, ano: int
) -> int:
    return int(
        siga.execute(
            text(
                f"SELECT COUNT(*) FROM {tabla_origen} "
                f"WHERE {col_ano} = :ano AND SEC_EJEC = :sec_ejec {filtro_extra}"
            ),
            {"ano": ano, "sec_ejec": int(settings.SEC_EJEC)},
        ).scalar_one()
    )


def _conteo_pg(pg: Any, ext: Extractor, ano: int) -> int:
    return int(
        pg.execute(
            text(f"SELECT COUNT(*) FROM siga.{ext.destino} WHERE {ext.filtro_ano}"),
            {"ano": ano},
        ).scalar_one()
    )


def reconciliacion_siga(ano: int | None = None) -> ResultadoReconciliacion:
    """Compara conteos SIGA vs snapshot y recarga las tablas desfasadas."""
    ano_ejec = ano if ano is not None else settings.ANO_VIGENTE
    res = ResultadoReconciliacion(ano=ano_ejec)

    todos = list(EXTRACTORES) + [EXTRACTOR_SEGUIMIENTO]
    por_destino = {e.destino: e for e in todos if e.destino in _ORIGEN}

    session = SessionLocal()
    engine = session.get_bind()
    try:
        with get_connection() as siga, engine.connect() as pg:
            for destino, ext in por_destino.items():
                tabla_origen, col_ano, filtro_extra = _ORIGEN[destino]
                n_siga = _conteo_siga(
                    siga, tabla_origen, col_ano, filtro_extra, ano_ejec
                )
                n_pg = _conteo_pg(pg, ext, ano_ejec)
                res.revisadas += 1
                if n_siga != n_pg:
                    res.desfasadas.append(f"{destino}({n_pg}->{n_siga})")
                    logger.warning(
                        "reconciliacion: siga.%s desfasada pg=%d siga=%d",
                        destino, n_pg, n_siga,
                    )
    finally:
        session.close()

    if not res.desfasadas:
        logger.info("reconciliacion OK: %d tablas cuadran", res.revisadas)
        return res

    # Recarga total de las desfasadas: para watermark, se borra el watermark
    # para que _correr traiga el año completo; luego se limpia el snapshot.
    desfasadas_destinos = {d.split("(")[0] for d in res.desfasadas}
    with engine.begin() as pg:
        for destino in desfasadas_destinos:
            ext = por_destino[destino]
            pg.execute(
                text(
                    "DELETE FROM sistema.sync_watermarks "
                    "WHERE tabla = :t AND ano_eje = :a"
                ),
                {"t": destino, "a": ano_ejec},
            )
            pg.execute(
                text(f"DELETE FROM siga.{ext.destino} WHERE {ext.filtro_ano}"),
                {"ano": ano_ejec},
            )

    recargar = [por_destino[d] for d in desfasadas_destinos]
    _correr(recargar, ano_ejec, job_sufijo="reconciliacion")
    res.recargadas = sorted(desfasadas_destinos)
    logger.info("reconciliacion: recargadas %s", res.recargadas)
    return res


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcilia snapshot SIGA")
    parser.add_argument("--ano", type=int, default=None)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        r = reconciliacion_siga(args.ano)
    except Exception:
        return 1
    print(
        f"[OK] ano={r.ano} revisadas={r.revisadas} "
        f"desfasadas={r.desfasadas or 'ninguna'} recargadas={r.recargadas or 'ninguna'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
