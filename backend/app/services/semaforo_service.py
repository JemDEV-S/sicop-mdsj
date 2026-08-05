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


# ─── Semáforo temporal (avance real vs. esperado por transcurso del año) ──────

# Umbrales de BRECHA (esperado − real, en puntos porcentuales). Configurables en
# sistema.umbrales_semaforos con metrica='avance_vs_esperado', direccion='menor'
# (menos rezago = mejor). Defaults si la fila no existe todavía.
_BRECHA_DEFAULT = {"verde": 10.0, "amarillo": 25.0, "direccion": "menor"}


def avance_esperado(mes_corte: int) -> float:
    """% de avance que se esperaría a un mes de corte, lineal sobre 12 meses.

    mes_corte es el mes de datos del snapshot (MAX(mes_eje)), no el mes del
    calendario. Ej.: corte julio (7) → 58.33% esperado. Se acota a [0, 100].
    """
    mes = max(0, min(12, mes_corte))
    return round(mes / 12 * 100, 2)


def color_temporal(
    db: Session,
    *,
    modulo: str,
    porcentaje_real: float | None,
    mes_corte: int,
) -> dict[str, Any]:
    """Semáforo que compara el avance real contra el esperado por el mes de corte.

    En lugar de un corte fijo (p.ej. <30% = rojo, que en julio sería injusto),
    mide el REZAGO = esperado − real y lo colorea con umbrales de brecha:
      - rezago ≤ verde        → verde   (al día o adelantado)
      - rezago ≤ amarillo     → amarillo (rezago moderado)
      - rezago >  amarillo    → rojo     (rezago severo)

    Devuelve un dict con el color y el contexto para que la UI explique el porqué:
      {color, esperado, real, rezago, mes_corte}. `color='desconocido'` si no hay
      dato real (meta sin cruce MEF).
    """
    esperado = avance_esperado(mes_corte)
    if porcentaje_real is None:
        return {
            "color": "desconocido",
            "esperado": esperado,
            "real": None,
            "rezago": None,
            "mes_corte": mes_corte,
        }

    rezago = round(esperado - porcentaje_real, 2)

    umbrales = _CACHE.get((modulo, "avance_vs_esperado"))
    if umbrales is None:
        cargar_umbrales(db)
        umbrales = _CACHE.get((modulo, "avance_vs_esperado")) or _BRECHA_DEFAULT

    verde, amarillo = umbrales["verde"], umbrales["amarillo"]
    # Ir por encima de lo esperado (rezago negativo) siempre es verde.
    if rezago <= verde:
        color_ = "verde"
    elif rezago <= amarillo:
        color_ = "amarillo"
    else:
        color_ = "rojo"

    return {
        "color": color_,
        "esperado": esperado,
        "real": round(porcentaje_real, 2),
        "rezago": rezago,
        "mes_corte": mes_corte,
    }
