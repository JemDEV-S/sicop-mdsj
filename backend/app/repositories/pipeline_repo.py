"""Repositorio SIGA de DETALLE del pipeline (lectura puntual de un documento).

Guia Pipeline v2 §07: el kanban ya NO vive aqui. La query masiva de 12 CTE
(`_SQL_KANBAN`) y el match composite por monto se retiraron: el kanban lee del
snapshot (siga.v_pipeline_pedido via pipeline_read_repo), sin tocar SIGA en
caliente. Lo que queda aqui consulta SIGA para UN pedido/bolsa a la vez
(detalle, vista de bolsa, validacion al asociar) — costo bajo, pocas filas.

Cadena estructural (FK real o composite verificado en 232/S y 005/B):

    [3]  SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL IS NOT NULL        -> cuadro necesidad
    [4]  SIG_CUADRO_MODIFICADO_CMN (puente pedido<->PAAC)       -> CCMN candidato
    [5]  SIG_PAAC_CONSOLIDADO.NRO_CONSOLID                      -> CCMN / EM(CVR)
    [6]  SIG_SOLICITUD_COTIZACION.NRO_CONSOLID                  -> cotizacion
    [7]  SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC                   -> cuadro adquisicion
    [8]  SIG_CERTIFICACION.NRO_CERTIFICA_SIAF IS NOT NULL       -> CCP
    [9]  SIG_ORDEN_ADQUISICION (cadena dura CCMN)               -> orden emitida

Filtro por CC del usuario (RN-04) via SIG_PEDIDOS.CENTRO_COSTO IN (...).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


# ─── Parseo de las fuentes declarativas ──────────────────────────────────
#
# SIGA no vincula pedido y CCMN (§1): logistica copia los datos del pedido a
# un CCMN nuevo sin relacionarlos. Lo unico que queda es el texto libre, donde
# el usuario escribe de que pedido viene. Regex validado contra todos los
# formatos observados en 2026 (§3.3):
#
#   PEDIDO 76 · PEDIDO 0225 · PEDIDO DE COMPRA N°000026-2026
#   PEDIDO DE SERVICIO N°228-2026 ACTUALIZADO · PEDIOD 0041 (typo)
#
# `SEGUN CONTRATO` se descarta: no es un pedido.

RE_PEDIDO = re.compile(
    r"PEDIDO\s*(?:DE\s*(?:SERVICIO|COMPRA)\s*)?N?[^0-9A-Z]{0,4}(\d{1,6})", re.I
)
RE_CONTRATO = re.compile(r"SEGUN\s+CONTRATO", re.I)

# El pedido de atencion ('1') declara su O/C en el motivo: "ATENCION DE PEDIDO
# A LA O/C N°570" (531/576 en 2026, diagnostico_sesion6/06). El caracter entre
# la N y el numero varia (°, mojibake, espacios) — de ahi el comodin.
RE_OC = re.compile(r"O/C\s*N[^0-9]{0,4}(\d{1,6})", re.I)


def parsear_nro_oc(texto: str | None) -> int | None:
    """Extrae el numero de O/C que un pedido de atencion declara en su motivo."""
    if not texto:
        return None
    m = RE_OC.search(texto)
    return int(m.group(1)) if m else None


def parsear_nro_pedido(texto: str | None) -> int | None:
    """Extrae el numero de pedido declarado en un texto libre de SIGA.

    Devuelve None cuando el texto no nombra un pedido (p.ej. `INFORME
    275-2026-MDSJ`, o `SEGUN CONTRATO`) — no adivina.
    """
    if not texto or RE_CONTRATO.search(texto):
        return None
    m = RE_PEDIDO.search(texto)
    return int(m.group(1)) if m else None


def _agrupar_declaraciones(rows: Any) -> dict[tuple[str, int], set[int]]:
    """(tipo_bien, nro_pedido) -> conjunto de CCMN que lo declaran.

    Se guarda el conjunto y no un ganador: si dos CCMN declaran el mismo
    pedido, elegir uno seria exactamente el "ganador por parecido" que la
    cascada existe para evitar.
    """
    out: dict[tuple[str, int], set[int]] = defaultdict(set)
    for r in rows:
        ped = parsear_nro_pedido(r["texto"])
        if ped is None or r["ccmn"] is None:
            continue
        out[((r["TIPO_BIEN"] or "").strip(), ped)].add(int(r["ccmn"]))
    return out


def _elegir_declarado(
    declaraciones: dict[tuple[str, int], set[int]],
    tipo_bien: str,
    nro_pedido: int,
    candidatos: frozenset[int],
) -> int | None:
    """CCMN declarado para el pedido, si la declaracion es inequivoca.

    Con varios CCMN declarando el mismo pedido se prefiere el que este entre
    los candidatos de la bolsa. Si queda mas de uno, se devuelve None: la
    fuente no desambigua y el pedido sigue `ambiguo`. Si el unico declarado
    esta FUERA de los candidatos se devuelve igual, para que la cascada lo
    marque `conflicto` en vez de silenciarlo.
    """
    decl = declaraciones.get((tipo_bien, nro_pedido))
    if not decl:
        return None
    dentro = decl & candidatos
    if len(dentro) == 1:
        return next(iter(dentro))
    if dentro:
        return None  # varios candidatos declarados: no desambigua
    return next(iter(decl)) if len(decl) == 1 else None



# ─── Fuentes declarativas (§3.3) ─────────────────────────────────────────
#
# Ambas emiten (tipo_bien, ccmn, texto). El texto nombra el PEDIDO; el parseo
# se hace en Python con RE_PEDIDO, no en SQL: el regex esta validado contra
# los formatos reales y en T-SQL seria ilegible e imposible de testear.

# La orden nombra el pedido en el texto libre del item. Su CCMN sale de la
# cadena propia de la orden (SEC_CUADRO -> NRO_CONS_PAAC), poblada en las
# 1,473 ordenes de 2026. Es la fuente de mayor prioridad: la orden es
# posterior en el proceso y estuvo bajo mas escrutinio.
_SQL_DECL_ORDEN = """
SELECT
    o.TIPO_BIEN,
    ca.NRO_CONS_PAAC                            AS ccmn,
    CAST(oi.ESPECIFICACIONES AS VARCHAR(2000))  AS texto
FROM SIG_ORDEN_ADQUISICION o
JOIN SIG_CUADRO_ADQUISICION ca
    ON ca.ANO_EJE = o.ANO_EJE
   AND ca.SEC_EJEC = o.SEC_EJEC
   AND ca.TIPO_BIEN = o.TIPO_BIEN
   AND ca.SEC_CUADRO = o.SEC_CUADRO
JOIN SIG_ORDEN_ITEM oi
    ON oi.ANO_EJE = o.ANO_EJE
   AND oi.SEC_EJEC = o.SEC_EJEC
   AND oi.TIPO_BIEN = o.TIPO_BIEN
   AND oi.NRO_ORDEN = o.NRO_ORDEN
WHERE o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
  AND oi.ESPECIFICACIONES IS NOT NULL
"""

# SIG_CERTIFICACION_DOC trae NRO_CONSOLID propio al 100% (876 S / 659 B en
# 2026) -- no hace falta pasar por SIG_CERTIFICACION_FASE.
_SQL_DECL_CERT = """
SELECT
    cd.TIPO_BIEN,
    cd.NRO_CONSOLID                         AS ccmn,
    CAST(cd.REQUERIMIENTO AS VARCHAR(500))  AS texto
FROM SIG_CERTIFICACION_DOC cd
WHERE cd.ANO_EJE = :ano AND cd.SEC_EJEC = :sec_ejec
  AND cd.REQUERIMIENTO IS NOT NULL
"""




# ─── Vista de bolsa (SEC_CUA_MOD_SAL) ────────────────────────────────────


def contexto_pedido_bolsa(
    ano: int, tipo_bien: str, tipo_pedido: str, nro_pedido: int
) -> dict[str, Any] | None:
    """Bolsa(s), CC y CCMN candidatos de un pedido — para validar al asociar.

    Se usa antes de escribir una resolucion manual: comprueba que el pedido
    existe, de que CC es (RN-04) y que el CCMN elegido esta de verdad entre
    los candidatos de su bolsa. Sin esto se podria asociar cualquier numero.
    """
    params = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "tipo": tipo_bien,
        "tipo_ped": tipo_pedido,
        "nro": nro_pedido,
    }
    with get_connection() as conn:
        cab = conn.execute(
            text(
                """
                SELECT TOP 1 p.NRO_PEDIDO, p.TIPO_BIEN, p.TIPO_PEDIDO,
                       LTRIM(RTRIM(p.CENTRO_COSTO)) AS CENTRO_COSTO,
                       p.sec_func, p.ESTADO AS estado_pedido, p.FECHA_PEDIDO
                FROM SIG_PEDIDOS p
                WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
                  AND p.TIPO_BIEN = :tipo AND p.TIPO_PEDIDO = :tipo_ped
                  AND p.NRO_PEDIDO = :nro
                """
            ),
            params,
        ).mappings().first()

        if cab is None:
            return None

        filas = conn.execute(
            text(
                """
                SELECT DISTINCT dp.SEC_CUA_MOD_SAL, cmn.NRO_CONSOLID
                FROM SIG_DETALLE_PEDIDOS dp
                LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
                    ON cmn.SEC_EJEC = dp.SEC_EJEC
                   AND cmn.ANNO_EJEC = dp.ANO_EJE
                   AND cmn.SEC_CUA_MOD_SAL = dp.SEC_CUA_MOD_SAL
                   AND cmn.TIPO_BIEN = dp.TIPO_BIEN
                WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                  AND dp.TIPO_BIEN = :tipo AND dp.NRO_PEDIDO = :nro
                  AND dp.TIPO_PEDIDO = :tipo_ped
                  AND dp.SEC_CUA_MOD_SAL IS NOT NULL
                """
            ),
            params,
        ).all()

    bolsas = sorted({int(b) for b, _ in filas if b is not None})
    candidatos = sorted({int(c) for _, c in filas if c is not None})
    cand_set = frozenset(candidatos)

    # Declaraciones de las dos fuentes de texto (§3.3), para que el caller
    # pueda resolver la cascada sin repetir el parseo.
    p_decl = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    with get_connection() as conn:
        decl_orden = _agrupar_declaraciones(
            conn.execute(text(_SQL_DECL_ORDEN), p_decl).mappings().all()
        )
        decl_cert = _agrupar_declaraciones(
            conn.execute(text(_SQL_DECL_CERT), p_decl).mappings().all()
        )

    return {
        **dict(cab),
        "centro_costo": (cab["CENTRO_COSTO"] or "").strip(),
        "bolsas": bolsas,
        "candidatos": candidatos,
        "ccmn_declarado_orden": _elegir_declarado(
            decl_orden, tipo_bien, nro_pedido, cand_set
        ),
        "ccmn_declarado_cert": _elegir_declarado(
            decl_cert, tipo_bien, nro_pedido, cand_set
        ),
    }


def obtener_bolsa(
    ano: int, sec_cua_mod_sal: int, tipo_bien: str
) -> dict[str, Any] | None:
    """Pedidos y CCMN candidatos que comparten una bolsa `SEC_CUA_MOD_SAL`.

    La bolsa es donde vive la ambiguedad (§2.1): el CCMN es una copia del
    pedido, asi que comparten item, meta, clasificador y centro de costo
    **por construccion** -- justo los campos que los agrupan aqui.

    Orden **cronologico y neutro**, de mas reciente a mas antiguo, con
    desempate por numero descendente para que sea estable entre recargas.
    El monto se devuelve para mostrarlo, pero NO se ordena ni se sugiere por
    el: ordenar por proximidad de monto seria una recomendacion disfrazada, y
    ese metodo esta descartado en §2 -- pierde el CCMN correcto en 33 casos.

    Solo TIPO_PEDIDO='2' (pedido de compra, ver diccionario §10.2.1): SIGA
    reutiliza SEC_CUA_MOD_SAL en items de atencion de almacen (TIPO_PEDIDO='1')
    que no tienen relacion con el circuito de compras de esta bolsa -- sin el
    filtro aparecen como un "pedido" mas de la bolsa con motivo y CC ajenos
    (caso medido: bolsa 8905 trae el pedido 16/TIPO_PEDIDO=1 mezclado con los
    3 pedidos 834/694/16 de TIPO_PEDIDO=2 que si son de esta bolsa).

    Ref: doc de refactorizacion §8.2
    """
    params = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "bolsa": sec_cua_mod_sal,
        "tipo": tipo_bien,
    }
    with get_connection() as conn:
        pedidos = conn.execute(
            text(
                """
                SELECT DISTINCT
                    p.NRO_PEDIDO, p.TIPO_BIEN, p.TIPO_PEDIDO,
                    p.CENTRO_COSTO, p.sec_func, p.ESTADO AS estado_pedido,
                    p.FECHA_PEDIDO,
                    LTRIM(RTRIM(CAST(p.MOTIVO_PEDIDO AS VARCHAR(500)))) AS motivo,
                    LTRIM(RTRIM(p.NOMBRE_EMPLEADO))                     AS solicitante,
                    -- VALOR_TOTAL viene en 0.00 en los servicios (verificado
                    -- en los 3 pedidos de la bolsa 11553): el monto real esta
                    -- en CANT_SOLICITADA * PRECIO_UNIT. Tomar VALOR_TOTAL a
                    -- secas mostraria toda la bolsa en S/ 0 -- fallo silencioso.
                    CASE
                        WHEN COALESCE(dp.VALOR_TOTAL, 0) > 0 THEN dp.VALOR_TOTAL
                        ELSE COALESCE(dp.CANT_SOLICITADA, 0)
                             * COALESCE(dp.PRECIO_UNIT, 0)
                    END                                                 AS valor_soles,
                    LTRIM(RTRIM(dp.GRUPO_BIEN)) + '-' + LTRIM(RTRIM(dp.CLASE_BIEN))
                      + '-' + LTRIM(RTRIM(dp.FAMILIA_BIEN)) + '-'
                      + LTRIM(RTRIM(dp.ITEM_BIEN))                      AS item
                FROM SIG_DETALLE_PEDIDOS dp
                INNER JOIN SIG_PEDIDOS p
                    ON p.ANO_EJE = dp.ANO_EJE AND p.SEC_EJEC = dp.SEC_EJEC
                   AND p.TIPO_BIEN = dp.TIPO_BIEN AND p.NRO_PEDIDO = dp.NRO_PEDIDO
                   AND p.TIPO_PEDIDO = dp.TIPO_PEDIDO
                WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                  AND dp.SEC_CUA_MOD_SAL = :bolsa
                  AND dp.TIPO_BIEN = :tipo
                  AND dp.TIPO_PEDIDO = '2'
                  AND p.ESTADO IN ('0', '1', '7')
                ORDER BY p.FECHA_PEDIDO DESC, p.NRO_PEDIDO DESC
                """
            ),
            params,
        ).mappings().all()

        if not pedidos:
            return None

        candidatos = conn.execute(
            text(
                """
                SELECT DISTINCT
                    pc.NRO_CONSOLID, pc.TIPO_CONSOLID,
                    pc.FECHA_CONS, pc.VALOR_PLAN,
                    pc.NRO_EST_MDO, pc.NRO_CERTIFICA,
                    c.NRO_CERTIFICA_SIAF,
                    ca.SEC_CUADRO,
                    o.NRO_ORDEN, o.FECHA_ORDEN
                FROM SIG_CUADRO_MODIFICADO_CMN cmn
                INNER JOIN SIG_PAAC_CONSOLIDADO pc
                    ON pc.ANO_EJE = cmn.ANNO_EJEC
                   AND pc.SEC_EJEC = cmn.SEC_EJEC
                   AND pc.TIPO_CONSOLID = cmn.TIPO_CONSOLID
                   AND pc.NRO_CONSOLID = cmn.NRO_CONSOLID
                   AND pc.TIPO_BIEN = cmn.TIPO_BIEN
                LEFT JOIN SIG_CERTIFICACION c
                    ON c.ANO_EJE = pc.ANO_EJE AND c.SEC_EJEC = pc.SEC_EJEC
                   AND c.NRO_CERTIFICA = pc.NRO_CERTIFICA
                LEFT JOIN SIG_CUADRO_ADQUISICION ca
                    ON ca.ANO_EJE = pc.ANO_EJE AND ca.SEC_EJEC = pc.SEC_EJEC
                   AND ca.TIPO_BIEN = pc.TIPO_BIEN
                   AND ca.NRO_CONS_PAAC = pc.NRO_CONSOLID
                LEFT JOIN SIG_ORDEN_ADQUISICION o
                    ON o.ANO_EJE = ca.ANO_EJE AND o.SEC_EJEC = ca.SEC_EJEC
                   AND o.TIPO_BIEN = ca.TIPO_BIEN AND o.SEC_CUADRO = ca.SEC_CUADRO
                WHERE cmn.ANNO_EJEC = :ano AND cmn.SEC_EJEC = :sec_ejec
                  AND cmn.SEC_CUA_MOD_SAL = :bolsa
                  AND cmn.TIPO_BIEN = :tipo
                ORDER BY pc.FECHA_CONS DESC, pc.NRO_CONSOLID DESC
                """
            ),
            params,
        ).mappings().all()

    return {
        "sec_cua_mod_sal": sec_cua_mod_sal,
        "ano_eje": ano,
        "tipo_bien": tipo_bien,
        "pedidos": [dict(p) for p in pedidos],
        "candidatos": [dict(c) for c in candidatos],
    }


# ─── Detalle de un pedido con la cadena completa ─────────────────────────


def _flags_programacion(
    ano: int, tipo_bien: str, tipo_pedido: str, nro_pedido: int,
    ccmn: int | None = None,
) -> dict[str, Any]:
    """Presencia y FECHAS de las etapas 4-7 mirando la cadena del CCMN.

    Mismos joins que los CTE del kanban (bolsa -> CCMN -> PAAC -> cotizacion ->
    cuadro de adquisicion). Devuelve los flags que `construir_timeline` usa para
    distinguir cada etapa, y `nro_est_mdo` / `nro_consolid` como identificadores
    del estudio de mercado.

    Sin esto el detalle solo veia la cadena hacia abajo desde la orden, y un
    pedido detenido en el estudio de mercado se mostraba en "cuadro necesidad"
    (caso 311/S).

    `ccmn`: cuando el puente pedido<->CCMN esta resuelto (manual, declarado o
    candidato unico), acota la cadena a ESE cuadro consolidado. Sin el filtro,
    el MAX() responde "¿ALGUN candidato de la bolsa llego a la etapa?" y un
    pedido asociado a un CCMN detenido hereda el avance de otro candidato
    (caso 286/B: asociado al 2530 sin cotizacion, mostraba la cotizacion y el
    cuadro del 3472).
    """
    params: dict[str, Any] = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "tipo": tipo_bien,
        "tipo_ped": tipo_pedido,
        "nro": nro_pedido,
    }
    filtro_ccmn = ""
    if ccmn is not None:
        filtro_ccmn = "AND cmn.NRO_CONSOLID = :ccmn"
        params["ccmn"] = int(ccmn)
    with get_connection() as conn:
        fila = conn.execute(
            text(
                f"""
                WITH det AS (
                    SELECT DISTINCT dp.SEC_CUA_MOD_SAL, dp.TIPO_BIEN,
                           dp.ANO_EJE, dp.SEC_EJEC
                    FROM SIG_DETALLE_PEDIDOS dp
                    WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                      AND dp.TIPO_BIEN = :tipo AND dp.TIPO_PEDIDO = :tipo_ped
                      AND dp.NRO_PEDIDO = :nro
                      AND dp.SEC_CUA_MOD_SAL IS NOT NULL
                )
                SELECT
                    MAX(CASE WHEN cmn.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END) AS tiene_puente_paac,
                    MAX(CASE WHEN pc.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END)  AS tiene_ccmn,
                    MAX(CASE WHEN sc.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END)  AS tiene_cotizacion,
                    MAX(CASE WHEN ca.SEC_CUADRO IS NOT NULL THEN 1 ELSE 0 END)    AS tiene_cuadro_adq,
                    MIN(pc.NRO_CONSOLID)                                          AS nro_consolid,
                    MIN(pc.NRO_EST_MDO)                                           AS nro_est_mdo,
                    MIN(ca.SEC_CUADRO)                                            AS sec_cuadro_prog,
                    -- Fechas de la cadena: primera vez que se alcanzo cada hito.
                    MIN(pc.FECHA_CONS)                                            AS fecha_consolid,
                    MIN(sc.FECHA_REG)                                             AS fecha_cotizacion_prog,
                    MIN(ca.FECHA_AUTORIZ)                                         AS fecha_cuadro_prog
                FROM det d
                LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
                    ON cmn.SEC_EJEC = d.SEC_EJEC
                   AND cmn.ANNO_EJEC = d.ANO_EJE
                   AND cmn.SEC_CUA_MOD_SAL = d.SEC_CUA_MOD_SAL
                   AND cmn.TIPO_BIEN = d.TIPO_BIEN
                   {filtro_ccmn}
                LEFT JOIN SIG_PAAC_CONSOLIDADO pc
                    ON pc.ANO_EJE = cmn.ANNO_EJEC
                   AND pc.SEC_EJEC = cmn.SEC_EJEC
                   AND pc.TIPO_CONSOLID = cmn.TIPO_CONSOLID
                   AND pc.NRO_CONSOLID = cmn.NRO_CONSOLID
                   AND pc.TIPO_BIEN = cmn.TIPO_BIEN
                LEFT JOIN SIG_SOLICITUD_COTIZACION sc
                    ON sc.ANO_EJE = cmn.ANNO_EJEC
                   AND sc.SEC_EJEC = cmn.SEC_EJEC
                   AND sc.tipo_bien = cmn.TIPO_BIEN
                   AND sc.NRO_CONSOLID = cmn.NRO_CONSOLID
                LEFT JOIN SIG_CUADRO_ADQUISICION ca
                    ON ca.ANO_EJE = cmn.ANNO_EJEC
                   AND ca.SEC_EJEC = cmn.SEC_EJEC
                   AND ca.TIPO_BIEN = cmn.TIPO_BIEN
                   AND ca.NRO_CONS_PAAC = cmn.NRO_CONSOLID
                """
            ),
            params,
        ).mappings().first()

    if fila is None:
        return {
            "tiene_puente_paac": 0, "tiene_ccmn": 0,
            "tiene_cotizacion": 0, "tiene_cuadro_adq": 0,
            "nro_consolid": None, "nro_est_mdo": None, "sec_cuadro_prog": None,
            "fecha_consolid": None, "fecha_cotizacion_prog": None,
            "fecha_cuadro_prog": None,
        }
    return dict(fila)


def _fechas_seguimiento(
    conn: Any, params: dict[str, Any]
) -> dict[str, Any]:
    """Fechas del flujo administrativo del pedido (SIG_SEGUIMIENTO).

    La cabecera de SIG_PEDIDOS trae FECHA_APROB/FECHA_ATENC en NULL en el
    100% de los pedidos de compra 2026 (diagnostico_sesion6/08); las fechas
    reales viven en el seguimiento. Ojo: los pedidos de compra ('2') nunca
    llegan al estado '2' (Aprobado) del seguimiento — su hito de aprobacion
    es el VB del jefe (estado '1', 100% con fecha).
    """
    filas = conn.execute(
        text(
            """
            SELECT se.ESTADO_SEGUIMIENTO AS estado, MIN(se.FECHA_ESTADO) AS fecha
            FROM SIG_SEGUIMIENTO s
            JOIN SIG_SEGUIMIENTO_ESTADO se
                ON se.ANO_EJE = s.ANO_EJE AND se.SEC_EJEC = s.SEC_EJEC
               AND se.TIPO_TRANSACCION = s.TIPO_TRANSACCION
               AND se.NRO_ORIGEN = s.NRO_ORIGEN
            WHERE s.ANO_EJE = :ano AND s.SEC_EJEC = :sec_ejec
              AND s.TIPO_BIEN = :tipo AND s.TIPO_PEDIDO = :tipo_ped
              AND TRY_CAST(s.NRO_PEDIDO AS INT) = :nro
            GROUP BY se.ESTADO_SEGUIMIENTO
            """
        ),
        params,
    ).mappings().all()
    por_estado = {(f["estado"] or "").strip(): f["fecha"] for f in filas}
    return {
        "fecha_vb_jefe": por_estado.get("1"),
        "fecha_aprob_seg": por_estado.get("2"),
        "fecha_atendido_seg": por_estado.get("8"),
    }


def obtener_pedido(
    ano: int, nro_pedido: int, tipo_bien: str, tipo_pedido: str,
    ccmn_manual: int | None = None,
) -> dict[str, Any] | None:
    """Cabecera + items + orden(es) + cadena arriba + conformidades + almacen.

    `NRO_PEDIDO` solo NO es unico (§5 CLAUDE.md): SIGA reutiliza el mismo
    numero para pedidos distintos que solo se distinguen por TIPO_PEDIDO (p.
    ej. 000003/B tiene un pedido de compra TIPO_PEDIDO='2' y una atencion de
    almacen TIPO_PEDIDO='1' sin relacion entre si). Toda query de aqui debe
    filtrar por los 4 campos de la llave o mezcla items/ordenes de pedidos
    distintos bajo una sola pantalla (caso medido: pedido 3/B).

    `ccmn_manual` (resolucion de Postgres, la inyecta el router) participa en
    la atribucion: si el puente resuelve (manual > declarado > unico), la
    cadena de programacion y las ordenes se acotan a ESE CCMN.
    """
    # Contexto de bolsa ANTES de las queries: la cascada decide a que CCMN se
    # acota la cadena (manual > declarado > candidato unico). Sin resolver, se
    # mira la bolsa completa y el timeline marca el avance como "del grupo".
    ctx = contexto_pedido_bolsa(ano, tipo_bien, tipo_pedido, nro_pedido)
    if ctx is None:
        return None
    candidatos = frozenset(ctx.get("candidatos") or ())
    ccmn_resuelto = (
        ccmn_manual
        or ctx.get("ccmn_declarado_orden")
        or ctx.get("ccmn_declarado_cert")
        or (next(iter(candidatos)) if len(candidatos) == 1 else None)
    )

    params: dict[str, Any] = {
        "ano": ano, "sec_ejec": settings.SEC_EJEC,
        "nro": nro_pedido, "tipo": tipo_bien, "tipo_ped": tipo_pedido,
        "ccmn_res": int(ccmn_resuelto) if ccmn_resuelto is not None else None,
    }
    with get_connection() as conn:
        cab = conn.execute(
            text(
                """
                SELECT
                    p.ANO_EJE, p.SEC_EJEC, p.NRO_PEDIDO, p.TIPO_BIEN,
                    p.TIPO_PEDIDO, p.CENTRO_COSTO, p.sec_func,
                    LTRIM(RTRIM(p.ACT_PROY))         AS act_proy,
                    p.ESTADO                         AS estado_pedido,
                    p.FECHA_PEDIDO, p.FECHA_APROB, p.FECHA_ATENC,
                    LTRIM(RTRIM(CAST(p.MOTIVO_PEDIDO AS VARCHAR(500)))) AS motivo,
                    -- NOMBRE_EMPLEADO viene NULL en el 100% de los pedidos
                    -- 2026; el solicitante real se resuelve por el codigo
                    -- EMPLEADO contra el maestro de personal (100% cruza).
                    COALESCE(
                        NULLIF(LTRIM(RTRIM(p.NOMBRE_EMPLEADO)), ''),
                        NULLIF(LTRIM(RTRIM(CONCAT(
                            LTRIM(RTRIM(pe.nombres)), ' ',
                            LTRIM(RTRIM(pe.apellido_paterno)), ' ',
                            LTRIM(RTRIM(pe.apellido_materno))
                        ))), '')
                    )                                AS solicitante,
                    -- FUENTE_FINANC (texto) viene NULL; el codigo real esta
                    -- en fuente_fto (100% poblado) y su nombre en el catalogo.
                    COALESCE(
                        NULLIF(LTRIM(RTRIM(p.FUENTE_FINANC)), ''),
                        LTRIM(RTRIM(p.fuente_fto))
                    )                                AS fuente_financ,
                    LTRIM(RTRIM(ff.NOMBRE))          AS fuente_financ_nombre,
                    LTRIM(RTRIM(cc.NOMBRE_DEPEND))   AS centro_costo_nombre,
                    LTRIM(RTRIM(m.nombre))           AS nombre_meta
                FROM SIG_PEDIDOS p
                LEFT JOIN SIG_CENTRO_COSTO cc
                    ON cc.ANO_EJE = p.ANO_EJE AND cc.SEC_EJEC = p.SEC_EJEC
                   AND cc.CENTRO_COSTO = p.CENTRO_COSTO
                LEFT JOIN META m
                    ON m.ano_eje = p.ANO_EJE AND m.sec_ejec = p.SEC_EJEC
                   AND m.sec_func = p.sec_func
                OUTER APPLY (
                    SELECT TOP 1 x.nombres, x.apellido_paterno, x.apellido_materno
                    FROM SIG_PERSONAL x
                    WHERE x.SEC_EJEC = p.SEC_EJEC AND x.empleado = p.EMPLEADO
                ) pe
                OUTER APPLY (
                    SELECT TOP 1 f.NOMBRE
                    FROM FUENTE_FINANC f
                    WHERE f.ANO_EJE = p.ANO_EJE
                      AND f.FUENTE_FINANC = LTRIM(RTRIM(p.fuente_fto))
                ) ff
                WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
                  AND p.NRO_PEDIDO = :nro AND p.TIPO_BIEN = :tipo
                  AND p.TIPO_PEDIDO = :tipo_ped
                """
            ),
            params,
        ).mappings().first()

        if cab is None:
            return None

        seguimiento = _fechas_seguimiento(conn, params)

        items = conn.execute(
            text(
                """
                SELECT
                    dp.SECUENCIA,
                    LTRIM(RTRIM(dp.GRUPO_BIEN))     AS grupo_bien,
                    LTRIM(RTRIM(dp.CLASE_BIEN))     AS clase_bien,
                    LTRIM(RTRIM(dp.FAMILIA_BIEN))   AS familia_bien,
                    LTRIM(RTRIM(dp.ITEM_BIEN))      AS item_bien,
                    dp.CANT_SOLICITADA, dp.CANT_APROBADA, dp.CANT_ATENDIDA,
                    -- VALOR_TOTAL viene en 0.00 en servicios; el monto real
                    -- es CANT_SOLICITADA * PRECIO_UNIT. Ver §9.5 del doc.
                    CASE
                        WHEN COALESCE(dp.VALOR_TOTAL, 0) > 0 THEN dp.VALOR_TOTAL
                        ELSE COALESCE(dp.CANT_SOLICITADA, 0)
                             * COALESCE(dp.PRECIO_UNIT, 0)
                    END                             AS VALOR_TOTAL,
                    LTRIM(RTRIM(dp.CLASIFICADOR))   AS clasificador,
                    dp.NRO_ORDEN                    AS nro_orden_declarado,
                    dp.NRO_PECOSA,
                    dp.SEC_CUA_MOD_SAL,
                    dp.ESTADO_PED, dp.ESTADO_ATEND,
                    dp.ESTADO_CONFOR, dp.ESTADO_COMPRA,
                    dp.FECHA_CONFOR
                FROM SIG_DETALLE_PEDIDOS dp
                WHERE dp.ANO_EJE = :ano AND dp.sec_ejec = :sec_ejec
                  AND dp.NRO_PEDIDO = :nro AND dp.TIPO_BIEN = :tipo
                  AND dp.TIPO_PEDIDO = :tipo_ped
                ORDER BY dp.SECUENCIA
                """
            ),
            params,
        ).mappings().all()

        ordenes = conn.execute(
            text(
                """
                WITH det AS (
                    SELECT
                        dp.NRO_PECOSA,
                        dp.NRO_ORDEN                                AS nro_orden_declarado,
                        p.sec_func                                  AS sec_func_item,
                        LTRIM(RTRIM(dp.CLASIFICADOR))               AS clasificador,
                        LTRIM(RTRIM(dp.GRUPO_BIEN))                 AS grupo_bien,
                        LTRIM(RTRIM(dp.CLASE_BIEN))                 AS clase_bien,
                        LTRIM(RTRIM(dp.FAMILIA_BIEN))               AS familia_bien,
                        LTRIM(RTRIM(dp.ITEM_BIEN))                  AS item_bien,
                        -- Mismo fallback que el kanban: con VALOR_TOTAL en 0
                        -- el composite acepta cualquier monto y trae las
                        -- ordenes de los demas pedidos de la bolsa.
                        CASE
                            WHEN COALESCE(dp.VALOR_TOTAL, 0) > 0
                                THEN dp.VALOR_TOTAL
                            ELSE COALESCE(dp.CANT_SOLICITADA, 0)
                                 * COALESCE(dp.PRECIO_UNIT, 0)
                        END                                         AS valor_soles
                    FROM SIG_DETALLE_PEDIDOS dp
                    INNER JOIN SIG_PEDIDOS p
                        ON p.ANO_EJE = dp.ANO_EJE AND p.SEC_EJEC = dp.SEC_EJEC
                       AND p.TIPO_BIEN = dp.TIPO_BIEN AND p.NRO_PEDIDO = dp.NRO_PEDIDO
                       AND p.TIPO_PEDIDO = dp.TIPO_PEDIDO
                    WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                      AND dp.TIPO_BIEN = :tipo AND dp.NRO_PEDIDO = :nro
                      AND dp.TIPO_PEDIDO = :tipo_ped
                ),
                pecosa AS (
                    SELECT DISTINCT ma.NRO_ORDEN
                    FROM det d
                    INNER JOIN SIG_MOVIM_ALMACEN ma
                        ON ma.ANO_EJE = :ano AND ma.SEC_EJEC = :sec_ejec
                       AND ma.TIPO_BIEN = :tipo AND ma.NRO_MOVIMTO = d.NRO_PECOSA
                    WHERE d.NRO_PECOSA > 0
                ),
                composite AS (
                    SELECT DISTINCT oi.NRO_ORDEN
                    FROM det d
                    INNER JOIN SIG_ORDEN_ITEM oi
                        ON oi.ANO_EJE = :ano AND oi.SEC_EJEC = :sec_ejec
                       AND oi.TIPO_BIEN = :tipo
                       AND LTRIM(RTRIM(oi.GRUPO_BIEN)) = d.grupo_bien
                       AND LTRIM(RTRIM(oi.CLASE_BIEN)) = d.clase_bien
                       AND LTRIM(RTRIM(oi.FAMILIA_BIEN)) = d.familia_bien
                       AND LTRIM(RTRIM(oi.ITEM_BIEN)) = d.item_bien
                    INNER JOIN SIG_ORDEN_ITEM_PPTO op
                        ON op.ANO_EJE = oi.ANO_EJE AND op.SEC_EJEC = oi.SEC_EJEC
                       AND op.NRO_ORDEN = oi.NRO_ORDEN AND op.TIPO_BIEN = oi.TIPO_BIEN
                       AND op.TIPO_PPTO = oi.TIPO_PPTO AND op.SEC_ORDEN = oi.SEC_ORDEN
                       AND op.SEC_ITEM = oi.SEC_ITEM
                       AND op.SEC_FUNC = d.sec_func_item
                       AND LTRIM(RTRIM(op.CLASIFICADOR)) = d.clasificador
                       AND (d.valor_soles = 0 OR ROUND(op.VALOR_SOLES, 2) = ROUND(d.valor_soles, 2))
                ),
                declarado AS (
                    SELECT DISTINCT nro_orden_declarado AS NRO_ORDEN
                    FROM det WHERE nro_orden_declarado > 0
                ),
                -- Cadena dura CCMN -> cuadro de adquisicion -> orden. FK real
                -- de SIGA, no heuristica de monto. Solo se activa cuando la
                -- bolsa tiene UN SOLO CCMN candidato (caso `unico`): ahi el
                -- cuadro es de ESTE pedido con certeza, asi que no reintroduce
                -- el fallo de §2 (mezcla ordenes en bolsas compartidas).
                -- Recupera ordenes que el composite pierde cuando el monto
                -- cambio tras cotizar (226/S: pidio 5600, la OC 97 salio 5500).
                bolsa_unica AS (
                    SELECT dp.SEC_CUA_MOD_SAL, MIN(cmn.NRO_CONSOLID) AS ccmn
                    FROM SIG_DETALLE_PEDIDOS dp
                    JOIN SIG_CUADRO_MODIFICADO_CMN cmn
                        ON cmn.SEC_EJEC = dp.SEC_EJEC
                       AND cmn.ANNO_EJEC = dp.ANO_EJE
                       AND cmn.SEC_CUA_MOD_SAL = dp.SEC_CUA_MOD_SAL
                       AND cmn.TIPO_BIEN = dp.TIPO_BIEN
                    WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                      AND dp.TIPO_BIEN = :tipo AND dp.NRO_PEDIDO = :nro
                      AND dp.TIPO_PEDIDO = :tipo_ped
                      AND dp.SEC_CUA_MOD_SAL IS NOT NULL
                    GROUP BY dp.SEC_CUA_MOD_SAL
                    HAVING COUNT(DISTINCT cmn.NRO_CONSOLID) = 1
                ),
                cadena_ccmn AS (
                    SELECT DISTINCT o.NRO_ORDEN
                    FROM bolsa_unica b
                    JOIN SIG_CUADRO_ADQUISICION ca
                        ON ca.ANO_EJE = :ano AND ca.SEC_EJEC = :sec_ejec
                       AND ca.TIPO_BIEN = :tipo AND ca.NRO_CONS_PAAC = b.ccmn
                    JOIN SIG_ORDEN_ADQUISICION o
                        ON o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
                       AND o.TIPO_BIEN = :tipo AND o.SEC_CUADRO = ca.SEC_CUADRO
                ),
                -- Misma cadena dura (CCMN -> cuadro adq. -> orden), pero para
                -- el CCMN que la cascada atribuyo a ESTE pedido (manual,
                -- declarado o unico). Es lo que permite atribuir la O/C de un
                -- BIEN igual que la O/S de un servicio: la orden trae
                -- SEC_CUADRO en el 100% de los casos (diag. sesion6/08-E) y
                -- el cuadro nombra su CCMN via NRO_CONS_PAAC.
                cadena_resuelta AS (
                    SELECT DISTINCT o.NRO_ORDEN
                    FROM SIG_CUADRO_ADQUISICION ca
                    JOIN SIG_ORDEN_ADQUISICION o
                        ON o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
                       AND o.TIPO_BIEN = :tipo AND o.SEC_CUADRO = ca.SEC_CUADRO
                    WHERE :ccmn_res IS NOT NULL
                      AND ca.ANO_EJE = :ano AND ca.SEC_EJEC = :sec_ejec
                      AND ca.TIPO_BIEN = :tipo AND ca.NRO_CONS_PAAC = :ccmn_res
                ),
                todas AS (
                    SELECT NRO_ORDEN, 'pecosa' AS metodo FROM pecosa
                    UNION SELECT NRO_ORDEN, 'composite' FROM composite
                    UNION SELECT NRO_ORDEN, 'declarado' FROM declarado
                    UNION SELECT NRO_ORDEN, 'cadena_ccmn' FROM cadena_ccmn
                    UNION SELECT NRO_ORDEN, 'cadena_ccmn' FROM cadena_resuelta
                )
                SELECT
                    o.NRO_ORDEN, o.TIPO_BIEN,
                    o.EXP_SIAF, o.EXP_SIGA,
                    o.SEC_CUADRO, o.NRO_CERTIFICA,
                    -- CCMN del que sale la orden: permite quedarse solo con
                    -- las ordenes del CCMN atribuido a ESTE pedido.
                    ca_o.NRO_CONS_PAAC,
                    o.ESTADO, o.ESTADO_SIAF,
                    o.TOTAL_FACT_SOLES,
                    LTRIM(RTRIM(CAST(o.CONCEPTO AS VARCHAR(500)))) AS concepto,
                    o.FECHA_ORDEN,
                    LTRIM(RTRIM(c.NOMBRE_PROV))      AS proveedor_nombre,
                    LTRIM(RTRIM(c.NRO_RUC))          AS proveedor_ruc,
                    -- Recepcion de la orden: el minimo FLAG_RECEP de sus items
                    -- ('1'=pendiente, '2'=parcial, '3'=recibido completo) y la
                    -- fecha de cierre (ultima recepcion) solo si TODO se recibio.
                    -- El cierre real del pedido cuelga de aqui, no de ESTADO='7'.
                    rc.FLAG_RECEP, rc.FECHA_CIERRE,
                    STUFF((
                        SELECT ',' + t2.metodo
                        FROM todas t2 WHERE t2.NRO_ORDEN = o.NRO_ORDEN
                        FOR XML PATH('')
                    ), 1, 1, '')                     AS match_metodos
                FROM SIG_ORDEN_ADQUISICION o
                INNER JOIN (SELECT DISTINCT NRO_ORDEN FROM todas) t
                    ON t.NRO_ORDEN = o.NRO_ORDEN
                LEFT JOIN SIG_CUADRO_ADQUISICION ca_o
                    ON ca_o.ANO_EJE = o.ANO_EJE AND ca_o.SEC_EJEC = o.SEC_EJEC
                   AND ca_o.TIPO_BIEN = o.TIPO_BIEN
                   AND ca_o.SEC_CUADRO = o.SEC_CUADRO
                LEFT JOIN SIG_CONTRATISTAS c ON c.PROVEEDOR = o.PROVEEDOR
                OUTER APPLY (
                    SELECT MIN(oi.FLAG_RECEP) AS FLAG_RECEP,
                           CASE WHEN MIN(oi.FLAG_RECEP) = '3'
                                THEN MAX(oi.FECHA_RECEP) END AS FECHA_CIERRE
                    FROM SIG_ORDEN_ITEM oi
                    WHERE oi.ANO_EJE = o.ANO_EJE AND oi.SEC_EJEC = o.SEC_EJEC
                      AND oi.TIPO_BIEN = o.TIPO_BIEN AND oi.NRO_ORDEN = o.NRO_ORDEN
                ) rc
                WHERE o.ANO_EJE = :ano AND o.SEC_EJEC = :sec_ejec
                  AND o.TIPO_BIEN = :tipo
                ORDER BY o.FECHA_ORDEN
                """
            ),
            params,
        ).mappings().all()

        ordenes_list = [dict(o) for o in ordenes]

        # Con el puente resuelto, las ordenes atribuibles son las de la cadena
        # del CCMN resuelto mas las con evidencia dura de ESTE pedido (pecosa
        # del item o NRO_ORDEN declarado en el item). El match composite es
        # evidencia de la BOLSA, no del pedido: en una bolsa compartida trae
        # las ordenes de los demas candidatos (caso 286/B: asociado al 2530
        # sin orden, el composite mostraria la O/C 618 del 3472).
        if ccmn_resuelto is not None:
            def _atribuible(o: dict[str, Any]) -> bool:
                if o.get("NRO_CONS_PAAC") is not None:
                    return int(o["NRO_CONS_PAAC"]) == int(ccmn_resuelto)
                metodos = (o.get("match_metodos") or "").split(",")
                return "pecosa" in metodos or "declarado" in metodos
            ordenes_list = [o for o in ordenes_list if _atribuible(o)]

        cadena_ids = {
            "sec_cuadros": sorted({o["SEC_CUADRO"] for o in ordenes_list if o.get("SEC_CUADRO")}),
            "nro_certifs": sorted({o["NRO_CERTIFICA"] for o in ordenes_list if o.get("NRO_CERTIFICA")}),
            "exp_sigas": sorted({o["EXP_SIGA"] for o in ordenes_list if o.get("EXP_SIGA")}),
            "exp_siafs": sorted({o["EXP_SIAF"] for o in ordenes_list if o.get("EXP_SIAF")}),
        }

        cuadros: list[dict[str, Any]] = []
        if cadena_ids["sec_cuadros"]:
            binds = ", ".join(f":sc{i}" for i in range(len(cadena_ids["sec_cuadros"])))
            p = {f"sc{i}": v for i, v in enumerate(cadena_ids["sec_cuadros"])}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC, "tipo": tipo_bien})
            cuadros = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
                        SELECT ca.SEC_CUADRO, ca.TIPO_BIEN, ca.ESTADO,
                               ca.FECHA_CUADRO, ca.FECHA_AUTORIZ, ca.FECHA_COMPRA,
                               ca.VALOR_TOTAL
                        FROM SIG_CUADRO_ADQUISICION ca
                        WHERE ca.ANO_EJE = :ano AND ca.SEC_EJEC = :sec_ejec
                          AND ca.TIPO_BIEN = :tipo
                          AND ca.SEC_CUADRO IN ({binds})
                        ORDER BY ca.SEC_CUADRO
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        certificaciones: list[dict[str, Any]] = []
        if cadena_ids["nro_certifs"]:
            binds = ", ".join(f":ce{i}" for i in range(len(cadena_ids["nro_certifs"])))
            p = {f"ce{i}": v for i, v in enumerate(cadena_ids["nro_certifs"])}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC})
            certificaciones = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
                        SELECT c.NRO_CERTIFICA, c.NRO_CERTIFICA_SIAF,
                               c.ESTADO_CERTIFICA_SIAF, c.FECHA
                        FROM SIG_CERTIFICACION c
                        WHERE c.ANO_EJE = :ano AND c.SEC_EJEC = :sec_ejec
                          AND c.NRO_CERTIFICA IN ({binds})
                        ORDER BY c.NRO_CERTIFICA
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        expedientes: list[dict[str, Any]] = []
        if cadena_ids["exp_sigas"]:
            binds = ", ".join(f":es{i}" for i in range(len(cadena_ids["exp_sigas"])))
            p = {f"es{i}": v for i, v in enumerate(cadena_ids["exp_sigas"])}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC})
            expedientes = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
                        SELECT e.EXP_SIGA, e.TIPO_PPTO, e.TIPO_FASE,
                               e.EXP_SIAF, e.ESTADO_SIAF,
                               e.FECHA_EXP_SIGA, e.FECHA_DOCUMENTO, e.FECHA_SIAF,
                               -- Fecha de interfase al SIAF (compromiso). Es la
                               -- misma senal que usa el kanban: el compromiso se
                               -- hizo aunque SIAF aun no devuelva EXP_SIAF /
                               -- FECHA_SIAF (caso 1005/S). Sin esto el detalle
                               -- subcuenta la etapa 10 respecto al kanban.
                               doc.FECHA_INTERFASE
                        FROM SIG_EXP_SIGA e
                        LEFT JOIN (
                            SELECT ANO_EJE, SEC_EJEC, EXP_SIGA,
                                   MIN(FECHA_INTERFASE) AS FECHA_INTERFASE
                            FROM SIG_EXP_SIGA_DOCU
                            WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
                              AND FECHA_INTERFASE IS NOT NULL
                            GROUP BY ANO_EJE, SEC_EJEC, EXP_SIGA
                        ) doc
                            ON doc.ANO_EJE = e.ANO_EJE
                           AND doc.SEC_EJEC = e.SEC_EJEC
                           AND doc.EXP_SIGA = e.EXP_SIGA
                        WHERE e.ANO_EJE = :ano AND e.SEC_EJEC = :sec_ejec
                          AND e.EXP_SIGA IN ({binds})
                        ORDER BY e.EXP_SIGA
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        conformidades: list[dict[str, Any]] = []
        nro_ordenes = [o["NRO_ORDEN"] for o in ordenes_list]
        if nro_ordenes:
            binds = ", ".join(f":no{i}" for i in range(len(nro_ordenes)))
            p = {f"no{i}": v for i, v in enumerate(nro_ordenes)}
            p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC, "tipo": tipo_bien})
            conformidades = [
                dict(r) for r in conn.execute(
                    text(
                        f"""
                        SELECT
                            cf.NRO_ORDEN, cf.ANO_ORDEN, cf.TIPO_BIEN,
                            cf.FECHA_MOVIMTO,
                            LTRIM(RTRIM(cf.INDI_CONFOR))        AS indi_confor,
                            LTRIM(RTRIM(cf.NOMBRE_PROVEEDOR))   AS proveedor,
                            cf.ESTADO_DEVENG,
                            LTRIM(RTRIM(cf.EXPEDIENTE_SIAF))    AS exp_siaf,
                            LTRIM(RTRIM(cf.RESPONSABLE))        AS responsable,
                            LTRIM(RTRIM(CAST(cf.OBSERVACION AS VARCHAR(500)))) AS observacion
                        FROM SIG_MOVIM_CONFOR_SERVICIO cf
                        WHERE cf.ANO_ORDEN = :ano AND cf.SEC_EJEC = :sec_ejec
                          AND cf.TIPO_BIEN = :tipo
                          AND cf.NRO_ORDEN IN ({binds})
                        ORDER BY cf.FECHA_MOVIMTO DESC
                        """
                    ),
                    p,
                ).mappings().all()
            ]

        # Circuito de almacen de las ORDENES del pedido (bienes):
        #   - Recepcion: la entrada ('I') referencia NRO_ORDEN — llave dura,
        #     100% de las entradas 2026 (diagnostico_sesion6/05).
        #   - Despacho: la salida ('S') NO referencia orden; se llega por el
        #     pedido de atencion ('1') que declara la O/C en su motivo y cuyos
        #     items llevan la pecosa (declarativo, 92% de cobertura).
        movimientos_almacen: list[dict[str, Any]] = []
        if tipo_bien == "B":
            movimientos_almacen = [
                dict(r) for r in conn.execute(
                    text(
                        """
                        SELECT DISTINCT
                            ma.NRO_MOVIMTO, ma.NRO_ORDEN, ma.TIPO_MOVIMTO,
                            ma.TIPO_TRANSAC, ma.TIPO_PPTO,
                            ma.FECHA_MOVIMTO,
                            LTRIM(RTRIM(ma.NRO_GUIA))       AS nro_guia
                        FROM SIG_MOVIM_ALMACEN ma
                        INNER JOIN SIG_DETALLE_PEDIDOS dp
                            ON dp.ANO_EJE = ma.ANO_EJE AND dp.SEC_EJEC = ma.SEC_EJEC
                           AND dp.TIPO_BIEN = ma.TIPO_BIEN
                           AND dp.NRO_PECOSA = ma.NRO_MOVIMTO
                        WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                          AND dp.NRO_PEDIDO = :nro AND dp.TIPO_BIEN = :tipo
                          AND dp.TIPO_PEDIDO = :tipo_ped
                          AND dp.NRO_PECOSA > 0
                        ORDER BY ma.FECHA_MOVIMTO
                        """
                    ),
                    params,
                ).mappings().all()
            ]

            # Los items del pedido de compra ('2') NUNCA llevan pecosa: sin
            # estos puentes la ejecucion de bienes era invisible en el detalle
            # mientras el kanban (v_bolsa_avance, migracion a7e5f8c1d2b9) si
            # la veia — el mismo dato debe salir igual en ambas vistas.
            movimientos_almacen.extend(
                _movimientos_por_ordenes(conn, ano, nro_ordenes)
            )
            unicos: dict[tuple[Any, str], dict[str, Any]] = {}
            for m in movimientos_almacen:
                unicos.setdefault(
                    (m["NRO_MOVIMTO"], (m["TIPO_MOVIMTO"] or "").strip()), m
                )
            movimientos_almacen = list(unicos.values())

    # Etapas 4-7 (programacion): solo se ven por la cadena del CCMN, y este
    # `obtener_pedido` construye la cadena hacia abajo DESDE la orden. Un pedido
    # que llego al estudio de mercado pero no tiene orden aun no traeria ninguna
    # de estas etapas, y el detalle se cortaba en "cuadro de necesidad" aunque
    # el estudio de mercado ya existiera (caso 311/S). Estos flags miran la
    # cadena hacia ARRIBA, igual que el kanban, y se acotan al CCMN resuelto
    # cuando el puente resuelve.
    prog = _flags_programacion(
        ano, tipo_bien, tipo_pedido, nro_pedido, ccmn=ccmn_resuelto
    )

    # Fechas de aprobacion/atencion: la cabecera viene NULL en el 100% de los
    # pedidos de compra; se completan desde el seguimiento. El VB del jefe solo
    # cuenta como aprobacion si la cabecera ya dice aprobado/cerrado.
    estado_cab = str(cab["estado_pedido"] or "").strip()
    fecha_aprob = cab["FECHA_APROB"]
    if fecha_aprob is None and estado_cab in ("1", "7"):
        fecha_aprob = (
            seguimiento.get("fecha_aprob_seg") or seguimiento.get("fecha_vb_jefe")
        )
    fecha_atenc = cab["FECHA_ATENC"] or seguimiento.get("fecha_atendido_seg")

    return {
        **dict(cab),
        **prog,
        **seguimiento,
        "FECHA_APROB": fecha_aprob,
        "FECHA_ATENC": fecha_atenc,
        "n_candidatos_ccmn": len(candidatos),
        "ccmn_candidatos": candidatos,
        "ccmn_declarado_orden": ctx.get("ccmn_declarado_orden"),
        "ccmn_declarado_cert": ctx.get("ccmn_declarado_cert"),
        "ccmn_manual": ccmn_manual,
        "sec_cua_mod_sal": (ctx.get("bolsas") or [None])[0],
        "items": [dict(i) for i in items],
        "ordenes": ordenes_list,
        "cuadros": cuadros,
        "certificaciones": certificaciones,
        "expedientes": expedientes,
        "conformidades": conformidades,
        "movimientos_almacen": movimientos_almacen,
    }


def _movimientos_por_ordenes(
    conn: Any, ano: int, nro_ordenes: list[Any]
) -> list[dict[str, Any]]:
    """Movimientos de almacen de las O/C dadas (recepcion y despacho).

    Entradas ('I') por llave dura NRO_ORDEN; salidas ('S') via el pedido de
    atencion ('1') que declara la O/C en su motivo (RE_OC). Es el equivalente
    en caliente de los laterales `alm`/`pec` de v_bolsa_avance (a7e5f8c1d2b9).
    """
    ordenes = {int(o) for o in nro_ordenes if o is not None}
    if not ordenes:
        return []

    out: list[dict[str, Any]] = []
    binds = ", ".join(f":oc{i}" for i in range(len(ordenes)))
    p: dict[str, Any] = {f"oc{i}": v for i, v in enumerate(sorted(ordenes))}
    p.update({"ano": ano, "sec_ejec": settings.SEC_EJEC})

    out.extend(
        dict(r) for r in conn.execute(
            text(
                f"""
                SELECT DISTINCT
                    ma.NRO_MOVIMTO, ma.NRO_ORDEN, ma.TIPO_MOVIMTO,
                    ma.TIPO_TRANSAC, ma.TIPO_PPTO, ma.FECHA_MOVIMTO,
                    LTRIM(RTRIM(ma.NRO_GUIA)) AS nro_guia
                FROM SIG_MOVIM_ALMACEN ma
                WHERE ma.ANO_EJE = :ano AND ma.SEC_EJEC = :sec_ejec
                  AND ma.TIPO_MOVIMTO = 'I' AND ma.TIPO_TRANSAC = 1
                  AND ma.NRO_ORDEN IN ({binds})
                """
            ),
            p,
        ).mappings().all()
    )

    # Pedidos de atencion que declaran alguna de estas O/C. El parseo del
    # motivo se hace en Python (regex validado), no en T-SQL.
    atenciones = conn.execute(
        text(
            """
            SELECT NRO_PEDIDO, CAST(MOTIVO_PEDIDO AS VARCHAR(300)) AS MOTIVO
            FROM SIG_PEDIDOS
            WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec
              AND TIPO_BIEN = 'B' AND TIPO_PEDIDO = '1'
            """
        ),
        {"ano": ano, "sec_ejec": settings.SEC_EJEC},
    ).mappings().all()
    ped_atencion = sorted({
        int(a["NRO_PEDIDO"])
        for a in atenciones
        if parsear_nro_oc(a["MOTIVO"]) in ordenes
    })
    if not ped_atencion:
        return out

    binds_pa = ", ".join(f":pa{i}" for i in range(len(ped_atencion)))
    p2: dict[str, Any] = {f"pa{i}": v for i, v in enumerate(ped_atencion)}
    p2.update({"ano": ano, "sec_ejec": settings.SEC_EJEC})
    out.extend(
        dict(r) for r in conn.execute(
            text(
                f"""
                SELECT DISTINCT
                    ma.NRO_MOVIMTO, ma.NRO_ORDEN, ma.TIPO_MOVIMTO,
                    ma.TIPO_TRANSAC, ma.TIPO_PPTO, ma.FECHA_MOVIMTO,
                    LTRIM(RTRIM(ma.NRO_GUIA)) AS nro_guia
                FROM SIG_MOVIM_ALMACEN ma
                INNER JOIN SIG_DETALLE_PEDIDOS dp
                    ON dp.ANO_EJE = ma.ANO_EJE AND dp.SEC_EJEC = ma.SEC_EJEC
                   AND dp.NRO_PECOSA = ma.NRO_MOVIMTO
                WHERE dp.ANO_EJE = :ano AND dp.SEC_EJEC = :sec_ejec
                  AND dp.TIPO_BIEN = 'B' AND dp.TIPO_PEDIDO = '1'
                  AND dp.NRO_PEDIDO IN ({binds_pa}) AND dp.NRO_PECOSA > 0
                  AND ma.TIPO_MOVIMTO = 'S' AND ma.TIPO_TRANSAC = 1
                """
            ),
            p2,
        ).mappings().all()
    )
    return out
