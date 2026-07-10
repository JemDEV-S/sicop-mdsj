"""Queries SIGA para el job de sincronización de catálogos.

Filtran siempre por `SEC_EJEC=300687` y por año vigente. Ver §11 del
diccionario para las queries de referencia y §5 de datos-iniciales-siga
para el modelo relacional.

Todas devuelven `list[dict]` para facilitar el testing (mock estático).
"""

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


def _filtro_ejec_ano(ano: int) -> dict[str, Any]:
    return {"ano": ano, "sec_ejec": settings.SEC_EJEC}


def leer_centros_costo(ano: int) -> list[dict[str, Any]]:
    """Lee todos los centros de costo del año, activos o no.

    Se traen inactivos también para mantener trazabilidad de metas históricas.
    El flag `activo` (`ESTADO='A'`) se conserva.

    Normalizaciones aplicadas en la query:
    - `CENTRO_PADRE` con solo whitespace → NULL (raíz del árbol)
    - Trim de nombres/abreviados
    """
    sql = """
        SELECT
            LTRIM(RTRIM(CENTRO_COSTO))                             AS codigo,
            LTRIM(RTRIM(NOMBRE_DEPEND))                            AS nombre,
            LTRIM(RTRIM(ABREVIADO_DEPEND))                         AS abreviado,
            NULLIF(LTRIM(RTRIM(ISNULL(CENTRO_PADRE, ''))), '')     AS centro_padre,
            SEDE                                                   AS sede,
            LTRIM(RTRIM(TIPO_DEPEND))                              AS tipo_dependencia,
            NRO_PERSONAL                                           AS nro_personal,
            CASE WHEN LTRIM(RTRIM(ISNULL(FLAG_CN, ''))) = 'S'
                 THEN 1 ELSE 0 END                                 AS flag_cn,
            CASE WHEN LTRIM(RTRIM(ISNULL(FLAG_PRESUPUESTO, ''))) = 'S'
                 THEN 1 ELSE 0 END                                 AS flag_presupuesto,
            CASE WHEN LTRIM(RTRIM(ISNULL(flag_ppr, ''))) = 'S'
                 THEN 1 ELSE 0 END                                 AS flag_ppr,
            CASE WHEN ESTADO = 'A' THEN 1 ELSE 0 END               AS activo
        FROM SIG_CENTRO_COSTO
        WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), _filtro_ejec_ano(ano)).mappings().all()
    return [dict(r) for r in rows]


def leer_metas(ano: int) -> list[dict[str, Any]]:
    """Lee todas las metas del año.

    `tipo_meta` se calcula según el prefijo de `act_proy` (§18.8 dicc):
    - `3999999` → actividad genérica
    - `2xxxxxx` → proyecto de inversión
    - `3xxxxxx` (≠ 3999999) → actividad PP
    - resto → otros
    """
    sql = """
        SELECT
            CAST(sec_func AS BIGINT)                       AS sec_func,
            CAST(ano_eje AS SMALLINT)                      AS ano_eje,
            LTRIM(RTRIM(meta))                             AS meta,
            LTRIM(RTRIM(nombre))                           AS nombre,
            LTRIM(RTRIM(funcion))                          AS funcion,
            LTRIM(RTRIM(programa))                         AS programa,
            LTRIM(RTRIM(sub_programa))                     AS sub_programa,
            LTRIM(RTRIM(act_proy))                         AS act_proy,
            LTRIM(RTRIM(componente))                       AS componente,
            LTRIM(RTRIM(finalidad))                        AS finalidad,
            LTRIM(RTRIM(unidad_med))                       AS unidad_med,
            CASE WHEN estado = 'A' THEN 1 ELSE 0 END       AS activo
        FROM META
        WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), _filtro_ejec_ano(ano)).mappings().all()

    resultado = []
    for r in rows:
        d = dict(r)
        d["tipo_meta"] = _clasificar_tipo_meta(d.get("act_proy"))
        resultado.append(d)
    return resultado


def leer_metas_centro_costo(ano: int) -> list[dict[str, Any]]:
    """Lee el puente meta↔CC deduplicado.

    Se descartan filas donde no exista el par (sec_func, centro_costo) en las
    tablas maestras, para evitar violar las FK en el swap.
    """
    sql = """
        SELECT
            CAST(mxc.sec_func AS BIGINT)                   AS sec_func,
            LTRIM(RTRIM(mxc.centro_costo))                 AS centro_costo,
            CAST(mxc.secuencia AS SMALLINT)                AS secuencia,
            LTRIM(RTRIM(mxc.fuente_financ))                AS fuente_financ,
            LTRIM(RTRIM(mxc.tipo_recurso))                 AS tipo_recurso,
            mxc.porc_techo                                 AS porc_techo
        FROM SIG_METAS_X_CENTRO mxc
        INNER JOIN META m
            ON m.ano_eje = mxc.ano_eje
           AND m.sec_ejec = mxc.sec_ejec
           AND m.sec_func = mxc.sec_func
        INNER JOIN SIG_CENTRO_COSTO cc
            ON cc.ANO_EJE = mxc.ano_eje
           AND cc.SEC_EJEC = mxc.sec_ejec
           AND cc.CENTRO_COSTO = mxc.centro_costo
        WHERE mxc.ano_eje = :ano AND mxc.sec_ejec = :sec_ejec
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), _filtro_ejec_ano(ano)).mappings().all()
    return [dict(r) for r in rows]


def _clasificar_tipo_meta(act_proy: str | None) -> str:
    """Clasifica el tipo de meta por el prefijo de `act_proy` (§18.8 dicc)."""
    if not act_proy:
        return "otros"
    codigo = act_proy.strip()
    if codigo == "3999999":
        return "actividad_generica"
    if codigo.startswith("2"):
        return "proyecto_inversion"
    if codigo.startswith("3"):
        return "actividad_pp"
    return "otros"
