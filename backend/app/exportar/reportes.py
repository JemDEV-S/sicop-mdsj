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
from app.services import ejecucion_service, permisos_service, saldos_service
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


# ─── Registro ────────────────────────────────────────────────────────────

_REGISTRO: dict[str, Reporte] = {
    r.codigo: r
    for r in (
        REPORTE_SALDOS,
        REPORTE_SALDOS_DETALLE,
        REPORTE_EJECUCION_DETALLE,
        REPORTE_PEDIDOS,
        REPORTE_CONTRATOS,
    )
}


def obtener_reporte(codigo: str) -> Reporte | None:
    return _REGISTRO.get(codigo)


def listar_reportes() -> list[dict[str, str]]:
    return [{"codigo": r.codigo, "titulo": r.titulo} for r in _REGISTRO.values()]
