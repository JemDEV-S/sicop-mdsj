"""Repositorio SIGA: saldos presupuestales (`SIG_TECHO_PRESUPUESTO`).

Fuente para PIM/certificado/comprometido a nivel meta (§18.2, §18.3 del
diccionario). Todas las queries fijan SEC_EJEC=300687 y filtran por
centros_costo del usuario cuando aplica (RN-04 filtro por CC).

`SIG_TECHO_PRESUPUESTO` tiene PK compuesta `ANO_EJE + SEC_EJEC + sec_func +
CLASIFICADOR + CENTRO_COSTO`.

Hallazgos empíricos (2026-07-16, ver backend/scripts/diagnostico_cruce_mef_siga.py):

  1. **264 filas con SEC_FUNC IS NULL en 2026** — S/ 116.6M de PIM cargado a
     nivel de pliego (canon, impuestos, FONCOMUN) que aún no se ha desagregado
     a metas ejecutables. Se **excluyen** de las agregaciones para que el PIM
     y % de ejecución del widget reflejen "lo asignado a metas" y no infle.
     Estas filas tienen PPTO_DISP_SIAF=0 (no aparecen en la ejecución SIAF).

  2. **MNTO_ACUM_DEVGDO_SIGA = 0** en 2026 (columna no poblada por el SIGA de
     la muni). Antes usábamos `PPTO_MODIF - PPTO_DISP_SIAF` como proxy, pero
     ese proxy incluye el techo huérfano y sobreestima brutalmente (S/ 92M
     vs. S/ 31M reales). Ahora reportamos:
       - certificado (mnto_acum_cert) — S/ ~15.8M
       - comprometido (mnto_acum_coma) — S/ ~12.9M
     Y el widget usa el snapshot MEF (siaf.ejecucion_presupuestal) para el
     devengado oficial que sí cuadra con el portal público.

  3. El PIM SIGA (asignado a metas) = S/ 46.7M vs. PIM MEF = S/ 69.5M. La
     diferencia (S/ 22.8M) son fuentes cargadas en el SIAF pero aún no en el
     SIGA — es un lag operativo de la muni, no un bug del código.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection


def _predicado_cc_detalle(
    centros: list[str] | None, params: dict[str, Any]
) -> str | None:
    """Predicado de CC para el DETALLE de UNA meta (cabecera + desglose).

    A diferencia del LISTADO (que decide elegibilidad de meta con `CENTRO_COSTO
    IN (...)` estricto), el detalle de una meta ya elegible debe mostrar TODAS
    sus líneas, incluidas las de `CENTRO_COSTO IS NULL` (presupuesto de la meta a
    nivel cabecera, no desagregado a una dependencia). Ver bug meta 57: la mitad
    del PIM vive en filas de CC nulo y quedaba oculto al usuario con alcance.

    Seguridad: los nulos se incluyen SOLO si la meta tiene al menos una línea de
    un CC del alcance del usuario (`EXISTS`). Así una meta ajena que solo tenga
    líneas de CC nulo NO se filtra (evita fuga: hay 164 metas con CC nulo sin
    línea del usuario). Admin (`centros=None`) no filtra nada.

    Muta `params` con los binds `:ccd0, :ccd1, ...`. Devuelve el fragmento SQL o
    `None` si no hay que filtrar (admin).
    """
    if centros is None:
        return None
    binds = [f":ccd{i}" for i in range(len(centros))]
    for i, c in enumerate(centros):
        params[f"ccd{i}"] = c
    in_list = ", ".join(binds)
    # La subconsulta EXISTS confirma que la meta tiene alguna línea del alcance
    # del usuario antes de dejar pasar las líneas de CC nulo de esa misma meta.
    return (
        f"(t.CENTRO_COSTO IN ({in_list}) OR (t.CENTRO_COSTO IS NULL AND EXISTS ("
        f"  SELECT 1 FROM SIG_TECHO_PRESUPUESTO t2"
        f"   WHERE t2.ANO_EJE = t.ANO_EJE AND t2.SEC_EJEC = t.SEC_EJEC"
        f"     AND t2.sec_func = t.sec_func"
        f"     AND t2.CENTRO_COSTO IN ({in_list}))))"
    )


def listar_saldos(
    ano: int,
    centros: list[str] | None = None,
    *,
    sec_func: int | None = None,
    clasificador: str | None = None,
    fuente_financ: str | None = None,
    solo_con_pim: bool = True,
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Devuelve saldos SIGA agregados **por meta** (`sec_func`).

    Una meta tiene ~9.6 filas en SIG_TECHO_PRESUPUESTO (clasificador × CC). Se
    agrega por `sec_func` para que:
      1. cada fila sea una meta (misma granularidad que resumen/metas_rezagadas
         y que el portal público);
      2. el bloque MEF por meta (que el service adjunta luego) no se multiplique
         por el número de clasificadores/CC. Ver
         Docs/consolidacion-backend-presupuestal.md (Iteración 2).

    Solo devuelve montos SIGA operativos: `certificado` y `comprometido` con sus
    nombres propios (fases previas). **No devuelve "devengado"** — el devengado
    real, único y oficial, lo adjunta el service desde el snapshot MEF.

    `clasificador`/`fuente_financ` filtran a nivel meta (incluye la meta si
    tiene al menos una fila con ese clasificador/fuente), no fragmentan la fila.

    `centros=None` = admin (sin filtro). `centros=[]` = usuario sin CC asignado
    (devuelve vacio).
    """
    if centros is not None and len(centros) == 0:
        return []

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        # Excluye ~264 filas de "techo del pliego sin desagregar a meta"
        # que inflan artificialmente el PIM (S/ 116M en 2026). Ver
        # diagnostico_cruce_mef_siga.py.
        "t.SEC_FUNC IS NOT NULL",
    ]
    params: dict[str, Any] = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
    }
    if solo_con_pim:
        where.append("t.PPTO_MODIF > 0")
    if sec_func is not None:
        where.append("t.sec_func = :sec_func")
        params["sec_func"] = sec_func
    if clasificador is not None:
        where.append("t.CLASIFICADOR = :clasificador")
        params["clasificador"] = clasificador
    if fuente_financ is not None:
        where.append("t.FUENTE_FINANC = :fuente")
        params["fuente"] = fuente_financ
    if centros is not None:
        # Bindeamos cada CC como :cc0, :cc1, ... porque SQL Server con pyodbc
        # no admite tuplas directas.
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"t.CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    sql = f"""
        SELECT
            t.sec_func,
            LTRIM(RTRIM(MAX(m.nombre)))                     AS nombre_meta,
            LTRIM(RTRIM(MAX(m.act_proy)))                   AS act_proy,
            COALESCE(SUM(t.PPTO_PIA), 0)                    AS pia,
            COALESCE(SUM(t.PPTO_MODIF), 0)                  AS pim,
            -- Fases previas SIGA, con su nombre propio (NO son devengado).
            COALESCE(SUM(t.mnto_acum_cert), 0)              AS certificado,
            COALESCE(SUM(t.mnto_acum_coma), 0)              AS comprometido_anual,
            COALESCE(SUM(t.mnto_acum_comm), 0)              AS comprometido_mensual,
            COALESCE(SUM(t.PPTO_DISP_SIAF), 0)              AS saldo_disponible,
            COALESCE(SUM(t.MNTO_RESERVA_PEDIDO), 0)         AS reservado_pedido,
            COUNT(*)                                        AS filas_clasificador
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        WHERE {" AND ".join(where)}
        GROUP BY t.sec_func
        ORDER BY SUM(t.PPTO_MODIF) DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    params["limit"] = limit
    params["offset"] = offset

    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def contar_saldos(
    ano: int,
    centros: list[str] | None = None,
    *,
    solo_con_pim: bool = True,
) -> int:
    """COUNT(*) para paginacion."""
    if centros is not None and len(centros) == 0:
        return 0

    where = [
        "ANO_EJE = :ano",
        "SEC_EJEC = :sec_ejec",
        "SEC_FUNC IS NOT NULL",  # Excluir techo del pliego sin desagregar.
    ]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    if solo_con_pim:
        where.append("PPTO_MODIF > 0")
    if centros is not None:
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    # La lista es por meta → contamos metas distintas, no filas clasificador×CC.
    sql = (
        "SELECT COUNT(DISTINCT sec_func) FROM SIG_TECHO_PRESUPUESTO "
        f"WHERE {' AND '.join(where)}"
    )
    with get_connection() as conn:
        return int(conn.execute(text(sql), params).scalar_one())


def resumen_saldos(
    ano: int,
    centros: list[str] | None = None,
) -> dict[str, Any]:
    """Agrega totales SIGA operativos por meta para el dashboard T-44.

    Devuelve los montos SIGA crudos (PIM, certificado, comprometido, saldo
    disponible, reservado) y la lista de metas candidatas con su PIM+cert+compr.
    **No calcula devengado ni % ni criticidad** — eso lo hace el service con el
    devengado MEF real (una meta "crítica" es la que tiene bajo % devengado
    OFICIAL, no bajo cert+compr). Ver Docs/consolidacion-backend-presupuestal.md
    (Iteración 2).
    """
    if centros is not None and len(centros) == 0:
        return {
            "pia": 0, "pim": 0, "certificado": 0, "comprometido": 0,
            "saldo_disponible": 0, "reservado_pedido": 0,
            "metas_total": 0, "metas": [],
        }

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        "t.PPTO_MODIF > 0",
        "t.SEC_FUNC IS NOT NULL",  # Excluir techo del pliego sin desagregar.
    ]
    params: dict[str, Any] = {"ano": ano, "sec_ejec": settings.SEC_EJEC}
    if centros is not None:
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"t.CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    where_sql = " AND ".join(where)

    sql_totales = f"""
        SELECT
            COALESCE(SUM(t.PPTO_PIA), 0)                    AS pia,
            COALESCE(SUM(t.PPTO_MODIF), 0)                  AS pim,
            COALESCE(SUM(t.mnto_acum_cert), 0)              AS certificado,
            COALESCE(SUM(t.mnto_acum_coma), 0)              AS comprometido,
            COALESCE(SUM(t.PPTO_DISP_SIAF), 0)              AS saldo_disponible,
            COALESCE(SUM(t.MNTO_RESERVA_PEDIDO), 0)         AS reservado_pedido,
            COUNT(DISTINCT t.sec_func)                      AS metas_total
        FROM SIG_TECHO_PRESUPUESTO t
        WHERE {where_sql}
    """

    # Todas las metas candidatas con su PIM + cert/compr SIGA. El service las
    # cruza con MEF, calcula el % devengado real y elige las críticas.
    sql_metas = f"""
        SELECT
            t.sec_func,
            LTRIM(RTRIM(MAX(m.nombre)))                     AS nombre_meta,
            SUM(COALESCE(t.PPTO_MODIF, 0))                  AS pim,
            SUM(COALESCE(t.mnto_acum_cert, 0))              AS certificado,
            SUM(COALESCE(t.mnto_acum_coma, 0))              AS comprometido
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        WHERE {where_sql}
        GROUP BY t.sec_func
        ORDER BY SUM(t.PPTO_MODIF) DESC
    """

    with get_connection() as conn:
        totales = dict(conn.execute(text(sql_totales), params).mappings().one())
        metas = [dict(r) for r in conn.execute(text(sql_metas), params).mappings().all()]

    totales["metas"] = metas
    return totales


def detalle_meta_jerarquico(
    ano: int,
    sec_func: int,
    centros: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Composición operativa SIGA de UNA meta: fuente × clasificador × CC.

    Devuelve una fila por combinación `FUENTE_FINANC × CLASIFICADOR`, con nombres
    legibles (fuente y clasificador). El service la arma en árbol
    Fuente → Clasificadores.

    **Muestra TODOS los clasificadores**, incluidos los de PIM 0 (líneas del plan
    sin techo activo o residuales): un clasificador con PIM 0 sigue siendo
    información para el funcionario (puede tener certificado/compromiso histórico
    o quedar como línea prevista). El filtro `PPTO_MODIF > 0` que antes los ocultaba
    causaba el bug de la meta 57 (mostraba 7 de 12 clasificadores).

    Solo montos SIGA operativos (detalle del gasto, NO presupuesto): el presupuesto
    oficial es del SIAF/MEF y no se desagrega a este nivel.
    """
    if centros is not None and len(centros) == 0:
        return []

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        "t.sec_func = :sec_func",
        "t.CLASIFICADOR IS NOT NULL",  # descarta filas sin clasificar (ruido)
    ]
    params: dict[str, Any] = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "sec_func": sec_func,
    }
    # Detalle de meta elegible: incluye las líneas de CC nulo de ESTA meta
    # (presupuesto de cabecera) además de las del CC del usuario. Ver
    # _predicado_cc_detalle y el bug de la meta 57.
    pred_cc = _predicado_cc_detalle(centros, params)
    if pred_cc is not None:
        where.append(pred_cc)

    sql = f"""
        SELECT
            t.FUENTE_FINANC                            AS fuente_codigo,
            LTRIM(RTRIM(MAX(ff.nombre)))               AS fuente_nombre,
            t.CLASIFICADOR                             AS codigo,
            LTRIM(RTRIM(MAX(cg.NOMBRE_CLASIF)))        AS nombre,
            COALESCE(SUM(t.PPTO_PIA), 0)               AS pia,
            COALESCE(SUM(t.PPTO_MODIF), 0)             AS pim,
            COALESCE(SUM(t.mnto_acum_cert), 0)         AS certificado,
            COALESCE(SUM(t.mnto_acum_coma), 0)         AS comprometido,
            COALESCE(SUM(t.PPTO_DISP_SIAF), 0)         AS saldo_disponible,
            COALESCE(SUM(t.MNTO_RESERVA_PEDIDO), 0)    AS reservado_pedido,
            COUNT(*)                                   AS filas
        FROM SIG_TECHO_PRESUPUESTO t
        LEFT JOIN FUENTE_FINANC ff
            ON ff.FUENTE_FINANC = t.FUENTE_FINANC AND ff.ANO_EJE = t.ANO_EJE
            AND ff.ORIGEN = t.ORIGEN
        LEFT JOIN SIG_CLASIFICADOR_GASTO cg
            ON cg.CLASIFICADOR = t.CLASIFICADOR AND cg.ANO_EJE = t.ANO_EJE
        WHERE {" AND ".join(where)}
        GROUP BY t.FUENTE_FINANC, t.CLASIFICADOR
        ORDER BY t.FUENTE_FINANC, SUM(t.PPTO_MODIF) DESC
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def cabecera_meta(
    ano: int,
    sec_func: int,
    centros: list[str] | None = None,
) -> dict[str, Any] | None:
    """Totales SIGA de una meta + su nombre, para la cabecera del detalle.

    Devuelve `None` si la meta no existe / no es visible para el usuario. Los
    montos son la suma sobre las líneas visibles (mismo alcance que el desglose).
    """
    if centros is not None and len(centros) == 0:
        return None

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        "t.sec_func = :sec_func",
        "t.PPTO_MODIF > 0",
    ]
    params: dict[str, Any] = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
        "sec_func": sec_func,
    }
    # Misma regla que el desglose: la cabecera de una meta elegible suma también
    # sus líneas de CC nulo (coherencia KPI ↔ detalle). Ver _predicado_cc_detalle.
    pred_cc = _predicado_cc_detalle(centros, params)
    if pred_cc is not None:
        where.append(pred_cc)

    sql = f"""
        SELECT
            t.sec_func,
            LTRIM(RTRIM(MAX(m.nombre)))                AS nombre_meta,
            LTRIM(RTRIM(MAX(m.act_proy)))              AS act_proy,
            COALESCE(SUM(t.PPTO_PIA), 0)               AS pia,
            COALESCE(SUM(t.PPTO_MODIF), 0)             AS pim,
            COALESCE(SUM(t.mnto_acum_cert), 0)         AS certificado,
            COALESCE(SUM(t.mnto_acum_coma), 0)         AS comprometido,
            COALESCE(SUM(t.PPTO_DISP_SIAF), 0)         AS saldo_disponible,
            COALESCE(SUM(t.MNTO_RESERVA_PEDIDO), 0)    AS reservado_pedido,
            COUNT(*)                                   AS filas_clasificador,
            COUNT(DISTINCT t.CLASIFICADOR)             AS n_clasificadores,
            COUNT(DISTINCT t.FUENTE_FINANC)            AS n_fuentes
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        WHERE {" AND ".join(where)}
        GROUP BY t.sec_func
    """
    with get_connection() as conn:
        row = conn.execute(text(sql), params).mappings().one_or_none()
    return dict(row) if row else None


def metas_con_saldo(
    ano: int,
    centros: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Todas las metas con PIM > 0 y sus montos SIGA operativos, por meta.

    Base para HU-16 (metas rezagadas): el filtro por umbral de % devengado lo
    aplica el service usando el devengado MEF real (no cert+compr). Aquí solo
    entregamos PIM + cert + compr agregados por `sec_func`. Ver
    Docs/consolidacion-backend-presupuestal.md (Iteración 2).

    Agrega por sec_func (una meta tiene varias filas por clasificador/CC).
    """
    if centros is not None and len(centros) == 0:
        return []

    where = [
        "t.ANO_EJE = :ano",
        "t.SEC_EJEC = :sec_ejec",
        "t.PPTO_MODIF > 0",
        "t.SEC_FUNC IS NOT NULL",  # Excluir techo del pliego sin desagregar.
    ]
    params: dict[str, Any] = {
        "ano": ano,
        "sec_ejec": settings.SEC_EJEC,
    }
    if centros is not None:
        binds = [f":cc{i}" for i in range(len(centros))]
        where.append(f"t.CENTRO_COSTO IN ({', '.join(binds)})")
        for i, c in enumerate(centros):
            params[f"cc{i}"] = c

    sql = f"""
        SELECT
            t.sec_func,
            LTRIM(RTRIM(MAX(m.nombre)))                AS nombre_meta,
            LTRIM(RTRIM(MAX(m.act_proy)))              AS act_proy,
            SUM(COALESCE(t.PPTO_MODIF, 0))             AS pim,
            SUM(COALESCE(t.mnto_acum_cert, 0))         AS certificado,
            SUM(COALESCE(t.mnto_acum_coma, 0))         AS comprometido
        FROM SIG_TECHO_PRESUPUESTO t
        INNER JOIN META m
            ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
        WHERE {" AND ".join(where)}
        GROUP BY t.sec_func
        ORDER BY SUM(t.PPTO_MODIF) DESC
    """
    with get_connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]
