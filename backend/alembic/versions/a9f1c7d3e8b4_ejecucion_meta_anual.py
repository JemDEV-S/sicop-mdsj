"""Vista siaf.v_ejecucion_meta_anual: ejecucion MEF agregada por meta (sec_func)

Revision ID: a9f1c7d3e8b4
Revises: e6f7a8b9c2d3
Create Date: 2026-08-04 10:00:00

Contexto (Docs/consolidacion-backend-presupuestal.md, Iteracion 1):
    El panel interno necesita el devengado OFICIAL (MEF) desagregado por meta,
    no solo el total del pliego. Hasta ahora `ejecucion_mef_repo` solo exponia
    `resumen_mef` (agregado global), lo que obligaba a ocultar el bloque MEF a
    los usuarios con filtro de CC y dejaba al modulo de cruce mostrando
    devengado=0 (usaba MNTO_ACUM_DEVGDO_SIGA, columna vacia en esta muni).

    Esta vista es la FUENTE UNICA de ejecucion presupuestal por meta que
    consumen Saldos (T-48) y Cruce (T-51). Replica exactamente la regla de
    granularidad que ya usa el portal publico (ejecucion_service.py):

      - PIA / PIM      -> desde mes_eje = 0 (fila maestra de la API MEF).
      - Certificado / Comprometido / Devengado / Girado -> flujos mensuales,
        se suman TODOS los meses > 0.

    Ver Docs/hallazgos-granularidad-siaf.md §4 (reglas de agregacion) y
    CLAUDE.md §5. Nunca mezclar en el mismo SUM las filas mes_eje=0 con las de
    mes_eje>0.

    Se apoya en la tabla base `siaf.ejecucion_presupuestal` (no en la vista
    normalizada) porque aqui solo interesan las llaves + montos por sec_func;
    los nombres de jerarquia los aportan `ref.*` en quien consuma la vista.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "a9f1c7d3e8b4"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CREATE_VIEW = """
CREATE VIEW siaf.v_ejecucion_meta_anual AS
SELECT
    ano_eje,
    sec_ejec,
    sec_func,
    COALESCE(SUM(monto_pia)                FILTER (WHERE mes_eje = 0), 0) AS pia,
    COALESCE(SUM(monto_pim)                FILTER (WHERE mes_eje = 0), 0) AS pim,
    COALESCE(SUM(monto_certificado)        FILTER (WHERE mes_eje > 0), 0) AS certificado,
    COALESCE(SUM(monto_comprometido_anual) FILTER (WHERE mes_eje > 0), 0) AS comprometido,
    COALESCE(SUM(monto_devengado)          FILTER (WHERE mes_eje > 0), 0) AS devengado,
    COALESCE(SUM(monto_girado)             FILTER (WHERE mes_eje > 0), 0) AS girado,
    MAX(sincronizado_en)                                                  AS sincronizado_en
FROM siaf.ejecucion_presupuestal
GROUP BY ano_eje, sec_ejec, sec_func
"""


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS siaf.v_ejecucion_meta_anual")
    op.execute(_CREATE_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS siaf.v_ejecucion_meta_anual")
