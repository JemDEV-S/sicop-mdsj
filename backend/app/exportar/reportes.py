"""Registro de reportes exportables.

Cada reporte define: `codigo`, `titulo`, `columnas` y `obtener_datos(db, filtros, user)`.
Los servicios existentes se reutilizan para consistencia con lo que se ve en pantalla.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.security.deps import CurrentUser
from app.services import (
    ejecucion_service,
    permisos_service,
    pipeline_reporte_service,
    saldos_service,
)
from app.repositories import contratos_repo, pipeline_repo


@dataclass(frozen=True)
class Columna:
    key: str
    label: str
    formato: str = "texto"  # "texto" | "numero" | "moneda" | "fecha" | "porcentaje"


@dataclass(frozen=True)
class Reporte:
    codigo: str
    titulo: str
    columnas: list[Columna]
    obtener_datos: Callable[[Session, dict[str, Any], CurrentUser | None], list[dict[str, Any]]]
    con_totales: bool = False
    columnas_totalizables: list[str] = field(default_factory=list)


# ─── Reporte: SALDOS ─────────────────────────────────────────────────────

def _datos_saldos(
    db: Session, filtros: dict[str, Any], user: CurrentUser | None
) -> list[dict[str, Any]]:
    # Respeta el CC del filtro (centro_costo) igual que el endpoint de pantalla,
    # no solo el alcance completo del usuario. Alineado al esquema DUAL por meta:
    # las columnas SIGA son fases previas y el devengado sale del MEF (_mef).
    permitidos = user.centros_permitidos if user else None
    centros = permisos_service.restringir_a_subrama(
        db, permitidos, filtros.get("centro_costo")
    )
    items, _ = saldos_service.listar_saldos(
        db,
        ano=filtros.get("ano") or settings.ANO_VIGENTE,
        centros=centros,
        sec_func=filtros.get("sec_func"),
        clasificador=filtros.get("clasificador"),
        fuente_financ=filtros.get("fuente_financ"),
        solo_con_pim=filtros.get("solo_con_pim", True),
        limit=filtros.get("limit", 5000),
        offset=0,
    )
    return items


REPORTE_SALDOS = Reporte(
    codigo="saldos",
    titulo="Saldos presupuestales por meta (ejecución oficial SIAF)",
    columnas=[
        Columna("sec_func", "Meta"),
        Columna("nombre_meta", "Nombre de meta"),
        Columna("act_proy", "Acto/Proy"),
        # ── Cadena de ejecución oficial (SIAF/MEF) ──
        Columna("pim_mef", "PIM", "moneda"),
        Columna("certificado_mef", "Certificado", "moneda"),
        Columna("comprometido_mef", "Comprometido", "moneda"),
        Columna("devengado_mef", "Devengado", "moneda"),
        Columna("girado_mef", "Girado", "moneda"),
        # ── Saldos y avance ──
        Columna("saldo_por_ejecutar", "Por ejecutar", "moneda"),
        Columna("saldo_por_pagar", "Por pagar", "moneda"),
        Columna("porcentaje_devengado", "% Devengado", "porcentaje"),
        Columna("porcentaje_girado", "% Girado", "porcentaje"),
        Columna("semaforo", "Estado"),
    ],
    obtener_datos=_datos_saldos,
    con_totales=True,
    columnas_totalizables=[
        "pim_mef", "certificado_mef", "comprometido_mef", "devengado_mef",
        "girado_mef", "saldo_por_ejecutar", "saldo_por_pagar",
    ],
)


# ─── Reporte: DETALLE DE META (drill-down por clasificador) ──────────────

def _datos_saldos_detalle(
    db: Session, filtros: dict[str, Any], user: CurrentUser | None
) -> list[dict[str, Any]]:
    """Detalle operativo SIGA de una meta, aplanado a filas fuente+clasificador
    (para exportar el drill-down jerárquico que se ve en pantalla). Requiere
    `sec_func` en los filtros. Incluye TODOS los clasificadores (también PIM 0).
    """
    sec_func = filtros.get("sec_func")
    if sec_func is None:
        return []
    permitidos = user.centros_permitidos if user else None
    centros = permisos_service.restringir_a_subrama(
        db, permitidos, filtros.get("centro_costo")
    )
    data = saldos_service.detalle_meta(
        db,
        ano=filtros.get("ano") or settings.ANO_VIGENTE,
        sec_func=int(sec_func),
        centros=centros,
    )
    if not data:
        return []
    filas: list[dict[str, Any]] = []
    for f in data["fuentes"]:
        for c in f["clasificadores"]:
            filas.append({
                "fuente_codigo": f["fuente_codigo"],
                "fuente_nombre": f["fuente_nombre"],
                "codigo": c["codigo"],
                "nombre": c["nombre"],
                "pim": c["pim"],
                "certificado": c["certificado"],
                "comprometido": c["comprometido"],
                "saldo_por_comprometer": c["saldo_por_comprometer"],
                "saldo_disponible": c["saldo_disponible"],
                "filas": c["filas"],
            })
    return filas


REPORTE_SALDOS_DETALLE = Reporte(
    codigo="saldos_detalle",
    titulo="Detalle operativo de meta (fuente y clasificador de gasto)",
    columnas=[
        Columna("fuente_codigo", "Fuente"),
        Columna("fuente_nombre", "Nombre fuente"),
        Columna("codigo", "Clasificador"),
        Columna("nombre", "Descripción"),
        Columna("pim", "PIM", "moneda"),
        Columna("certificado", "Certificado", "moneda"),
        Columna("comprometido", "Comprometido", "moneda"),
        Columna("saldo_por_comprometer", "Por comprometer", "moneda"),
        Columna("saldo_disponible", "Saldo disponible", "moneda"),
        Columna("filas", "Líneas", "numero"),
    ],
    obtener_datos=_datos_saldos_detalle,
    con_totales=True,
    columnas_totalizables=[
        "pim", "certificado", "comprometido",
        "saldo_por_comprometer", "saldo_disponible",
    ],
)


# ─── Reporte: EJECUCION DETALLE ─────────────────────────────────────────

def _datos_ejecucion_detalle(
    db: Session, filtros: dict[str, Any], user: CurrentUser | None
) -> list[dict[str, Any]]:
    items, _ = ejecucion_service.detalle(
        db,
        ano=filtros.get("ano"),
        funcion=filtros.get("funcion"),
        fuente=filtros.get("fuente"),
        categoria_gasto=filtros.get("categoria_gasto"),
        limit=filtros.get("limit", 5000),
        offset=0,
        sort=filtros.get("sort", "pim_desc"),
    )
    return items


REPORTE_EJECUCION_DETALLE = Reporte(
    codigo="ejecucion_detalle",
    titulo="Detalle de ejecucion presupuestal",
    columnas=[
        Columna("funcion_codigo", "Cod. Funcion"),
        Columna("funcion_nombre", "Funcion"),
        Columna("sec_func", "Meta"),
        Columna("meta_codigo", "Cod. Meta"),
        Columna("meta_nombre", "Nombre de meta"),
        Columna("producto_proyecto", "Producto/Proyecto"),
        Columna("pim", "PIM", "moneda"),
        Columna("certificado", "Certificado", "moneda"),
        Columna("devengado", "Devengado", "moneda"),
        Columna("girado", "Girado", "moneda"),
        Columna("porcentaje_ejecucion", "% Ejec.", "porcentaje"),
    ],
    obtener_datos=_datos_ejecucion_detalle,
    con_totales=True,
    columnas_totalizables=["pim", "certificado", "devengado", "girado"],
)


# ─── Reporte: PEDIDOS ────────────────────────────────────────────────────

def _datos_pedidos(
    db: Session, filtros: dict[str, Any], user: CurrentUser | None
) -> list[dict[str, Any]]:
    from app.services import pipeline_service
    centros = user.centros_permitidos if user else None
    filas = pipeline_service.clasificar_pedidos(
        db,
        ano=filtros.get("ano") or settings.ANO_VIGENTE,
        centros=centros,
    )
    etapa = filtros.get("etapa")
    macrofase = filtros.get("macrofase")
    if etapa:
        filas = [f for f in filas if f.get("etapa") == etapa]
    elif macrofase:
        filas = [f for f in filas if f.get("macrofase") == macrofase]
    return filas


REPORTE_PEDIDOS = Reporte(
    codigo="pedidos",
    titulo="Pipeline de pedidos",
    columnas=[
        Columna("ano_eje", "Ano"),
        Columna("nro_pedido", "Nro."),
        Columna("tipo_bien", "Tipo"),
        Columna("centro_costo", "CC"),
        Columna("sec_func", "Meta"),
        Columna("macrofase_label", "Macrofase"),
        Columna("etapa_numero", "Etapa #", "numero"),
        Columna("etapa_label", "Etapa"),
        Columna("fecha_pedido", "Fecha", "fecha"),
        Columna("motivo", "Motivo"),
        Columna("solicitante", "Solicitante"),
        Columna("monto_total", "Monto", "moneda"),
        Columna("items", "Items", "numero"),
    ],
    obtener_datos=_datos_pedidos,
    con_totales=True,
    columnas_totalizables=["monto_total"],
)


# ─── Reporte: CONTRATOS ──────────────────────────────────────────────────

def _datos_contratos(
    db: Session, filtros: dict[str, Any], user: CurrentUser | None
) -> list[dict[str, Any]]:
    filas = contratos_repo.listar_contratos(
        ano=filtros.get("ano"),
        proveedor_ruc=filtros.get("proveedor_ruc"),
        estado=filtros.get("estado"),
        limit=filtros.get("limit", 5000),
        offset=0,
    )
    mapa = {
        "ANO_EJE": "ano_eje", "SEC_EJEC": "sec_ejec",
        "TIPO_CONTRATO": "tipo_contrato",
        "NRO_CONTRATO": "nro_contrato", "SEC_CONTRATO": "sec_contrato",
        "TIPO_BIEN": "tipo_bien",
        "FECHA_INICIAL": "fecha_inicial", "FECHA_FINAL": "fecha_final",
        "VALOR_SOLES": "valor_soles",
    }
    return [{mapa.get(k, k): v for k, v in f.items()} for f in filas]


REPORTE_CONTRATOS = Reporte(
    codigo="contratos",
    titulo="Contratos",
    columnas=[
        Columna("ano_eje", "Ano"),
        Columna("nro_contrato", "Nro."),
        Columna("sec_contrato", "Sec."),
        Columna("proveedor_ruc", "RUC"),
        Columna("proveedor_nombre", "Proveedor"),
        Columna("fecha_inicial", "Inicio", "fecha"),
        Columna("fecha_final", "Fin", "fecha"),
        Columna("valor_soles", "Monto", "moneda"),
        Columna("objeto", "Objeto"),
        Columna("estado", "Estado"),
    ],
    obtener_datos=_datos_contratos,
    con_totales=True,
    columnas_totalizables=["valor_soles"],
)


# ─── Reporte: PIPELINE PROFESIONAL (Meta → Clasificador → Pedido) ────────
#
# Aplana el pivote §9.7 a filas-pedido. Regla anti-inflado (§7): la ÚNICA
# columna totalizable es el monto SIGA del pedido (sumable por fila). El
# devengado/comprometido MEF de la meta y de la celda van como CONTEXTO
# repetido y rotulado, NUNCA en `columnas_totalizables` — sumarlos por fila
# inflaría el resultado ×34.9. El devengado por pedido es estimado y tampoco
# se totaliza.

def _datos_pipeline_reporte(
    db: Session, filtros: dict[str, Any], user: CurrentUser | None
) -> list[dict[str, Any]]:
    permitidos = user.centros_permitidos if user else None
    centros = permisos_service.restringir_a_subrama(
        db, permitidos, filtros.get("centro_costo")
    )
    data = pipeline_reporte_service.reporte_profesional(
        db, ano=filtros.get("ano") or settings.ANO_VIGENTE, centros=centros
    )
    # Catálogo código → etiqueta (nombre + sigla) para que el CC del Excel sea
    # legible, igual que en la vista. Cae al código si no hay nombre.
    cc_label = {
        cc["codigo"]: (
            f"{cc['nombre']} ({cc['sigla']})" if cc.get("nombre") else cc["codigo"]
        )
        for cc in data.get("centros_costo", [])
    }

    def _cc(codigo: str | None) -> str | None:
        return cc_label.get(codigo, codigo) if codigo else None

    filas: list[dict[str, Any]] = []
    for m in data["metas"]:
        mef_meta = m["mef"]
        cc_meta = ", ".join(_cc(c) or c for c in m["centros_costo"]) or None
        for c in m["celdas"]:
            mef_celda = c["mef"] or {}
            for p in c["pedidos"]:
                ident = p.get("identificadores") or {}
                atrib = p.get("atribucion")
                dev = p.get("devengado_estimado")
                filas.append({
                    "sec_func": m["sec_func"],
                    "nombre_meta": m["nombre_meta"],
                    "centro_costo": _cc(p.get("centro_costo")) or cc_meta,
                    "clasificador": c["clasificador"],
                    "clasificador_nombre": c["clasificador_nombre"],
                    "nro_pedido": p["nro_pedido"],
                    "tipo_bien": p["tipo_bien"],
                    "motivo": p.get("motivo"),
                    "orden": ident.get("orden"),
                    "exp_siaf": ident.get("exp_siaf"),
                    "etapa_label": p.get("etapa_label"),
                    "dias_en_etapa": p.get("dias_en_etapa"),
                    "estado": "Estancado" if p.get("estancado") else "En curso",
                    "monto_siga": p.get("monto_siga") or 0,
                    # ── Contexto MEF (informativo, NO sumable) ──
                    "comprometido_pedido": p.get("comprometido_pedido"),
                    "devengado_pedido": dev,
                    "tipo_devengado": (
                        "directo (celda de 1 pedido)" if atrib == "directo"
                        else "estimado (reparto en celda)" if atrib == "estimado"
                        else ("sin ejecución (sin orden)" if not p.get("tiene_orden") else "")
                    ),
                    "comprometido_meta_mef": mef_meta["comprometido"],
                    "devengado_meta_mef": mef_meta["devengado"],
                    "pct_devengado_meta": mef_meta["porcentaje_devengado"],
                })
    return filas


REPORTE_PIPELINE_PROFESIONAL = Reporte(
    codigo="pipeline_reporte",
    titulo="Pipeline presupuestal — cruce SIGA × SIAF por clasificador (Meta → Clasificador → Pedido)",
    columnas=[
        Columna("sec_func", "Meta"),
        Columna("nombre_meta", "Nombre de meta"),
        Columna("centro_costo", "Centro de costo"),
        Columna("clasificador", "Clasificador"),
        Columna("clasificador_nombre", "Específica de gasto"),
        Columna("nro_pedido", "N° Pedido"),
        Columna("tipo_bien", "Tipo"),
        Columna("motivo", "Motivo"),
        Columna("orden", "N° Orden"),
        Columna("exp_siaf", "Exp. SIAF"),
        Columna("etapa_label", "Etapa actual"),
        Columna("dias_en_etapa", "Días en etapa", "numero"),
        Columna("estado", "Estado"),
        # Única columna que suma por fila (dinero SIGA del pedido).
        Columna("monto_siga", "Monto SIGA (pedido)", "moneda"),
        # Contexto MEF — informativo, no se totaliza (ver nota de la hoja).
        Columna("comprometido_pedido", "Comprometido pedido (MEF)", "moneda"),
        Columna("devengado_pedido", "Devengado pedido (MEF)", "moneda"),
        Columna("tipo_devengado", "Tipo devengado"),
        Columna("comprometido_meta_mef", "Comprometido meta (MEF, 1×)", "moneda"),
        Columna("devengado_meta_mef", "Devengado meta (MEF, 1×)", "moneda"),
        Columna("pct_devengado_meta", "% Devengado meta", "porcentaje"),
    ],
    obtener_datos=_datos_pipeline_reporte,
    con_totales=True,
    # SOLO el monto SIGA se totaliza. El dinero MEF NO — es contexto por meta
    # repetido en cada fila y sumarlo mentiría (§2.1, inflado ×34.9).
    columnas_totalizables=["monto_siga"],
)


# ─── Registro ────────────────────────────────────────────────────────────

_REGISTRO: dict[str, Reporte] = {
    r.codigo: r
    for r in (
        REPORTE_SALDOS,
        REPORTE_SALDOS_DETALLE,
        REPORTE_EJECUCION_DETALLE,
        REPORTE_PEDIDOS,
        REPORTE_PIPELINE_PROFESIONAL,
        REPORTE_CONTRATOS,
    )
}


def obtener_reporte(codigo: str) -> Reporte | None:
    return _REGISTRO.get(codigo)


def listar_reportes() -> list[dict[str, str]]:
    return [{"codigo": r.codigo, "titulo": r.titulo} for r in _REGISTRO.values()]
