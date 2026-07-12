"""Seed manual de siaf.inversiones usando datastore_search (filtros JSON).

Workaround temporal: la API del MEF tiene una regresión en datastore_search_sql
con cláusulas WHERE (devuelve HTTP 500). datastore_search con filtros JSON sigue
funcionando. Este script usa ese endpoint para poblar la tabla de inversiones con
datos reales del municipio de San Jerónimo (SEC_EJEC=300687).

Referencia: corrección retroactiva de T-12/T-13 en Docs/bitacora-agente.md.

NO reemplaza el pipeline automático (sync_invierte.py). Se usa exclusivamente como
seed de desarrollo para desbloquear tareas de frontend (T-38 verificación, T-40 mapa).

Uso:
    cd backend
    ./venv/bin/python scripts/seed_dev_mef_manual.py
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy import text

# Agregar el directorio padre al path para importar módulos de la app
sys.path.insert(0, ".")

from app.config import settings
from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Conversores (idénticos a sync_invierte.py) ─────────────────────────

def _str_o_none(v: Any, max_len: int | None = None) -> str | None:
    if v in (None, ""):
        return None
    s = str(v).strip()
    if not s:
        return None
    if max_len is not None and len(s) > max_len:
        s = s[:max_len]
    return s

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
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:len(fmt) + 8], fmt).date()
        except ValueError:
            continue
    return None


# ─── Mapeo de campos API → DB (mismo que sync_invierte.py) ──────────────

def _mapear_registro(r: dict[str, Any]) -> dict[str, Any]:
    """Convierte un registro de la API MEF al formato de siaf.inversiones."""
    return {
        "codigo_unico": _str_o_none(r.get("CODIGO_UNICO"), 20),
        "nombre_inversion": _str_o_none(r.get("NOMBRE_INVERSION")),
        "tipo_inversion": _str_o_none(r.get("TIPO_INVERSION"), 40),
        "marco": _str_o_none(r.get("MARCO"), 20),
        "estado": _str_o_none(r.get("ESTADO"), 20),
        "situacion": _str_o_none(r.get("SITUACION"), 30),
        "anio_proceso": _int_o_none(r.get("ANIO_PROCESO")),
        "sec_ejec": _str_o_none(r.get("SEC_EJEC"), 10),
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
        "etapa_f8": _str_o_none(r.get("ETAPA_F8"), 50),
        "tiene_f9": _si_no(r.get("TIENE_F9")),
        "tiene_f12b": _si_no(r.get("TIENE_F12B")),
        "informe_cierre": _si_no(r.get("INFORME_CIERRE")),
        "expediente_tecnico": _si_no(r.get("EXPEDIENTE_TECNICO")),
        "des_modalidad": _str_o_none(r.get("DES_MODALIDAD"), 40),
        "des_tipologia": _str_o_none(r.get("DES_TIPOLOGIA"), 80),
        "funcion": _str_o_none(r.get("FUNCION"), 80),
        "programa": _str_o_none(r.get("PROGRAMA"), 80),
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
    }


# ─── Columnas para INSERT (mismo orden que sync_invierte._COLUMNAS) ─────

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
]


def main() -> int:
    base_url = settings.MEF_BASE_URL.rstrip("/")
    resource_id = settings.MEF_RESOURCE_INVERSIONES
    sec_ejec = settings.SEC_EJEC

    # 1. Leer todas las inversiones de San Jerónimo via datastore_search
    logger.info("Descargando inversiones de SEC_EJEC=%s via datastore_search...", sec_ejec)
    all_records: list[dict[str, Any]] = []
    offset = 0
    page_size = 100

    with httpx.Client(timeout=60.0) as client:
        while True:
            resp = client.get(
                f"{base_url}/datastore_search",
                params={
                    "resource_id": resource_id,
                    "filters": json.dumps({"SEC_EJEC": sec_ejec}),
                    "limit": page_size,
                    "offset": offset,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            records = data.get("records", [])
            if not records:
                break
            all_records.extend(records)
            logger.info("  Página offset=%d: %d registros", offset, len(records))
            if len(records) < page_size:
                break
            offset += page_size

    total = len(all_records)
    logger.info("Total descargado: %d inversiones", total)

    # 2. Mapear a formato DB
    filas = [_mapear_registro(r) for r in all_records]
    filas_norm = [{k: fila.get(k) for k in _COLUMNAS} for fila in filas]

    # 3. Contar coordenadas
    con_coords = sum(1 for f in filas_norm if f["latitud"] is not None and f["longitud"] is not None)
    
    # 4. Insertar en DB (transacción atómica: DELETE + INSERT)
    try:
        with engine.begin() as conn:
            # DELETE + INSERT dentro del mismo context manager = atómico
            conn.execute(
                text("DELETE FROM siaf.inversiones WHERE sec_ejec = :sec_ejec"),
                {"sec_ejec": sec_ejec},
            )

            cols = ", ".join(_COLUMNAS)
            binds = ", ".join(f":{c}" for c in _COLUMNAS)
            stmt = text(f"INSERT INTO siaf.inversiones ({cols}) VALUES ({binds})")
            conn.execute(stmt, filas_norm)
            
        logger.info("INSERT completado: %d filas en siaf.inversiones", total)

        # 5. Registrar en logs.sincronizacion (transacción separada, auditoría de éxito)
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO logs.sincronizacion (job, estado, fin, registros_procesados)
                    VALUES ('seed_manual_mef_workaround', 'exito', now(), :n)
                """),
                {"n": total},
            )
        logger.info("Registrado en logs.sincronizacion (job='seed_manual_mef_workaround')")

        # 6. Verificación final (lectura sin transacción implícita de escritura)
        with engine.connect() as conn:
            count_db = conn.execute(
                text("SELECT COUNT(*) FROM siaf.inversiones WHERE sec_ejec = :sec_ejec"),
                {"sec_ejec": sec_ejec},
            ).scalar()
            count_coords = conn.execute(
                text("""
                    SELECT COUNT(*) FROM siaf.inversiones
                    WHERE sec_ejec = :sec_ejec AND latitud IS NOT NULL AND longitud IS NOT NULL
                """),
                {"sec_ejec": sec_ejec},
            ).scalar()
            sync_row = conn.execute(
                text("SELECT * FROM logs.sincronizacion WHERE job = 'seed_manual_mef_workaround' ORDER BY fin DESC LIMIT 1")
            ).mappings().first()

        print("\n" + "=" * 60)
        print("RESULTADO DEL SEED")
        print("=" * 60)
        print(f"Total inversiones en DB:     {count_db}")
        print(f"Con coordenadas (lat/lng):   {count_coords}")
        print(f"Sin coordenadas:             {count_db - count_coords}")
        print(f"Sync log:                    job={sync_row['job']}, estado={sync_row['estado']}, registros={sync_row['registros_procesados']}")
        print("=" * 60)

    except Exception as exc:
        logger.exception("Error durante el seed")
        # Transacción separada para registrar el error
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO logs.sincronizacion (job, estado, fin, error_mensaje)
                        VALUES ('seed_manual_mef_workaround', 'error', now(), :msg)
                    """),
                    {"msg": str(exc)[:2000]},
                )
        except Exception:
            logger.exception("Fallo crítico al intentar guardar el error en logs")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
