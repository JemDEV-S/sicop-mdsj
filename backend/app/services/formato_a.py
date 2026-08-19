"""Parser del reporte SIAF "Formato A" (Modulo Administrativo -> Reporte de
registro SIAF - Gastos, por mes de documento).

Este Excel es una carga PROVISIONAL: complementa lo que la API MEF publica.
La API MEF entrega ejecucion agregada por `sec_func` y mes (max 8 columnas,
sin detalle de documento). El Formato A, en cambio, trae el detalle a nivel
de DOCUMENTO / expediente que la API no da:

    - expediente SIAF + fase (Certificacion, Compromiso/Devengado, Girado,
      Pagado, Rendicion) con su sub-registro y correlativo;
    - clasificador de gasto completo (los 5 niveles, p.ej. 2.3.2.1.2.2);
    - proveedor con RUC y razon social;
    - documento sustento (tipo, numero, fecha) y fechas por fase
      (documento, aprobacion, proceso, contable);
    - fuente de financiamiento (rubro) y meta / sec_func.

El parser NO toca la base: solo lee el .xlsx y devuelve filas normalizadas
(dicts) + la cabecera del reporte (ejecutora, periodo, fecha de emision).
La persistencia vive en `app.jobs.import_formato_a`.

Formato del archivo (validado 2026-08 contra el export real de la muni):
    - Fila 1-2:  titulo del reporte ("SIAF - Modulo Administrativo" ...).
    - Fila 3-6:  cabecera SECTOR / PLIEGO / EJECUTORA / PERIODO (col C).
    - Fila 7:    encabezados de columna.
    - Fila 8+:   una fila por documento-fase. La col A es el expediente
                 (10 digitos) en las filas de datos; en filas de subtotal /
                 pie va vacia o con texto, por eso filtramos por "col A digito".

El texto puede venir con mojibake UTF-8/latin-1 (mismo defecto que SIGA); se
repara con `_demojibake` reutilizado de los extractores SIGA.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from openpyxl import load_workbook

from app.jobs.siga_extractores import _demojibake

# ─── Indices de columna en la fila 7 (0-based). Validados 2026-08. ───────────
# Solo mapeamos las columnas con valor analitico; el resto del ancho (67 cols)
# son auxiliares del aplicativo (Bnc, Cta, TP/TR/TC, db oracle, edicion...).
COL = {
    "expediente": 0,
    "ano_eje": 1,
    "sec_ejec": 3,
    "tipo_op": 6,
    "mod_compra": 7,
    "ciclo": 10,
    "fase": 11,
    "sub_reg": 12,
    "correlativo": 13,
    "secuencia_padre": 15,
    "origen": 16,
    "rubro": 17,
    "rubro_nombre": 18,
    "tipo_financ": 19,
    "cod_doc": 20,
    "num_doc": 21,
    "fecha_doc": 22,
    "tipo_prov": 29,
    "proveedor_ruc": 30,
    "proveedor_nombre": 31,
    "clasificador": 33,
    "sec_func": 34,
    "tipo_giro": 35,
    "monto_origen": 42,
    "monto_soles": 43,
    "fecha_aprobacion": 44,
    "fecha_proceso": 45,
    "sec_est": 46,
    "est_registro": 47,
    "certificado": 48,
    "certificado_secuencia": 49,
    "producto_proyecto": 53,
    "funcion": 56,
    "meta": 59,
}

HEADER_ROW = 7  # 1-based (fila de encabezados de columna)

# Codigos de fase del ciclo de gasto (col "Fase").
FASES = {
    "C": "Certificacion",
    "D": "Devengado",
    "G": "Girado",
    "P": "Pagado",
    "R": "Rendicion",
}


@dataclass
class CabeceraFormatoA:
    """Metadatos del reporte (filas 3-6 + fecha de emision)."""

    ejecutora: str | None = None
    periodo: str | None = None          # p.ej. "2026 - AGOSTO"
    ano: int | None = None
    emitido_en: datetime | None = None


@dataclass
class ResultadoParseo:
    cabecera: CabeceraFormatoA
    filas: list[dict[str, Any]] = field(default_factory=list)
    descartadas: int = 0                # filas de datos ignoradas (no-dato)


# ─── Conversores robustos ────────────────────────────────────────────────────

def _s(v: Any) -> str | None:
    if v is None:
        return None
    s = _demojibake(str(v)).strip()
    return s or None


def _i(v: Any) -> int | None:
    if v in (None, "", " "):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _f(v: Any) -> float:
    if v in (None, "", " "):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _fecha(v: Any) -> date | None:
    """Las fechas vienen como 'dd/mm/yyyy' (texto) o datetime de Excel."""
    if v in (None, "", " "):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _ruc(v: Any) -> str | None:
    """El RUC llega como float (10239927811.0). Lo pasamos a texto sin punto."""
    if v in (None, "", " "):
        return None
    if isinstance(v, (int, float)):
        return str(int(v))
    return _s(v)


# ─── Nucleo del parseo ───────────────────────────────────────────────────────

def _es_fila_dato(fila: tuple[Any, ...]) -> bool:
    """Una fila es de datos si la col A es un expediente (solo digitos)."""
    exp = fila[COL["expediente"]] if fila else None
    return isinstance(exp, str) and exp.strip().isdigit()


def _cabecera_reporte(por_fila: dict[int, tuple[Any, ...]]) -> CabeceraFormatoA:
    """Lee EJECUTORA / PERIODO (col C, index 2) de las filas 3-6 y la fecha
    de emision (fila 1, ultima celda con datetime)."""
    cab = CabeceraFormatoA()
    for _, fila in por_fila.items():
        etiqueta = _s(fila[0]) if fila else None
        valor = _s(fila[2]) if fila and len(fila) > 2 else None
        if etiqueta == "EJECUTORA":
            cab.ejecutora = valor
        elif etiqueta == "PERIODO":
            cab.periodo = valor
            if valor:
                cab.ano = _i(valor.split("-")[0].strip())
        # Fecha de emision: primer datetime de la fila 1.
        if fila and fila is por_fila.get(1):
            for celda in fila:
                if isinstance(celda, datetime):
                    cab.emitido_en = celda
                    break
    return cab


def _mapear_fila(fila: tuple[Any, ...]) -> dict[str, Any]:
    """Traduce una fila cruda del Excel al dict de columnas de la tabla."""
    def g(clave: str) -> Any:
        idx = COL[clave]
        return fila[idx] if idx < len(fila) else None

    fase = _s(g("fase"))
    return {
        "expediente": _s(g("expediente")),
        "ano_eje": _i(g("ano_eje")),
        "sec_ejec": _s(g("sec_ejec")),
        "tipo_op": _s(g("tipo_op")),
        "mod_compra": _s(g("mod_compra")),
        "ciclo": _s(g("ciclo")),
        "fase": fase,
        "fase_nombre": FASES.get(fase or ""),
        "sub_reg": _s(g("sub_reg")),
        "correlativo": _s(g("correlativo")),
        "secuencia_padre": _s(g("secuencia_padre")),
        "origen": _s(g("origen")),
        "rubro": _s(g("rubro")),
        "rubro_nombre": _s(g("rubro_nombre")),
        "tipo_financ": _s(g("tipo_financ")),
        "cod_doc": _s(g("cod_doc")),
        "num_doc": _s(g("num_doc")),
        "fecha_doc": _fecha(g("fecha_doc")),
        "tipo_prov": _s(g("tipo_prov")),
        "proveedor_ruc": _ruc(g("proveedor_ruc")),
        "proveedor_nombre": _s(g("proveedor_nombre")),
        "clasificador": _s(g("clasificador")),
        "sec_func": _i(g("sec_func")),
        "tipo_giro": _s(g("tipo_giro")),
        "monto_origen": _f(g("monto_origen")),
        "monto_soles": _f(g("monto_soles")),
        "fecha_aprobacion": _fecha(g("fecha_aprobacion")),
        "fecha_proceso": _fecha(g("fecha_proceso")),
        "sec_est": _s(g("sec_est")),
        "est_registro": _s(g("est_registro")),
        "certificado": _s(g("certificado")),
        "certificado_secuencia": _s(g("certificado_secuencia")),
        "producto_proyecto": _s(g("producto_proyecto")),
        "funcion": _s(g("funcion")),
        "meta": _s(g("meta")),
    }


def parsear_formato_a(origen: str | bytes | Any) -> ResultadoParseo:
    """Lee un .xlsx de Formato A y devuelve cabecera + filas normalizadas.

    `origen` puede ser una ruta, bytes, o un file-like (lo que acepte openpyxl).
    Se usa `data_only=True` para tomar los valores calculados, no formulas.
    """
    wb = load_workbook(origen, data_only=True, read_only=False)
    ws = wb.active

    por_fila: dict[int, tuple[Any, ...]] = {}
    filas_dato: list[tuple[Any, ...]] = []
    for idx, fila in enumerate(ws.iter_rows(values_only=True), start=1):
        if idx <= HEADER_ROW:
            por_fila[idx] = fila
            continue
        if _es_fila_dato(fila):
            filas_dato.append(fila)

    cabecera = _cabecera_reporte(por_fila)
    mapeadas = [_mapear_fila(f) for f in filas_dato]
    # Descartamos filas sin expediente o sin fase reconocible (defensivo).
    validas = [m for m in mapeadas if m["expediente"] and m["fase"] in FASES]
    descartadas = len(mapeadas) - len(validas)

    wb.close()
    return ResultadoParseo(
        cabecera=cabecera, filas=validas, descartadas=descartadas
    )


def resumen_por_fase(filas: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Suma `monto_soles` por fase (solo estado 'A' = aprobado). Util para el
    smoke test y para la respuesta del endpoint de carga."""
    total: dict[str, float] = {}
    for f in filas:
        if f.get("est_registro") == "A":
            total[f["fase"]] = total.get(f["fase"], 0.0) + f["monto_soles"]
    return total
