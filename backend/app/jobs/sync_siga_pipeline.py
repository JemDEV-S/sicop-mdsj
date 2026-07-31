"""Job: snapshot del pipeline SIGA (SQL Server) -> PostgreSQL siga.*.

Guia Pipeline v2 §01. El kanban dejo de consultar SIGA en caliente: este job
sincroniza las tablas del pipeline a Postgres y las vistas leen de ahi.

Estrategia por tabla (§01.2):
    - Tablas pequeñas (<5k/año) que mas cambian de estado: recarga COMPLETA por
      año en cada corrida — mas barato y simple que la logica incremental.
    - Tablas grandes (pedido_items 8k, seguimiento_estados 16k): watermark por
      FECHA_REG/FECHA_ESTADO (solo se trae WHERE fecha > ultima_fecha).
    - bolsas (SIG_CUADRO_MODIFICADO_CMN): sin FECHA_REG -> recarga completa.

Todo SELECT fija SEC_EJEC=300687 y ANO_EJE=<año> (RN-01). SIGA es solo lectura
(RN-02): toda escritura va a Postgres.

Ejecucion:
    python -m app.jobs.sync_siga_pipeline
    python -m app.jobs.sync_siga_pipeline --ano 2025
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import SessionLocal
from app.jobs.siga_extractores import EXTRACTOR_SEGUIMIENTO, EXTRACTORES, Extractor
from app.siga.conexion import get_connection

logger = logging.getLogger(__name__)

JOB_NAME = "siga_pipeline"


@dataclass
class ResultadoSync:
    ano: int
    tablas: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.tablas.values())


# ─── Watermarks (sistema.sync_watermarks) ────────────────────────────────


def _leer_watermark(conn: Connection, tabla: str, ano: int) -> datetime | None:
    row = conn.execute(
        text(
            """
            SELECT ultima_fecha FROM sistema.sync_watermarks
             WHERE tabla = :t AND ano_eje = :a
            """
        ),
        {"t": tabla, "a": ano},
    ).first()
    return row[0] if row else None


def _guardar_watermark(
    conn: Connection, tabla: str, ano: int, ultima_fecha: datetime | None, filas: int
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO sistema.sync_watermarks
                   (tabla, ano_eje, ultima_fecha, ultima_corrida, filas)
            VALUES (:t, :a, :f, now(), :n)
            ON CONFLICT (tabla, ano_eje) DO UPDATE SET
                ultima_fecha = COALESCE(EXCLUDED.ultima_fecha,
                                        sistema.sync_watermarks.ultima_fecha),
                ultima_corrida = now(),
                filas = EXCLUDED.filas
            """
        ),
        {"t": tabla, "a": ano, "f": ultima_fecha, "n": filas},
    )


# ─── Registro en logs.sincronizacion (mismo patron que sync_siaf) ────────


def _registrar_inicio(conn: Connection, ano: int) -> int:
    row = conn.execute(
        text(
            """
            INSERT INTO logs.sincronizacion (job, estado)
            VALUES (:job, 'en_curso') RETURNING id
            """
        ),
        {"job": f"{JOB_NAME}:{ano}"},
    ).first()
    return int(row.id)  # type: ignore[union-attr]


def _registrar_fin(
    conn: Connection, sync_id: int, *, ok: bool, n: int, error: str | None = None
) -> None:
    conn.execute(
        text(
            """
            UPDATE logs.sincronizacion
               SET estado = :estado, fin = now(),
                   registros_procesados = :n, error_mensaje = :err
             WHERE id = :id
            """
        ),
        {
            "id": sync_id,
            "estado": "exito" if ok else "error",
            "n": n,
            "err": (error or "")[:2000] or None,
        },
    )


# ─── Motor de sincronizacion de una tabla ────────────────────────────────


def _upsert(pg: Connection, ext: Extractor, filas: list[dict[str, Any]]) -> None:
    """UPSERT por PK (o INSERT si la recarga ya limpio la tabla)."""
    if not filas:
        return
    cols = ext.columnas
    col_list = ", ".join(cols)
    val_list = ", ".join(f":{c}" for c in cols)
    if ext.recarga_completa:
        stmt = text(
            f"INSERT INTO siga.{ext.destino} ({col_list}) VALUES ({val_list})"
        )
    else:
        no_pk = [c for c in cols if c not in ext.pk]
        # Si todas las columnas son PK (p. ej. bolsas), no hay nada que
        # actualizar: DO NOTHING. Un DO UPDATE SET vacio es error de sintaxis.
        conflicto = (
            f"DO UPDATE SET {', '.join(f'{c} = EXCLUDED.{c}' for c in no_pk)}"
            if no_pk else "DO NOTHING"
        )
        stmt = text(
            f"INSERT INTO siga.{ext.destino} ({col_list}) VALUES ({val_list}) "
            f"ON CONFLICT ({', '.join(ext.pk)}) {conflicto}"
        )
    lote = 500
    for i in range(0, len(filas), lote):
        pg.execute(stmt, filas[i : i + lote])


def _sincronizar_tabla(
    siga: Connection, pg: Connection, ext: Extractor, ano: int
) -> int:
    """Extrae de SIGA y escribe en Postgres una tabla. Devuelve nº de filas."""
    watermark = None
    if ext.watermark:
        watermark = _leer_watermark(pg, ext.destino, ano)

    params: dict[str, Any] = {"ano": ano, "sec_ejec": int(settings.SEC_EJEC)}
    if ext.watermark and watermark is not None:
        params["watermark"] = watermark

    sql = ext.sql(con_watermark=ext.watermark and watermark is not None)
    filas = [ext.mapear(dict(r)) for r in siga.execute(text(sql), params).mappings()]

    if ext.recarga_completa:
        pg.execute(
            text(f"DELETE FROM siga.{ext.destino} WHERE {ext.filtro_ano}"),
            {"ano": ano},
        )

    _upsert(pg, ext, filas)

    if ext.watermark:
        nueva_fecha = max(
            (f[ext.col_fecha] for f in filas if f.get(ext.col_fecha)),
            default=watermark,
        )
        n_total = pg.execute(
            text(f"SELECT COUNT(*) FROM siga.{ext.destino} WHERE {ext.filtro_ano}"),
            {"ano": ano},
        ).scalar_one()
        _guardar_watermark(pg, ext.destino, ano, nueva_fecha, int(n_total))

    return len(filas)


def _refrescar_vista(engine: Any) -> None:
    """REFRESH de la vista materializada del kanban tras un sync.

    CONCURRENTLY exige indice unico (existe) y no bloquea lecturas. Si falla
    (p. ej. primer refresh sin datos), cae a un refresh normal. El error no
    aborta el sync: los datos ya estan en las tablas base.
    """
    try:
        with engine.begin() as pg:
            pg.execute(
                text("REFRESH MATERIALIZED VIEW CONCURRENTLY siga.v_pipeline_pedido")
            )
    except Exception:
        logger.warning("REFRESH CONCURRENTLY fallo; intentando refresh normal",
                       exc_info=True)
        try:
            with engine.begin() as pg:
                pg.execute(text("REFRESH MATERIALIZED VIEW siga.v_pipeline_pedido"))
        except Exception:
            logger.exception("REFRESH de la vista del pipeline fallo")


def _correr(
    extractores: list[Extractor], ano: int, *, job_sufijo: str
) -> ResultadoSync:
    """Sincroniza una lista de extractores para un año, con registro en logs.

    Cada tabla va en su propia transaccion Postgres: si una falla, las ya
    sincronizadas quedan firmes y el error se registra. SIGA se toca en una
    sola conexion de lectura (RN-02) para toda la corrida.
    """
    resultado = ResultadoSync(ano=ano)
    session = SessionLocal()
    engine = session.get_bind()
    with engine.begin() as pg:
        sync_id = _registrar_inicio(pg, ano)

    try:
        with get_connection() as siga:
            for ext in extractores:
                with engine.begin() as pg:
                    n = _sincronizar_tabla(siga, pg, ext, ano)
                resultado.tablas[ext.destino] = n
                logger.info("sync siga.%s: %d filas", ext.destino, n)

        # Al final de cada sync se refresca la vista materializada del kanban
        # (§01.1). CONCURRENTLY para no bloquear las lecturas en curso.
        _refrescar_vista(engine)

        with engine.begin() as pg:
            _registrar_fin(pg, sync_id, ok=True, n=resultado.total)
        logger.info(
            "sync_siga_%s OK: ano=%d filas=%d", job_sufijo, ano, resultado.total
        )
        return resultado

    except Exception as exc:
        with engine.begin() as pg:
            _registrar_fin(
                pg, sync_id, ok=False, n=resultado.total,
                error=f"{type(exc).__name__}: {exc}",
            )
        logger.exception("sync_siga_%s FALLO", job_sufijo)
        raise
    finally:
        session.close()


def sync_siga_pipeline(
    ano: int | None = None, solo: list[str] | None = None
) -> ResultadoSync:
    """Sincroniza las tablas del pipeline (todas o las de `solo`) para un año."""
    ano_ejec = ano if ano is not None else settings.ANO_VIGENTE
    extractores = [e for e in EXTRACTORES if solo is None or e.destino in solo]
    return _correr(extractores, ano_ejec, job_sufijo="pipeline")


def sync_siga_seguimiento(ano: int | None = None) -> ResultadoSync:
    """Sincroniza el timeline de seguimiento (tabla grande, watermark, §01.3)."""
    ano_ejec = ano if ano is not None else settings.ANO_VIGENTE
    return _correr([EXTRACTOR_SEGUIMIENTO], ano_ejec, job_sufijo="seguimiento")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza pipeline SIGA -> Postgres")
    parser.add_argument("--ano", type=int, default=None)
    parser.add_argument(
        "--solo", type=str, default=None,
        help="Lista separada por comas de tablas destino a sincronizar",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    solo = args.solo.split(",") if args.solo else None
    try:
        r = sync_siga_pipeline(args.ano, solo)
    except Exception:
        return 1
    print(f"[OK] ano={r.ano} total={r.total} " + " ".join(
        f"{k}={v}" for k, v in r.tablas.items()
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
