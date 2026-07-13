"""Job: sincronizacion Invierte.pe (API MEF -> siaf.inversiones).

Analogo a `sync_siaf`. Volumen bajo (~70 registros para San Jeronimo).

Como la API MEF limita a ~8 columnas por request, dividimos la lectura en
varios "batches" que comparten la clave `CODIGO_UNICO` y hacemos merge en
memoria antes del swap. Ver `Docs/actividad-3-arquitectura-tecnica.md` §6.2.

Ejecucion:
    python -m app.jobs.sync_invierte
"""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import SessionLocal
from app.services.mef_client import (
    MefClient,
    sql_inversiones,
    sql_inversiones_avance,
    sql_inversiones_costo,
    sql_inversiones_cronograma,
    sql_inversiones_etapa,
    sql_inversiones_geo,
    sql_inversiones_unidades,
)

logger = logging.getLogger(__name__)

JOB_NAME = "invierte"


@dataclass
class ResultadoSyncInvierte:
    inversiones: int


# ─── Helpers logs ────────────────────────────────────────────────────────

def _registrar_inicio(conn: Connection) -> int:
    row = conn.execute(
        text(
            """
            INSERT INTO logs.sincronizacion (job, estado)
            VALUES (:job, 'en_curso') RETURNING id
            """
        ),
        {"job": JOB_NAME},
    ).first()
    conn.commit()
    return int(row.id)  # type: ignore[union-attr]


def _registrar_fin_exito(conn: Connection, sync_id: int, procesados: int) -> None:
    conn.execute(
        text(
            """
            UPDATE logs.sincronizacion
               SET estado='exito', fin=now(), registros_procesados=:n
             WHERE id=:id
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
               SET estado='error', fin=now(), error_mensaje=:msg
             WHERE id=:id
            """
        ),
        {"id": sync_id, "msg": mensaje[:2000]},
    )
    conn.commit()


# ─── Lectura unificada ───────────────────────────────────────────────────

def _leer_todo(client: MefClient) -> dict[str, dict[str, Any]]:
    """Extrae datos de Invierte.pe usando paginacion JSON nativa."""
    resource = settings.MEF_RESOURCE_INVERSIONES
    consolidado: dict[str, dict[str, Any]] = {}
    
    filtros = {
        "SEC_EJEC": str(settings.SEC_EJEC)
    }

    logger.info("Leyendo registros Invierte.pe (paginado)...")
    for pagina in client.paginar_json(resource, filtros, page_size=200):
        for r in pagina:
            codigo = _str_o_none(r.get("CODIGO_UNICO"))
            if not codigo:
                continue
                
            consolidado[codigo] = {
                "codigo_unico": codigo,
                "nombre_inversion": _str_o_none(r.get("NOMBRE_INVERSION")),
                "tipo_inversion": _str_o_none(r.get("TIPO_INVERSION")),
                "marco": _str_o_none(r.get("MARCO")),
                "estado": _str_o_none(r.get("ESTADO")),
                "situacion": _str_o_none(r.get("SITUACION")),
                "anio_proceso": _int_o_none(r.get("ANIO_PROCESO")),
                "sec_ejec": _str_o_none(r.get("SEC_EJEC")),
                "avance_fisico": _num_o_none(r.get("AVANCE_FISICO")),
                "avance_ejecucion": _num_o_none(r.get("AVANCE_EJECUCION")),
                "tiene_avan_fisico": _si_no(r.get("TIENE_AVAN_FISICO")),
                "pim_anio_actual": _num_o_none(r.get("PIM_ANIO_ACTUAL")),
                "dev_anio_actual": _num_o_none(r.get("DEV_ANIO_ACTUAL")),
                "deven_acumul_anio_ant": _num_o_none(r.get("DEVEN_ACUMUL_ANIO_ANT")),
                "comprom_anual_anio_actual": _num_o_none(r.get("COMPROM_ANUAL_ANIO_ACTUAL")),
                "certif_anio_actual": _num_o_none(r.get("CERTIF_ANIO_ACTUAL")),
                "costo_actualizado": _num_o_none(r.get("COSTO_ACTUALIZADO")),
                "monto_viable": _num_o_none(r.get("MONTO_VIABLE")),
                "saldo_ejecutar": _num_o_none(r.get("SALDO_EJECUTAR")),
                "tiene_f8": _si_no(r.get("TIENE_F8")),
                "etapa_f8": _str_o_none(r.get("ETAPA_F8")),
                "tiene_f9": _si_no(r.get("TIENE_F9")),
                "tiene_f12b": _si_no(r.get("TIENE_F12B")),
                "informe_cierre": _si_no(r.get("INFORME_CIERRE")),
                "expediente_tecnico": _si_no(r.get("EXPEDIENTE_TECNICO")),
                "des_modalidad": _str_o_none(r.get("DES_MODALIDAD")),
                "des_tipologia": _str_o_none(r.get("DES_TIPOLOGIA")),
                "funcion": _str_o_none(r.get("FUNCION")),
                "programa": _str_o_none(r.get("PROGRAMA")),
                "fec_ini_ejecucion": _fecha(r.get("FEC_INI_EJECUCION")),
                "fec_fin_ejecucion": _fecha(r.get("FEC_FIN_EJECUCION")),
                "fec_ini_ejec_fisica": _fecha(r.get("FEC_INI_EJEC_FISICA")),
                "fec_fin_ejec_fisica": _fecha(r.get("FEC_FIN_EJEC_FISICA")),
                "fecha_viabilidad": _fecha(r.get("FECHA_VIABILIDAD")),
                "primer_devengado": _fecha(r.get("PRIMER_DEVENGADO")),
                "ultimo_devengado": _fecha(r.get("ULTIMO_DEVENGADO")),
                "latitud": _num_o_none(r.get("LATITUD")),
                "longitud": _num_o_none(r.get("LONGITUD")),
                "ubigeo": _str_o_none(r.get("UBIGEO")),
                "departamento": _str_o_none(r.get("DEPARTAMENTO")),
                "provincia": _str_o_none(r.get("PROVINCIA")),
                "distrito": _str_o_none(r.get("DISTRITO")),
                "nombre_uei": _str_o_none(r.get("NOMBRE_UEI")),
                "nombre_uf": _str_o_none(r.get("NOMBRE_UF")),
                "nombre_opmi": _str_o_none(r.get("NOMBRE_OPMI")),
                # Alta prioridad — agregados 2026-07-13
                "pia_anio_actual": _num_o_none(r.get("PIA_ANIO_ACTUAL")),
                "num_habitantes_benef": _int_o_none(r.get("NUM_HABITANTES_BENEF")),
                "registrado_pmi": _si_no(r.get("REGISTRADO_PMI")),
                "pmi_anio_1": _num_o_none(r.get("PMI_ANIO_1")),
                "pmi_anio_2": _num_o_none(r.get("PMI_ANIO_2")),
                "pmi_anio_3": _num_o_none(r.get("PMI_ANIO_3")),
                "pmi_anio_4": _num_o_none(r.get("PMI_ANIO_4")),
                "ult_fec_decla_estim": _fecha(r.get("ULT_FEC_DECLA_ESTIM")),
            }
            
    return consolidado


# ─── Swap atomico ────────────────────────────────────────────────────────

_COLUMNAS = [
    "codigo_unico", "nombre_inversion", "tipo_inversion", "marco", "estado",
    "situacion", "anio_proceso", "sec_ejec", "avance_fisico", "avance_ejecucion",
    "tiene_avan_fisico", "pim_anio_actual", "dev_anio_actual",
    "deven_acumul_anio_ant", "comprom_anual_anio_actual", "certif_anio_actual",
    "costo_actualizado", "monto_viable", "saldo_ejecutar", "tiene_f8",
    "etapa_f8", "tiene_f9", "tiene_f12b", "informe_cierre", "expediente_tecnico",
    "des_modalidad", "des_tipologia", "funcion", "programa",
    "fec_ini_ejecucion", "fec_fin_ejecucion", "fec_ini_ejec_fisica",
    "fec_fin_ejec_fisica", "fecha_viabilidad", "primer_devengado",
    "ultimo_devengado", "latitud", "longitud", "ubigeo", "departamento",
    "provincia", "distrito", "nombre_uei", "nombre_uf", "nombre_opmi",
    # Alta prioridad
    "pia_anio_actual", "num_habitantes_benef", "registrado_pmi",
    "pmi_anio_1", "pmi_anio_2", "pmi_anio_3", "pmi_anio_4",
    "ult_fec_decla_estim",
]


def _swap(conn: Connection, filas: list[dict[str, Any]]) -> None:
    conn.execute(
        text("DELETE FROM siaf.inversiones WHERE sec_ejec = :sec_ejec"),
        {"sec_ejec": settings.SEC_EJEC},
    )
    if not filas:
        return
    cols = ", ".join(_COLUMNAS)
    binds = ", ".join(f":{c}" for c in _COLUMNAS)
    stmt = text(f"INSERT INTO siaf.inversiones ({cols}) VALUES ({binds})")
    # Homogeneizar: cada fila debe tener todas las claves.
    filas_norm = [{k: fila.get(k) for k in _COLUMNAS} for fila in filas]
    conn.execute(stmt, filas_norm)


# ─── Conversores ─────────────────────────────────────────────────────────

def _str_o_none(v: Any) -> str | None:
    if v in (None, ""):
        return None
    s = str(v).strip()
    return s or None


def _int_o_none(v: Any) -> int | None:
    if v in (None, "", " "):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _num_o_none(v: Any) -> float | None:
    if v in (None, "", " "):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _si_no(v: Any) -> str | None:
    if v in (None, ""):
        return None
    s = str(v).strip().upper()
    if s in ("SI", "NO"):
        return s
    return None


def _fecha(v: Any) -> date | None:
    if v in (None, ""):
        return None
    s = str(v).strip()
    if not s:
        return None
    # La API devuelve varios formatos. Intentamos los mas probables.
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[: len(fmt) + 8], fmt).date()
        except ValueError:
            continue
    return None


# ─── Entrada principal ───────────────────────────────────────────────────

def sync_invierte() -> ResultadoSyncInvierte:
    session = SessionLocal()
    sync_id = _registrar_inicio(session.connection())

    try:
        with MefClient() as client:
            consolidado = _leer_todo(client)
        filas = list(consolidado.values())

        engine = session.get_bind()
        with engine.begin() as conn:
            _swap(conn, filas)

        with engine.begin() as conn:
            _registrar_fin_exito(conn, sync_id, len(filas))
            
        logger.info("sync_invierte OK: %d proyectos procesados", len(filas))
        return ResultadoSyncInvierte(inversiones=len(filas))

    except Exception as exc:
        engine = session.get_bind()
        with engine.begin() as conn:
            mensaje = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            _registrar_fin_error(conn, sync_id, mensaje)
        logger.exception("sync_invierte FALLO")
        raise
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        resultado = sync_invierte()
    except Exception:
        return 1
    print(f"[OK] inversiones={resultado.inversiones}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
