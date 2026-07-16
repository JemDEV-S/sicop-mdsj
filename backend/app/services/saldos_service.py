"""Servicio de saldos: orquesta saldos_repo + snapshot MEF + semaforo.

Aplica RN-04 (filtro por CC): admin ve todo, otros ven solo sus CC
(descendientes ya resueltos por `permisos_service`).

Diseño de indicadores duales (2026-07-16):
  - Bloque SIGA (saldos_repo): PIM/certificado/comprometido a nivel meta,
    con filtro por CC. Refleja la operación interna.
  - Bloque MEF (ejecucion_mef_repo): PIA/PIM/devengado oficial que ve el
    ciudadano en el portal. Sin filtro por CC (es agregado del pliego).

El widget muestra ambos lado a lado para que el funcionario vea a la vez
"lo asignado a mi unidad" (SIGA) y "el número público" (MEF).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import ejecucion_mef_repo, saldos_repo
from app.services import semaforo_service


def _con_semaforo(db: Session, fila: dict[str, Any]) -> dict[str, Any]:
    fila["semaforo"] = semaforo_service.color(
        db,
        modulo="saldos",
        metrica="avance_devengado",
        valor=float(fila.get("porcentaje_devengado") or 0),
    )
    return fila


def listar_saldos(
    db: Session,
    *,
    ano: int,
    centros: list[str] | None,
    sec_func: int | None = None,
    clasificador: str | None = None,
    fuente_financ: str | None = None,
    solo_con_pim: bool = True,
    limit: int = 25,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    filas = saldos_repo.listar_saldos(
        ano=ano,
        centros=centros,
        sec_func=sec_func,
        clasificador=clasificador,
        fuente_financ=fuente_financ,
        solo_con_pim=solo_con_pim,
        limit=limit,
        offset=offset,
    )
    total = saldos_repo.contar_saldos(
        ano=ano, centros=centros, solo_con_pim=solo_con_pim
    )
    return [_con_semaforo(db, f) for f in filas], total


def resumen_saldos(
    db: Session,
    *,
    ano: int,
    centros: list[str] | None,
) -> dict[str, Any]:
    """Totales agregados + top-3 metas críticas para el dashboard T-44.

    Devuelve un resumen dual:
      - Campos "planos" (pim, devengado, ...): datos SIGA a nivel meta con
        filtro por CC. Se mantienen para compatibilidad con el widget existente.
      - Bloque `mef`: totales oficiales del snapshot MEF (sin filtro por CC).
        Es lo que ve el ciudadano en el portal público.

    El semáforo se aplica al % del bloque MEF (número oficial) cuando existe;
    si el snapshot está vacío o el CC del usuario limita la vista, se usa el %
    del bloque SIGA como fallback.
    """
    resumen = saldos_repo.resumen_saldos(ano=ano, centros=centros)

    resumen["ano"] = ano
    resumen["top_metas_criticas"] = [
        _con_semaforo(db, m) for m in resumen.get("top_metas_criticas", [])
    ]

    # Snapshot MEF (oficial, sin filtro por CC — es del pliego).
    # Solo tiene sentido si el usuario ve el pliego completo (admin/decisor sin
    # filtro). Si el usuario está restringido a una subrama de CC, el número
    # MEF no coincidiría con lo que ve en el bloque SIGA — lo omitimos.
    ve_pliego_completo = centros is None
    if ve_pliego_completo:
        resumen["mef"] = ejecucion_mef_repo.resumen_mef(db, ano=ano)
    else:
        resumen["mef"] = None

    # Semáforo: usar el % del MEF si existe (número oficial), si no el SIGA.
    porcentaje_para_semaforo = (
        float(resumen["mef"]["porcentaje_devengado"])
        if resumen["mef"] is not None
        else float(resumen.get("porcentaje_devengado") or 0)
    )
    resumen["semaforo"] = semaforo_service.color(
        db,
        modulo="saldos",
        metrica="avance_devengado",
        valor=porcentaje_para_semaforo,
    )
    return resumen


def metas_rezagadas(
    db: Session,
    *,
    ano: int,
    centros: list[str] | None,
    umbral_porcentaje: float = 50.0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    filas = saldos_repo.metas_rezagadas(
        ano=ano,
        centros=centros,
        umbral_porcentaje=umbral_porcentaje,
        limit=limit,
    )
    return [_con_semaforo(db, f) for f in filas]
