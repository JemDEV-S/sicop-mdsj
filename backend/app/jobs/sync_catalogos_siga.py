"""Job: sincronización de catálogos SIGA (CC, metas, puente) → PostgreSQL.

Patrón: staging + swap atómico.

1. Registra inicio en `logs.sincronizacion` (fuera de la tx principal).
2. Lee los 3 datasets de SIGA.
3. Abre una transacción:
   - Crea 3 tablas TEMP (staging).
   - Inserta los datos leídos en staging.
   - `TRUNCATE` las 3 tablas finales (RESTART IDENTITY).
   - `INSERT ... SELECT` desde staging → tablas finales.
   - Reconstruye la columna `ruta` (ltree) con BFS.
4. Marca fin exitoso en `logs.sincronizacion`.

Si algo falla, la transacción hace rollback: las tablas ref.* quedan como
estaban antes del job (no se sirve nada a medio poblar). El error se
registra en `logs.sincronizacion`.

Ejecución:
    python -m app.jobs.sync_catalogos_siga
"""

from __future__ import annotations

import logging
import sys
import traceback
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import SessionLocal
from app.jobs.ltree_builder import construir_rutas
from app.siga.catalogos import (
    leer_centros_costo,
    leer_metas,
    leer_metas_centro_costo,
)

logger = logging.getLogger(__name__)

JOB_NAME = "catalogos_siga"


@dataclass
class ResultadoSync:
    centros_costo: int
    metas: int
    metas_centro_costo: int

    def total(self) -> int:
        return self.centros_costo + self.metas + self.metas_centro_costo


# ─── Helpers para logs.sincronizacion ────────────────────────────────────

def _registrar_inicio(conn: Connection, ano: int) -> int:
    """Inserta la fila `en_curso` y devuelve su id."""
    row = conn.execute(
        text(
            """
            INSERT INTO logs.sincronizacion (job, estado)
            VALUES (:job, 'en_curso')
            RETURNING id
            """
        ),
        {"job": f"{JOB_NAME}:{ano}"},
    ).first()
    conn.commit()
    return int(row.id)  # type: ignore[union-attr]


def _registrar_fin_exito(conn: Connection, sync_id: int, procesados: int) -> None:
    conn.execute(
        text(
            """
            UPDATE logs.sincronizacion
               SET estado = 'exito',
                   fin = now(),
                   registros_procesados = :n
             WHERE id = :id
            """
        ),
        {"id": sync_id, "n": procesados},
    )
    conn.commit()


def _registrar_fin_error(conn: Connection, sync_id: int, mensaje: str) -> None:
    conn.execute(
        text(
            """
            UPDATE logs.sincronizacion
               SET estado = 'error',
                   fin = now(),
                   error_mensaje = :msg
             WHERE id = :id
            """
        ),
        {"id": sync_id, "msg": mensaje[:2000]},
    )
    conn.commit()


# ─── Swap dentro de una transacción ──────────────────────────────────────

def _validar_permisos_preservables(conn: Connection) -> None:
    """Verifica que ningún permiso de usuario apunte a un CC que desaparecerá.

    Si un usuario tiene asignado un centro de costo que ya no existe en el
    dataset nuevo, mejor abortar aquí que perder silenciosamente el permiso.
    """
    huerfanos = conn.execute(
        text(
            """
            SELECT ucc.centro_costo, COUNT(*) AS n_permisos
              FROM auth.usuarios_centros_costo ucc
             WHERE NOT EXISTS (
                 SELECT 1 FROM cc_stg s WHERE s.codigo = ucc.centro_costo
             )
             GROUP BY ucc.centro_costo
            """
        )
    ).all()
    if huerfanos:
        detalle = ", ".join(f"{r.centro_costo}({r.n_permisos})" for r in huerfanos)
        raise RuntimeError(
            "El sync eliminaria centros de costo referenciados por "
            f"auth.usuarios_centros_costo: {detalle}. "
            "Revisar antes de continuar."
        )


def _crear_staging(conn: Connection) -> None:
    """Crea tablas TEMP con la misma forma que las finales (menos ruta/ltree)."""
    conn.execute(
        text(
            """
            CREATE TEMP TABLE cc_stg (
                codigo            varchar(15) PRIMARY KEY,
                nombre            varchar(200) NOT NULL,
                abreviado         varchar(60),
                centro_padre      varchar(15),
                sede              smallint,
                tipo_dependencia  char(1),
                nro_personal      smallint,
                flag_cn           boolean,
                flag_presupuesto  boolean,
                flag_ppr          boolean,
                activo            boolean NOT NULL
            ) ON COMMIT DROP
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TEMP TABLE metas_stg (
                sec_func      bigint PRIMARY KEY,
                ano_eje       smallint NOT NULL,
                meta          varchar(5) NOT NULL,
                nombre        varchar(200) NOT NULL,
                funcion       varchar(2),
                programa      varchar(3),
                sub_programa  varchar(4),
                act_proy      varchar(7),
                componente    varchar(7),
                finalidad     varchar(10),
                tipo_meta     varchar(20) NOT NULL,
                unidad_med    varchar(3),
                activo        boolean NOT NULL
            ) ON COMMIT DROP
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TEMP TABLE mcc_stg (
                sec_func       bigint NOT NULL,
                centro_costo   varchar(15) NOT NULL,
                secuencia      smallint NOT NULL,
                fuente_financ  varchar(2),
                tipo_recurso   varchar(2),
                porc_techo     numeric(8,4)
            ) ON COMMIT DROP
            """
        )
    )


def _normalizar_flags_cc(centros: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza flags 0/1 → bool y decimals → int para psycopg2/PG."""
    normalizados = []
    for c in centros:
        d = dict(c)
        for k in ("flag_cn", "flag_presupuesto", "flag_ppr", "activo"):
            v = d.get(k)
            d[k] = None if v is None else bool(v)
        for k in ("sede", "nro_personal"):
            v = d.get(k)
            d[k] = None if v is None else int(v)
        normalizados.append(d)
    return normalizados


def _normalizar_metas(metas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalizadas = []
    for m in metas:
        d = dict(m)
        v = d.get("activo")
        d["activo"] = None if v is None else bool(v)
        for k in ("sec_func", "ano_eje"):
            v = d.get(k)
            if v is not None:
                d[k] = int(v)
        normalizadas.append(d)
    return normalizadas


def _insertar_staging(
    conn: Connection,
    centros: list[dict[str, Any]],
    metas: list[dict[str, Any]],
    mxc: list[dict[str, Any]],
) -> None:
    centros = _normalizar_flags_cc(centros)
    metas = _normalizar_metas(metas)
    if centros:
        conn.execute(
            text(
                """
                INSERT INTO cc_stg (
                    codigo, nombre, abreviado, centro_padre, sede,
                    tipo_dependencia, nro_personal, flag_cn, flag_presupuesto,
                    flag_ppr, activo
                ) VALUES (
                    :codigo, :nombre, :abreviado, :centro_padre, :sede,
                    :tipo_dependencia, :nro_personal, :flag_cn, :flag_presupuesto,
                    :flag_ppr, :activo
                )
                """
            ),
            centros,
        )
    if metas:
        conn.execute(
            text(
                """
                INSERT INTO metas_stg (
                    sec_func, ano_eje, meta, nombre, funcion, programa,
                    sub_programa, act_proy, componente, finalidad, tipo_meta,
                    unidad_med, activo
                ) VALUES (
                    :sec_func, :ano_eje, :meta, :nombre, :funcion, :programa,
                    :sub_programa, :act_proy, :componente, :finalidad, :tipo_meta,
                    :unidad_med, :activo
                )
                """
            ),
            metas,
        )
    if mxc:
        # Deduplicar por (sec_func, centro_costo, secuencia) — la unique constraint
        # existe en la tabla final. Si SIGA tuviera duplicados exactos, el swap
        # fallaría; los eliminamos aquí antes de insertar en staging.
        vistos: set[tuple[int, str, int]] = set()
        deduplicados: list[dict[str, Any]] = []
        for fila in mxc:
            clave = (fila["sec_func"], fila["centro_costo"], fila["secuencia"])
            if clave in vistos:
                continue
            vistos.add(clave)
            deduplicados.append(fila)
        conn.execute(
            text(
                """
                INSERT INTO mcc_stg (
                    sec_func, centro_costo, secuencia, fuente_financ,
                    tipo_recurso, porc_techo
                ) VALUES (
                    :sec_func, :centro_costo, :secuencia, :fuente_financ,
                    :tipo_recurso, :porc_techo
                )
                """
            ),
            deduplicados,
        )


def _swap_atomico(
    conn: Connection,
    rutas: dict[str, tuple[str, int]],
) -> None:
    """TRUNCATE + INSERT SELECT desde staging → tablas finales.

    Orden respetando FKs:
    1. metas_centro_costo (hija de metas y centros_costo) → TRUNCATE primero.
    2. metas y centros_costo → TRUNCATE.
    3. centros_costo primero (metas_centro_costo depende).
    4. metas.
    5. metas_centro_costo.

    TRUNCATE ... RESTART IDENTITY para reiniciar secuencias.
    """
    # ── Vaciado ordenado (DELETE, no TRUNCATE) ──
    # No usamos TRUNCATE porque ref.centros_costo es referenciada por
    # auth.usuarios_centros_costo (permisos de usuarios), y un TRUNCATE
    # CASCADE borraría esas asignaciones. Con DELETE, la FK detecta
    # asignaciones inválidas y aborta el swap — mejor a perderlas.
    conn.execute(text("DELETE FROM ref.metas_centro_costo"))
    conn.execute(text("ALTER SEQUENCE ref.metas_centro_costo_id_seq RESTART WITH 1"))
    conn.execute(text("DELETE FROM ref.metas"))
    # Los permisos de usuario apuntan a centros de costo; validamos que los
    # códigos nuevos sigan cubriendo los referenciados antes de borrar.
    _validar_permisos_preservables(conn)
    conn.execute(text("DELETE FROM ref.centros_costo"))

    # ── Centros de costo: primero con ruta placeholder, luego UPDATE ──
    conn.execute(
        text(
            """
            INSERT INTO ref.centros_costo (
                codigo, nombre, abreviado, centro_padre, ruta, nivel, sede,
                tipo_dependencia, nro_personal, flag_cn, flag_presupuesto,
                flag_ppr, activo
            )
            SELECT
                s.codigo, s.nombre, s.abreviado, s.centro_padre,
                'root'::ltree,                            -- placeholder
                0,                                        -- placeholder
                s.sede, s.tipo_dependencia, s.nro_personal,
                s.flag_cn, s.flag_presupuesto, s.flag_ppr, s.activo
            FROM cc_stg s
            """
        )
    )

    # UPDATE de ruta y nivel calculados por BFS en Python.
    if rutas:
        conn.execute(
            text(
                """
                UPDATE ref.centros_costo AS cc
                   SET ruta = v.ruta::ltree,
                       nivel = v.nivel
                  FROM (VALUES {values}) AS v(codigo, ruta, nivel)
                 WHERE cc.codigo = v.codigo
                """.format(
                    values=", ".join(
                        f"(:c_{i}, :r_{i}, :n_{i})" for i in range(len(rutas))
                    )
                )
            ),
            {
                k: v
                for i, (codigo, (ruta, nivel)) in enumerate(rutas.items())
                for k, v in [
                    (f"c_{i}", codigo),
                    (f"r_{i}", ruta),
                    (f"n_{i}", nivel),
                ]
            },
        )

    # ── Metas ──
    conn.execute(
        text(
            """
            INSERT INTO ref.metas (
                sec_func, ano_eje, meta, nombre, funcion, programa,
                sub_programa, act_proy, componente, finalidad, tipo_meta,
                unidad_med, activo
            )
            SELECT
                sec_func, ano_eje, meta, nombre, funcion, programa,
                sub_programa, act_proy, componente, finalidad, tipo_meta,
                unidad_med, activo
            FROM metas_stg
            """
        )
    )

    # ── Puente metas ↔ centros de costo ──
    conn.execute(
        text(
            """
            INSERT INTO ref.metas_centro_costo (
                sec_func, centro_costo, secuencia, fuente_financ,
                tipo_recurso, porc_techo
            )
            SELECT
                sec_func, centro_costo, secuencia, fuente_financ,
                tipo_recurso, porc_techo
            FROM mcc_stg
            """
        )
    )


# ─── Punto de entrada ────────────────────────────────────────────────────

def sync_catalogos(ano: int | None = None) -> ResultadoSync:
    """Ejecuta el job. Devuelve el conteo de filas por tabla.

    Args:
        ano: año a sincronizar. Por defecto `settings.ANO_VIGENTE`.
    """
    ano_ejec = ano if ano is not None else settings.ANO_VIGENTE

    # 1) Leer SIGA (fuera de la transacción PG — SIGA es solo lectura)
    logger.info("Leyendo SIGA para ano=%s...", ano_ejec)
    centros = leer_centros_costo(ano_ejec)
    metas = leer_metas(ano_ejec)
    mxc = leer_metas_centro_costo(ano_ejec)
    logger.info(
        "SIGA leido: %d centros, %d metas, %d puente_mxc",
        len(centros), len(metas), len(mxc),
    )

    # 2) Registrar inicio en logs.sincronizacion (con commit propio)
    session = SessionLocal()
    conn_meta = session.connection()
    sync_id = _registrar_inicio(conn_meta, ano_ejec)

    try:
        # 3) Calcular rutas ltree en Python (antes de abrir la tx de swap)
        rutas = construir_rutas(centros)

        # 4) Swap atómico
        conn_meta.begin()  # asegura una nueva tx tras el commit del INSERT
        _crear_staging(conn_meta)
        _insertar_staging(conn_meta, centros, metas, mxc)
        _swap_atomico(conn_meta, rutas)
        conn_meta.commit()

        procesados = len(centros) + len(metas) + len(mxc)
        _registrar_fin_exito(conn_meta, sync_id, procesados)
        logger.info(
            "sync_catalogos_siga OK: %d centros, %d metas, %d mxc",
            len(centros), len(metas), len(mxc),
        )
        return ResultadoSync(
            centros_costo=len(centros),
            metas=len(metas),
            metas_centro_costo=len(mxc),
        )

    except Exception as exc:
        conn_meta.rollback()
        mensaje = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        _registrar_fin_error(conn_meta, sync_id, mensaje)
        logger.exception("sync_catalogos_siga FALLO")
        raise
    finally:
        session.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        resultado = sync_catalogos()
    except Exception:
        return 1
    print(
        f"[OK] centros={resultado.centros_costo} "
        f"metas={resultado.metas} "
        f"mxc={resultado.metas_centro_costo}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
