"""Job: sincronizacion SIAF ejecucion presupuestal (API MEF -> siaf.ejecucion_presupuestal).

Patron: staging (TEMP TABLE) + swap atomico. Ver `Docs/actividad-3-arquitectura-tecnica.md` §6.1.

Flujo:
    1. Registrar inicio en logs.sincronizacion.
    2. Leer campos maestros (MES_EJE=0): identificacion + clasificadores.
       Consolidamos por sec_func en un dict `maestros`.
    3. Para cada MES_EJE de 0 .. mes_actual: leer montos (8 col) paginados.
    4. Insertar todo en TEMP table `ejec_stg`.
    5. TRUNCATE siaf.ejecucion_presupuestal + INSERT SELECT desde staging.
    6. Marcar fin en logs.sincronizacion.

Ejecucion:
    python -m app.jobs.sync_siaf
    python -m app.jobs.sync_siaf --ano 2025
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import SessionLocal
from app.services.mef_client import (
    MefClient,
    sql_ejecucion_clasificadores,
    sql_ejecucion_identificacion,
    sql_ejecucion_por_mes,
)

logger = logging.getLogger(__name__)

JOB_NAME = "siaf_ejecucion"


@dataclass
class ResultadoSyncSiaf:
    ano: int
    meses: int
    registros: int


# ─── Helpers logs.sincronizacion ─────────────────────────────────────────

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


def _leer_registros(
    client: MefClient, ano: int, mes_top: int
) -> list[dict[str, Any]]:
    """Extrae todos los registros del anio desde datastore_search y filtra por mes."""
    resource = settings.MEF_RESOURCE_EJECUCION
    filas: list[dict[str, Any]] = []
    
    filtros = {
        "SEC_EJEC": str(settings.SEC_EJEC),
        "ANO_EJE": str(ano)
    }
    
    for pagina in client.paginar_json(resource, filtros, page_size=200):
        logger.info(f"Pagina obtenida, len={len(pagina)}")
        if pagina:
            logger.info(f"Primera fila: {pagina[0]}")
        for r in pagina:
            sf = _int_o_none(r.get("SEC_FUNC"))
            mes_eje = _int_o_none(r.get("MES_EJE"))
            if sf is None or mes_eje is None:
                continue
                
            # Filtrar localmente los meses que no nos interesan
            if mes_eje > mes_top:
                continue
                
            filas.append(
                {
                    "sec_func": sf,
                    "mes_eje": mes_eje,
                    "producto_proyecto": _str_o_none(r.get("PRODUCTO_PROYECTO")),
                    "producto_proyecto_nombre": _str_o_none(r.get("PRODUCTO_PROYECTO_NOMBRE")),
                    "tipo_act_proy": _str_o_none(r.get("TIPO_ACT_PROY")),
                    "meta": _str_o_none(r.get("META")),
                    "meta_nombre": _str_o_none(r.get("META_NOMBRE")),
                    "funcion": _str_o_none(r.get("FUNCION")),
                    "funcion_nombre": _str_o_none(r.get("FUNCION_NOMBRE")),
                    "programa_ppto": _str_o_none(r.get("PROGRAMA_PPTO")),
                    "programa_ppto_nombre": _str_o_none(r.get("PROGRAMA_PPTO_NOMBRE")),
                    "generica": _str_o_none(r.get("GENERICA")),
                    "generica_nombre": _str_o_none(r.get("GENERICA_NOMBRE")),
                    "fuente_financiamiento": _str_o_none(r.get("FUENTE_FINANCIAMIENTO")),
                    "fuente_financiamiento_nombre": _str_o_none(r.get("FUENTE_FINANCIAMIENTO_NOMBRE")),
                    "rubro": _str_o_none(r.get("RUBRO")),
                    "monto_pia": _num(r.get("MONTO_PIA")),
                    "monto_pim": _num(r.get("MONTO_PIM")),
                    "monto_certificado": _num(r.get("MONTO_CERTIFICADO")),
                    "monto_comprometido_anual": _num(r.get("MONTO_COMPROMETIDO_ANUAL")),
                    "monto_devengado": _num(r.get("MONTO_DEVENGADO")),
                    "monto_girado": _num(r.get("MONTO_GIRADO")),
                    "monto_comprometido": _num(r.get("MONTO_COMPROMETIDO")),
                }
            )
    return filas


def _mes_actual_defecto(ano: int) -> int:
    hoy = date.today()
    if ano < hoy.year:
        return 12
    if ano > hoy.year:
        return 0
    return hoy.month


# ─── Swap atomico ────────────────────────────────────────────────────────

def _crear_staging(conn: Connection) -> None:
    conn.execute(
        text(
            """
            CREATE TEMP TABLE ejec_stg (
                sec_func                  bigint NOT NULL,
                mes_eje                   smallint NOT NULL,
                producto_proyecto         varchar(20),
                producto_proyecto_nombre  text,
                tipo_act_proy             char(1),
                meta                      varchar(10),
                meta_nombre               text,
                funcion                   varchar(4),
                funcion_nombre            varchar(120),
                programa_ppto             varchar(10),
                programa_ppto_nombre      text,
                generica                  varchar(4),
                generica_nombre           varchar(120),
                fuente_financiamiento     varchar(4),
                fuente_financiamiento_nombre varchar(120),
                rubro                     varchar(4),
                monto_pia                 numeric(18,2) NOT NULL,
                monto_pim                 numeric(18,2) NOT NULL,
                monto_certificado         numeric(18,2) NOT NULL,
                monto_comprometido_anual  numeric(18,2) NOT NULL,
                monto_comprometido        numeric(18,2) NOT NULL,
                monto_devengado           numeric(18,2) NOT NULL,
                monto_girado              numeric(18,2) NOT NULL
            ) ON COMMIT DROP
            """
        )
    )


def _insertar_staging(conn: Connection, filas: list[dict[str, Any]]) -> None:
    if not filas:
        return
    # Insertar en lotes de 500 para no exceder parametros bindeados.
    lote = 500
    stmt = text(
        """
        INSERT INTO ejec_stg (
            sec_func, mes_eje, producto_proyecto, producto_proyecto_nombre,
            tipo_act_proy, meta, meta_nombre, funcion, funcion_nombre,
            programa_ppto, programa_ppto_nombre, generica, generica_nombre,
            fuente_financiamiento, fuente_financiamiento_nombre, rubro,
            monto_pia, monto_pim, monto_certificado, monto_comprometido_anual,
            monto_comprometido, monto_devengado, monto_girado
        ) VALUES (
            :sec_func, :mes_eje, :producto_proyecto, :producto_proyecto_nombre,
            :tipo_act_proy, :meta, :meta_nombre, :funcion, :funcion_nombre,
            :programa_ppto, :programa_ppto_nombre, :generica, :generica_nombre,
            :fuente_financiamiento, :fuente_financiamiento_nombre, :rubro,
            :monto_pia, :monto_pim, :monto_certificado, :monto_comprometido_anual,
            :monto_comprometido, :monto_devengado, :monto_girado
        )
        """
    )
    for i in range(0, len(filas), lote):
        conn.execute(stmt, filas[i : i + lote])


def _swap_atomico(conn: Connection, ano: int) -> None:
    """TRUNCATE + INSERT SELECT para el ano solicitado.

    Solo eliminamos filas del ano que estamos sincronizando (permite mantener
    otros anios en la misma tabla).
    """
    conn.execute(
        text("DELETE FROM siaf.ejecucion_presupuestal WHERE ano_eje = :ano"),
        {"ano": ano},
    )
    conn.execute(
        text(
            """
            INSERT INTO siaf.ejecucion_presupuestal (
                ano_eje, mes_eje, sec_ejec, sec_func,
                producto_proyecto, producto_proyecto_nombre, tipo_act_proy,
                meta, meta_nombre, funcion, funcion_nombre,
                programa_ppto, programa_ppto_nombre,
                generica, generica_nombre,
                fuente_financiamiento, fuente_financiamiento_nombre, rubro,
                monto_pia, monto_pim, monto_certificado,
                monto_comprometido_anual, monto_comprometido,
                monto_devengado, monto_girado
            )
            SELECT
                :ano, mes_eje, :sec_ejec, sec_func,
                producto_proyecto, producto_proyecto_nombre, tipo_act_proy,
                meta, meta_nombre, funcion, funcion_nombre,
                programa_ppto, programa_ppto_nombre,
                generica, generica_nombre,
                fuente_financiamiento, fuente_financiamiento_nombre, rubro,
                monto_pia, monto_pim, monto_certificado,
                monto_comprometido_anual, monto_comprometido,
                monto_devengado, monto_girado
            FROM ejec_stg
            """
        ),
        {"ano": ano, "sec_ejec": settings.SEC_EJEC},
    )


# ─── Conversores robustos ────────────────────────────────────────────────

def _num(valor: Any) -> float:
    if valor in (None, "", " "):
        return 0.0
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _int_o_none(valor: Any) -> int | None:
    if valor in (None, "", " "):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _str_o_none(valor: Any) -> str | None:
    if valor in (None, ""):
        return None
    s = str(valor).strip()
    return s or None


# ─── Entrada principal ───────────────────────────────────────────────────

def sync_siaf(
    ano: int | None = None,
    mes_hasta: int | None = None,
) -> ResultadoSyncSiaf:
    ano_ejec = ano if ano is not None else settings.ANO_VIGENTE
    mes_top = mes_hasta if mes_hasta is not None else _mes_actual_defecto(ano_ejec)

    session = SessionLocal()
    sync_id = _registrar_inicio(session.connection(), ano_ejec)

    try:
        # 1) Leer montos de la API via datastore_search
        with MefClient() as client:
            logger.info("Leyendo registros SIAF Ejecucion (paginado)...")
            filas = _leer_registros(client, ano_ejec, mes_top)
            logger.info("Extraidos %d registros totales", len(filas))

        # 2) Swap atomico con context manager para correcta manipulacion de TX
        engine = session.get_bind()
        with engine.begin() as conn:
            _crear_staging(conn)
            _insertar_staging(conn, filas)
            _swap_atomico(conn, ano_ejec)

        # 3) Registrar exito
        with engine.begin() as conn:
            _registrar_fin_exito(conn, sync_id, len(filas))
            
        logger.info(
            "sync_siaf OK: ano=%d meses=0..%d registros=%d",
            ano_ejec, mes_top, len(filas),
        )
        return ResultadoSyncSiaf(ano=ano_ejec, meses=mes_top + 1, registros=len(filas))

    except Exception as exc:
        engine = session.get_bind()
        with engine.begin() as conn:
            mensaje = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            _registrar_fin_error(conn, sync_id, mensaje)
        logger.exception("sync_siaf FALLO")
        raise
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza SIAF -> PostgreSQL")
    parser.add_argument("--ano", type=int, default=None)
    parser.add_argument("--mes-hasta", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        resultado = sync_siaf(args.ano, args.mes_hasta)
    except Exception:
        return 1
    print(
        f"[OK] ano={resultado.ano} meses={resultado.meses} "
        f"registros={resultado.registros}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
