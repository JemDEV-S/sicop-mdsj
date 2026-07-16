"""Diagnóstico contra SIGA para calibrar los widgets del dashboard interno.

Responde 3 preguntas empíricas, cada una imprimiendo su resultado:

  A. contratos_por_vencer — ¿por qué el conteo actual está inflado?
     - Distribución de SIG_CONTRATOS por ANO_EJE + ESTADO.
     - Cuántos matchea el filtro actual vs. filtros corregidos.

  B. devengado del pedido 232/S — ¿MNTO_ACUM_DEVGDO_SIGA tiene lag vs. conformidades?
     - Devengado del techo (SIG_TECHO_PRESUPUESTO) para el sec_func del 232/S.
     - Suma de conformidades (SIG_MOVIM_CONFOR_SERVICIO) del mismo pedido.
     - Diferencia = "devengado en tránsito" que no aparece en el widget.

  C. pedidos_estancados — sensibilidad a TIPO_PEDIDO.
     - Cuántos pedidos activos hay por (TIPO_PEDIDO, ESTADO_PEDIDO) en 2026.
     - Cuántos se marcan estancados si excluimos TIPO_PEDIDO IN ('1','I').

Correr desde la raíz del repo:
    python -m backend.scripts.diagnostico_alertas_saldos
o desde backend/:
    python -m scripts.diagnostico_alertas_saldos
"""

from __future__ import annotations

import sys
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.siga.conexion import get_connection

ANO = settings.ANO_VIGENTE
SEC_EJEC = settings.SEC_EJEC
PEDIDO_TESTIGO = 232
TIPO_BIEN_TESTIGO = "S"


def _print_rows(rows: list[dict[str, Any]], titulo: str) -> None:
    print(f"\n── {titulo} " + "─" * (78 - len(titulo)))
    if not rows:
        print("  (sin resultados)")
        return
    cols = list(rows[0].keys())
    header = " | ".join(c.rjust(12) for c in cols)
    print(header)
    print("-" * len(header))
    for r in rows:
        print(" | ".join(str(r[c])[:12].rjust(12) for c in cols))


def diagnostico_a_contratos(conn: Any) -> None:
    print("\n" + "=" * 80)
    print("A. CONTRATOS POR VENCER — distribución y efecto de los filtros")
    print("=" * 80)

    # A.1 — Distribución total: ¿cuántos años hay en la tabla y con qué estados?
    rows = conn.execute(
        text(
            """
            SELECT
                c.ANO_EJE                                       AS ano,
                LTRIM(RTRIM(ISNULL(c.ESTADO, '(null)')))        AS estado,
                COUNT(*)                                        AS total,
                SUM(CASE WHEN c.FECHA_CESE IS NOT NULL THEN 1 ELSE 0 END) AS con_cese,
                SUM(CASE WHEN c.FECHA_FINAL IS NULL THEN 1 ELSE 0 END)    AS sin_fecha_final
            FROM SIG_CONTRATOS c
            WHERE c.SEC_EJEC = :sec_ejec
            GROUP BY c.ANO_EJE, LTRIM(RTRIM(ISNULL(c.ESTADO, '(null)')))
            ORDER BY c.ANO_EJE DESC, total DESC
            """
        ),
        {"sec_ejec": SEC_EJEC},
    ).mappings().all()
    _print_rows([dict(r) for r in rows], "A.1 Distribución SIG_CONTRATOS por año + estado")

    # A.2 — Filtro actual (el que usa contratos_por_vencer): sin ANO_EJE, sin ESTADO
    r_actual = conn.execute(
        text(
            """
            SELECT COUNT(*) AS n
            FROM SIG_CONTRATOS c
            WHERE c.SEC_EJEC = :sec_ejec
              AND c.FECHA_FINAL IS NOT NULL
              AND c.FECHA_FINAL >= CAST(GETDATE() AS DATE)
              AND c.FECHA_FINAL <= DATEADD(day, 30, CAST(GETDATE() AS DATE))
            """
        ),
        {"sec_ejec": SEC_EJEC},
    ).scalar_one()
    print(f"\n  → Filtro ACTUAL (sin ANO_EJE ni ESTADO):        {r_actual} contratos")

    # A.3 — Filtro propuesto: ANO_EJE actual + FECHA_CESE IS NULL + ESTADO válido
    #       Nota: "estado válido" queda por decidir cuando veamos A.1.
    r_propuesto = conn.execute(
        text(
            """
            SELECT COUNT(*) AS n
            FROM SIG_CONTRATOS c
            WHERE c.SEC_EJEC = :sec_ejec
              AND c.ANO_EJE = :ano
              AND c.FECHA_FINAL IS NOT NULL
              AND c.FECHA_CESE IS NULL
              AND c.FECHA_FINAL >= CAST(GETDATE() AS DATE)
              AND c.FECHA_FINAL <= DATEADD(day, 30, CAST(GETDATE() AS DATE))
            """
        ),
        {"sec_ejec": SEC_EJEC, "ano": ANO},
    ).scalar_one()
    print(f"  → Filtro PROPUESTO (ANO_EJE={ANO} + FECHA_CESE IS NULL): {r_propuesto} contratos")


def diagnostico_b_devengado(conn: Any) -> None:
    print("\n" + "=" * 80)
    print(f"B. DEVENGADO — pedido testigo {PEDIDO_TESTIGO}/{TIPO_BIEN_TESTIGO} en {ANO}")
    print("=" * 80)

    # B.1 — Datos del pedido (sec_func viene directo en SIG_PEDIDOS.sec_func).
    detalle = conn.execute(
        text(
            """
            SELECT
                p.NRO_PEDIDO, p.TIPO_BIEN, p.TIPO_PEDIDO, p.ESTADO,
                p.FECHA_PEDIDO, p.FECHA_APROB, p.FECHA_ATENC,
                p.sec_func, p.CENTRO_COSTO
            FROM SIG_PEDIDOS p
            WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
              AND CAST(p.NRO_PEDIDO AS INT) = :nro
              AND p.TIPO_BIEN = :tipo_bien
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC, "nro": PEDIDO_TESTIGO, "tipo_bien": TIPO_BIEN_TESTIGO},
    ).mappings().all()
    _print_rows([dict(r) for r in detalle], f"B.1 Datos del pedido {PEDIDO_TESTIGO}/{TIPO_BIEN_TESTIGO}")

    if not detalle:
        print("  ⚠ El pedido testigo no existe en 2026. Salteando B.2/B.3.")
        return

    sec_funcs = sorted({r["sec_func"] for r in detalle if r["sec_func"]})
    if not sec_funcs:
        print("  ⚠ El testigo no tiene sec_func en SIG_PEDIDOS. Salteando B.2/B.3.")
        return
    print(f"\n  sec_func del testigo: {sec_funcs}")

    # B.2 — MNTO_ACUM_DEVGDO_SIGA en el techo para ese sec_func
    binds = ",".join(f":sf{i}" for i in range(len(sec_funcs)))
    params: dict[str, Any] = {"ano": ANO, "sec_ejec": SEC_EJEC}
    for i, sf in enumerate(sec_funcs):
        params[f"sf{i}"] = sf

    techo = conn.execute(
        text(
            f"""
            SELECT
                t.SEC_FUNC,
                SUM(t.PPTO_MODIF)                AS pim,
                SUM(t.MNTO_ACUM_DEVGDO_SIGA)     AS devengado_techo,
                SUM(t.PPTO_DISP_SIAF)            AS saldo,
                COUNT(*)                         AS filas
            FROM SIG_TECHO_PRESUPUESTO t
            WHERE t.ANO_EJE = :ano AND t.SEC_EJEC = :sec_ejec
              AND t.SEC_FUNC IN ({binds})
            GROUP BY t.SEC_FUNC
            ORDER BY t.SEC_FUNC
            """
        ),
        params,
    ).mappings().all()
    _print_rows([dict(r) for r in techo], "B.2 SIG_TECHO_PRESUPUESTO por sec_func del testigo")

    # B.3 — Devengado en SIG_DEVENGADO_ITEM_PPTO para ese sec_func.
    #       Este es el registro autoritativo de devengado por meta.
    dev_meta = conn.execute(
        text(
            f"""
            SELECT
                dip.SEC_FUNC,
                COUNT(DISTINCT dip.NRO_DEVENGADO)   AS devengados,
                SUM(dip.VALOR_SOLES)                AS devengado_items,
                MIN(d.FECHA_REG)                    AS primer_devengado,
                MAX(d.FECHA_REG)                    AS ultimo_devengado
            FROM SIG_DEVENGADO_ITEM_PPTO dip
            INNER JOIN SIG_DEVENGADO d
                ON d.ANO_EJE = dip.ANO_EJE AND d.SEC_EJEC = dip.SEC_EJEC
               AND d.NRO_DEVENGADO = dip.NRO_DEVENGADO
            WHERE dip.ANO_EJE = :ano AND dip.SEC_EJEC = :sec_ejec
              AND dip.SEC_FUNC IN ({binds})
            GROUP BY dip.SEC_FUNC
            ORDER BY dip.SEC_FUNC
            """
        ),
        params,
    ).mappings().all()
    _print_rows([dict(r) for r in dev_meta], "B.3 SIG_DEVENGADO_ITEM_PPTO por sec_func (registro autoritativo)")

    # B.4 — Devengado global 2026 según cada fuente. Comparación macro.
    macro = conn.execute(
        text(
            """
            SELECT
                (SELECT COALESCE(SUM(MNTO_ACUM_DEVGDO_SIGA),0)
                 FROM SIG_TECHO_PRESUPUESTO
                 WHERE ANO_EJE=:ano AND SEC_EJEC=:sec_ejec)  AS techo_devgdo_siga,
                (SELECT COALESCE(SUM(MNTO_ACUM_DEVGDO_SIAF),0)
                 FROM SIG_TECHO_PRESUPUESTO
                 WHERE ANO_EJE=:ano AND SEC_EJEC=:sec_ejec)  AS techo_devgdo_siaf,
                (SELECT COALESCE(SUM(dip.VALOR_SOLES),0)
                 FROM SIG_DEVENGADO_ITEM_PPTO dip
                 WHERE dip.ANO_EJE=:ano AND dip.SEC_EJEC=:sec_ejec) AS devengado_items
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().one()
    print(f"\n  B.4 Devengado global 2026 según cada fuente:")
    print(f"    · MNTO_ACUM_DEVGDO_SIGA (widget actual):  {float(macro['techo_devgdo_siga']):>18,.2f}")
    print(f"    · MNTO_ACUM_DEVGDO_SIAF (columna hermana): {float(macro['techo_devgdo_siaf']):>18,.2f}")
    print(f"    · SIG_DEVENGADO_ITEM_PPTO (autoritativo):  {float(macro['devengado_items']):>18,.2f}")


def diagnostico_c_estancados(conn: Any) -> None:
    print("\n" + "=" * 80)
    print("C. PEDIDOS — sensibilidad de estancados a TIPO_PEDIDO / ESTADO_PEDIDO")
    print("=" * 80)

    rows = conn.execute(
        text(
            """
            SELECT
                LTRIM(RTRIM(ISNULL(p.TIPO_PEDIDO,'(null)')))    AS tipo_pedido,
                p.ESTADO                                        AS estado,
                COUNT(*)                                        AS total,
                SUM(CASE WHEN DATEDIFF(day, p.FECHA_PEDIDO, GETDATE()) > 15
                         THEN 1 ELSE 0 END)                     AS mas_15_dias
            FROM SIG_PEDIDOS p
            WHERE p.ANO_EJE = :ano AND p.SEC_EJEC = :sec_ejec
            GROUP BY LTRIM(RTRIM(ISNULL(p.TIPO_PEDIDO,'(null)'))), p.ESTADO
            ORDER BY p.ESTADO, tipo_pedido
            """
        ),
        {"ano": ANO, "sec_ejec": SEC_EJEC},
    ).mappings().all()
    _print_rows(
        [dict(r) for r in rows],
        "C.1 SIG_PEDIDOS por (TIPO_PEDIDO, ESTADO) + edad > 15 días desde FECHA_PEDIDO",
    )
    print(
        "\n  Interpretación: el fix propone excluir TIPO_PEDIDO IN ('1','I') y ESTADO=7."
        "\n  La columna 'mas_15_dias' muestra el techo grosero de falsos estancados si NO se excluye."
    )


def main() -> int:
    print(f"\nDiagnóstico contra SIGA ({settings.MSSQL_DB}) · ANO_EJE={ANO} · SEC_EJEC={SEC_EJEC}")
    print("Fuente de referencia: Docs/exploracion-siga-pipeline-extendido.md §§16-17")
    try:
        with get_connection() as conn:
            diagnostico_a_contratos(conn)
            diagnostico_b_devengado(conn)
            diagnostico_c_estancados(conn)
    except Exception as e:  # noqa: BLE001
        print(f"\n✗ ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print("\n✓ Diagnóstico completo.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
