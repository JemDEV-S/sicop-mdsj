"""Repositorio de obras — combina `siaf.inversiones` con `siaf.ejecucion_presupuestal`.

Ambas tablas viven en PostgreSQL (snapshot del MEF via T-12/T-13). El cruce
es por `CODIGO_UNICO ↔ PRODUCTO_PROYECTO` con `TIPO_ACT_PROY = '2'` (HU-01
AC-01.2 y §12.3 de actividad-1).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


# ─── Listado (HU-01) ─────────────────────────────────────────────────────

def listar_obras(
    db: Session,
    *,
    ano: int | None = None,
    funcion: str | None = None,
    tipologia: str | None = None,
    modalidad: str | None = None,
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
    sort: str = "pim_desc",
) -> tuple[list[dict[str, Any]], int]:
    """Devuelve (filas, total). Cada fila trae los campos para las tarjetas HU-01.

    Combina Invierte.pe (fuente principal) con el PIM/DEV mas recientes desde
    `siaf.ejecucion_presupuestal` (agregado por producto_proyecto).
    """
    ano_ejec = ano or settings.ANO_VIGENTE
    where = ["i.sec_ejec = :sec_ejec"]
    params: dict[str, Any] = {"sec_ejec": settings.SEC_EJEC, "ano": ano_ejec}

    if funcion is not None:
        where.append("i.funcion = :funcion")
        params["funcion"] = funcion
    if tipologia is not None:
        where.append("i.des_tipologia = :tipologia")
        params["tipologia"] = tipologia
    if modalidad is not None:
        where.append("i.des_modalidad = :modalidad")
        params["modalidad"] = modalidad
    if q:
        where.append(
            "(i.nombre_inversion ILIKE :q OR i.codigo_unico ILIKE :q)"
        )
        params["q"] = f"%{q}%"

    order_map = {
        "pim_desc": "COALESCE(i.pim_anio_actual, 0) DESC",
        "pim_asc": "COALESCE(i.pim_anio_actual, 0) ASC",
        "avance_desc": "COALESCE(i.avance_fisico, 0) DESC",
        "avance_asc": "COALESCE(i.avance_fisico, 0) ASC",
        "inicio_desc": "i.fec_ini_ejecucion DESC NULLS LAST",
        "inicio_asc": "i.fec_ini_ejecucion ASC NULLS LAST",
        "alfabetico": "i.nombre_inversion ASC",
    }
    order_by = order_map.get(sort, order_map["pim_desc"])

    sql_total = f"SELECT COUNT(*) FROM siaf.inversiones i WHERE {' AND '.join(where)}"
    total = int(db.execute(text(sql_total), params).scalar_one())

    sql_rows = f"""
        SELECT
            i.codigo_unico,
            i.nombre_inversion,
            i.funcion,
            i.des_tipologia    AS tipologia,
            i.des_modalidad    AS modalidad,
            i.estado,
            i.situacion,
            i.etapa_f8,
            i.avance_fisico,
            i.avance_ejecucion,
            i.pim_anio_actual,
            i.dev_anio_actual,
            i.tiene_avan_fisico,
            i.latitud,
            i.longitud
          FROM siaf.inversiones i
         WHERE {" AND ".join(where)}
      ORDER BY {order_by}
         LIMIT :limit OFFSET :offset
    """
    params_rows = {**params, "limit": limit, "offset": offset}
    rows = db.execute(text(sql_rows), params_rows).mappings().all()
    return [dict(r) for r in rows], total


# ─── Ficha (HU-02) ───────────────────────────────────────────────────────

def obtener_obra(
    db: Session, *, codigo_unico: str
) -> dict[str, Any] | None:
    """Devuelve la ficha completa de Invierte.pe. Los agregados SIAF (PIM,
    devengado, etc.) se sacan en `montos_de_obra` para no acoplar ambos."""
    row = (
        db.execute(
            text(
                """
                SELECT *
                  FROM siaf.inversiones
                 WHERE codigo_unico = :codigo
                   AND sec_ejec = :sec_ejec
                """
            ),
            {"codigo": codigo_unico, "sec_ejec": settings.SEC_EJEC},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def montos_de_obra(
    db: Session, *, codigo_unico: str, ano: int | None = None
) -> dict[str, float]:
    """Suma PIA/PIM/certificado/devengado/girado desde `siaf.ejecucion_presupuestal`.

    PIA/PIM solo vienen en mes_eje=0. Devengado/girado/certificado son flujos
    mensuales — se suman todos los meses > 0. Ver Docs/hallazgos-granularidad-siaf.md.
    """
    ano_ejec = ano or settings.ANO_VIGENTE
    row = (
        db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN mes_eje = 0 THEN monto_pia  ELSE 0 END), 0) AS pia,
                    COALESCE(SUM(CASE WHEN mes_eje = 0 THEN monto_pim  ELSE 0 END), 0) AS pim,
                    COALESCE(SUM(CASE WHEN mes_eje > 0 THEN monto_certificado       ELSE 0 END), 0) AS certificado,
                    COALESCE(SUM(CASE WHEN mes_eje > 0 THEN monto_comprometido_anual ELSE 0 END), 0) AS comprometido_anual,
                    COALESCE(SUM(CASE WHEN mes_eje > 0 THEN monto_devengado         ELSE 0 END), 0) AS devengado,
                    COALESCE(SUM(CASE WHEN mes_eje > 0 THEN monto_girado            ELSE 0 END), 0) AS girado
                  FROM siaf.ejecucion_presupuestal
                 WHERE ano_eje = :ano
                   AND sec_ejec = :sec_ejec
                   AND producto_proyecto = :codigo
                """
            ),
            {"ano": ano_ejec, "sec_ejec": settings.SEC_EJEC, "codigo": codigo_unico},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else {
        "pia": 0.0, "pim": 0.0, "certificado": 0.0,
        "comprometido_anual": 0.0, "devengado": 0.0, "girado": 0.0,
    }


# ─── Mapa (HU-04) ────────────────────────────────────────────────────────

def obras_para_mapa(
    db: Session,
    *,
    ano: int | None = None,
    funcion: str | None = None,
) -> list[dict[str, Any]]:
    """Respuesta ligera para marcadores: solo lat/lng + campos clave."""
    ano_ejec = ano or settings.ANO_VIGENTE
    where = ["sec_ejec = :sec_ejec", "latitud IS NOT NULL", "longitud IS NOT NULL"]
    params: dict[str, Any] = {"sec_ejec": settings.SEC_EJEC}
    if funcion:
        where.append("funcion = :funcion")
        params["funcion"] = funcion

    rows = (
        db.execute(
            text(
                f"""
                SELECT codigo_unico, nombre_inversion, funcion,
                       avance_fisico, pim_anio_actual,
                       latitud, longitud
                  FROM siaf.inversiones
                 WHERE {" AND ".join(where)}
                """
            ),
            params,
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def obras_sin_coordenadas(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            text(
                """
                SELECT codigo_unico, nombre_inversion, funcion,
                       avance_fisico, pim_anio_actual
                  FROM siaf.inversiones
                 WHERE sec_ejec = :sec_ejec
                   AND (latitud IS NULL OR longitud IS NULL)
                """
            ),
            {"sec_ejec": settings.SEC_EJEC},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


# ─── Catalogos de filtros (HU-01) ────────────────────────────────────────

def funciones_disponibles(db: Session) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT funcion
              FROM siaf.inversiones
             WHERE sec_ejec = :sec_ejec AND funcion IS NOT NULL
          ORDER BY funcion
            """
        ),
        {"sec_ejec": settings.SEC_EJEC},
    ).all()
    return [r.funcion for r in rows]


def tipologias_disponibles(db: Session) -> list[str]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT des_tipologia
              FROM siaf.inversiones
             WHERE sec_ejec = :sec_ejec AND des_tipologia IS NOT NULL
          ORDER BY des_tipologia
            """
        ),
        {"sec_ejec": settings.SEC_EJEC},
    ).all()
    return [r.des_tipologia for r in rows]
