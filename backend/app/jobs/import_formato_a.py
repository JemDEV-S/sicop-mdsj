"""Carga del reporte SIAF "Formato A" (Excel) -> siaf.ejecucion_detalle_siaf.

Carga PROVISIONAL: un admin sube el .xlsx del Modulo Administrativo. Se parsea
con `app.services.formato_a` y se persiste con el patron staging + swap atomico
POR ANO (igual que `sync_siaf`): solo se reemplazan las filas del ano cargado,
otros anios sobreviven.

Se registra en `logs.sincronizacion` con job = "formato_a:<ano>" para que la
vista de estado de sincronizaciones lo muestre junto al resto.

Ejecucion CLI (util para el smoke test):
    python -m app.jobs.import_formato_a --file excel/....xlsx
    python -m app.jobs.import_formato_a --file excel/....xlsx --ano 2026
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import SessionLocal
from app.services.formato_a import (
    ResultadoParseo,
    parsear_formato_a,
    resumen_por_fase,
)

logger = logging.getLogger(__name__)

JOB_NAME = "formato_a"

# Columnas de la tabla en el orden del INSERT (sin id / cargado_en, que son
# autogenerados). `origen_archivo` se rellena aparte.
_COLUMNAS = [
    "expediente", "ano_eje", "sec_ejec", "ciclo", "fase", "fase_nombre",
    "sub_reg", "correlativo", "secuencia_padre", "origen", "tipo_op",
    "mod_compra", "producto_proyecto", "funcion", "meta", "sec_func",
    "clasificador", "rubro", "rubro_nombre", "tipo_financ", "cod_doc",
    "num_doc", "fecha_doc", "tipo_giro", "tipo_prov", "proveedor_ruc",
    "proveedor_nombre", "monto_origen", "monto_soles", "fecha_aprobacion",
    "fecha_proceso", "sec_est", "est_registro", "certificado",
    "certificado_secuencia",
]


@dataclass
class ResultadoImportFormatoA:
    ano: int
    registros: int
    descartadas: int
    resumen_por_fase: dict[str, float]
    ejecutora: str | None
    periodo: str | None


# ─── Helpers logs.sincronizacion (mismo patron que sync_siaf) ───────────────

def _registrar_inicio(conn: Connection, ano: int) -> int:
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
               SET estado = 'exito', fin = now(), registros_procesados = :n
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
               SET estado = 'error', fin = now(), error_mensaje = :msg
             WHERE id = :id
            """
        ),
        {"id": sync_id, "msg": mensaje[:2000]},
    )
    conn.commit()


# ─── Persistencia: swap atomico por ano ──────────────────────────────────────

def _persistir(
    conn: Connection, ano: int, filas: list[dict[str, Any]], origen_archivo: str
) -> None:
    """Reemplaza las filas del `ano` con las recien parseadas, en una sola TX."""
    conn.execute(
        text("DELETE FROM siaf.ejecucion_detalle_siaf WHERE ano_eje = :ano"),
        {"ano": ano},
    )
    if not filas:
        return

    cols_sql = ", ".join(_COLUMNAS + ["origen_archivo"])
    binds_sql = ", ".join(f":{c}" for c in _COLUMNAS) + ", :origen_archivo"
    stmt = text(
        f"INSERT INTO siaf.ejecucion_detalle_siaf ({cols_sql}) "  # noqa: S608
        f"VALUES ({binds_sql})"
    )
    lote = 500
    for i in range(0, len(filas), lote):
        bloque = filas[i : i + lote]
        params = [{**f, "origen_archivo": origen_archivo} for f in bloque]
        conn.execute(stmt, params)


# ─── Entrada principal ───────────────────────────────────────────────────────

def importar_formato_a(
    origen: str | bytes | Any,
    nombre_archivo: str,
    ano: int | None = None,
) -> ResultadoImportFormatoA:
    """Parsea el Excel y lo carga en siaf.ejecucion_detalle_siaf.

    `origen`: ruta, bytes o file-like que acepte openpyxl.
    `nombre_archivo`: se guarda como procedencia (origen_archivo) de las filas.
    `ano`: fuerza el ano de carga; si es None se toma de la cabecera del reporte
           (PERIODO) y, en su defecto, del ano de la mayoria de las filas.
    """
    parseo: ResultadoParseo = parsear_formato_a(origen)
    filas = parseo.filas

    ano_carga = ano or parseo.cabecera.ano
    if ano_carga is None and filas:
        # Fallback: ano mas frecuente entre las filas.
        conteo: dict[int, int] = {}
        for f in filas:
            a = f.get("ano_eje")
            if a is not None:
                conteo[a] = conteo.get(a, 0) + 1
        if conteo:
            ano_carga = max(conteo, key=lambda k: conteo[k])
    if ano_carga is None:
        ano_carga = settings.ANO_VIGENTE

    # El Formato A puede traer filas de ejercicios anteriores (rezagos). Para el
    # swap por ano cargamos SOLO las filas del ano de corte; el resto se ignora
    # para no borrar/mezclar otros anios de forma inconsistente.
    filas_ano = [f for f in filas if f.get("ano_eje") == ano_carga]
    fuera_de_ano = len(filas) - len(filas_ano)

    session = SessionLocal()
    sync_id = _registrar_inicio(session.connection(), ano_carga)
    try:
        engine = session.get_bind()
        with engine.begin() as conn:
            _persistir(conn, ano_carga, filas_ano, nombre_archivo)
        with engine.begin() as conn:
            _registrar_fin_exito(conn, sync_id, len(filas_ano))

        resumen = resumen_por_fase(filas_ano)
        logger.info(
            "import_formato_a OK: ano=%d registros=%d descartadas=%d "
            "fuera_de_ano=%d",
            ano_carga, len(filas_ano), parseo.descartadas, fuera_de_ano,
        )
        return ResultadoImportFormatoA(
            ano=ano_carga,
            registros=len(filas_ano),
            descartadas=parseo.descartadas + fuera_de_ano,
            resumen_por_fase=resumen,
            ejecutora=parseo.cabecera.ejecutora,
            periodo=parseo.cabecera.periodo,
        )
    except Exception as exc:
        engine = session.get_bind()
        with engine.begin() as conn:
            mensaje = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            _registrar_fin_error(conn, sync_id, mensaje)
        logger.exception("import_formato_a FALLO")
        raise
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Carga un Excel SIAF Formato A -> PostgreSQL"
    )
    parser.add_argument("--file", required=True, help="ruta al .xlsx")
    parser.add_argument("--ano", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    import os

    try:
        resultado = importar_formato_a(
            args.file, os.path.basename(args.file), args.ano
        )
    except Exception:
        return 1

    print(
        f"[OK] ano={resultado.ano} registros={resultado.registros} "
        f"descartadas={resultado.descartadas}"
    )
    print(f"     ejecutora={resultado.ejecutora} periodo={resultado.periodo}")
    print("     monto S/. por fase (est=A):")
    for fase, monto in sorted(resultado.resumen_por_fase.items()):
        print(f"       {fase}: {monto:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
