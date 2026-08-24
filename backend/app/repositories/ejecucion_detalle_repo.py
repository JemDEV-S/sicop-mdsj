"""Repositorio de lectura del detalle SIAF por documento (`siaf.ejecucion_detalle_siaf`).

Este detalle viene del "Formato A" del Modulo Administrativo (carga PROVISIONAL,
ver memoria `project-formato-a-detalle-siaf`). Complementa el snapshot MEF
agregado con lo que la API publica no da: expediente, fase por documento,
proveedor (RUC), clasificador completo y fechas por fase.

Regla anti-inflado (CLAUDE.md RN §3, memoria `feedback-mef-unica-fuente-presupuesto`):
este modulo NO produce totales de tablero. Alimenta trazabilidad (timeline del
pedido) y reportes de detalle ROTULADOS como carga provisional. Los KPIs
oficiales siguen saliendo de `ejecucion_mef_repo`.

Regla de neteo (memoria `project-formato-a-neteo-sec-est`, confirmada con
documentacion MEF del SIAF Modulo Administrativo):

    monto vigente por expediente+fase = SUM(monto_soles)
        WHERE est_registro = 'A'   -- estado del registro = Aprobado por el MEF
          AND sec_est      = 'N'   -- tipo de secuencia = Nuevo (Op. inicial + Ampliacion)

  - `est_registro`: estado del registro en el flujo de transmision al MEF
    (A=Aprobado, P=Pendiente, T=Transmitido, R=Rechazado, ...). Solo 'A' es oficial.
  - `sec_est`: tipo de secuencia del ciclo de gasto. 'N' es la secuencia vigente
    (positiva). Las anulaciones/rebajas ('G','A','R','C','e' -> negativas) reversan
    un padre que no esta en el set 'A', asi que quedarian huerfanas y descuadrarian
    el neto; los traspasos internos ('H'<->'I') netean a 0. Filtrar `sec_est='N'`
    deja solo lo vigente.

Nunca contar filas: los montos llevan signo y las rectificaciones se netean con SUM.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings

# Predicado de neteo vigente compartido por todas las consultas de montos.
_VIGENTE = "est_registro = 'A' AND sec_est = 'N'"

# Fases del ciclo de gasto en orden, con su nombre legible. La 'R' (Rendicion/
# Regularizacion) existe pero no es una etapa del pago; el timeline usa C/D/G/P.
_FASES_ORDEN = ["C", "D", "G", "P", "R"]
_FASE_NOMBRE = {
    "C": "Certificacion",
    "D": "Devengado",
    "G": "Girado",
    "P": "Pagado",
    "R": "Rendicion",
}


def _norm_exp(exp: str | int) -> str:
    """Normaliza el expediente al ancho con que se guardo (10 digitos, zero-pad).

    El `exp_siaf` que llega del pedido puede ser int (`1717`); en la tabla vive
    como `'0000001717'`. Verificado: `length(expediente)` es 10 en todas las filas.
    """
    return str(exp).strip().zfill(10)


def sec_funcs_de_centros(db: Session, centros: list[str]) -> list[int]:
    """Metas (sec_func) asignadas a un conjunto de centros de costo.

    Usa `ref.metas_centro_costo` (PostgreSQL, poblada por el sync de catálogos)
    en vez de golpear SIGA. Es la traducción CC→meta que necesita el filtro de
    alcance del detalle/reportes SIAF (plan §6): el detalle SIAF tiene `sec_func`,
    así que se restringe a las metas del alcance del usuario.

    `centros` vacío → `[]`.
    """
    if not centros:
        return []
    binds = [f":cc{i}" for i in range(len(centros))]
    params = {f"cc{i}": c for i, c in enumerate(centros)}
    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT sec_func
              FROM ref.metas_centro_costo
             WHERE centro_costo IN ({", ".join(binds)})
               AND sec_func IS NOT NULL
            """
        ),
        params,
    ).all()
    return [int(r[0]) for r in rows]


def procedencia(db: Session, ano: int) -> dict[str, Any]:
    """Metadatos de la carga del Formato A del año (para rotular el dato).

    El Formato A se carga por mes (swap por año+mes). `meses_cargados` deja ver
    hasta dónde llega el rastro: la UI rotula "meses cargados: ene–ago" para que
    el funcionario no confunda "sin dato" con "mes aún no cargado". `emitido_en`
    es el del mes más reciente cargado.

    Returns `{tiene_datos, meses_cargados, emitido_en, cargado_en,
    origen_archivo, n_filas}`. `tiene_datos=False` si nadie cargó nada del año
    (degradación limpia).
    """
    r = db.execute(
        text(
            """
            SELECT COUNT(*)         AS n_filas,
                   MAX(emitido_en)  AS emitido_en,
                   MAX(cargado_en)  AS cargado_en,
                   MAX(origen_archivo) AS origen_archivo
              FROM siaf.ejecucion_detalle_siaf
             WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
            """
        ),
        {"ano": ano, "sec_ejec": settings.SEC_EJEC},
    ).mappings().one()
    n = int(r["n_filas"] or 0)

    meses = [
        int(m[0])
        for m in db.execute(
            text(
                """
                SELECT DISTINCT mes_corte
                  FROM siaf.ejecucion_detalle_siaf
                 WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
                   AND mes_corte IS NOT NULL
                 ORDER BY mes_corte
                """
            ),
            {"ano": ano, "sec_ejec": settings.SEC_EJEC},
        ).all()
    ]
    return {
        "tiene_datos": n > 0,
        "meses_cargados": meses,
        "emitido_en": r["emitido_en"],
        "cargado_en": r["cargado_en"],
        "origen_archivo": r["origen_archivo"],
        "n_filas": n,
    }


def sec_func_de_expediente(
    db: Session, exp_siaf: str | int, ano: int
) -> list[int]:
    """Metas (sec_func) que toca un expediente. Para el filtro de CC del endpoint:
    el detalle SIAF sí tiene `sec_func`, así que se valida contra las metas del
    alcance del usuario (plan §6)."""
    exp = _norm_exp(exp_siaf)
    rows = db.execute(
        text(
            """
            SELECT DISTINCT sec_func
              FROM siaf.ejecucion_detalle_siaf
             WHERE expediente = :exp AND ano_eje = :ano AND sec_ejec = :sec_ejec
               AND sec_func IS NOT NULL
            """
        ),
        {"exp": exp, "ano": ano, "sec_ejec": settings.SEC_EJEC},
    ).all()
    return [int(r[0]) for r in rows]


def por_expediente(db: Session, exp_siaf: str | int, ano: int) -> list[dict[str, Any]]:
    """Fases netadas de un expediente, para completar el rastro del pedido (Fase 1).

    Agrupa por fase sumando `monto_soles` de los registros vigentes
    (`est_registro='A' AND sec_est='N'`), con el rango de fechas del documento y
    la lista de documentos sustento por fase. El proveedor se toma del documento
    de mayor monto de la fase (normalmente uno solo por expediente).

    Devuelve una fila por fase presente (C/D/G/P/R), en orden del ciclo. Si el
    expediente no tiene detalle cargado devuelve `[]` (degradacion limpia: el
    llamador marca las etapas como `sin_dato`).

    Returns:
        `list[{fase, fase_nombre, monto_neto, fecha_min, fecha_max, n_documentos,
        proveedor_ruc, proveedor_nombre, documentos: [{cod_doc, num_doc,
        fecha_doc, monto_soles}]}]`. Solo se listan fases con `monto_neto != 0`
        o con documentos vigentes.
    """
    exp = _norm_exp(exp_siaf)
    rows = db.execute(
        text(
            f"""
            SELECT
                fase,
                cod_doc, num_doc, fecha_doc,
                proveedor_ruc, proveedor_nombre,
                SUM(monto_soles) AS monto_doc
              FROM siaf.ejecucion_detalle_siaf
             WHERE expediente = :exp
               AND ano_eje = :ano
               AND sec_ejec = :sec_ejec
               AND {_VIGENTE}
             GROUP BY fase, cod_doc, num_doc, fecha_doc,
                      proveedor_ruc, proveedor_nombre
             ORDER BY fase, fecha_doc, num_doc
            """
        ),
        {"exp": exp, "ano": ano, "sec_ejec": settings.SEC_EJEC},
    ).mappings().all()

    # Agrupar en Python por fase (mantiene el detalle de documentos y elige el
    # proveedor dominante = el del documento de mayor monto absoluto).
    por_fase: dict[str, dict[str, Any]] = {}
    for r in rows:
        fase = r["fase"]
        g = por_fase.setdefault(
            fase,
            {
                "fase": fase,
                "fase_nombre": _FASE_NOMBRE.get(fase, fase),
                "monto_neto": 0.0,
                "fecha_min": None,
                "fecha_max": None,
                "documentos": [],
                "_prov": (0.0, None, None),  # (monto_abs, ruc, nombre)
            },
        )
        monto = float(r["monto_doc"] or 0)
        g["monto_neto"] += monto
        fecha = r["fecha_doc"]
        if fecha is not None:
            g["fecha_min"] = fecha if g["fecha_min"] is None else min(g["fecha_min"], fecha)
            g["fecha_max"] = fecha if g["fecha_max"] is None else max(g["fecha_max"], fecha)
        g["documentos"].append(
            {
                "cod_doc": r["cod_doc"],
                "num_doc": r["num_doc"],
                "fecha_doc": fecha,
                "monto_soles": monto,
            }
        )
        if abs(monto) >= g["_prov"][0] and (r["proveedor_ruc"] or r["proveedor_nombre"]):
            g["_prov"] = (abs(monto), r["proveedor_ruc"], r["proveedor_nombre"])

    salida: list[dict[str, Any]] = []
    for fase in _FASES_ORDEN:
        g = por_fase.get(fase)
        if g is None:
            continue
        _, ruc, nombre = g.pop("_prov")
        g["proveedor_ruc"] = ruc
        g["proveedor_nombre"] = nombre
        g["monto_neto"] = round(g["monto_neto"], 2)
        g["n_documentos"] = len(g["documentos"])
        salida.append(g)
    return salida


# ─── Fase 2: agregados por dimension (proveedor / clasificador / rubro) ───────

# Dimensiones soportadas por `agregados`: llave -> (columnas de agrupacion SQL,
# columnas de etiqueta que viajan en la respuesta).
_GROUP_BY: dict[str, dict[str, list[str]]] = {
    "proveedor": {
        "keys": ["proveedor_ruc", "proveedor_nombre"],
        "labels": ["proveedor_ruc", "proveedor_nombre"],
    },
    "clasificador": {
        "keys": ["clasificador"],
        "labels": ["clasificador"],
    },
    "rubro": {
        "keys": ["rubro", "rubro_nombre"],
        "labels": ["rubro", "rubro_nombre"],
    },
}


def agregados(
    db: Session,
    ano: int,
    *,
    group_by: str,
    sec_funcs: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Ejecucion vigente agregada por proveedor | clasificador | rubro (Fase 2).

    Pivotea las fases del ciclo de gasto (Certificado/Devengado/Girado/Pagado)
    sobre la dimension pedida, sumando solo los registros vigentes
    (`est_registro='A' AND sec_est='N'`). Es el detalle que la API MEF no puede
    dar (RUC, clasificador de 5 niveles), rotulado en UI como carga provisional.

    Args:
        ano: año fiscal.
        group_by: `'proveedor'`, `'clasificador'` o `'rubro'`.
        sec_funcs: si se pasa, restringe a esas metas (alcance por CC del usuario,
            igual criterio que `ejecucion_mef_repo`). `None` = todas las metas.
            Lista vacia -> `[]` (sin alcance).

    Returns:
        `list[{<etiquetas de la dimension>, certificado, devengado, girado,
        pagado, en_transito, n_expedientes, n_metas}]`, ordenado por devengado
        descendente. `en_transito = devengado - pagado` (brecha de tesoreria).

    Raises:
        ValueError: si `group_by` no es una dimension soportada.
    """
    if group_by not in _GROUP_BY:
        raise ValueError(
            f"group_by invalido: {group_by!r}. Use uno de {list(_GROUP_BY)}."
        )
    if sec_funcs is not None and len(sec_funcs) == 0:
        return []

    dim = _GROUP_BY[group_by]
    keys_sql = ", ".join(dim["keys"])
    labels_sql = ", ".join(dim["labels"])

    where = [
        "ano_eje = :ano",
        "sec_ejec = :sec_ejec",
        _VIGENTE,
    ]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    if sec_funcs is not None:
        binds = [f":sf{i}" for i in range(len(sec_funcs))]
        where.append(f"sec_func IN ({', '.join(binds)})")
        for i, sf in enumerate(sec_funcs):
            params[f"sf{i}"] = sf

    rows = db.execute(
        text(
            f"""
            SELECT
                {labels_sql},
                COALESCE(SUM(monto_soles) FILTER (WHERE fase = 'C'), 0) AS certificado,
                COALESCE(SUM(monto_soles) FILTER (WHERE fase = 'D'), 0) AS devengado,
                COALESCE(SUM(monto_soles) FILTER (WHERE fase = 'G'), 0) AS girado,
                COALESCE(SUM(monto_soles) FILTER (WHERE fase = 'P'), 0) AS pagado,
                COUNT(DISTINCT expediente) AS n_expedientes,
                COUNT(DISTINCT sec_func)   AS n_metas
              FROM siaf.ejecucion_detalle_siaf
             WHERE {" AND ".join(where)}
             GROUP BY {keys_sql}
             ORDER BY devengado DESC
            """
        ),
        params,
    ).mappings().all()

    salida: list[dict[str, Any]] = []
    for r in rows:
        d: dict[str, Any] = {k: r[k] for k in dim["labels"]}
        dev = float(r["devengado"] or 0)
        pag = float(r["pagado"] or 0)
        d["certificado"] = round(float(r["certificado"] or 0), 2)
        d["devengado"] = round(dev, 2)
        d["girado"] = round(float(r["girado"] or 0), 2)
        d["pagado"] = round(pag, 2)
        d["en_transito"] = round(dev - pag, 2)
        d["n_expedientes"] = int(r["n_expedientes"] or 0)
        d["n_metas"] = int(r["n_metas"] or 0)
        salida.append(d)
    return salida


def totales_por_fase(
    db: Session, ano: int, *, sec_funcs: list[int] | None = None
) -> dict[str, float]:
    """Totales vigentes por fase (C/D/G/P/R). Usado por el estado vacio/rotulo
    de los reportes de Fase 2. Respeta el alcance por CC si se pasa `sec_funcs`.
    """
    if sec_funcs is not None and len(sec_funcs) == 0:
        return {}

    where = ["ano_eje = :ano", "sec_ejec = :sec_ejec", _VIGENTE]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    if sec_funcs is not None:
        binds = [f":sf{i}" for i in range(len(sec_funcs))]
        where.append(f"sec_func IN ({', '.join(binds)})")
        for i, sf in enumerate(sec_funcs):
            params[f"sf{i}"] = sf

    rows = db.execute(
        text(
            f"""
            SELECT fase, COALESCE(SUM(monto_soles), 0) AS total
              FROM siaf.ejecucion_detalle_siaf
             WHERE {" AND ".join(where)}
             GROUP BY fase
            """
        ),
        params,
    ).mappings().all()
    return {r["fase"]: round(float(r["total"] or 0), 2) for r in rows}
