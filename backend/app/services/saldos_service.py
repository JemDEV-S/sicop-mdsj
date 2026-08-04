"""Servicio de saldos: cruza SIGA operativo + devengado MEF real + semáforo.

Aplica RN-04 (filtro por CC): admin ve todo, otros ven solo sus CC
(descendientes ya resueltos por `permisos_service`).

Modelo dual por meta (Docs/consolidacion-backend-presupuestal.md, Iteración 2):

  - **SIGA operativo** (saldos_repo): PIM, certificado, comprometido, saldo
    disponible y reservado a nivel meta, con filtro por CC. Son las fases
    PREVIAS al devengado; nunca se etiquetan como "devengado".
  - **Devengado MEF real** (ejecucion_mef_repo, vista v_ejecucion_meta_anual):
    el devengado OFICIAL por meta, el mismo que ve el ciudadano en el portal.
    Se cruza por `sec_func` (cruce verificado 100% con las metas SIGA con PIM).

El % de ejecución y el semáforo se calculan SIEMPRE sobre el devengado MEF
real (`devengado_mef / pim_mef`). Solo si una meta no está en el snapshot MEF
se cae al PIM SIGA como último recurso, dejando el devengado en None.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import ejecucion_mef_repo, saldos_repo
from app.services import semaforo_service


def _fusionar_mef(
    fila_siga: dict[str, Any], mef: dict[str, Any] | None
) -> dict[str, Any]:
    """Adjunta el bloque MEF de la meta y calcula % + saldo sobre el dato real.

    `fila_siga` trae los montos SIGA operativos (pim, certificado, comprometido).
    `mef` es la fila de `ejecucion_por_meta` para ese sec_func, o None si la meta
    no está en el snapshot MEF.
    """
    fila = dict(fila_siga)

    # Montos MEF (oficiales). Sufijo _mef explícito para no confundir la fuente.
    pim_mef = float(mef["pim"]) if mef else None
    devengado_mef = float(mef["devengado"]) if mef else None
    fila["pim_mef"] = pim_mef
    fila["certificado_mef"] = float(mef["certificado"]) if mef else None
    fila["comprometido_mef"] = float(mef["comprometido"]) if mef else None
    fila["devengado_mef"] = devengado_mef
    fila["girado_mef"] = float(mef["girado"]) if mef else None

    # % de ejecución y saldo: SIEMPRE sobre el devengado real del MEF.
    if pim_mef and pim_mef > 0 and devengado_mef is not None:
        fila["porcentaje_devengado"] = round(devengado_mef / pim_mef * 100, 2)
        fila["saldo_disponible_mef"] = pim_mef - devengado_mef
    else:
        # La meta no cruza con MEF (raro: solo metas sin PIM). Sin devengado
        # oficial, el % queda indefinido — no lo inventamos con cert+compr.
        fila["porcentaje_devengado"] = None
        fila["saldo_disponible_mef"] = None

    return fila


def _con_semaforo(db: Session, fila: dict[str, Any]) -> dict[str, Any]:
    """Colorea sobre el % devengado MEF real (o 'desconocido' si no hay dato)."""
    fila["semaforo"] = semaforo_service.color(
        db,
        modulo="saldos",
        metrica="avance_devengado",
        valor=fila.get("porcentaje_devengado"),
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

    # Un solo golpe al snapshot MEF para las metas de esta página.
    sec_funcs = [int(f["sec_func"]) for f in filas]
    mef_por_meta = ejecucion_mef_repo.ejecucion_por_meta(
        db, ano=ano, sec_funcs=sec_funcs
    )

    items = [
        _con_semaforo(db, _fusionar_mef(f, mef_por_meta.get(int(f["sec_func"]))))
        for f in filas
    ]
    return items, total


def resumen_saldos(
    db: Session,
    *,
    ano: int,
    centros: list[str] | None,
    top_criticas_limit: int = 3,
    umbral_critico: float = 30.0,
) -> dict[str, Any]:
    """Totales agregados + top-N metas críticas para el dashboard T-44.

    Devuelve un resumen dual:
      - Totales SIGA operativos (pim, certificado, comprometido, saldo, ...):
        con filtro por CC.
      - Bloque `mef`: totales oficiales del snapshot MEF, restringidos a las
        metas visibles del usuario (ya no se oculta a quien tiene filtro de CC).
      - `top_metas_criticas`: metas con menor % devengado REAL (MEF) y alto PIM.

    El semáforo global se calcula sobre el % del bloque MEF (número oficial).
    """
    resumen = saldos_repo.resumen_saldos(ano=ano, centros=centros)
    metas_siga = resumen.pop("metas", [])
    resumen["ano"] = ano

    # Devengado MEF real para las metas visibles del usuario. Restringido a los
    # sec_func de su alcance → el bloque MEF ahora SÍ existe para decisores/CC.
    sec_funcs = [int(m["sec_func"]) for m in metas_siga]
    mef_por_meta = ejecucion_mef_repo.ejecucion_por_meta(
        db, ano=ano, sec_funcs=sec_funcs if centros is not None else None
    )

    # Bloque MEF agregado del alcance (suma de las metas visibles).
    pim_mef = sum(m["pim"] for m in mef_por_meta.values())
    dev_mef = sum(m["devengado"] for m in mef_por_meta.values())
    resumen["mef"] = {
        "pia": sum(m["pia"] for m in mef_por_meta.values()),
        "pim": pim_mef,
        "certificado": sum(m["certificado"] for m in mef_por_meta.values()),
        "comprometido": sum(m["comprometido"] for m in mef_por_meta.values()),
        "devengado": dev_mef,
        "girado": sum(m["girado"] for m in mef_por_meta.values()),
        "saldo_disponible": pim_mef - dev_mef,
        "porcentaje_devengado": round(dev_mef / pim_mef * 100, 2) if pim_mef > 0 else 0.0,
        "sincronizado_en": next(
            (m["sincronizado_en"] for m in mef_por_meta.values() if m.get("sincronizado_en")),
            None,
        ),
    } if mef_por_meta else None

    # Criticidad por % devengado MEF real. Metas sin dato MEF no se marcan.
    criticas: list[dict[str, Any]] = []
    for m in metas_siga:
        mef = mef_por_meta.get(int(m["sec_func"]))
        if not mef or mef["pim"] <= 0:
            continue
        pct = round(mef["devengado"] / mef["pim"] * 100, 2)
        if pct < umbral_critico:
            criticas.append({
                "sec_func": m["sec_func"],
                "nombre_meta": m["nombre_meta"],
                "pim": mef["pim"],
                "devengado": mef["devengado"],
                "porcentaje_devengado": pct,
            })
    # Prioriza por PIM (mayor peso presupuestal) descendente.
    criticas.sort(key=lambda x: x["pim"], reverse=True)
    resumen["metas_criticas"] = len(criticas)
    resumen["top_metas_criticas"] = [
        _con_semaforo(db, c) for c in criticas[:top_criticas_limit]
    ]

    # % y semáforo global sobre el bloque MEF (número oficial).
    porcentaje_global = (
        float(resumen["mef"]["porcentaje_devengado"])
        if resumen["mef"] is not None
        else None
    )
    resumen["porcentaje_devengado"] = porcentaje_global or 0.0
    resumen["semaforo"] = semaforo_service.color(
        db,
        modulo="saldos",
        metrica="avance_devengado",
        valor=porcentaje_global,
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
    """Metas con % devengado REAL (MEF) < umbral (HU-16, RN-02).

    El umbral se evalúa sobre el devengado oficial del MEF, no sobre cert+compr.
    Ordena por % ascendente (las más rezagadas primero).
    """
    metas_siga = saldos_repo.metas_con_saldo(ano=ano, centros=centros)
    sec_funcs = [int(m["sec_func"]) for m in metas_siga]
    mef_por_meta = ejecucion_mef_repo.ejecucion_por_meta(
        db, ano=ano, sec_funcs=sec_funcs if centros is not None else None
    )

    rezagadas: list[dict[str, Any]] = []
    for m in metas_siga:
        mef = mef_por_meta.get(int(m["sec_func"]))
        if not mef or mef["pim"] <= 0:
            continue
        pct = round(mef["devengado"] / mef["pim"] * 100, 2)
        if pct < umbral_porcentaje:
            fila = {
                "sec_func": m["sec_func"],
                "nombre_meta": m["nombre_meta"],
                "act_proy": m["act_proy"],
                "pim": mef["pim"],
                "devengado": mef["devengado"],
                "porcentaje_devengado": pct,
            }
            rezagadas.append(_con_semaforo(db, fila))

    rezagadas.sort(key=lambda x: x["porcentaje_devengado"])
    return rezagadas[:limit]
