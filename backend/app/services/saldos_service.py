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
    certificado_mef = float(mef["certificado"]) if mef else None
    comprometido_mef = float(mef["comprometido"]) if mef else None
    devengado_mef = float(mef["devengado"]) if mef else None
    girado_mef = float(mef["girado"]) if mef else None
    fila["pim_mef"] = pim_mef
    fila["certificado_mef"] = certificado_mef
    fila["comprometido_mef"] = comprometido_mef
    fila["devengado_mef"] = devengado_mef
    fila["girado_mef"] = girado_mef

    # ── Cadena de ejecución SIAF/MEF con saldos entre fases y % por fase ──────
    # El presupuesto es SIEMPRE del SIAF/MEF (el PIM SIGA discrepa en el 75% de
    # las metas). Toda cifra presupuestal y todo saldo/% de la fila sale de aquí.
    if pim_mef and pim_mef > 0 and devengado_mef is not None:
        cert = certificado_mef or 0
        compr = comprometido_mef or 0
        dev = devengado_mef
        gir = girado_mef or 0

        # Saldos entre fases consecutivas (dónde está detenido el gasto).
        fila["saldo_por_certificar"] = round(pim_mef - cert, 2)   # PIM − Certificado
        fila["saldo_por_comprometer_mef"] = round(cert - compr, 2)  # Cert − Comprometido
        fila["saldo_por_devengar"] = round(compr - dev, 2)         # Compr − Devengado
        fila["saldo_por_ejecutar"] = round(pim_mef - dev, 2)       # PIM − Devengado (clave)
        fila["saldo_por_pagar"] = round(dev - gir, 2)              # Devengado − Girado
        fila["saldo_disponible_mef"] = fila["saldo_por_ejecutar"]  # alias legado

        # % de avance por fase sobre el PIM oficial (dónde se estanca).
        fila["porcentaje_certificado"] = round(cert / pim_mef * 100, 2)
        fila["porcentaje_comprometido"] = round(compr / pim_mef * 100, 2)
        fila["porcentaje_devengado"] = round(dev / pim_mef * 100, 2)
        fila["porcentaje_girado"] = round(gir / pim_mef * 100, 2)
        fila["devengado_no_girado_mef"] = round(dev - gir, 2)
    else:
        # La meta no cruza con MEF (raro: solo metas sin PIM). Sin cifra oficial,
        # los saldos y % quedan indefinidos — no se inventan con datos SIGA.
        for k in (
            "saldo_por_certificar", "saldo_por_comprometer_mef", "saldo_por_devengar",
            "saldo_por_ejecutar", "saldo_por_pagar", "saldo_disponible_mef",
            "porcentaje_certificado", "porcentaje_comprometido",
            "porcentaje_devengado", "porcentaje_girado", "devengado_no_girado_mef",
        ):
            fila[k] = None

    # ── Referencia operativa SIGA (NO presupuestal) ──────────────────────────
    # El PIM SIGA discrepa del SIAF en el 75% de las metas → no se expone como
    # cifra de presupuesto. Se conserva remapeado con sufijo _siga solo como
    # referencia operativa; el detalle real por clasificador vive en el drill-down.
    fila["pim_siga"] = float(fila.pop("pim", 0) or 0)
    fila["certificado_siga"] = float(fila.pop("certificado", 0) or 0)
    fila["comprometido_siga"] = float(fila.pop("comprometido_anual", 0) or 0)
    fila["saldo_disponible_siga"] = float(fila.pop("saldo_disponible", 0) or 0)
    fila["reservado_pedido"] = float(fila.get("reservado_pedido", 0) or 0)
    # Limpieza de llaves SIGA que ya no exponemos como cifra.
    fila.pop("comprometido_mensual", None)
    fila.pop("pia", None)

    return fila


def _con_semaforo(db: Session, fila: dict[str, Any], *, mes_corte: int) -> dict[str, Any]:
    """Semáforo temporal: compara el % devengado real vs. el esperado por el mes.

    En vez de un corte fijo, mide el rezago (esperado − real) y expone el contexto
    en `semaforo_ctx` para que la UI explique el color (esperado/real/rezago/mes).
    El campo plano `semaforo` conserva el color para compatibilidad.
    """
    ctx = semaforo_service.color_temporal(
        db,
        modulo="saldos",
        porcentaje_real=fila.get("porcentaje_devengado"),
        mes_corte=mes_corte,
    )
    fila["semaforo"] = ctx["color"]
    fila["semaforo_ctx"] = ctx
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
    mes_corte = ejecucion_mef_repo.mes_maximo_ejecutado(db, ano=ano)

    items = [
        _con_semaforo(
            db,
            _fusionar_mef(f, mef_por_meta.get(int(f["sec_func"]))),
            mes_corte=mes_corte,
        )
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

    # Criticidad por REZAGO temporal (esperado − real), no por corte fijo: una
    # meta es crítica si su semáforo temporal da rojo. Metas sin MEF no se marcan.
    mes_corte = ejecucion_mef_repo.mes_maximo_ejecutado(db, ano=ano)
    resumen["mes_corte"] = mes_corte
    resumen["avance_esperado"] = semaforo_service.avance_esperado(mes_corte)

    criticas: list[dict[str, Any]] = []
    for m in metas_siga:
        mef = mef_por_meta.get(int(m["sec_func"]))
        if not mef or mef["pim"] <= 0:
            continue
        pct = round(mef["devengado"] / mef["pim"] * 100, 2)
        ctx = semaforo_service.color_temporal(
            db, modulo="saldos", porcentaje_real=pct, mes_corte=mes_corte
        )
        if ctx["color"] == "rojo":
            criticas.append({
                "sec_func": m["sec_func"],
                "nombre_meta": m["nombre_meta"],
                "pim": mef["pim"],
                "devengado": mef["devengado"],
                "porcentaje_devengado": pct,
                "semaforo": ctx["color"],
                "semaforo_ctx": ctx,
            })
    # Prioriza por PIM (mayor peso presupuestal) descendente.
    criticas.sort(key=lambda x: x["pim"], reverse=True)
    resumen["metas_criticas"] = len(criticas)
    resumen["top_metas_criticas"] = criticas[:top_criticas_limit]

    # % y semáforo global temporal sobre el bloque MEF (número oficial).
    porcentaje_global = (
        float(resumen["mef"]["porcentaje_devengado"])
        if resumen["mef"] is not None
        else None
    )
    resumen["porcentaje_devengado"] = porcentaje_global or 0.0
    ctx_global = semaforo_service.color_temporal(
        db, modulo="saldos", porcentaje_real=porcentaje_global, mes_corte=mes_corte
    )
    resumen["semaforo"] = ctx_global["color"]
    resumen["semaforo_ctx"] = ctx_global
    return resumen


def detalle_meta(
    db: Session,
    *,
    ano: int,
    sec_func: int,
    centros: list[str] | None,
) -> dict[str, Any] | None:
    """Detalle drill-down de una meta: cabecera oficial + árbol operativo SIGA.

    Estructura:
      - `cabecera`: la cadena de ejecución oficial (SIAF/MEF) de la meta con sus
        saldos entre fases, % por fase y semáforo temporal — igual que la fila de
        la lista.
      - `fuentes`: árbol Fuente de Financiamiento → Clasificadores. Es el detalle
        OPERATIVO del SIGA (qué se compra en cada clasificador), NO presupuesto:
        el presupuesto oficial vive en la cabecera. Incluye TODOS los
        clasificadores, también los de PIM 0 (marcados `sin_pim`), para no ocultar
        líneas del plan (era el bug de la meta 57).

    Devuelve `None` si la meta no existe o no es visible para el usuario.
    """
    cab_siga = saldos_repo.cabecera_meta(ano=ano, sec_func=sec_func, centros=centros)
    if cab_siga is None:
        return None

    mef_por_meta = ejecucion_mef_repo.ejecucion_por_meta(
        db, ano=ano, sec_funcs=[sec_func]
    )
    mes_corte = ejecucion_mef_repo.mes_maximo_ejecutado(db, ano=ano)
    cabecera = _con_semaforo(
        db, _fusionar_mef(cab_siga, mef_por_meta.get(sec_func)), mes_corte=mes_corte
    )

    lineas = saldos_repo.detalle_meta_jerarquico(ano, sec_func, centros)
    fuentes = _agrupar_por_fuente(lineas)

    return {
        "ano": ano,
        "cabecera": cabecera,
        "fuentes": fuentes,
    }


def _agrupar_por_fuente(lineas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Arma el árbol Fuente → Clasificadores a partir de las filas planas.

    Cada fuente lleva sus clasificadores y los subtotales de la fuente. Los
    clasificadores con PIM 0 se marcan `sin_pim` (para que la UI los distinga sin
    ocultarlos). Ordena fuentes por PIM descendente, clasificadores idem.
    """
    por_codigo: dict[str, dict[str, Any]] = {}
    for ln in lineas:
        fcod = (ln.get("fuente_codigo") or "").strip() or "—"
        grupo = por_codigo.setdefault(
            fcod,
            {
                "fuente_codigo": fcod,
                "fuente_nombre": (ln.get("fuente_nombre") or "").strip() or None,
                "pim": 0.0,
                "certificado": 0.0,
                "comprometido": 0.0,
                "saldo_disponible": 0.0,
                "clasificadores": [],
            },
        )
        pim = float(ln.get("pim") or 0)
        cert = float(ln.get("certificado") or 0)
        compr = float(ln.get("comprometido") or 0)
        disp = float(ln.get("saldo_disponible") or 0)

        grupo["pim"] += pim
        grupo["certificado"] += cert
        grupo["comprometido"] += compr
        grupo["saldo_disponible"] += disp
        grupo["clasificadores"].append(
            {
                "codigo": (ln.get("codigo") or "").strip() or None,
                "nombre": (ln.get("nombre") or "").strip() or None,
                "pim": round(pim, 2),
                "certificado": round(cert, 2),
                "comprometido": round(compr, 2),
                "saldo_disponible": round(disp, 2),
                "saldo_por_comprometer": round(pim - compr, 2),
                "reservado_pedido": float(ln.get("reservado_pedido") or 0),
                "filas": int(ln.get("filas") or 0),
                "sin_pim": pim == 0,
            }
        )

    fuentes = list(por_codigo.values())
    for g in fuentes:
        g["pim"] = round(g["pim"], 2)
        g["certificado"] = round(g["certificado"], 2)
        g["comprometido"] = round(g["comprometido"], 2)
        g["saldo_disponible"] = round(g["saldo_disponible"], 2)
        g["n_clasificadores"] = len(g["clasificadores"])
        g["clasificadores"].sort(key=lambda c: c["pim"], reverse=True)
    fuentes.sort(key=lambda g: g["pim"], reverse=True)
    return fuentes


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
    mes_corte = ejecucion_mef_repo.mes_maximo_ejecutado(db, ano=ano)

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
            rezagadas.append(_con_semaforo(db, fila, mes_corte=mes_corte))

    rezagadas.sort(key=lambda x: x["porcentaje_devengado"])
    return rezagadas[:limit]
