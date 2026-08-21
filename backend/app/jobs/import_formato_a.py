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
    "expediente", "ano_eje", "mes_corte", "sec_ejec", "ciclo", "fase",
    "fase_nombre", "sub_reg", "correlativo", "secuencia_padre", "origen",
    "tipo_op", "mod_compra", "producto_proyecto", "funcion", "meta", "sec_func",
    "clasificador", "rubro", "rubro_nombre", "tipo_financ", "cod_doc",
    "num_doc", "fecha_doc", "tipo_giro", "tipo_prov", "proveedor_ruc",
    "proveedor_nombre", "monto_origen", "monto_soles", "fecha_aprobacion",
    "fecha_proceso", "sec_est", "est_registro", "certificado",
    "certificado_secuencia",
]


@dataclass
class ResultadoImportFormatoA:
    ano: int
    mes: int | None
    registros: int
    descartadas: int
    resumen_por_fase: dict[str, float]
    ejecutora: str | None
    periodo: str | None


# ─── Helpers logs.sincronizacion (mismo patron que sync_siaf) ───────────────

def _job_id(ano: int, mes: int | None) -> str:
    """Nombre del job para logs.sincronizacion: `formato_a:2026-08` (o `:2026`
    si el mes no se pudo derivar). El mes deja ver la carga por mes en la vista."""
    return f"{JOB_NAME}:{ano}-{mes:02d}" if mes else f"{JOB_NAME}:{ano}"


def _registrar_inicio(conn: Connection, ano: int, mes: int | None) -> int:
    row = conn.execute(
        text(
            """
            INSERT INTO logs.sincronizacion (job, estado)
            VALUES (:job, 'en_curso')
            RETURNING id
            """
        ),
        {"job": _job_id(ano, mes)},
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


# ─── Persistencia: swap atomico por (ano, mes) ───────────────────────────────

def _persistir(
    conn: Connection,
    ano: int,
    mes: int | None,
    filas: list[dict[str, Any]],
    origen_archivo: str,
    emitido_en: Any = None,
) -> None:
    """Reemplaza las filas del `(ano, mes)` con las recien parseadas, en una TX.

    Swap por (año, mes): borra SOLO el mes cargado y mete las nuevas filas. Asi
    se acumula el rastro cargando varios meses (cada expediente avanza de fase
    entre meses) y el mes en curso se recarga a diario sin duplicar (el Formato
    A del mes en curso es acumulado hasta la fecha, asi que la ultima foto
    reemplaza a la anterior del mismo mes).

    Si `mes` es None (cabecera ilegible), cae al swap por año (comportamiento
    previo) para no dejar la tabla a medias.

    `emitido_en` (fecha de emision del reporte) es un unico valor por carga; se
    replica en todas las filas para mostrarlo junto al detalle sin un join extra.
    """
    if mes is not None:
        conn.execute(
            text(
                "DELETE FROM siaf.ejecucion_detalle_siaf "
                "WHERE ano_eje = :ano AND mes_corte = :mes"
            ),
            {"ano": ano, "mes": mes},
        )
    else:
        conn.execute(
            text("DELETE FROM siaf.ejecucion_detalle_siaf WHERE ano_eje = :ano"),
            {"ano": ano},
        )
    if not filas:
        return

    extra = ["origen_archivo", "emitido_en"]
    cols_sql = ", ".join(_COLUMNAS + extra)
    binds_sql = ", ".join(f":{c}" for c in _COLUMNAS + extra)
    stmt = text(
        f"INSERT INTO siaf.ejecucion_detalle_siaf ({cols_sql}) "  # noqa: S608
        f"VALUES ({binds_sql})"
    )
    lote = 500
    for i in range(0, len(filas), lote):
        bloque = filas[i : i + lote]
        params = [
            {
                **f,
                "mes_corte": mes,
                "origen_archivo": origen_archivo,
                "emitido_en": emitido_en,
            }
            for f in bloque
        ]
        conn.execute(stmt, params)


# ─── Entrada principal ───────────────────────────────────────────────────────

def _mes_mas_frecuente(filas: list[dict[str, Any]]) -> int | None:
    """Fallback del mes de corte: el mes de `fecha_doc` mas frecuente entre las
    filas. Solo se usa si la cabecera no trae un PERIODO legible."""
    conteo: dict[int, int] = {}
    for f in filas:
        fd = f.get("fecha_doc")
        if fd is not None:
            conteo[fd.month] = conteo.get(fd.month, 0) + 1
    return max(conteo, key=lambda k: conteo[k]) if conteo else None


def importar_formato_a(
    origen: str | bytes | Any,
    nombre_archivo: str,
    ano: int | None = None,
    mes: int | None = None,
) -> ResultadoImportFormatoA:
    """Parsea el Excel y lo carga en siaf.ejecucion_detalle_siaf.

    `origen`: ruta, bytes o file-like que acepte openpyxl.
    `nombre_archivo`: se guarda como procedencia (origen_archivo) de las filas.
    `ano`: fuerza el ano de carga; si es None se toma de la cabecera del reporte
           (PERIODO) y, en su defecto, del ano de la mayoria de las filas.
    `mes`: fuerza el mes de corte (1-12); si es None se toma del PERIODO de la
           cabecera y, en su defecto, del mes de `fecha_doc` mas frecuente. El
           swap reemplaza SOLO ese (ano, mes): asi se acumulan varios meses.
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
    # swap cargamos SOLO las filas del ano de corte; el resto se ignora para no
    # borrar/mezclar otros anios de forma inconsistente.
    filas_ano = [f for f in filas if f.get("ano_eje") == ano_carga]
    fuera_de_ano = len(filas) - len(filas_ano)

    # Mes de corte: el declarado > el de la cabecera > el mas frecuente por fecha.
    mes_carga = mes or parseo.cabecera.mes or _mes_mas_frecuente(filas_ano)

    session = SessionLocal()
    sync_id = _registrar_inicio(session.connection(), ano_carga, mes_carga)
    try:
        engine = session.get_bind()
        with engine.begin() as conn:
            _persistir(
                conn, ano_carga, mes_carga, filas_ano, nombre_archivo,
                emitido_en=parseo.cabecera.emitido_en,
            )
        with engine.begin() as conn:
            _registrar_fin_exito(conn, sync_id, len(filas_ano))

        resumen = resumen_por_fase(filas_ano)
        logger.info(
            "import_formato_a OK: ano=%d mes=%s registros=%d descartadas=%d "
            "fuera_de_ano=%d",
            ano_carga, mes_carga, len(filas_ano), parseo.descartadas, fuera_de_ano,
        )
        return ResultadoImportFormatoA(
            ano=ano_carga,
            mes=mes_carga,
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
    parser.add_argument(
        "--mes", type=int, default=None,
        help="fuerza el mes de corte (1-12); por defecto sale del PERIODO.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    import os

    try:
        resultado = importar_formato_a(
            args.file, os.path.basename(args.file), args.ano, args.mes
        )
    except Exception:
        return 1

    print(
        f"[OK] ano={resultado.ano} mes={resultado.mes} "
        f"registros={resultado.registros} descartadas={resultado.descartadas}"
    )
    print(f"     ejecutora={resultado.ejecutora} periodo={resultado.periodo}")
    print("     monto S/. por fase (est=A):")
    for fase, monto in sorted(resultado.resumen_por_fase.items()):
        print(f"       {fase}: {monto:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
