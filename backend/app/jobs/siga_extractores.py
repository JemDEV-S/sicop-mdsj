"""Extractores declarativos SIGA -> siga.* (usados por sync_siga_pipeline).

Cada `Extractor` describe una tabla del snapshot: su destino, su PK, si se
recarga completa o por watermark, el SELECT contra SIGA y como se mapea cada
fila a las columnas de Postgres. Toda la logica de "que columnas y de donde"
vive aqui, en un solo lugar por tabla; el motor de sync (sync_siga_pipeline)
no sabe nada de SIGA.

Convenciones:
    - El SELECT SIEMPRE filtra por :sec_ejec y :ano (RN-01). Las tablas con
      watermark aceptan ademas :watermark y su SQL lo inyecta con `con_watermark`.
    - `mapear` recibe la fila cruda (dict con las columnas del SELECT) y devuelve
      el dict con las columnas exactas de la tabla destino. Normaliza tipos
      (strip a strings, valor_soles calculado) para que el job sea tonto.

Los nombres de columna SIGA se validaron contra INFORMATION_SCHEMA (2026-07-31).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def _s(v: Any) -> str | None:
    """Strip de string SQL Server (char/varchar vienen con padding)."""
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _i(v: Any) -> int | None:
    if v in (None, "", " "):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _f(v: Any) -> float | None:
    if v in (None, "", " "):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Extractor:
    """Descripcion de la sincronizacion de una tabla del snapshot."""

    destino: str                       # tabla en siga.*
    pk: tuple[str, ...]                # columnas PK en Postgres
    columnas: tuple[str, ...]          # columnas destino en orden de INSERT
    _sql_base: str                     # SELECT contra SIGA (sin filtro watermark)
    mapear: Callable[[dict[str, Any]], dict[str, Any]]
    recarga_completa: bool = True      # True: DELETE+INSERT por año; False: UPSERT
    watermark: bool = False            # True: incremental por col_fecha
    col_fecha: str = "fecha_reg"       # columna (destino) del watermark
    _sql_watermark: str = ""           # fragmento AND a añadir cuando hay watermark
    filtro_ano: str = "ano_eje = :ano"  # WHERE para DELETE/COUNT en Postgres

    def sql(self, *, con_watermark: bool) -> str:
        if con_watermark and self._sql_watermark:
            return self._sql_base + " " + self._sql_watermark
        return self._sql_base


# ═══════════════════════════════════════════════════════════════════════
# Definiciones por tabla
# ═══════════════════════════════════════════════════════════════════════

# ── pedidos (SIG_PEDIDOS) ────────────────────────────────────────────────
_PEDIDOS = Extractor(
    destino="pedidos",
    pk=("ano_eje", "sec_ejec", "tipo_bien", "tipo_pedido", "nro_pedido"),
    columnas=(
        "ano_eje", "sec_ejec", "tipo_bien", "tipo_pedido", "nro_pedido",
        "centro_costo", "sec_func", "estado", "act_proy",
        "fecha_pedido", "fecha_aprob", "fecha_atenc",
        "motivo", "solicitante", "fuente_financ", "fecha_reg",
    ),
    _sql_base="""
        SELECT p.ANO_EJE, p.SEC_EJEC, p.TIPO_BIEN, p.TIPO_PEDIDO, p.NRO_PEDIDO,
               p.CENTRO_COSTO, p.sec_func, p.ESTADO, p.ACT_PROY,
               p.FECHA_PEDIDO, p.FECHA_APROB, p.FECHA_ATENC,
               CAST(p.MOTIVO_PEDIDO AS VARCHAR(2000)) AS MOTIVO,
               -- NOMBRE_EMPLEADO viene NULL en el 100% de los pedidos 2026;
               -- el solicitante real se resuelve por el codigo EMPLEADO contra
               -- el maestro de personal (100% cruza, diagnostico_sesion6/09).
               COALESCE(
                   NULLIF(LTRIM(RTRIM(p.NOMBRE_EMPLEADO)), ''),
                   NULLIF(LTRIM(RTRIM(CONCAT(
                       LTRIM(RTRIM(pe.nombres)), ' ',
                       LTRIM(RTRIM(pe.apellido_paterno)), ' ',
                       LTRIM(RTRIM(pe.apellido_materno))
                   ))), '')
               ) AS SOLICITANTE,
               -- FUENTE_FINANC (texto) viene NULL; el codigo real (catalogo
               -- MEF: 09=RDR, 18=Canon...) esta en fuente_fto, 100% poblado.
               COALESCE(
                   NULLIF(LTRIM(RTRIM(p.FUENTE_FINANC)), ''),
                   LTRIM(RTRIM(p.fuente_fto))
               ) AS FUENTE_FINANC,
               p.FECHA_REG
        FROM SIG_PEDIDOS p
        OUTER APPLY (
            SELECT TOP 1 x.nombres, x.apellido_paterno, x.apellido_materno
            FROM SIG_PERSONAL x
            WHERE x.SEC_EJEC = p.SEC_EJEC AND x.empleado = p.EMPLEADO
        ) pe
        WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
    """,
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "tipo_pedido": _s(r["TIPO_PEDIDO"]),
        "nro_pedido": _i(r["NRO_PEDIDO"]),
        "centro_costo": _s(r["CENTRO_COSTO"]), "sec_func": _i(r["sec_func"]),
        "estado": _s(r["ESTADO"]), "act_proy": _s(r["ACT_PROY"]),
        "fecha_pedido": r["FECHA_PEDIDO"], "fecha_aprob": r["FECHA_APROB"],
        "fecha_atenc": r["FECHA_ATENC"],
        "motivo": _s(r["MOTIVO"]), "solicitante": _s(r["SOLICITANTE"]),
        "fuente_financ": _s(r["FUENTE_FINANC"]), "fecha_reg": r["FECHA_REG"],
    },
)

# ── pedido_items (SIG_DETALLE_PEDIDOS) — grande -> watermark ─────────────
_PEDIDO_ITEMS = Extractor(
    destino="pedido_items",
    pk=("ano_eje", "sec_ejec", "tipo_bien", "tipo_pedido", "nro_pedido", "secuencia"),
    columnas=(
        "ano_eje", "sec_ejec", "tipo_bien", "tipo_pedido", "nro_pedido", "secuencia",
        "sec_cua_mod_sal", "nro_orden_declarado", "nro_pecosa", "clasificador",
        "grupo_bien", "clase_bien", "familia_bien", "item_bien",
        "cant_solicitada", "cant_aprobada", "cant_atendida", "precio_unit",
        "valor_soles", "estado_confor", "fecha_reg",
    ),
    recarga_completa=False,
    watermark=True,
    _sql_base="""
        SELECT dp.ANO_EJE, dp.SEC_EJEC, dp.TIPO_BIEN, dp.TIPO_PEDIDO,
               dp.NRO_PEDIDO, dp.SECUENCIA,
               dp.SEC_CUA_MOD_SAL, dp.NRO_ORDEN AS NRO_ORDEN_DECLARADO,
               dp.NRO_PECOSA, dp.CLASIFICADOR,
               dp.GRUPO_BIEN, dp.CLASE_BIEN, dp.FAMILIA_BIEN, dp.ITEM_BIEN,
               dp.CANT_SOLICITADA, dp.CANT_APROBADA, dp.CANT_ATENDIDA,
               dp.PRECIO_UNIT, dp.VALOR_TOTAL, dp.ESTADO_CONFOR, dp.FECHA_REG
        FROM SIG_DETALLE_PEDIDOS dp
        WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
    """,
    _sql_watermark="AND dp.FECHA_REG > :watermark",
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "tipo_pedido": _s(r["TIPO_PEDIDO"]),
        "nro_pedido": _i(r["NRO_PEDIDO"]), "secuencia": _i(r["SECUENCIA"]),
        "sec_cua_mod_sal": _i(r["SEC_CUA_MOD_SAL"]),
        "nro_orden_declarado": _i(r["NRO_ORDEN_DECLARADO"]),
        "nro_pecosa": _i(r["NRO_PECOSA"]), "clasificador": _s(r["CLASIFICADOR"]),
        "grupo_bien": _s(r["GRUPO_BIEN"]), "clase_bien": _s(r["CLASE_BIEN"]),
        "familia_bien": _s(r["FAMILIA_BIEN"]), "item_bien": _s(r["ITEM_BIEN"]),
        "cant_solicitada": _f(r["CANT_SOLICITADA"]),
        "cant_aprobada": _f(r["CANT_APROBADA"]),
        "cant_atendida": _f(r["CANT_ATENDIDA"]),
        "precio_unit": _f(r["PRECIO_UNIT"]),
        # VALOR_TOTAL viene 0 en el 100% de servicios: el monto real es
        # cant * precio. Se normaliza aqui para que el snapshot ya tenga el
        # valor bueno y las vistas no repitan el CASE.
        "valor_soles": (
            _f(r["VALOR_TOTAL"]) if (_f(r["VALOR_TOTAL"]) or 0) > 0
            else (_f(r["CANT_SOLICITADA"]) or 0) * (_f(r["PRECIO_UNIT"]) or 0)
        ),
        "estado_confor": _s(r["ESTADO_CONFOR"]), "fecha_reg": r["FECHA_REG"],
    },
)

# ── bolsas (SIG_CUADRO_MODIFICADO_CMN) — sin FECHA_REG -> recarga completa ─
_BOLSAS = Extractor(
    destino="bolsas",
    pk=("ano_eje", "sec_ejec", "tipo_bien", "sec_cua_mod_sal", "tipo_consolid", "nro_consolid"),
    columnas=("ano_eje", "sec_ejec", "tipo_bien", "sec_cua_mod_sal", "tipo_consolid", "nro_consolid"),
    _sql_base="""
        SELECT ANNO_EJEC AS ANO_EJE, SEC_EJEC, TIPO_BIEN,
               SEC_CUA_MOD_SAL, TIPO_CONSOLID, NRO_CONSOLID
        FROM SIG_CUADRO_MODIFICADO_CMN
        WHERE ANNO_EJEC = :ano AND SEC_EJEC = :sec_ejec
    """,
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "sec_cua_mod_sal": _i(r["SEC_CUA_MOD_SAL"]),
        "tipo_consolid": _s(r["TIPO_CONSOLID"]), "nro_consolid": _i(r["NRO_CONSOLID"]),
    },
)

# ── expedientes_ccmn (PAAC + cotizacion + cuadro adq, 1 fila por CCMN) ────
_EXPEDIENTES_CCMN = Extractor(
    destino="expedientes_ccmn",
    pk=("ano_eje", "sec_ejec", "tipo_bien", "tipo_consolid", "nro_consolid"),
    columnas=(
        "ano_eje", "sec_ejec", "tipo_bien", "tipo_consolid", "nro_consolid",
        "nro_est_mdo", "nro_certifica", "valor_plan", "fecha_cons",
        "fecha_cotizacion", "sec_cuadro", "fecha_cuadro", "fecha_reg",
    ),
    _sql_base="""
        SELECT pc.ANO_EJE, pc.SEC_EJEC, pc.TIPO_BIEN, pc.TIPO_CONSOLID,
               pc.NRO_CONSOLID, pc.NRO_EST_MDO, pc.NRO_CERTIFICA,
               pc.VALOR_PLAN, pc.FECHA_CONS, pc.FECHA_REG,
               cot.FECHA_COTIZACION,
               ca.SEC_CUADRO, ca.FECHA_CUADRO
        FROM SIG_PAAC_CONSOLIDADO pc
        LEFT JOIN (
            SELECT ANO_EJE, SEC_EJEC, tipo_bien, NRO_CONSOLID,
                   MIN(FECHA_REG) AS FECHA_COTIZACION
            FROM SIG_SOLICITUD_COTIZACION
            WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
            GROUP BY ANO_EJE, SEC_EJEC, tipo_bien, NRO_CONSOLID
        ) cot ON cot.ANO_EJE = pc.ANO_EJE AND cot.SEC_EJEC = pc.SEC_EJEC
             AND cot.tipo_bien = pc.TIPO_BIEN AND cot.NRO_CONSOLID = pc.NRO_CONSOLID
        LEFT JOIN (
            -- FECHA_CUADRO real esta poblada en solo el 3% de las filas 2026;
            -- el hito "cuadro autorizado" es FECHA_AUTORIZ (100% poblada,
            -- = FECHA_COMPRA en el 99%). MIN = primera vez que se alcanzo
            -- (diagnostico_sesion6/01-02).
            SELECT ANO_EJE, SEC_EJEC, TIPO_BIEN, NRO_CONS_PAAC,
                   MIN(SEC_CUADRO) AS SEC_CUADRO, MIN(FECHA_AUTORIZ) AS FECHA_CUADRO
            FROM SIG_CUADRO_ADQUISICION
            WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
            GROUP BY ANO_EJE, SEC_EJEC, TIPO_BIEN, NRO_CONS_PAAC
        ) ca ON ca.ANO_EJE = pc.ANO_EJE AND ca.SEC_EJEC = pc.SEC_EJEC
            AND ca.TIPO_BIEN = pc.TIPO_BIEN AND ca.NRO_CONS_PAAC = pc.NRO_CONSOLID
        WHERE pc.ANO_EJE = :ano AND pc.SEC_EJEC = :sec_ejec
    """,
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "tipo_consolid": _s(r["TIPO_CONSOLID"]),
        "nro_consolid": _i(r["NRO_CONSOLID"]), "nro_est_mdo": _i(r["NRO_EST_MDO"]),
        "nro_certifica": _i(r["NRO_CERTIFICA"]), "valor_plan": _f(r["VALOR_PLAN"]),
        "fecha_cons": r["FECHA_CONS"], "fecha_cotizacion": r["FECHA_COTIZACION"],
        "sec_cuadro": _i(r["SEC_CUADRO"]), "fecha_cuadro": r["FECHA_CUADRO"],
        "fecha_reg": r["FECHA_REG"],
    },
)

# ── ordenes (SIG_ORDEN_ADQUISICION + presupuesto + certificacion_fase) ────
# Las llaves de cruce MEF (sec_func, clasificador, exp_siaf, mes_cale) salen de
# SIG_ORDEN_PRESUPUESTO; el CCMN de la orden (cadena dura) de la certificacion
# por fase (100% medido). Ambos se aplanan a la primera fila por orden.
_ORDENES = Extractor(
    destino="ordenes",
    pk=("ano_eje", "sec_ejec", "tipo_bien", "nro_orden"),
    columnas=(
        "ano_eje", "sec_ejec", "tipo_bien", "nro_orden", "sec_cuadro",
        "nro_consolid", "nro_certifica", "exp_siga", "exp_siaf",
        "sec_func", "clasificador", "mes_cale",
        "proveedor", "proveedor_nombre", "proveedor_ruc", "concepto",
        "total_fact_soles", "estado", "estado_siaf", "fecha_orden", "fecha_reg",
    ),
    _sql_base="""
        SELECT o.ANO_EJE, o.SEC_EJEC, o.TIPO_BIEN, o.NRO_ORDEN,
               o.SEC_CUADRO, o.NRO_CERTIFICA, o.EXP_SIGA, o.EXP_SIAF,
               o.PROVEEDOR, o.TOTAL_FACT_SOLES, o.ESTADO, o.ESTADO_SIAF,
               o.FECHA_ORDEN, o.FECHA_REG,
               CAST(o.CONCEPTO AS VARCHAR(2000)) AS CONCEPTO,
               ca.NRO_CONS_PAAC AS NRO_CONSOLID,
               op.SEC_FUNC, op.CLASIFICADOR, op.MES_CALE,
               c.NOMBRE_PROV, c.NRO_RUC
        FROM SIG_ORDEN_ADQUISICION o
        LEFT JOIN SIG_CUADRO_ADQUISICION ca
            ON ca.ANO_EJE = o.ANO_EJE AND ca.SEC_EJEC = o.SEC_EJEC
           AND ca.TIPO_BIEN = o.TIPO_BIEN AND ca.SEC_CUADRO = o.SEC_CUADRO
        LEFT JOIN (
            SELECT ANO_EJE, SEC_EJEC, TIPO_BIEN, NRO_ORDEN,
                   MIN(SEC_FUNC) AS SEC_FUNC, MIN(CLASIFICADOR) AS CLASIFICADOR,
                   MIN(MES_CALE) AS MES_CALE
            FROM SIG_ORDEN_PRESUPUESTO
            WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
            GROUP BY ANO_EJE, SEC_EJEC, TIPO_BIEN, NRO_ORDEN
        ) op ON op.ANO_EJE = o.ANO_EJE AND op.SEC_EJEC = o.SEC_EJEC
            AND op.TIPO_BIEN = o.TIPO_BIEN AND op.NRO_ORDEN = o.NRO_ORDEN
        LEFT JOIN SIG_CONTRATISTAS c ON c.PROVEEDOR = o.PROVEEDOR
        WHERE o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
    """,
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "nro_orden": _i(r["NRO_ORDEN"]),
        "sec_cuadro": _i(r["SEC_CUADRO"]), "nro_consolid": _i(r["NRO_CONSOLID"]),
        "nro_certifica": _i(r["NRO_CERTIFICA"]), "exp_siga": _i(r["EXP_SIGA"]),
        "exp_siaf": _i(r["EXP_SIAF"]), "sec_func": _i(r["SEC_FUNC"]),
        "clasificador": _s(r["CLASIFICADOR"]), "mes_cale": _s(r["MES_CALE"]),
        "proveedor": _i(r["PROVEEDOR"]), "proveedor_nombre": _s(r["NOMBRE_PROV"]),
        "proveedor_ruc": _s(r["NRO_RUC"]), "concepto": _s(r["CONCEPTO"]),
        "total_fact_soles": _f(r["TOTAL_FACT_SOLES"]), "estado": _s(r["ESTADO"]),
        "estado_siaf": _s(r["ESTADO_SIAF"]), "fecha_orden": r["FECHA_ORDEN"],
        "fecha_reg": r["FECHA_REG"],
    },
)

# ── certificaciones (SIG_CERTIFICACION_FASE) ─────────────────────────────
_CERTIFICACIONES = Extractor(
    destino="certificaciones",
    pk=("ano_eje", "sec_ejec", "nro_certifica", "secuencia_fase"),
    columnas=(
        "ano_eje", "sec_ejec", "nro_certifica", "secuencia_fase",
        "nro_consolid", "nro_orden", "nro_certifica_siaf", "tipo_bien",
        "valor_soles", "fecha_reg",
    ),
    _sql_base="""
        SELECT ANO_EJE, SEC_EJEC, NRO_CERTIFICA, SECUENCIA_FASE,
               NRO_CONSOLID, NRO_ORDEN, NRO_CERTIFICA_SIAF, TIPO_BIEN,
               VALOR_SOLES, FECHA_REG
        FROM SIG_CERTIFICACION_FASE
        WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
    """,
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "nro_certifica": _i(r["NRO_CERTIFICA"]),
        "secuencia_fase": _i(r["SECUENCIA_FASE"]),
        "nro_consolid": _i(r["NRO_CONSOLID"]), "nro_orden": _i(r["NRO_ORDEN"]),
        "nro_certifica_siaf": _i(r["NRO_CERTIFICA_SIAF"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "valor_soles": _f(r["VALOR_SOLES"]),
        "fecha_reg": r["FECHA_REG"],
    },
)

# ── compromisos (SIG_EXP_SIGA_DOCU) ──────────────────────────────────────
_COMPROMISOS = Extractor(
    destino="compromisos",
    pk=("ano_eje", "sec_ejec", "exp_siga", "exp_siga_doc"),
    columnas=(
        "ano_eje", "sec_ejec", "exp_siga", "exp_siga_doc",
        "tipo_operacion", "exp_siaf", "fecha_interfase",
        "fecha_documento", "fecha_reg",
    ),
    _sql_base="""
        SELECT ANO_EJE, SEC_EJEC, EXP_SIGA, EXP_SIGA_DOC,
               TIPO_OPERACION, EXP_SIAF, FECHA_INTERFASE,
               FECHA_DOCUMENTO, FECHA_REG
        FROM SIG_EXP_SIGA_DOCU
        WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
    """,
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "exp_siga": _i(r["EXP_SIGA"]), "exp_siga_doc": _i(r["EXP_SIGA_DOC"]),
        "tipo_operacion": _s(r["TIPO_OPERACION"]), "exp_siaf": _i(r["EXP_SIAF"]),
        "fecha_interfase": r["FECHA_INTERFASE"],
        "fecha_documento": r["FECHA_DOCUMENTO"], "fecha_reg": r["FECHA_REG"],
    },
)

# ── conformidades (SIG_MOVIM_CONFOR_SERVICIO) — ANO_ORDEN, glosa minuscula ─
_CONFORMIDADES = Extractor(
    destino="conformidades",
    pk=("ano_orden", "sec_ejec", "tipo_bien", "nro_orden", "nro_movimto"),
    columnas=(
        "ano_orden", "sec_ejec", "tipo_bien", "nro_orden", "nro_movimto",
        "indi_confor", "estado_deveng", "expediente_siaf", "secuencia_siaf",
        "proveedor_nombre", "responsable", "glosa", "observacion",
        "fecha_movimto", "fecha_reg",
    ),
    filtro_ano="ano_orden = :ano",
    _sql_base="""
        SELECT ANO_ORDEN, SEC_EJEC, TIPO_BIEN, NRO_ORDEN, NRO_MOVIMTO,
               INDI_CONFOR, ESTADO_DEVENG, EXPEDIENTE_SIAF, SECUENCIA_SIAF,
               NOMBRE_PROVEEDOR, RESPONSABLE,
               CAST(glosa AS VARCHAR(2000)) AS GLOSA,
               CAST(OBSERVACION AS VARCHAR(2000)) AS OBSERVACION,
               FECHA_MOVIMTO
        FROM SIG_MOVIM_CONFOR_SERVICIO
        WHERE ANO_ORDEN = :ano AND SEC_EJEC = :sec_ejec
    """,
    mapear=lambda r: {
        "ano_orden": _i(r["ANO_ORDEN"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "nro_orden": _i(r["NRO_ORDEN"]),
        "nro_movimto": _i(r["NRO_MOVIMTO"]), "indi_confor": _s(r["INDI_CONFOR"]),
        "estado_deveng": _s(r["ESTADO_DEVENG"]),
        "expediente_siaf": _i(r["EXPEDIENTE_SIAF"]),
        "secuencia_siaf": _i(r["SECUENCIA_SIAF"]),
        "proveedor_nombre": _s(r["NOMBRE_PROVEEDOR"]),
        "responsable": _s(r["RESPONSABLE"]), "glosa": _s(r["GLOSA"]),
        "observacion": _s(r["OBSERVACION"]), "fecha_movimto": r["FECHA_MOVIMTO"],
        # Sin FECHA_REG en origen; se usa FECHA_MOVIMTO como sello del snapshot.
        "fecha_reg": r["FECHA_MOVIMTO"],
    },
)

# ── movimientos_almacen (SIG_MOVIM_ALMACEN) — solo lo que usa el pipeline ─
_MOVIMIENTOS_ALMACEN = Extractor(
    destino="movimientos_almacen",
    pk=("ano_eje", "sec_ejec", "tipo_bien", "tipo_movimto", "tipo_transac", "nro_movimto"),
    columnas=(
        "ano_eje", "sec_ejec", "tipo_bien", "tipo_movimto", "tipo_transac",
        "nro_movimto", "nro_orden", "nro_pecosa",
        "nro_guia", "fecha_movimto", "fecha_reg",
    ),
    _sql_base="""
        SELECT ANO_EJE, SEC_EJEC,
               -- Los movimientos de salida (S, pecosa) a veces traen TIPO_BIEN
               -- NULL; el almacen es solo de bienes, asi que se fija 'B'.
               COALESCE(NULLIF(LTRIM(RTRIM(TIPO_BIEN)), ''), 'B') AS TIPO_BIEN,
               NRO_MOVIMTO,
               TIPO_MOVIMTO, TIPO_TRANSAC, NRO_ORDEN, NRO_MOVIMTO AS NRO_PECOSA,
               NRO_GUIA, FECHA_MOVIMTO, FECHA_REG
        FROM SIG_MOVIM_ALMACEN
        WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
          AND TIPO_MOVIMTO IN ('I', 'R', 'S') AND TIPO_TRANSAC = 1
    """,
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "nro_movimto": _i(r["NRO_MOVIMTO"]),
        "tipo_movimto": _s(r["TIPO_MOVIMTO"]), "tipo_transac": _i(r["TIPO_TRANSAC"]),
        "nro_orden": _i(r["NRO_ORDEN"]), "nro_pecosa": _i(r["NRO_PECOSA"]),
        "nro_guia": _s(r["NRO_GUIA"]), "fecha_movimto": r["FECHA_MOVIMTO"],
        "fecha_reg": r["FECHA_REG"],
    },
)

# ── seguimiento_estados (SIG_SEGUIMIENTO + _ESTADO) — grande -> watermark ─
# El estado y su fecha viven en _ESTADO; el documento (tipo, numero, CC) en la
# cabecera. Se juntan por (TIPO_TRANSACCION, NRO_ORIGEN). Watermark por
# FECHA_ESTADO (la que avanza cuando cambia un estado).
_SEGUIMIENTO = Extractor(
    destino="seguimiento_estados",
    pk=("ano_eje", "sec_ejec", "tipo_transaccion", "nro_origen", "sec_estado"),
    columnas=(
        "ano_eje", "sec_ejec", "tipo_transaccion", "nro_origen", "sec_estado",
        "tipo_bien", "tipo_pedido", "nro_pedido", "nro_consolid",
        "centro_costo", "estado_seguimiento", "cuser_id",
        "fecha_estado", "fecha_reg",
    ),
    recarga_completa=False,
    watermark=True,
    col_fecha="fecha_estado",
    _sql_base="""
        SELECT se.ANO_EJE, se.SEC_EJEC, se.TIPO_TRANSACCION, se.NRO_ORIGEN,
               se.SEC_ESTADO, se.ESTADO_SEGUIMIENTO, se.CUSER_ID,
               se.FECHA_ESTADO, se.FECHA_REG,
               sg.TIPO_BIEN, sg.TIPO_PEDIDO, sg.NRO_PEDIDO,
               sg.NRO_CONSOLID, sg.CENTRO_COSTO
        FROM SIG_SEGUIMIENTO_ESTADO se
        LEFT JOIN SIG_SEGUIMIENTO sg
            ON sg.ANO_EJE = se.ANO_EJE AND sg.SEC_EJEC = se.SEC_EJEC
           AND sg.TIPO_TRANSACCION = se.TIPO_TRANSACCION
           AND sg.NRO_ORIGEN = se.NRO_ORIGEN
        WHERE se.ANO_EJE = :ano AND se.SEC_EJEC = :sec_ejec
    """,
    _sql_watermark="AND se.FECHA_ESTADO > :watermark",
    mapear=lambda r: {
        "ano_eje": _i(r["ANO_EJE"]), "sec_ejec": _i(r["SEC_EJEC"]),
        "tipo_transaccion": _i(r["TIPO_TRANSACCION"]),
        "nro_origen": _i(r["NRO_ORIGEN"]), "sec_estado": _i(r["SEC_ESTADO"]),
        "tipo_bien": _s(r["TIPO_BIEN"]), "tipo_pedido": _s(r["TIPO_PEDIDO"]),
        "nro_pedido": _s(r["NRO_PEDIDO"]), "nro_consolid": _i(r["NRO_CONSOLID"]),
        "centro_costo": _s(r["CENTRO_COSTO"]),
        "estado_seguimiento": _s(r["ESTADO_SEGUIMIENTO"]),
        "cuser_id": _s(r["CUSER_ID"]), "fecha_estado": r["FECHA_ESTADO"],
        "fecha_reg": r["FECHA_REG"],
    },
)

# ── catalogo_estados (SIG_TRANSACCION_ESTADO) — estatico, sin filtro año ──
_CATALOGO_ESTADOS = Extractor(
    destino="catalogo_estados",
    pk=("cod_maestro", "cod_detalle", "estado"),
    columnas=("cod_maestro", "cod_detalle", "estado", "nombre"),
    filtro_ano="TRUE",  # sin dimension de año: se limpia entera cada recarga
    _sql_base="""
        SELECT COD_MAESTRO, COD_DETALLE, ESTADO, NOMBRE
        FROM SIG_TRANSACCION_ESTADO
    """,
    mapear=lambda r: {
        "cod_maestro": _s(r["COD_MAESTRO"]), "cod_detalle": _i(r["COD_DETALLE"]),
        "estado": _s(r["ESTADO"]), "nombre": _s(r["NOMBRE"]),
    },
)


# Orden de sincronizacion: las referenciadas primero no importa (no hay FKs
# entre tablas del snapshot), pero se listan de "arriba" (pedido) hacia
# "abajo" (ejecucion) por legibilidad. seguimiento va aparte (job propio).
EXTRACTORES: tuple[Extractor, ...] = (
    _PEDIDOS,
    _PEDIDO_ITEMS,
    _BOLSAS,
    _EXPEDIENTES_CCMN,
    _ORDENES,
    _CERTIFICACIONES,
    _COMPROMISOS,
    _CONFORMIDADES,
    _MOVIMIENTOS_ALMACEN,
    _CATALOGO_ESTADOS,
)

# El seguimiento es voluminoso y cambia con otra cadencia: job separado (§01.3).
EXTRACTOR_SEGUIMIENTO: Extractor = _SEGUIMIENTO
