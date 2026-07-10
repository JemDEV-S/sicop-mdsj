"""Seed de catálogos fijos MEF en ref.*

Revision ID: 0002_seed_ref_catalogos
Revises: 0001_initial
Create Date: 2026-07-09

Fuentes de datos:
- `Docs/actividad-1-exploracion-mef.md` §7 (programas activos) y §8 (fuentes)
- `Docs/diccionario-datos-unificado.md` (funciones y rubros)

Los catálogos de funciones y programas se cargan con nombres observados en
la exploración; nombres brutos del MEF pueden diferir en tildes/mayúsculas
y se refrescan anualmente vía job. Ver §3.3 del doc de arquitectura.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_seed_ref_catalogos"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FUENTES = [
    ("1", "RECURSOS ORDINARIOS"),
    ("2", "RECURSOS DIRECTAMENTE RECAUDADOS"),
    ("4", "DONACIONES Y TRANSFERENCIAS"),
    ("5", "RECURSOS DETERMINADOS"),
]

RUBROS = [
    ("00", "RECURSOS ORDINARIOS", "1"),
    ("07", "FONCOMUN", "5"),
    ("08", "IMPUESTOS MUNICIPALES", "5"),
    ("09", "RECURSOS DIRECTAMENTE RECAUDADOS", "2"),
    ("13", "DONACIONES Y TRANSFERENCIAS", "4"),
    ("18", "CANON Y SOBRECANON, REGALIAS, RENTA DE ADUANAS Y PARTICIPACIONES", "5"),
]

# Funciones observadas en la Municipalidad Distrital de San Jerónimo (2026).
# El catálogo completo (67 funciones MEF) se refresca vía job desde SIAF cuando
# aparezcan códigos nuevos. Códigos seleccionados según diccionario MEF estándar.
FUNCIONES = [
    ("03", "PLANEAMIENTO, GESTION Y RESERVA DE CONTINGENCIA"),
    ("05", "ORDEN PUBLICO Y SEGURIDAD"),
    ("08", "COMERCIO"),
    ("09", "TURISMO"),
    ("10", "AGROPECUARIA"),
    ("11", "PESCA"),
    ("12", "ENERGIA"),
    ("13", "MINERIA"),
    ("14", "INDUSTRIA"),
    ("15", "TRANSPORTE"),
    ("16", "COMUNICACIONES"),
    ("17", "AMBIENTE"),
    ("18", "SANEAMIENTO"),
    ("19", "VIVIENDA Y DESARROLLO URBANO"),
    ("20", "SALUD"),
    ("21", "CULTURA Y DEPORTE"),
    ("22", "EDUCACION"),
    ("23", "PROTECCION SOCIAL"),
    ("24", "PREVISION SOCIAL"),
    ("25", "DEUDA PUBLICA"),
]

# Programas presupuestales activos observados en 2026 (ver actividad-1 §7).
# Los nombres pueden diferir del MEF — se refrescan anualmente.
PROGRAMAS = [
    ("0002", "SALUD MATERNO NEONATAL"),
    ("0017", "ENFERMEDADES METAXENICAS Y ZOONOSIS"),
    ("0030", "REDUCCION DE DELITOS Y FALTAS QUE AFECTAN LA SEGURIDAD CIUDADANA"),
    ("0036", "GESTION INTEGRAL DE RESIDUOS SOLIDOS"),
    ("0041", "MEJORA DE LA INOCUIDAD AGROALIMENTARIA"),
    ("0042", "APROVECHAMIENTO DE LOS RECURSOS HIDRICOS PARA USO AGRARIO"),
    ("0048", "PREVENCION Y ATENCION DE INCENDIOS, EMERGENCIAS Y URGENCIAS"),
    ("0068", "REDUCCION DE VULNERABILIDAD Y ATENCION DE EMERGENCIAS POR DESASTRES"),
    ("0082", "PROGRAMA NACIONAL DE SANEAMIENTO URBANO"),
    ("0083", "PROGRAMA NACIONAL DE SANEAMIENTO RURAL"),
    ("0090", "LOGROS DE APRENDIZAJE DE ESTUDIANTES DE EDUCACION BASICA REGULAR"),
    ("0101", "INCREMENTO DE LA PRACTICA DE ACTIVIDADES FISICAS Y DEPORTIVAS"),
    ("0117", "ATENCION OPORTUNA DE NIÑAS, NIÑOS Y ADOLESCENTES EN PRESUNTO ESTADO DE ABANDONO"),
    ("0121", "MEJORA DE LA ARTICULACION DE PEQUEÑOS PRODUCTORES AL MERCADO"),
    ("0140", "DESARROLLO Y PROMOCION DE LAS ARTES E INDUSTRIAS CULTURALES"),
    ("0142", "ACCESO DE PERSONAS ADULTAS MAYORES A SERVICIOS ESPECIALIZADOS"),
    ("0146", "ACCESO DE FAMILIAS A VIVIENDA Y ENTORNO URBANO ADECUADO"),
    ("0148", "REDUCCION DEL TIEMPO, INSEGURIDAD Y COSTO AMBIENTAL EN EL TRANSPORTE URBANO"),
    ("1001", "PRODUCTOS ESPECIFICOS PARA DESARROLLO INFANTIL TEMPRANO"),
    ("9001", "ACCIONES CENTRALES"),
    ("9002", "ASIGNACIONES PRESUPUESTARIAS QUE NO RESULTAN EN PRODUCTOS"),
]


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "INSERT INTO ref.fuentes_financiamiento (codigo, nombre) VALUES (:c, :n)"
        ),
        [{"c": c, "n": n} for c, n in FUENTES],
    )

    conn.execute(
        sa.text(
            "INSERT INTO ref.rubros (codigo, nombre, fuente_financ_codigo) "
            "VALUES (:c, :n, :f)"
        ),
        [{"c": c, "n": n, "f": f} for c, n, f in RUBROS],
    )

    conn.execute(
        sa.text("INSERT INTO ref.funciones (codigo, nombre) VALUES (:c, :n)"),
        [{"c": c, "n": n} for c, n in FUNCIONES],
    )

    conn.execute(
        sa.text("INSERT INTO ref.programas_presupuestales (codigo, nombre) VALUES (:c, :n)"),
        [{"c": c, "n": n} for c, n in PROGRAMAS],
    )


def downgrade() -> None:
    op.execute("DELETE FROM ref.programas_presupuestales")
    op.execute("DELETE FROM ref.funciones")
    op.execute("DELETE FROM ref.rubros")
    op.execute("DELETE FROM ref.fuentes_financiamiento")
