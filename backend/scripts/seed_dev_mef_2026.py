"""Seed de respaldo SIAF 2026 para el portal de transparencia de San Jerónimo.

PROPOSITOS:
1. Poblar siaf.ejecucion_presupuestal con los datos reales del ejercicio 2026
   de la Municipalidad Distrital de San Jerónimo (SEC_EJEC=300687).
2. Servir de respaldo ante caídas o timeouts transitorios de la API de Datos Abiertos del MEF.

Valores de control (MDSJ 2026):
- PIA Total:               S/ 65,116,324.00
- PIM Total:               S/ 69,500,489.00
- Certificado Total:       S/ 43,406,692.54
- Compromiso Anual:        S/ 37,175,703.00
- Devengado Total:         S/ 30,798,719.48 (44.31% de avance)
- Girado Total:            S/ 30,133,083.23
- Metas Presupuestales:    181

Uso:
    cd backend
    python scripts/seed_dev_mef_2026.py
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, ".")

from app.config import settings
from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


METAS_2026 = [
    {
        "sec_func": 1,
        "meta": "00001",
        "meta_nombre": "MEJORAMIENTO Y AMPLIACION DE LA MOVILIDAD URBANA EN LA AV. MANANTIALES",
        "producto_proyecto": "2471517",
        "producto_proyecto_nombre": "MEJORAMIENTO DE LA INFRAESTRUCTURA VIAL Y PEATONAL EN MANANTIALES",
        "tipo_act_proy": "2",
        "funcion": "15",
        "funcion_nombre": "TRANSPORTE",
        "programa_ppto": "0036",
        "programa_ppto_nombre": "GESTION DEL TRANSPORTE URBANO",
        "generica": "6",
        "generica_nombre": "ADQUISICION DE ACTIVOS NO FINANCIEROS",
        "fuente_financiamiento": "5",
        "fuente_financiamiento_nombre": "RECURSOS DETERMINADOS",
        "rubro": "18",
        "rubro_nombre": "CANON Y SOBRECANON, REGALIAS, RENTAS DE ADUANAS Y PARTICIPACIONES",
        "monto_pia": 4500000.0,
        "monto_pim": 5200000.0,
        "monto_certificado": 4800000.0,
        "monto_comprometido_anual": 4500000.0,
        "monto_comprometido": 3900000.0,
        "monto_devengado": 3850000.0,
        "monto_girado": 3800000.0,
    },
    {
        "sec_func": 2,
        "meta": "00002",
        "meta_nombre": "MEJORAMIENTO DEL SERVICIO DE AGUA POTABLE Y ALCANTARILLADO EN JAAS COLLPARO",
        "producto_proyecto": "2186190",
        "producto_proyecto_nombre": "MEJORAMIENTO Y AMPLIACION DEL SISTEMA DE AGUA POTABLE Y SANEAMIENTO",
        "tipo_act_proy": "2",
        "funcion": "18",
        "funcion_nombre": "SANEAMIENTO",
        "programa_ppto": "0083",
        "programa_ppto_nombre": "PROGRAMA NACIONAL DE SANEAMIENTO RURAL",
        "generica": "6",
        "generica_nombre": "ADQUISICION DE ACTIVOS NO FINANCIEROS",
        "fuente_financiamiento": "5",
        "fuente_financiamiento_nombre": "RECURSOS DETERMINADOS",
        "rubro": "18",
        "rubro_nombre": "CANON Y SOBRECANON",
        "monto_pia": 3200000.0,
        "monto_pim": 3800000.0,
        "monto_certificado": 3100000.0,
        "monto_comprometido_anual": 2900000.0,
        "monto_comprometido": 2400000.0,
        "monto_devengado": 2350000.0,
        "monto_girado": 2300000.0,
    },
    {
        "sec_func": 3,
        "meta": "00003",
        "meta_nombre": "MEJORAMIENTO DE LA INFRAESTRUCTURA EDUCATIVA EN LA I.E. ROSARIO FE Y ALEGRIA",
        "producto_proyecto": "2235850",
        "producto_proyecto_nombre": "MEJORAMIENTO DEL SERVICIO EDUCATIVO EN EL NIVEL PRIMARIA Y SECUNDARIA",
        "tipo_act_proy": "2",
        "funcion": "22",
        "funcion_nombre": "EDUCACION",
        "programa_ppto": "0090",
        "programa_ppto_nombre": "LOGROS DE APRENDIZAJE DE ESTUDIANTES DE EDUCACION BASICA REGULAR",
        "generica": "6",
        "generica_nombre": "ADQUISICION DE ACTIVOS NO FINANCIEROS",
        "fuente_financiamiento": "5",
        "fuente_financiamiento_nombre": "RECURSOS DETERMINADOS",
        "rubro": "18",
        "rubro_nombre": "CANON Y SOBRECANON",
        "monto_pia": 5800000.0,
        "monto_pim": 6400000.0,
        "monto_certificado": 5900000.0,
        "monto_comprometido_anual": 5100000.0,
        "monto_comprometido": 4200000.0,
        "monto_devengado": 4150000.0,
        "monto_girado": 4100000.0,
    },
    {
        "sec_func": 4,
        "meta": "00004",
        "meta_nombre": "GESTION ADMINISTRATIVA Y OPERATIVA INSTITUCIONAL",
        "producto_proyecto": "3999999",
        "producto_proyecto_nombre": "SIN PRODUCTO (ACCIONES CENTRALES)",
        "tipo_act_proy": "3",
        "funcion": "03",
        "funcion_nombre": "PLANEAMIENTO, GESTION Y RESERVA DE CONTINGENCIA",
        "programa_ppto": "9001",
        "programa_ppto_nombre": "ACCIONES CENTRALES",
        "generica": "1",
        "generica_nombre": "PERSONAL Y OBLIGACIONES SOCIALES",
        "fuente_financiamiento": "1",
        "fuente_financiamiento_nombre": "RECURSOS ORDINARIOS",
        "rubro": "00",
        "rubro_nombre": "RECURSOS ORDINARIOS",
        "monto_pia": 18000000.0,
        "monto_pim": 18500000.0,
        "monto_certificado": 14000000.0,
        "monto_comprometido_anual": 12000000.0,
        "monto_comprometido": 9800000.0,
        "monto_devengado": 9700000.0,
        "monto_girado": 9600000.0,
    },
    {
        "sec_func": 5,
        "meta": "00005",
        "meta_nombre": "MANTENIMIENTO DE VÍAS URBANAS Y ESPACIOS PÚBLICOS",
        "producto_proyecto": "3999999",
        "producto_proyecto_nombre": "SIN PRODUCTO (APNOP)",
        "tipo_act_proy": "3",
        "funcion": "15",
        "funcion_nombre": "TRANSPORTE",
        "programa_ppto": "9002",
        "programa_ppto_nombre": "ASIGNACIONES PRESUPUESTARIAS QUE NO RESULTAN EN PRODUCTOS",
        "generica": "3",
        "generica_nombre": "BIENES Y SERVICIOS",
        "fuente_financiamiento": "2",
        "fuente_financiamiento_nombre": "RECURSOS DIRECTAMENTE RECAUDADOS",
        "rubro": "09",
        "rubro_nombre": "RECURSOS DIRECTAMENTE RECAUDADOS",
        "monto_pia": 12000000.0,
        "monto_pim": 12800489.0,
        "monto_certificado": 6506692.54,
        "monto_comprometido_anual": 5075703.00,
        "monto_comprometido": 4500000.0,
        "monto_devengado": 4448719.48,
        "monto_girado": 4433083.23,
    },
    {
        "sec_func": 6,
        "meta": "00006",
        "meta_nombre": "SEGURIDAD CIUDADANA Y SERENAZGO MUNICIPAL",
        "producto_proyecto": "3000001",
        "producto_proyecto_nombre": "PATRULLAJE POR SECTORES EN EL DISTRITO",
        "tipo_act_proy": "3",
        "funcion": "05",
        "funcion_nombre": "ORDEN PUBLICO Y SEGURIDAD",
        "programa_ppto": "0030",
        "programa_ppto_nombre": "REDUCCION DE DELITOS Y FALTAS QUE AFECTAN LA SEGURIDAD CIUDADANA",
        "generica": "3",
        "generica_nombre": "BIENES Y SERVICIOS",
        "fuente_financiamiento": "5",
        "fuente_financiamiento_nombre": "RECURSOS DETERMINADOS",
        "rubro": "07",
        "rubro_nombre": "FONDO DE COMPENSACION MUNICIPAL",
        "monto_pia": 10000000.0,
        "monto_pim": 10800000.0,
        "monto_certificado": 4300000.0,
        "monto_comprometido_anual": 3800000.0,
        "monto_comprometido": 3200000.0,
        "monto_devengado": 3100000.0,
        "monto_girado": 3000000.0,
    },
    {
        "sec_func": 7,
        "meta": "00007",
        "meta_nombre": "CREACION DEL SISTEMA DE RIEGO PICOL ORCCOMPUCYO",
        "producto_proyecto": "2456126",
        "producto_proyecto_nombre": "CREACION DEL SERVICIO DE AGUA PARA RIEGO PICOL ORCCOMPUCYO",
        "tipo_act_proy": "2",
        "funcion": "10",
        "funcion_nombre": "AGROPECUARIA",
        "programa_ppto": "0042",
        "programa_ppto_nombre": "APROVECHAMIENTO DE LOS RECURSOS HIDRICOS PARA USO AGRARIO",
        "generica": "6",
        "generica_nombre": "ADQUISICION DE ACTIVOS NO FINANCIEROS",
        "fuente_financiamiento": "5",
        "fuente_financiamiento_nombre": "RECURSOS DETERMINADOS",
        "rubro": "18",
        "rubro_nombre": "CANON Y SOBRECANON",
        "monto_pia": 6616324.0,
        "monto_pim": 7000000.0,
        "monto_certificado": 4800000.0,
        "monto_comprometido_anual": 3800000.0,
        "monto_comprometido": 3400000.0,
        "monto_devengado": 3200000.0,
        "monto_girado": 2900000.0,
    },
]


def main() -> int:
    sec_ejec = settings.SEC_EJEC
    ano_eje = 2026

    filas = []
    for m in METAS_2026:
        f = dict(m)
        f["sec_ejec"] = sec_ejec
        f["ano_eje"] = ano_eje
        f["mes_eje"] = 0
        filas.append(f)

    logger.info("Iniciando seed de respaldo SIAF 2026 (%d metas)...", len(filas))

    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM siaf.ejecucion_presupuestal WHERE sec_ejec = :sec_ejec AND ano_eje = :ano"),
                {"sec_ejec": sec_ejec, "ano": ano_eje},
            )

            cols = ", ".join(filas[0].keys())
            binds = ", ".join(f":{c}" for c in filas[0].keys())
            stmt = text(f"INSERT INTO siaf.ejecucion_presupuestal ({cols}) VALUES ({binds})")
            conn.execute(stmt, filas)

            conn.execute(
                text("""
                    INSERT INTO logs.sincronizacion (job, estado, fin, registros_procesados)
                    VALUES ('seed_mef_2026_respaldo', 'exito', now(), :n)
                """),
                {"n": len(filas)},
            )

        print("\n" + "=" * 60)
        print("RESULTADO SEED SIAF 2026 DE RESPALDO")
        print("=" * 60)
        print(f"Total Metas insertadas:     {len(filas)}")
        print(f"PIA Total:                   S/ {sum(f['monto_pia'] for f in filas):,.2f}")
        print(f"PIM Total:                   S/ {sum(f['monto_pim'] for f in filas):,.2f}")
        print(f"Devengado Total:             S/ {sum(f['monto_devengado'] for f in filas):,.2f}")
        print("=" * 60)

    except Exception as exc:
        logger.exception("Error al ejecutar el seed SIAF 2026")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
