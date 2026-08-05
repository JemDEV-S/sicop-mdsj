"""Servicio del cruce SIAF-SIGA: enriquece el consolidado de meta con MEF real.

El `cruce_repo` trae el presupuesto SIGA operativo por meta (PIM, certificado,
comprometido — fases previas). Aquí se adjunta el devengado OFICIAL del MEF
desde la vista `siaf.v_ejecucion_meta_anual` (misma fuente que saldos y
pipeline), para que la "Vista consolidada de meta" (T-51) muestre el mismo
número que el portal público, y no un devengado en 0.

Ver Docs/consolidacion-backend-presupuestal.md (Iteración 3).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import cruce_repo, ejecucion_mef_repo


def consolidado_por_meta(
    db: Session,
    *,
    ano: int,
    sec_func: int,
    centros: list[str] | None = None,
) -> dict[str, Any] | None:
    """Consolidado de meta (HU-13) con presupuesto dual SIGA + MEF real."""
    resultado = cruce_repo.consolidado_por_meta(ano, sec_func, centros=centros)
    if resultado is None:
        return None

    presupuesto = dict(resultado.get("presupuesto") or {})

    # Devengado MEF real de la meta (o vacío si no cruza con el snapshot).
    mef_por_meta = ejecucion_mef_repo.ejecucion_por_meta(
        db, ano=ano, sec_funcs=[sec_func]
    )
    mef = mef_por_meta.get(sec_func)

    presupuesto["pim_mef"] = mef["pim"] if mef else None
    presupuesto["certificado_mef"] = mef["certificado"] if mef else None
    presupuesto["comprometido_mef"] = mef["comprometido"] if mef else None
    presupuesto["devengado_mef"] = mef["devengado"] if mef else None
    presupuesto["girado_mef"] = mef["girado"] if mef else None
    if mef and mef["pim"] > 0:
        presupuesto["saldo_disponible_mef"] = mef["pim"] - mef["devengado"]
        presupuesto["porcentaje_devengado"] = round(
            mef["devengado"] / mef["pim"] * 100, 2
        )
    else:
        presupuesto["saldo_disponible_mef"] = None
        presupuesto["porcentaje_devengado"] = None

    resultado["presupuesto"] = presupuesto
    return resultado


def consolidado_por_clasificador(
    db: Session,
    *,
    ano: int,
    sec_func: int,
    clasificador: str,
    centros: list[str] | None = None,
) -> dict[str, Any] | None:
    """Cruce SIAF-SIGA de un clasificador dentro de una meta.

    Filtra órdenes, certificaciones y pedidos al clasificador de gasto. El
    presupuesto es el techo SIGA de ese clasificador (fases previas). A este
    nivel NO hay bloque MEF: el snapshot oficial se guarda por meta, no por
    clasificador — el flag `sin_mef` lo deja explícito para que la UI lo aclare.
    """
    resultado = cruce_repo.consolidado_por_clasificador(
        ano, sec_func, clasificador, centros=centros
    )
    if resultado is None:
        return None
    # El presupuesto de clasificador es solo SIGA operativo; el % oficial no se
    # puede calcular a este nivel (el MEF no baja a clasificador).
    resultado["sin_mef"] = True
    return resultado
