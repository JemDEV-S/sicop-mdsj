"""Servicio de saldos: orquesta saldos_repo + semaforo.

Aplica RN-04 (filtro por CC): admin ve todo, otros ven solo sus CC
(descendientes ya resueltos por `permisos_service`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import saldos_repo
from app.services import semaforo_service


def _con_semaforo(db: Session, fila: dict[str, Any]) -> dict[str, Any]:
    fila["semaforo"] = semaforo_service.color(
        db,
        modulo="saldos",
        metrica="porcentaje_devengado",
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

    Delega la agregación al repo (una sola pasada por SIG_TECHO_PRESUPUESTO) y
    aplica el semáforo global sobre el % devengado agregado y a cada meta crítica.
    """
    resumen = saldos_repo.resumen_saldos(ano=ano, centros=centros)

    resumen["ano"] = ano
    resumen["semaforo"] = semaforo_service.color(
        db,
        modulo="saldos",
        metrica="porcentaje_devengado",
        valor=float(resumen.get("porcentaje_devengado") or 0),
    )
    resumen["top_metas_criticas"] = [
        _con_semaforo(db, m) for m in resumen.get("top_metas_criticas", [])
    ]
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
