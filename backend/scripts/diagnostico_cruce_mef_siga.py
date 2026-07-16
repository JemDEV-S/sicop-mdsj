"""Diagnóstico del desalineamiento entre widgets internos (SIGA) y portal MEF.

Contraste observado (2026-07-16):

    Métrica                MEF (portal amigable)   Widget interno (SIGA)
    -------                --------------------   ---------------------
    PIM total              S/ 69,500,489          S/ 163,255,720   ← 2.35×
    Ejecución total        S/ 31,135,921 (44.8%)  S/ 91,981,282 (56.3%)
    Pedidos estancados     —                       1335 (esperado <8)

Responde 3 preguntas empíricas:

  A. PIM inflado — ¿SUM(PPTO_MODIF) suma filas duplicadas?
     - Filas totales vs. metas distintas en SIG_TECHO_PRESUPUESTO.
     - PIM sumando todo vs. PIM por meta única.

  B. Devengado — el proxy "PIM - DISP_SIAF" sobreestima.
     - Comparar techo (proxy) vs. SIG_DEVENGADO_ITEM_PPTO (autoritativo)
       vs. compromiso (mnto_acum_coma) vs. certificado (mnto_acum_cert).
     - Detectar si el proxy = certificado + comprometido + devengado.

  C. Estancados — analizar por qué son 1335 en lugar de ~8.
     - Distribución por (etapa, ¿fecha_etapa disponible?).
     - Cuántos caen a FECHA_APROB como último recurso (etapa sin fecha propia).
     - Cuántos serían estancados si excluyéramos TIPO_PEDIDO='I' + ESTADO='7'.

Correr:
    docker exec sicop_backend_dev python -m scripts.diagnostico_cruce_mef_siga
"""

from __future__ import annotations

import sys
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection

ANO = settings.ANO_VIGENTE
SEC_EJEC = settings.SEC_EJEC


def _print_rows(rows: list[dict[str, Any]], titulo: str, max_col_width: int = 18) -> None:
    print(f"\n── {titulo} " + "─" * max(4, 78 - len(titulo)))
    if not rows:
        print("  (sin resultados)")
        return
    cols = list(rows[0].keys())
    header = " | ".join(c.rjust(max_col_width) for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        print(" | ".join(str(r[c])[:max_col_width].rjust(max_col_width) for c in cols))


def diagnostico_a_pim(conn: Any) -> None:
    print("\n" + "=" * 80)
    print("A. PIM INFLADO — ¿SUM(PPTO_MODIF) suma filas duplicadas?")
    print("=" * 80)

    # A.1 — Conteo global de filas del techo
    r = conn.execute(
        text(
            """
            SELECT
                COUNT(*)                                          AS filas_totales,
                COUNT(DISTINCT t.SEC_FUNC)                        AS metas_distintas,
                COUNT(DISTINCT t.CLASIFICADOR)                    AS clasificadores,
                COUNT(DISTINCT t.CENTRO_COSTO)                    AS centros_costo,
                COUNT(DISTINCT t.FUENTE_FINANC)                   AS fuentes_financ,
                SUM(t.PPTO_PIA)                                   AS pia_sumado,
                SUM(t.PPTO_MODIF)                                 AS pim_sumado,
                SUM(t.PPTO_DISP_SIAF)                             AS saldo_sumado
            FROM SIG_TECHO_PRESUPUESTO t
            WHERE t.ANO_EJE = :ano AND t.SEC_EJEC = :sec_ejec
              AND t.PPTO_MODIF > 0
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().one()
    print("\n  A.1 Universo del techo (año {}) con PPTO_MODIF > 0:".format(ANO))
    print(f"    · Filas totales:      {r['filas_totales']:>10,}")
    print(f"    · Metas distintas:    {r['metas_distintas']:>10,}")
    print(f"    · Clasificadores:     {r['clasificadores']:>10,}")
    print(f"    · Centros de costo:   {r['centros_costo']:>10,}")
    print(f"    · Fuentes financ.:    {r['fuentes_financ']:>10,}")
    print(f"    · PIA sumado (todo):  S/ {float(r['pia_sumado'] or 0):>16,.2f}")
    print(f"    · PIM sumado (todo):  S/ {float(r['pim_sumado'] or 0):>16,.2f}")
    print(f"    · Saldo disponible:   S/ {float(r['saldo_sumado'] or 0):>16,.2f}")

    # A.2 — Distribución de filas por meta (¿cuántas filas por sec_func?)
    rows = conn.execute(
        text(
            """
            SELECT
                filas_por_meta,
                COUNT(*) AS metas,
                SUM(pim_meta) AS pim_total
            FROM (
                SELECT
                    t.SEC_FUNC,
                    COUNT(*) AS filas_por_meta,
                    SUM(t.PPTO_MODIF) AS pim_meta
                FROM SIG_TECHO_PRESUPUESTO t
                WHERE t.ANO_EJE = :ano AND t.SEC_EJEC = :sec_ejec
                  AND t.PPTO_MODIF > 0
                GROUP BY t.SEC_FUNC
            ) x
            GROUP BY filas_por_meta
            ORDER BY filas_por_meta
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().all()
    _print_rows([dict(r) for r in rows], "A.2 Cuántas filas del techo tiene cada meta")

    # A.3 — Comparación crítica: PIM al nivel FILA vs. al nivel META
    r = conn.execute(
        text(
            """
            SELECT
                (SELECT SUM(t.PPTO_MODIF)
                 FROM SIG_TECHO_PRESUPUESTO t
                 WHERE t.ANO_EJE=:ano AND t.SEC_EJEC=:sec_ejec AND t.PPTO_MODIF>0)  AS pim_sum_filas,
                (SELECT SUM(pim_meta)
                 FROM (SELECT SUM(t.PPTO_MODIF) AS pim_meta
                       FROM SIG_TECHO_PRESUPUESTO t
                       WHERE t.ANO_EJE=:ano AND t.SEC_EJEC=:sec_ejec AND t.PPTO_MODIF>0
                       GROUP BY t.SEC_FUNC) x)                                        AS pim_agrupado_meta,
                (SELECT SUM(pim_max)
                 FROM (SELECT MAX(t.PPTO_MODIF) AS pim_max
                       FROM SIG_TECHO_PRESUPUESTO t
                       WHERE t.ANO_EJE=:ano AND t.SEC_EJEC=:sec_ejec AND t.PPTO_MODIF>0
                       GROUP BY t.SEC_FUNC) x)                                        AS pim_max_por_meta
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().one()
    print("\n  A.3 Comparación PIM según nivel de agregación:")
    print(f"    · SUM(PPTO_MODIF) sobre TODAS las filas:       S/ {float(r['pim_sum_filas']):>16,.2f}")
    print(f"    · SUM por meta (SUM interno, SUM externo):     S/ {float(r['pim_agrupado_meta']):>16,.2f}")
    print(f"    · SUM(MAX por meta) — 1 fila máx por sec_func: S/ {float(r['pim_max_por_meta']):>16,.2f}")
    print(f"\n    → MEF muestra PIM = S/ 69,500,489. ¿Qué agregación se acerca?")

    # A.4 — Muestra de metas top con muchas filas
    rows = conn.execute(
        text(
            """
            SELECT TOP 10
                t.SEC_FUNC,
                LTRIM(RTRIM(m.nombre))          AS nombre_meta,
                COUNT(*)                        AS filas,
                COUNT(DISTINCT t.CLASIFICADOR)  AS clasif,
                COUNT(DISTINCT t.CENTRO_COSTO)  AS cc,
                COUNT(DISTINCT t.FUENTE_FINANC) AS fte,
                SUM(t.PPTO_MODIF)               AS pim_sumado,
                MAX(t.PPTO_MODIF)               AS pim_max
            FROM SIG_TECHO_PRESUPUESTO t
            INNER JOIN META m
                ON t.SEC_FUNC = m.sec_func AND t.ANO_EJE = m.ano_eje
            WHERE t.ANO_EJE = :ano AND t.SEC_EJEC = :sec_ejec
              AND t.PPTO_MODIF > 0
            GROUP BY t.SEC_FUNC, m.nombre
            ORDER BY COUNT(*) DESC
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().all()
    _print_rows(
        [
            {
                "sec_func": r["SEC_FUNC"],
                "meta": (r["nombre_meta"] or "")[:20],
                "filas": r["filas"],
                "clasif": r["clasif"],
                "cc": r["cc"],
                "fte": r["fte"],
                "pim_sum": f"{float(r['pim_sumado']):,.0f}",
                "pim_max": f"{float(r['pim_max']):,.0f}",
            }
            for r in rows
        ],
        "A.4 Top 10 metas con más filas en el techo",
        max_col_width=14,
    )


def diagnostico_b_devengado(conn: Any) -> None:
    print("\n" + "=" * 80)
    print("B. DEVENGADO — proxy vs. fuentes autoritativas")
    print("=" * 80)

    # B.1 — 5 componentes del techo, año completo
    r = conn.execute(
        text(
            """
            SELECT
                SUM(t.PPTO_PIA)                       AS pia,
                SUM(t.PPTO_MODIF)                     AS pim,
                SUM(t.mnto_acum_cert)                 AS certificado,
                SUM(t.mnto_acum_coma)                 AS comprometido_anual,
                SUM(t.mnto_acum_comm)                 AS comprometido_mensual,
                SUM(t.MNTO_ACUM_DEVGDO_SIGA)          AS devengado_siga,
                SUM(t.MNTO_ACUM_DEVGDO_SIAF)          AS devengado_siaf,
                SUM(t.PPTO_DISP_SIAF)                 AS saldo_disponible,
                SUM(t.MNTO_RESERVA_PEDIDO)            AS reservado_pedido,
                SUM(t.PPTO_MODIF - t.PPTO_DISP_SIAF)  AS proxy_ejecutado
            FROM SIG_TECHO_PRESUPUESTO t
            WHERE t.ANO_EJE = :ano AND t.SEC_EJEC = :sec_ejec
              AND t.PPTO_MODIF > 0
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().one()

    print(f"\n  B.1 Componentes del techo {ANO} (SUM sobre todas las filas con PIM>0):")
    print(f"    · PIA                                    S/ {float(r['pia'] or 0):>16,.2f}")
    print(f"    · PIM (PPTO_MODIF)                       S/ {float(r['pim'] or 0):>16,.2f}")
    print(f"    · Certificado (mnto_acum_cert)           S/ {float(r['certificado'] or 0):>16,.2f}")
    print(f"    · Comprometido anual (mnto_acum_coma)    S/ {float(r['comprometido_anual'] or 0):>16,.2f}")
    print(f"    · Comprometido mensual (mnto_acum_comm)  S/ {float(r['comprometido_mensual'] or 0):>16,.2f}")
    print(f"    · Devengado SIGA (MNTO_ACUM_DEVGDO_SIGA) S/ {float(r['devengado_siga'] or 0):>16,.2f}")
    print(f"    · Devengado SIAF (MNTO_ACUM_DEVGDO_SIAF) S/ {float(r['devengado_siaf'] or 0):>16,.2f}")
    print(f"    · Saldo disponible (PPTO_DISP_SIAF)      S/ {float(r['saldo_disponible'] or 0):>16,.2f}")
    print(f"    · Reservado por pedido                   S/ {float(r['reservado_pedido'] or 0):>16,.2f}")
    print(f"    · PROXY 'Ejecutado' (PIM - saldo)        S/ {float(r['proxy_ejecutado'] or 0):>16,.2f}")

    # B.2 — Descomposición: ¿el proxy = cert + comp + dev?
    print("\n  B.2 ¿El proxy encaja con cert + comp + dev?")
    proxy = float(r['proxy_ejecutado'] or 0)
    cert = float(r['certificado'] or 0)
    coma = float(r['comprometido_anual'] or 0)
    dev = float(r['devengado_siga'] or 0)
    print(f"    · proxy                    = S/ {proxy:>16,.2f}")
    print(f"    · cert + coma + dev_siga   = S/ {cert + coma + dev:>16,.2f}   (diff: {proxy - (cert + coma + dev):>+16,.2f})")
    print(f"    · cert + coma              = S/ {cert + coma:>16,.2f}   (diff: {proxy - (cert + coma):>+16,.2f})")
    print(f"    · coma solo                = S/ {coma:>16,.2f}   (diff: {proxy - coma:>+16,.2f})")

    # B.3 — Devengado autoritativo: SIG_DEVENGADO_ITEM_PPTO
    r = conn.execute(
        text(
            """
            SELECT
                COUNT(DISTINCT dip.NRO_DEVENGADO)   AS n_devengados,
                COUNT(*)                            AS n_items,
                SUM(dip.VALOR_SOLES)                AS devengado_items,
                MIN(d.FECHA_REG)                    AS primer_devengado,
                MAX(d.FECHA_REG)                    AS ultimo_devengado
            FROM SIG_DEVENGADO_ITEM_PPTO dip
            INNER JOIN SIG_DEVENGADO d
                ON d.ANO_EJE = dip.ANO_EJE AND d.SEC_EJEC = dip.SEC_EJEC
               AND d.NRO_DEVENGADO = dip.NRO_DEVENGADO
            WHERE dip.ANO_EJE = :ano AND dip.SEC_EJEC = :sec_ejec
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().one()
    print(f"\n  B.3 SIG_DEVENGADO_ITEM_PPTO (registro autoritativo del devengado):")
    print(f"    · N° devengados:            {r['n_devengados']}")
    print(f"    · N° items:                 {r['n_items']}")
    print(f"    · Suma VALOR_SOLES:         S/ {float(r['devengado_items'] or 0):>16,.2f}")
    print(f"    · Primer devengado:         {r['primer_devengado']}")
    print(f"    · Último devengado:         {r['ultimo_devengado']}")
    print(f"\n  → MEF muestra devengado total = S/ 31,135,921 (44.8%)")
    print(f"    Widget muestra ejecutado (proxy) = S/ 91,981,282 (56.3%) ← infla")


def diagnostico_c_estancados(conn: Any) -> None:
    print("\n" + "=" * 80)
    print("C. ESTANCADOS — ¿por qué son 1335 en lugar de <8?")
    print("=" * 80)

    # Este diagnóstico necesita correr la lógica de clasificación en Python,
    # así que replicamos el pipeline_service._enriquecer aquí a alto nivel.
    from app.repositories import pipeline_repo
    from app.services import pipeline_service
    from datetime import date

    raw = pipeline_repo.pipeline_pedidos_raw(ANO, None)
    print(f"\n  C.0 Universo: {len(raw)} pedidos {ANO}")

    hoy = date.today()
    # Simulamos ambos umbrales para el diagnóstico:
    #   - Antes: 15 días fijo.
    #   - Después: umbrales por macrofase del hallazgo empírico.
    dias_fallback = 15
    por_macrofase = dict(pipeline_service.DEFAULT_DIAS_POR_MACROFASE)

    # Enriquecemos para tener etapa, fecha_etapa y dias_en_etapa
    enriched = []
    for f in raw:
        f = dict(f)  # copia mutable
        f = pipeline_service._enriquecer(f, hoy, dias_fallback, por_macrofase)
        f["fecha_etapa"] = pipeline_service._fecha_etapa(f)
        enriched.append(f)

    # C.1 — Distribución por etapa (todos los pedidos)
    from collections import Counter
    por_etapa = Counter(f["etapa"] for f in enriched)
    print(f"\n  C.1 Distribución total por etapa:")
    for etapa, n in sorted(por_etapa.items(), key=lambda x: -x[1]):
        print(f"    · {etapa:<25s}  {n:>5d}")

    # C.2 — Estancados por etapa
    estancados = [f for f in enriched if f.get("estancado")]
    por_etapa_est = Counter(f["etapa"] for f in estancados)
    print(f"\n  C.2 Estancados actuales: {len(estancados)}")
    for etapa, n in sorted(por_etapa_est.items(), key=lambda x: -x[1]):
        print(f"    · {etapa:<25s}  {n:>5d}")

    # C.3 — ¿Cuántos estancados caen a FECHA_APROB o FECHA_PEDIDO como último recurso?
    # Lo detectamos comparando fecha_etapa con fecha_aprob/fecha_pedido.
    fallback_a_aprob = 0
    fallback_a_pedido = 0
    tiene_fecha_propia = 0
    for f in estancados:
        fe = f.get("fecha_etapa")
        fap = f.get("FECHA_APROB")
        fpe = f.get("FECHA_PEDIDO")
        # Coerción a date
        from datetime import datetime
        if isinstance(fe, datetime):
            fe = fe.date()
        if isinstance(fap, datetime):
            fap = fap.date()
        if isinstance(fpe, datetime):
            fpe = fpe.date()
        if fe is None:
            continue
        # Detectamos si fecha_etapa proviene de una fecha específica de etapa
        # o cayó al fallback de aprobación/pedido.
        fechas_propias = [
            f.get("fecha_ccmn"), f.get("fecha_cuadro_adq"),
            f.get("fecha_certificacion"), f.get("fecha_orden"),
            f.get("fecha_compromiso"), f.get("fecha_ejecucion"),
            f.get("fecha_kardex"), f.get("fecha_pecosa"),
            f.get("fecha_cierre_seg"),
        ]
        fechas_propias = [
            (x.date() if isinstance(x, datetime) else x) for x in fechas_propias
        ]
        if fe in fechas_propias:
            tiene_fecha_propia += 1
        elif fe == fap:
            fallback_a_aprob += 1
        elif fe == fpe:
            fallback_a_pedido += 1

    print(f"\n  C.3 Origen de fecha_etapa en los {len(estancados)} estancados:")
    print(f"    · Fecha propia de la etapa alcanzada:         {tiene_fecha_propia:>5d}")
    print(f"    · Fallback a FECHA_APROB (aprobación pedido): {fallback_a_aprob:>5d}")
    print(f"    · Fallback a FECHA_PEDIDO (registro pedido):  {fallback_a_pedido:>5d}")
    print(f"    · Otros:                                      {len(estancados) - tiene_fecha_propia - fallback_a_aprob - fallback_a_pedido:>5d}")

    # C.4 — Distribución de dias_en_etapa entre los estancados
    dias = [f.get("dias_en_etapa") or 0 for f in estancados]
    if dias:
        print(f"\n  C.4 Distribución de dias_en_etapa entre estancados:")
        buckets = [(16, 30), (31, 60), (61, 90), (91, 120), (121, 180), (181, 365), (366, 9999)]
        for lo, hi in buckets:
            n = sum(1 for d in dias if lo <= d <= hi)
            print(f"    · {lo:>4d}–{hi:<4d} días: {n:>5d}")

    # C.5 — Sensibilidad: excluir estados terminales / tipos internos
    from collections import Counter
    por_estado = Counter((f.get("estado_pedido") or f.get("ESTADO") or "?") for f in estancados)
    por_tipo = Counter((f.get("TIPO_PEDIDO") or "?") for f in estancados)
    print(f"\n  C.5 Estancados por ESTADO del pedido:")
    for k, v in sorted(por_estado.items(), key=lambda x: -x[1]):
        print(f"    · ESTADO='{k}':  {v}")
    print(f"\n  C.6 Estancados por TIPO_PEDIDO:")
    for k, v in sorted(por_tipo.items(), key=lambda x: -x[1]):
        print(f"    · TIPO='{k}':  {v}")


def main() -> int:
    print(f"\nDiagnóstico cruce MEF vs SIGA ({settings.MSSQL_DB})")
    print(f"ANO_EJE={ANO} · SEC_EJEC={SEC_EJEC}")
    print(f"Referencias MEF: PIM=S/69.5M · Ejecución=S/31.1M (44.8%)")
    try:
        with get_connection() as conn:
            diagnostico_a_pim(conn)
            diagnostico_b_devengado(conn)
        diagnostico_c_estancados(None)
    except Exception as e:
        import traceback
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
    print("\nDiagnóstico completo.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
