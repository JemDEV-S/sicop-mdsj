"""Servicio de semaforo (RN-01).

Los umbrales viven en `sistema.umbrales_semaforos` (modulo + metrica -> verde/amarillo/direccion).
Aqui se resuelve rapido con cache in-process (los cambios se hacen desde /admin/config,
no es critico invalidar).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def cargar_umbrales(db: Session) -> None:
    """Precarga la tabla `sistema.umbrales_semaforos` en memoria."""
    rows = db.execute(
        text(
            """
            SELECT modulo, metrica, umbral_verde, umbral_amarillo, direccion
              FROM sistema.umbrales_semaforos
            """
        )
    ).all()
    _CACHE.clear()
    for r in rows:
        _CACHE[(r.modulo, r.metrica)] = {
            "verde": float(r.umbral_verde),
            "amarillo": float(r.umbral_amarillo),
            "direccion": r.direccion,
        }


def color(
    db: Session, *, modulo: str, metrica: str, valor: float | None
) -> str:
    """Devuelve `verde | amarillo | rojo | desconocido`.

    `direccion=mayor`: valores altos son verdes (ej. avance fisico).
    `direccion=menor`: valores bajos son verdes (ej. dias estancado).
    """
    if valor is None:
        return "desconocido"

    umbrales = _CACHE.get((modulo, metrica))
    if umbrales is None:
        cargar_umbrales(db)
        umbrales = _CACHE.get((modulo, metrica))
    if umbrales is None:
        return "desconocido"

    verde, amarillo, direccion = umbrales["verde"], umbrales["amarillo"], umbrales["direccion"]
    if direccion == "mayor":
        if valor >= verde:
            return "verde"
        if valor >= amarillo:
            return "amarillo"
        return "rojo"
    # menor: menos es mejor
    if valor <= verde:
        return "verde"
    if valor <= amarillo:
        return "amarillo"
    return "rojo"


def invalidar_cache() -> None:
    _CACHE.clear()
