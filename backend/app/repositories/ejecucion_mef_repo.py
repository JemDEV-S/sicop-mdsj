"""Repositorio del snapshot MEF (PostgreSQL, `siaf.ejecucion_presupuestal`).

Este módulo consulta los agregados del snapshot que alimenta el portal ciudadano.
Se usa para exponer en el panel interno los **mismos números oficiales** que ve
el ciudadano en el MEF, lado a lado con los indicadores operativos del SIGA.

Reglas de granularidad SIAF (ver CLAUDE.md §5 y Docs/hallazgos-granularidad-siaf.md):

  - PIA/PIM: solo vienen con valor en `mes_eje = 0` (fila maestra de la API MEF).
  - Certificado/Comprometido/Devengado/Girado: son flujos mensuales, se suman
    todos los meses > 0 para el total anual.

Nunca mezclar en el mismo SUM las filas mes_eje=0 con mes_eje>0.

Fuente única (Docs/consolidacion-backend-presupuestal.md, Iteración 1):
  La vista `siaf.v_ejecucion_meta_anual` ya aplica esa regla de granularidad y
  agrega por `sec_func`. Tanto `resumen_mef` (total del pliego) como
  `ejecucion_por_meta` (desagregado) derivan de esa vista para que exista una
  sola definición de "ejecución MEF" en todo el backend.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


def _fila_vacia() -> dict[str, Any]:
    return {
        "pia": 0.0,
        "pim": 0.0,
        "certificado": 0.0,
        "comprometido": 0.0,
        "devengado": 0.0,
        "girado": 0.0,
        "saldo_disponible": 0.0,
        "porcentaje_devengado": 0.0,
        "sincronizado_en": None,
    }


def _con_derivados(base: dict[str, Any]) -> dict[str, Any]:
    """Añade `saldo_disponible` y `porcentaje_devengado` a un dict de montos MEF.

    saldo_disponible = pim - devengado.
    porcentaje_devengado = devengado / pim * 100 (el devengado REAL, no cert+compr).
    """
    pim = float(base.get("pim") or 0)
    devengado = float(base.get("devengado") or 0)
    return {
        "pia": float(base.get("pia") or 0),
        "pim": pim,
        "certificado": float(base.get("certificado") or 0),
        "comprometido": float(base.get("comprometido") or 0),
        "devengado": devengado,
        "girado": float(base.get("girado") or 0),
        "saldo_disponible": pim - devengado,
        "porcentaje_devengado": round(devengado / pim * 100, 2) if pim > 0 else 0.0,
        "sincronizado_en": base.get("sincronizado_en"),
    }


def mes_maximo_ejecutado(db: Session, *, ano: int) -> int:
    """Mes de ejecución más avanzado con datos en el snapshot (`MAX(mes_eje)`).

    Es el corte real de los datos, NO la fecha de hoy. Sobre un backup el
    snapshot puede ir a julio (mes 7) aunque hoy sea agosto — el avance esperado
    del semáforo debe medirse contra este mes, no contra el calendario, para no
    alarmar por el rezago propio del backup (memoria: datos-backup-no-tiempo-real).

    Devuelve 0 si no hay ejecución cargada (solo PIA/PIM en mes 0).
    """
    r = db.execute(
        text(
            """
            SELECT COALESCE(MAX(mes_eje), 0) AS mes
              FROM siaf.ejecucion_presupuestal
             WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje > 0
            """
        ),
        {"ano": ano, "sec_ejec": settings.SEC_EJEC},
    ).scalar_one()
    return int(r or 0)


def resumen_mef(db: Session, *, ano: int) -> dict[str, Any]:
    """Totales oficiales MEF del pliego (agregado de todas las metas).

    Devuelve un dict con las mismas llaves que el portal público muestra al
    ciudadano: pia, pim, certificado, comprometido, devengado, girado. Además
    calcula `saldo_disponible = pim - devengado` y `porcentaje_devengado`.

    Deriva de `siaf.v_ejecucion_meta_anual` (fuente única) sumando todas las
    metas, en vez de repetir la lógica de granularidad SIAF.
    """
    r = db.execute(
        text(
            """
            SELECT
                COALESCE(SUM(pia), 0)          AS pia,
                COALESCE(SUM(pim), 0)          AS pim,
                COALESCE(SUM(certificado), 0)  AS certificado,
                COALESCE(SUM(comprometido), 0) AS comprometido,
                COALESCE(SUM(devengado), 0)    AS devengado,
                COALESCE(SUM(girado), 0)       AS girado,
                MAX(sincronizado_en)           AS sincronizado_en
              FROM siaf.v_ejecucion_meta_anual
             WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
            """
        ),
        {"ano": ano, "sec_ejec": settings.SEC_EJEC},
    ).mappings().one_or_none()

    if r is None:
        return _fila_vacia()
    return _con_derivados(dict(r))


def ejecucion_por_meta(
    db: Session, *, ano: int, sec_funcs: list[int] | None = None
) -> dict[int, dict[str, Any]]:
    """Ejecución MEF oficial desagregada por meta (`sec_func`).

    Es la pieza que da a Saldos (T-48) y Cruce (T-51) el devengado real por
    meta. El devengado aquí es el OFICIAL del MEF (el mismo del portal público),
    nunca `cert + comprometido` ni `MNTO_ACUM_DEVGDO_SIGA`.

    Args:
        ano: año fiscal.
        sec_funcs: si se pasa, restringe a esas metas (para intersectar con las
            visibles del usuario según su CC). `None` = todas las metas del año.
            Lista vacía = ninguna (devuelve `{}`), coherente con "sin alcance".

    Returns:
        `dict[sec_func, {pia, pim, certificado, comprometido, devengado,
        girado, saldo_disponible, porcentaje_devengado, sincronizado_en}]`.
        Las metas sin fila en el snapshot simplemente no aparecen en el dict;
        el consumidor decide el fallback (LEFT JOIN en Python).
    """
    if sec_funcs is not None and len(sec_funcs) == 0:
        return {}

    where = ["ano_eje = :ano", "sec_ejec = :sec_ejec"]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    if sec_funcs is not None:
        binds = [f":sf{i}" for i in range(len(sec_funcs))]
        where.append(f"sec_func IN ({', '.join(binds)})")
        for i, sf in enumerate(sec_funcs):
            params[f"sf{i}"] = sf

    rows = db.execute(
        text(
            f"""
            SELECT
                sec_func, pia, pim, certificado, comprometido,
                devengado, girado, sincronizado_en
              FROM siaf.v_ejecucion_meta_anual
             WHERE {" AND ".join(where)}
            """
        ),
        params,
    ).mappings().all()

    return {int(r["sec_func"]): _con_derivados(dict(r)) for r in rows}
