"""Reporte profesional del pipeline: pivote Meta → Clasificador → Pedido.

Vista para economistas (Docs/pipeline-vista-profesional-v2.md, alternativa B+C
con el cruce fino por clasificador §9.7). Reúne, sin doble conteo:

  - Por pedido (SIGA): recorrido de macrofases con fechas, monto solicitado,
    estado/estancado. Sale de `pipeline_service.clasificar_pedidos` (la misma
    fuente que el kanban), así que la clasificación es idéntica entre vistas.
  - Por celda `SEC_FUNC + clasificador` (MEF): comprometido y devengado SIAF
    reales por específica de gasto (`ejecucion_mef_repo`). El cruce por
    clasificador baja el grano de meta (≈15 ped) a específica (≈3.5 ped) y en el
    27.7% de celdas la atribución es directa (1 pedido).
  - Por meta (MEF): PIM/comprometido/devengado de la meta completa, 1× por meta.

Regla de oro anti-inflado (§7): lo que se suma por fila es dinero SIGA del
pedido; el dinero MEF se suma UNA VEZ por meta. El devengado por pedido es una
ESTIMACIÓN por reparto dentro de su celda de clasificador — se rotula y NUNCA
entra en un total sumable. El total MEF del reporte es el devengado real por
meta distinta.

Alcance por CC (RN-04/RN-06): se hereda de `clasificar_pedidos` (filtra los
pedidos por los centros del usuario) y las metas MEF se intersectan con las
metas visibles de esos pedidos.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.repositories import ejecucion_mef_repo, pipeline_read_repo
from app.services import pipeline_service, semaforo_service

# Macrofases que cuentan como "en contratación" y "en ejecución" para el
# resumen por meta (columnas del pivote §3). Mismo criterio que el kanban.
_MACROFASES_CONTRATACION = frozenset({"programacion", "certificacion", "contratacion"})
_MACROFASES_EJECUCION = frozenset({"ejecucion", "cierre"})

# Clave que agrupa los pedidos sin clasificador de genérica 3 cruzable (planilla
# accidental, ítems sin clasificador). No cruza con MEF; se muestra aparte.
_SIN_CLASIF = "(sin clasificador)"


def _card_a_pedido_reporte(card: dict[str, Any]) -> dict[str, Any]:
    """Proyecta una card del pipeline a la fila-pedido del reporte.

    Conserva lo que la tabla profesional muestra por fila: identificación,
    recorrido (fechas por etapa + etapa actual), estado y monto SIGA. El
    comprometido/devengado por pedido se añade luego (capa de reparto).
    """
    puente = card.get("puente") or {}
    avance = puente.get("avance_bolsa") or {}
    return {
        "nro_pedido": card.get("nro_pedido"),
        "tipo_bien": card.get("tipo_bien"),
        "tipo_pedido": card.get("tipo_pedido"),
        "centro_costo": card.get("centro_costo"),
        "motivo": card.get("motivo"),
        "identificadores": card.get("identificadores"),
        "fechas": card.get("fechas") or {},
        "etapa": card.get("etapa"),
        "etapa_label": card.get("etapa_label"),
        "macrofase": card.get("macrofase"),
        "dias_en_etapa": card.get("dias_en_etapa"),
        "estancado": bool(card.get("estancado")),
        "alerta": card.get("alerta"),
        "monto_siga": float(card.get("monto_total") or 0),
        # Honestidad del puente (§2.2): si la bolsa se comparte, el recorrido de
        # bolsa es del grupo, no exclusivo de este pedido. La UI lo pinta tramado.
        "n_candidatos_ccmn": int(card.get("n_candidatos_ccmn") or 0),
        "confianza_ccmn": card.get("confianza_ccmn"),
        "tiene_orden": (avance.get("n_ordenes") or 0) > 0,
        # Se llenan en la capa de reparto por celda (o quedan None).
        "comprometido_pedido": None,
        "devengado_estimado": None,
        "atribucion": None,  # "directo" | "estimado" | None
    }


def _semaforo_meta(
    db: Session, porcentaje_devengado: float | None, mes_corte: int
) -> dict[str, Any]:
    return semaforo_service.color_temporal(
        db,
        modulo="saldos",
        porcentaje_real=porcentaje_devengado,
        mes_corte=mes_corte,
    )


def reporte_profesional(
    db: Session, *, ano: int, centros: list[str] | None
) -> dict[str, Any]:
    """Arma el pivote Meta → Clasificador → Pedido con montos MEF por celda.

    El alcance por CC ya viene aplicado en `clasificar_pedidos` (filtra por
    `centros`). El dinero MEF se pide solo para las metas de esos pedidos.
    """
    cards = pipeline_service.clasificar_pedidos(db, ano=ano, centros=centros)

    # Clasificador dominante por pedido (normalizado a la llave SIAF).
    clasif_por_ped = pipeline_read_repo.clasificador_por_pedido(db, ano)

    # Metas visibles = las de los pedidos del alcance. El MEF se restringe a
    # ellas (RN-06: no filtramos dinero de metas que el usuario no ve).
    sec_funcs = sorted({int(c["sec_func"]) for c in cards if c.get("sec_func")})
    mef_por_meta = ejecucion_mef_repo.ejecucion_por_meta(db, ano=ano, sec_funcs=sec_funcs)
    mef_por_celda = ejecucion_mef_repo.ejecucion_por_celda_clasificador(
        db, ano=ano, sec_funcs=sec_funcs
    )
    mes_corte = ejecucion_mef_repo.mes_maximo_ejecutado(db, ano=ano)
    nombres_meta = _nombres_meta(db, sec_funcs)

    # Catálogo de CC (código → {nombre, sigla}) de todos los centros presentes en
    # los pedidos del alcance. Sirve al filtro (nombre) y a la tabla (sigla).
    codigos_cc = {c.get("centro_costo") for c in cards if c.get("centro_costo")}
    catalogo_cc = _catalogo_cc(db, sorted(codigos_cc))

    # ── Agrupación: meta → clasificador → pedidos ────────────────────────────
    # Estructura intermedia mutable; se ordena y sella al final.
    metas: dict[int, dict[str, Any]] = {}

    for card in cards:
        sec_func = card.get("sec_func")
        if sec_func is None:
            continue
        sec_func = int(sec_func)
        meta = metas.setdefault(sec_func, {
            "sec_func": sec_func,
            "nombre_meta": None,  # se completa desde MEF/card abajo
            "centros_costo": set(),
            "celdas": {},
        })
        meta["centros_costo"].add(card.get("centro_costo"))

        clave = (
            (card.get("tipo_bien") or "").strip(),
            (card.get("tipo_pedido") or "").strip(),
            int(card["nro_pedido"]),
        )
        info_clasif = clasif_por_ped.get(clave)
        clasif = info_clasif["clasificador"] if info_clasif else _SIN_CLASIF

        celda = meta["celdas"].setdefault(clasif, {
            "clasificador": clasif,
            "clasificador_nombre": None,
            "pedidos": [],
        })
        celda["pedidos"].append(_card_a_pedido_reporte(card))

    # ── Reparto del devengado dentro de cada celda (capa estimada §9.1) ──────
    # El devengado real es de la celda MEF. Se reparte SOLO entre los pedidos
    # con orden de la celda, proporcional a su monto SIGA. Con 1 pedido: directo.
    salida_metas: list[dict[str, Any]] = []
    total_mef_devengado = 0.0  # 1× por meta — el total honesto
    total_siga_pedidos = 0.0
    total_pedidos = 0

    for sec_func in sorted(metas):
        meta = metas[sec_func]
        mef_meta = mef_por_meta.get(sec_func)

        celdas_salida: list[dict[str, Any]] = []
        n_pedidos_meta = 0
        en_contratacion = 0
        en_ejecucion = 0
        monto_siga_meta = 0.0

        for clasif in sorted(meta["celdas"]):
            celda = meta["celdas"][clasif]
            pedidos = celda["pedidos"]
            n = len(pedidos)
            mef_celda = mef_por_celda.get((sec_func, clasif))

            # Nombre del clasificador desde MEF (la fuente autoritativa).
            nombre_clasif = mef_celda.get("clasificador_nombre") if mef_celda else None

            devengado_celda = float(mef_celda["devengado"]) if mef_celda else 0.0
            comprometido_celda = float(mef_celda["comprometido"]) if mef_celda else 0.0

            # Reparto: base = suma del monto SIGA de los pedidos CON orden.
            con_orden = [p for p in pedidos if p["tiene_orden"]]
            base = sum(p["monto_siga"] for p in con_orden)
            directa = n == 1 and clasif != _SIN_CLASIF and mef_celda is not None

            for p in pedidos:
                monto_siga_meta += p["monto_siga"]
                if p["macrofase"] in _MACROFASES_CONTRATACION:
                    en_contratacion += 1
                elif p["macrofase"] in _MACROFASES_EJECUCION:
                    en_ejecucion += 1

                # Comprometido "duro" del pedido: no lo tenemos por pedido de
                # forma dura sin la orden; lo dejamos None salvo celda directa
                # (1 pedido), donde el comprometido de la celda ES del pedido.
                if directa and p["tiene_orden"]:
                    p["comprometido_pedido"] = round(comprometido_celda, 2)
                    p["devengado_estimado"] = round(devengado_celda, 2)
                    p["atribucion"] = "directo"
                elif p["tiene_orden"] and base > 0 and devengado_celda > 0:
                    p["devengado_estimado"] = round(
                        devengado_celda * p["monto_siga"] / base, 2
                    )
                    p["atribucion"] = "estimado"
                # sin orden → sin monto de ejecución (capa contexto §9.1.3)

            n_pedidos_meta += n
            celdas_salida.append({
                "clasificador": clasif,
                "clasificador_nombre": nombre_clasif,
                "n_pedidos": n,
                "atribucion_directa": directa,
                "monto_siga": round(sum(p["monto_siga"] for p in pedidos), 2),
                # Dinero MEF real de la celda (no reparto). None si no cruza.
                "mef": {
                    "pim": round(float(mef_celda["pim"]), 2),
                    "comprometido": round(comprometido_celda, 2),
                    "devengado": round(devengado_celda, 2),
                } if mef_celda else None,
                "pedidos": pedidos,
            })

        # Bloque MEF de la meta (1× — el número honesto que se suma).
        pim = float(mef_meta["pim"]) if mef_meta else 0.0
        comprometido = float(mef_meta["comprometido"]) if mef_meta else 0.0
        devengado = float(mef_meta["devengado"]) if mef_meta else 0.0
        pct_dev = round(devengado / pim * 100, 2) if pim > 0 else None
        semaforo = _semaforo_meta(db, pct_dev, mes_corte)

        total_mef_devengado += devengado
        total_siga_pedidos += monto_siga_meta
        total_pedidos += n_pedidos_meta

        # Nombre de meta y CC: el CC es el conjunto real de centros de los
        # pedidos (una meta puede tocar varios). El nombre viene del catálogo.
        centros_meta = sorted(c for c in meta["centros_costo"] if c)
        salida_metas.append({
            "sec_func": sec_func,
            "nombre_meta": nombres_meta.get(sec_func),
            "centros_costo": centros_meta,
            "n_pedidos": n_pedidos_meta,
            "en_contratacion": en_contratacion,
            "en_ejecucion": en_ejecucion,
            "monto_siga": round(monto_siga_meta, 2),
            "mef": {
                "pim": round(pim, 2),
                "comprometido": round(comprometido, 2),
                "devengado": round(devengado, 2),
                "porcentaje_devengado": pct_dev,
                "semaforo": semaforo["color"],
                "semaforo_ctx": semaforo,
            },
            "n_celdas": len(celdas_salida),
            "n_celdas_directas": sum(1 for c in celdas_salida if c["atribucion_directa"]),
            "celdas": celdas_salida,
        })

    sincronizado = _sincronizado(db)
    return {
        "ano": ano,
        "mes_corte": mes_corte,
        "avance_esperado": semaforo_service.avance_esperado(mes_corte),
        "sincronizado_siga": sincronizado["siga"],
        "sincronizado_mef": sincronizado["mef"],
        "centros_costo": catalogo_cc,
        "metas": salida_metas,
        "totales": {
            "n_metas": len(salida_metas),
            "n_pedidos": total_pedidos,
            # SIGA: suma por pedido (informativo). MEF: suma 1× por meta (real).
            "total_siga_pedidos": round(total_siga_pedidos, 2),
            "total_mef_devengado": round(total_mef_devengado, 2),
        },
    }


# ─── Metadatos (nombre de meta, frescura) ────────────────────────────────

def _nombres_meta(db: Session, sec_funcs: list[int]) -> dict[int, str | None]:
    """Nombres de meta desde `ref.metas` (catálogo poblado por el sync), en lote."""
    if not sec_funcs:
        return {}
    from sqlalchemy import bindparam, text

    rows = db.execute(
        text(
            "SELECT sec_func, nombre FROM ref.metas WHERE sec_func IN :sfs"
        ).bindparams(bindparam("sfs", expanding=True)),
        {"sfs": sec_funcs},
    ).all()
    return {int(r[0]): (r[1].strip() if r[1] else None) for r in rows}


def _catalogo_cc(db: Session, codigos: list[str]) -> list[dict[str, Any]]:
    """Catálogo {codigo, nombre, sigla} de los CC del reporte, en lote.

    La sigla usa `abreviado` de `ref.centros_costo`; si viene vacío, cae al
    propio código para que la tabla siempre tenga una etiqueta corta legible.
    """
    if not codigos:
        return []
    from sqlalchemy import bindparam, text

    rows = db.execute(
        text(
            """
            SELECT codigo, nombre, abreviado
              FROM ref.centros_costo
             WHERE codigo IN :cods
            """
        ).bindparams(bindparam("cods", expanding=True)),
        {"cods": codigos},
    ).all()
    por_codigo = {
        r[0]: {
            "codigo": r[0],
            "nombre": (r[1].strip() if r[1] else None),
            "sigla": (r[2].strip() if r[2] and r[2].strip() else r[0]),
        }
        for r in rows
    }
    # Garantiza una entrada por cada CC pedido, aun si no está en el catálogo.
    return [
        por_codigo.get(cod, {"codigo": cod, "nombre": None, "sigla": cod})
        for cod in codigos
    ]


def _sincronizado(db: Session) -> dict[str, Any]:
    """Frescura de cada fuente: SIGA (snapshot pipeline) y MEF (corte diario)."""
    from sqlalchemy import text

    siga = db.execute(
        text(
            """
            SELECT MAX(sincronizado_en) FROM siga.pedidos
             WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
            """
        ),
        {"ano": settings.ANO_VIGENTE, "sec_ejec": int(settings.SEC_EJEC)},
    ).scalar()
    mef = db.execute(
        text(
            """
            SELECT MAX(sincronizado_en) FROM siaf.ejecucion_presupuestal
             WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
            """
        ),
        {"ano": settings.ANO_VIGENTE, "sec_ejec": settings.SEC_EJEC},
    ).scalar()
    return {"siga": siga, "mef": mef}
