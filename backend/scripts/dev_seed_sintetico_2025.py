"""Seed sintético de SIAF (Ejecución e Inversiones) para el año 2025.

PROPOSITO:
Este script inyecta datos 100% SINTETICOS en las tablas siaf.ejecucion_presupuestal
y siaf.inversiones, anclados al año 2025. Se utiliza EXCLUSIVAMENTE para validar
visualmente el frontend (T-38 Obras, T-40 Mapa, T-41 Ejecucion) dado que el pipeline
real de sincronización (T-12/T-13) está bloqueado por falta de un resource_id histórico
de 2025 en la API pública del MEF.

ADVERTENCIA:
Los datos generados NO provienen del MEF y NO deben usarse en producción.
Se añaden marcadores [DEV-SEED] en los nombres descriptivos para fácil identificación
en las interfaces de usuario.

Uso:
    cd backend
    ./venv/bin/python scripts/dev_seed_sintetico_2025.py
"""

from __future__ import annotations

import logging
import sys
from datetime import date
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


def generar_inversiones_sinteticas() -> list[dict]:
    return [
        {
            "codigo_unico": "2471517", # Mismo del doc de exploración
            "nombre_inversion": "[DEV-SEED] MEJORAMIENTO MOVILIDAD URBANA MANANTIALES",
            "tipo_inversion": "PROYECTO DE INVERSIÓN",
            "marco": "INVIERTE",
            "estado": "ACTIVO",
            "situacion": "VIABLE",
            "anio_proceso": 2025,
            "sec_ejec": settings.SEC_EJEC,
            "avance_fisico": 85.5,
            "avance_ejecucion": 90.0,
            "tiene_avan_fisico": "SI",
            "pim_anio_actual": 1500000.0,
            "dev_anio_actual": 1350000.0,
            "deven_acumul_anio_ant": 500000.0,
            "comprom_anual_anio_actual": 1400000.0,
            "certif_anio_actual": 1500000.0,
            "costo_actualizado": 2000000.0,
            "monto_viable": 1800000.0,
            "saldo_ejecutar": 150000.0,
            "tiene_f8": "SI",
            "etapa_f8": "Ejecución física",
            "tiene_f9": "NO",
            "tiene_f12b": "NO",
            "informe_cierre": "NO",
            "expediente_tecnico": "SI",
            "des_modalidad": "ADMINISTRACIÓN DIRECTA",
            "des_tipologia": "PISTAS Y VEREDAS",
            "funcion": "TRANSPORTE",
            "programa": "0036",
            "fec_ini_ejecucion": date(2025, 1, 15),
            "fec_fin_ejecucion": date(2025, 12, 31),
            "fec_ini_ejec_fisica": date(2025, 2, 1),
            "fec_fin_ejec_fisica": None,
            "fecha_viabilidad": date(2024, 6, 1),
            "primer_devengado": date(2025, 3, 15),
            "ultimo_devengado": date(2025, 6, 15),
            "latitud": -13.5413,
            "longitud": -71.8845,
            "ubigeo": settings.UBIGEO,
            "departamento": "CUSCO",
            "provincia": "CUSCO",
            "distrito": "SAN JERONIMO",
            "nombre_uei": "UEI MUNICIPALIDAD DE SAN JERONIMO",
            "nombre_uf": "UF MUNICIPALIDAD DE SAN JERONIMO",
            "nombre_opmi": "OPMI SAN JERONIMO",
        },
        {
            "codigo_unico": "2186190", 
            "nombre_inversion": "[DEV-SEED] MEJORAMIENTO AGUA POTABLE Y ALCANTARILLADO JAAS",
            "tipo_inversion": "PROYECTO DE INVERSIÓN",
            "marco": "INVIERTE",
            "estado": "ACTIVO",
            "situacion": "VIABLE",
            "anio_proceso": 2025,
            "sec_ejec": settings.SEC_EJEC,
            "avance_fisico": 20.0,
            "avance_ejecucion": 25.0,
            "tiene_avan_fisico": "SI",
            "pim_anio_actual": 800000.0,
            "dev_anio_actual": 200000.0,
            "deven_acumul_anio_ant": 0.0,
            "comprom_anual_anio_actual": 500000.0,
            "certif_anio_actual": 800000.0,
            "costo_actualizado": 800000.0,
            "monto_viable": 800000.0,
            "saldo_ejecutar": 600000.0,
            "tiene_f8": "SI",
            "etapa_f8": "Expediente Técnico",
            "tiene_f9": "NO",
            "tiene_f12b": "NO",
            "informe_cierre": "NO",
            "expediente_tecnico": "NO",
            "des_modalidad": "CONTRATA",
            "des_tipologia": "SISTEMA DE AGUA",
            "funcion": "SANEAMIENTO",
            "programa": "0083",
            "fec_ini_ejecucion": date(2025, 5, 1),
            "fec_fin_ejecucion": date(2025, 11, 30),
            "fec_ini_ejec_fisica": None,
            "fec_fin_ejec_fisica": None,
            "fecha_viabilidad": date(2024, 8, 1),
            "primer_devengado": date(2025, 5, 10),
            "ultimo_devengado": date(2025, 5, 10),
            "latitud": -13.5420,
            "longitud": -71.8850,
            "ubigeo": settings.UBIGEO,
            "departamento": "CUSCO",
            "provincia": "CUSCO",
            "distrito": "SAN JERONIMO",
            "nombre_uei": "UEI MUNICIPALIDAD DE SAN JERONIMO",
            "nombre_uf": "UF MUNICIPALIDAD DE SAN JERONIMO",
            "nombre_opmi": "OPMI SAN JERONIMO",
        }
    ]


def generar_ejecucion_sintetica() -> list[dict]:
    # sec_func 0001 (asociado al proyecto 2471517) y 0002 (para gastos corrientes)
    return [
        {
            "sec_ejec": settings.SEC_EJEC,
            "ano_eje": 2025,
            "mes_eje": 6, # Junio 2025 (acumulado)
            "sec_func": "0001",
            "producto_proyecto": "2471517",
            "producto_proyecto_nombre": "[DEV-SEED] MEJORAMIENTO MOVILIDAD URBANA",
            "tipo_act_proy": "2",
            "meta": "00001",
            "meta_nombre": "[DEV-SEED] PAVIMENTACION TRAMO 1",
            "funcion": "15",
            "funcion_nombre": "TRANSPORTE",
            "programa_ppto": "0036",
            "programa_ppto_nombre": "GESTION DEL TRANSPORTE",
            "generica": "6",
            "generica_nombre": "ADQUISICION DE ACTIVOS NO FINANCIEROS",
            "fuente_financiamiento": "5",
            "fuente_financiamiento_nombre": "RECURSOS DETERMINADOS",
            "rubro": "18",
            
            "monto_pia": 0.0,
            "monto_pim": 1500000.0,
            "monto_certificado": 1500000.0,
            "monto_comprometido_anual": 1400000.0,
            "monto_comprometido": 1350000.0,
            "monto_devengado": 1350000.0,
            "monto_girado": 1300000.0,
        },
        {
            "sec_ejec": settings.SEC_EJEC,
            "ano_eje": 2025,
            "mes_eje": 6,
            "sec_func": "0002",
            "producto_proyecto": "3999999", # Actividad genérica
            "producto_proyecto_nombre": "[DEV-SEED] GESTION ADMINISTRATIVA",
            "tipo_act_proy": "3",
            "meta": "00002",
            "meta_nombre": "[DEV-SEED] PAGO DE SERVICIOS BÁSICOS",
            "funcion": "03",
            "funcion_nombre": "PLANEAMIENTO, GESTION Y RESERVA",
            "programa_ppto": "9001",
            "programa_ppto_nombre": "ACCIONES CENTRALES",
            "generica": "3",
            "generica_nombre": "BIENES Y SERVICIOS",
            "fuente_financiamiento": "2",
            "fuente_financiamiento_nombre": "RECURSOS DIRECTAMENTE RECAUDADOS",
            "rubro": "09",
            
            "monto_pia": 0.0,
            "monto_pim": 500000.0,
            "monto_certificado": 480000.0,
            "monto_comprometido_anual": 450000.0,
            "monto_comprometido": 300000.0,
            "monto_devengado": 280000.0,
            "monto_girado": 275000.0,
        }
    ]


def main() -> int:
    sec_ejec = settings.SEC_EJEC
    inv_data = generar_inversiones_sinteticas()
    ejec_data = generar_ejecucion_sintetica()

    try:
        with engine.begin() as conn:
            # Limpiar datos previos
            conn.execute(
                text("DELETE FROM siaf.ejecucion_presupuestal WHERE sec_ejec = :sec_ejec"),
                {"sec_ejec": sec_ejec}
            )
            conn.execute(
                text("DELETE FROM siaf.inversiones WHERE sec_ejec = :sec_ejec"),
                {"sec_ejec": sec_ejec}
            )

            # Insertar Inversiones
            if inv_data:
                cols_inv = ", ".join(inv_data[0].keys())
                binds_inv = ", ".join(f":{c}" for c in inv_data[0].keys())
                stmt_inv = text(f"INSERT INTO siaf.inversiones ({cols_inv}) VALUES ({binds_inv})")
                conn.execute(stmt_inv, inv_data)

            # Insertar Ejecucion
            if ejec_data:
                cols_ejec = ", ".join(ejec_data[0].keys())
                binds_ejec = ", ".join(f":{c}" for c in ejec_data[0].keys())
                stmt_ejec = text(f"INSERT INTO siaf.ejecucion_presupuestal ({cols_ejec}) VALUES ({binds_ejec})")
                conn.execute(stmt_ejec, ejec_data)

            # Audit log
            conn.execute(
                text("""
                    INSERT INTO logs.sincronizacion (job, estado, fin, registros_procesados)
                    VALUES ('dev_seed_sintetico_2025', 'exito', now(), :n)
                """),
                {"n": len(inv_data) + len(ejec_data)}
            )

        print("\n" + "=" * 60)
        print("RESULTADO DEL SEED SINTETICO 2025")
        print("=" * 60)
        print(f"Total Inversiones [DEV-SEED]: {len(inv_data)}")
        print(f"Total Ejecucion   [DEV-SEED]: {len(ejec_data)}")
        print("=" * 60)
        
    except Exception as exc:
        logger.exception("Fallo en el seed sintético")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
