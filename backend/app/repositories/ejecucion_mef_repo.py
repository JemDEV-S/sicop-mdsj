"""Repositorio del snapshot MEF (PostgreSQL, `siaf.ejecucion_presupuestal`).

Este módulo consulta los agregados del snapshot que alimenta el portal ciudadano.
Se usa para exponer en el panel interno los **mismos números oficiales** que ve
el ciudadano en el MEF, lado a lado con los indicadores operativos del SIGA.

Reglas de granularidad SIAF (ver CLAUDE.md §5 y Docs/hallazgos-granularidad-siaf.md):

  - PIA/PIM: solo vienen con valor en `mes_eje = 0` (fila maestra de la API MEF).
  - Certificado/Comprometido/Devengado/Girado: son flujos mensuales, se suman
    todos los meses > 0 para el total anual.

Nunca mezclar en el mismo SUM las filas mes_eje=0 con mes_eje>0.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


def resumen_mef(db: Session, *, ano: int) -> dict[str, Any]:
    """Totales oficiales MEF (PIA/PIM desde mes_0, ejecución desde meses>0).

    Devuelve un dict con las mismas llaves que el portal público muestra al
    ciudadano: pia, pim, certificado, comprometido, devengado, girado. Además
    calcula `saldo_disponible = pim - devengado` y `porcentaje_devengado`.
    """
    r = db.execute(
        text(
            """
            SELECT
              (SELECT COALESCE(SUM(monto_pia), 0)
                 FROM siaf.ejecucion_presupuestal
                WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                  AND mes_eje = 0)                            AS pia,
              (SELECT COALESCE(SUM(monto_pim), 0)
                 FROM siaf.ejecucion_presupuestal
                WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                  AND mes_eje = 0)                            AS pim,
              (SELECT COALESCE(SUM(monto_certificado), 0)
                 FROM siaf.ejecucion_presupuestal
                WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                  AND mes_eje > 0)                            AS certificado,
              (SELECT COALESCE(SUM(monto_comprometido_anual), 0)
                 FROM siaf.ejecucion_presupuestal
                WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                  AND mes_eje > 0)                            AS comprometido,
              (SELECT COALESCE(SUM(monto_devengado), 0)
                 FROM siaf.ejecucion_presupuestal
                WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                  AND mes_eje > 0)                            AS devengado,
              (SELECT COALESCE(SUM(monto_girado), 0)
                 FROM siaf.ejecucion_presupuestal
                WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                  AND mes_eje > 0)                            AS girado,
              (SELECT MAX(sincronizado_en)
                 FROM siaf.ejecucion_presupuestal
                WHERE ano_eje = :ano AND sec_ejec = :sec_ejec) AS sincronizado_en
            """
        ),
        {"ano": ano, "sec_ejec": settings.SEC_EJEC},
    ).mappings().one_or_none()

    if r is None:
        return {
            "pia": 0.0, "pim": 0.0, "certificado": 0.0, "comprometido": 0.0,
            "devengado": 0.0, "girado": 0.0, "saldo_disponible": 0.0,
            "porcentaje_devengado": 0.0, "sincronizado_en": None,
        }

    pim = float(r["pim"] or 0)
    devengado = float(r["devengado"] or 0)
    saldo_disponible = pim - devengado
    porcentaje = round(devengado / pim * 100, 2) if pim > 0 else 0.0

    return {
        "pia": float(r["pia"] or 0),
        "pim": pim,
        "certificado": float(r["certificado"] or 0),
        "comprometido": float(r["comprometido"] or 0),
        "devengado": devengado,
        "girado": float(r["girado"] or 0),
        "saldo_disponible": saldo_disponible,
        "porcentaje_devengado": porcentaje,
        "sincronizado_en": r["sincronizado_en"],
    }
