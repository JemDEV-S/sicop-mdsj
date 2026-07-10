"""Servicio de obras: orquesta obras_repo + semaforo."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import obras_repo
from app.services import semaforo_service


def _con_semaforo(db: Session, fila: dict[str, Any]) -> dict[str, Any]:
    fila["semaforo"] = semaforo_service.color(
        db,
        modulo="obras",
        metrica="avance_fisico",
        valor=float(fila["avance_fisico"]) if fila.get("avance_fisico") is not None else None,
    )
    return fila


def listar_obras(
    db: Session, **filtros
) -> tuple[list[dict[str, Any]], int]:
    filas, total = obras_repo.listar_obras(db, **filtros)
    return [_con_semaforo(db, f) for f in filas], total


def obtener_obra(
    db: Session, *, codigo_unico: str, ano: int | None = None
) -> dict[str, Any] | None:
    ficha = obras_repo.obtener_obra(db, codigo_unico=codigo_unico)
    if ficha is None:
        return None
    montos = obras_repo.montos_de_obra(db, codigo_unico=codigo_unico, ano=ano)
    porc = None
    pim = float(montos.get("pim") or 0)
    if pim > 0:
        porc = round(float(montos.get("devengado") or 0) / pim * 100, 2)
    ficha["montos_ejecucion"] = {**montos, "porcentaje_devengado": porc}
    ficha["semaforo"] = semaforo_service.color(
        db,
        modulo="obras",
        metrica="avance_fisico",
        valor=float(ficha["avance_fisico"]) if ficha.get("avance_fisico") is not None else None,
    )
    return ficha


def obras_para_mapa(
    db: Session, *, ano: int | None = None, funcion: str | None = None
) -> dict[str, Any]:
    con_coords = obras_repo.obras_para_mapa(db, ano=ano, funcion=funcion)
    sin_coords = obras_repo.obras_sin_coordenadas(db)
    items = [_con_semaforo(db, dict(f)) for f in con_coords]
    return {
        "items": items,
        "sin_coordenadas": sin_coords,
        "total_con_coords": len(items),
        "total_sin_coords": len(sin_coords),
    }
