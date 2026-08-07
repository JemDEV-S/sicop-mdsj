"""Mide la cobertura de los VÍNCULOS DUROS descubiertos en el script 03.

Los Docs actuales afirman que "no existe ruta dura pedido→CCMN" y por eso el
backend usa una cascada heurística. Pero las estructuras muestran:

  A. SIG_DETALLE_BSERV_CUADRO.nro_pedido / sec_item_pedido / tipo_pedido
     -> el detalle del CUADRO DE ADQUISICIÓN nombra a su pedido de origen.
     Con SEC_CUADRO se llega a la orden (SIG_ORDEN_ADQUISICION.SEC_CUADRO)
     y con NRO_CONS_PAAC al CCMN. FK item-level, sin heurística.

  B. SIG_CUADRO_NECESIDAD_DET.NRO_PEDIDO + NRO_CONSOLID
     -> el detalle del cuadro de necesidad une pedido y CCMN en una fila.

  C. SIG_CERTIFICACION_FASE.NRO_ORDEN + NRO_CONSOLID + NRO_CONTRATO
     -> la certificación nombra a la orden y al consolidado.

Este script mide cuántos pedidos/órdenes de 2026 cubre cada ruta y si las
rutas se contradicen entre sí o con el match actual.

Salida: resultados/04-vinculos-duros.md
"""

from __future__ import annotations

from _db import ANO, SEC_EJEC, Reporte, connect, q, salida_utf8

W = f"ANO_EJE = {ANO} AND SEC_EJEC = {SEC_EJEC}"


def w(alias: str) -> str:
    return f"{alias}.ANO_EJE = {ANO} AND {alias}.SEC_EJEC = {SEC_EJEC}"


def main() -> None:
    salida_utf8()
    rep = Reporte("04-vinculos-duros", "Cobertura de vínculos duros pedido↔cuadro↔orden")
    cn = connect()
    cur = cn.cursor()

    # ── A. SIG_DETALLE_BSERV_CUADRO.nro_pedido ───────────────────────────
    rep.h("A. Población de nro_pedido en SIG_DETALLE_BSERV_CUADRO (2026)")
    rep.tabla(q(cur, f"""
        SELECT TIPO_BIEN,
               COUNT(*)                                             AS items,
               SUM(CASE WHEN nro_pedido IS NOT NULL AND nro_pedido > 0
                        THEN 1 ELSE 0 END)                          AS con_pedido,
               SUM(CASE WHEN NRO_CONS_PAAC IS NOT NULL AND NRO_CONS_PAAC > 0
                        THEN 1 ELSE 0 END)                          AS con_ccmn,
               COUNT(DISTINCT SEC_CUADRO)                           AS cuadros
        FROM SIG_DETALLE_BSERV_CUADRO
        WHERE {W}
        GROUP BY TIPO_BIEN
    """))

    rep.h("Muestra de items del cuadro con pedido declarado", 3)
    rep.tabla(q(cur, f"""
        SELECT TOP 12 TIPO_BIEN, SEC_CUADRO, SECUENCIA, nro_pedido,
               sec_item_pedido, tipo_pedido, NRO_CONS_PAAC, FLAG_CONSOLID,
               ITEM_BIEN, CANT_APROBADA, VALOR_SOLES
        FROM SIG_DETALLE_BSERV_CUADRO
        WHERE {W} AND nro_pedido IS NOT NULL AND nro_pedido > 0
        ORDER BY SEC_CUADRO DESC
    """), max_rows=12)

    # Cobertura sobre el universo de pedidos del kanban (estado 0/1/7, compra).
    rep.h("Cobertura: pedidos 2026 alcanzados por la ruta A")
    rep.tabla(q(cur, f"""
        SELECT p.TIPO_BIEN,
               COUNT(DISTINCT p.NRO_PEDIDO)  AS pedidos,
               COUNT(DISTINCT CASE WHEN bc.nro_pedido IS NOT NULL
                     THEN p.NRO_PEDIDO END)  AS con_cuadro_directo,
               COUNT(DISTINCT CASE WHEN bc.NRO_CONS_PAAC IS NOT NULL
                     AND bc.NRO_CONS_PAAC > 0
                     THEN p.NRO_PEDIDO END)  AS con_ccmn_directo
        FROM SIG_PEDIDOS p
        LEFT JOIN SIG_DETALLE_BSERV_CUADRO bc
            ON bc.ANO_EJE = p.ANO_EJE AND bc.SEC_EJEC = p.SEC_EJEC
           AND bc.TIPO_BIEN = p.TIPO_BIEN
           AND bc.nro_pedido = p.NRO_PEDIDO
           AND bc.tipo_pedido = p.TIPO_PEDIDO
        WHERE {w('p')}
          AND p.ESTADO IN ('0', '1', '7')
        GROUP BY p.TIPO_BIEN
    """))

    # Ruta completa A: pedido -> cuadro -> orden.
    rep.h("Ruta A completa: pedido → SEC_CUADRO → orden")
    rep.tabla(q(cur, f"""
        SELECT p.TIPO_BIEN,
               COUNT(DISTINCT p.NRO_PEDIDO) AS pedidos,
               COUNT(DISTINCT CASE WHEN o.NRO_ORDEN IS NOT NULL
                     THEN p.NRO_PEDIDO END) AS pedidos_con_orden_dura
        FROM SIG_PEDIDOS p
        JOIN SIG_DETALLE_BSERV_CUADRO bc
            ON bc.ANO_EJE = p.ANO_EJE AND bc.SEC_EJEC = p.SEC_EJEC
           AND bc.TIPO_BIEN = p.TIPO_BIEN AND bc.nro_pedido = p.NRO_PEDIDO
           AND bc.tipo_pedido = p.TIPO_PEDIDO
        JOIN SIG_ORDEN_ADQUISICION o
            ON o.ANO_EJE = bc.ANO_EJE AND o.SEC_EJEC = bc.SEC_EJEC
           AND o.TIPO_BIEN = bc.TIPO_BIEN AND o.SEC_CUADRO = bc.SEC_CUADRO
        WHERE {w('p')}
          AND p.ESTADO IN ('0', '1', '7')
        GROUP BY p.TIPO_BIEN
    """))

    # ¿Un pedido puede aparecer en más de un cuadro? (ambigüedad residual)
    rep.h("Ambigüedad residual ruta A: pedidos con N cuadros distintos")
    rep.tabla(q(cur, f"""
        SELECT TIPO_BIEN, n_cuadros, COUNT(*) AS pedidos
        FROM (
            SELECT TIPO_BIEN, nro_pedido, tipo_pedido,
                   COUNT(DISTINCT SEC_CUADRO) AS n_cuadros
            FROM SIG_DETALLE_BSERV_CUADRO
            WHERE {W} AND nro_pedido IS NOT NULL AND nro_pedido > 0
            GROUP BY TIPO_BIEN, nro_pedido, tipo_pedido
        ) x
        GROUP BY TIPO_BIEN, n_cuadros
        ORDER BY TIPO_BIEN, n_cuadros
    """))

    # ── B. SIG_CUADRO_NECESIDAD_DET: pedido + CCMN en una fila ───────────
    rep.h("B. SIG_CUADRO_NECESIDAD_DET: población de NRO_PEDIDO y NRO_CONSOLID")
    rep.tabla(q(cur, f"""
        SELECT TIPO_BIEN, FASE_CUADRO,
               COUNT(*) AS items,
               SUM(CASE WHEN NRO_PEDIDO IS NOT NULL AND NRO_PEDIDO > 0
                        THEN 1 ELSE 0 END) AS con_pedido,
               SUM(CASE WHEN NRO_CONSOLID IS NOT NULL AND NRO_CONSOLID > 0
                        THEN 1 ELSE 0 END) AS con_consolid,
               SUM(CASE WHEN NRO_PEDIDO > 0 AND NRO_CONSOLID > 0
                        THEN 1 ELSE 0 END) AS ambos
        FROM SIG_CUADRO_NECESIDAD_DET
        WHERE {W}
        GROUP BY TIPO_BIEN, FASE_CUADRO
        ORDER BY TIPO_BIEN, FASE_CUADRO
    """))

    rep.h("Muestra fila con pedido y consolidado juntos", 3)
    rep.tabla(q(cur, f"""
        SELECT TOP 12 TIPO_BIEN, FASE_CUADRO, CENTRO_COSTO, NRO_PEDIDO,
               NRO_CONSOLID, ESTADO_PAAC, ITEM_BIEN, MNTO_TOTAL
        FROM SIG_CUADRO_NECESIDAD_DET
        WHERE {W} AND NRO_PEDIDO > 0 AND NRO_CONSOLID > 0
        ORDER BY NRO_PEDIDO
    """), max_rows=12)

    # ── C. SIG_CERTIFICACION_FASE: cert -> orden / consolidado ───────────
    rep.h("C. SIG_CERTIFICACION_FASE: población de NRO_ORDEN / NRO_CONSOLID")
    rep.tabla(q(cur, f"""
        SELECT TIPO_BIEN,
               COUNT(*) AS fases,
               SUM(CASE WHEN NRO_ORDEN IS NOT NULL AND NRO_ORDEN > 0
                        THEN 1 ELSE 0 END) AS con_orden,
               SUM(CASE WHEN NRO_CONSOLID IS NOT NULL AND NRO_CONSOLID > 0
                        THEN 1 ELSE 0 END) AS con_consolid,
               SUM(CASE WHEN NRO_CERTIFICA_SIAF IS NOT NULL
                        THEN 1 ELSE 0 END) AS con_ccp_siaf,
               SUM(CASE WHEN FLAG_COMPROMETIDO = 'S' THEN 1 ELSE 0 END) AS comprometidas
        FROM SIG_CERTIFICACION_FASE
        WHERE {W}
        GROUP BY TIPO_BIEN
    """))

    # ── D. Concordancia ruta A vs match composite actual ─────────────────
    # Para pedidos donde el backend actual encontró orden por composite,
    # ¿la ruta dura (bserv_cuadro -> SEC_CUADRO -> orden) da la MISMA orden?
    rep.h("D. Concordancia: orden por ruta dura vs por composite de monto")
    rep.tabla(q(cur, f"""
        WITH dura AS (
            SELECT bc.TIPO_BIEN, bc.nro_pedido, bc.tipo_pedido,
                   MIN(o.NRO_ORDEN) AS orden_dura,
                   COUNT(DISTINCT o.NRO_ORDEN) AS n_ordenes_dura
            FROM SIG_DETALLE_BSERV_CUADRO bc
            JOIN SIG_ORDEN_ADQUISICION o
                ON o.ANO_EJE = bc.ANO_EJE AND o.SEC_EJEC = bc.SEC_EJEC
               AND o.TIPO_BIEN = bc.TIPO_BIEN AND o.SEC_CUADRO = bc.SEC_CUADRO
            WHERE {w('bc')}
              AND bc.nro_pedido > 0
            GROUP BY bc.TIPO_BIEN, bc.nro_pedido, bc.tipo_pedido
        ),
        composite AS (
            SELECT d.TIPO_BIEN, d.NRO_PEDIDO, d.TIPO_PEDIDO,
                   MIN(oi.NRO_ORDEN) AS orden_composite
            FROM SIG_DETALLE_PEDIDOS d
            JOIN SIG_PEDIDOS p
                ON p.ANO_EJE = d.ANO_EJE AND p.SEC_EJEC = d.SEC_EJEC
               AND p.TIPO_BIEN = d.TIPO_BIEN AND p.NRO_PEDIDO = d.NRO_PEDIDO
            JOIN SIG_ORDEN_ITEM oi
                ON oi.ANO_EJE = d.ANO_EJE AND oi.SEC_EJEC = d.SEC_EJEC
               AND oi.TIPO_BIEN = d.TIPO_BIEN
               AND LTRIM(RTRIM(oi.GRUPO_BIEN)) = LTRIM(RTRIM(d.GRUPO_BIEN))
               AND LTRIM(RTRIM(oi.CLASE_BIEN)) = LTRIM(RTRIM(d.CLASE_BIEN))
               AND LTRIM(RTRIM(oi.FAMILIA_BIEN)) = LTRIM(RTRIM(d.FAMILIA_BIEN))
               AND LTRIM(RTRIM(oi.ITEM_BIEN)) = LTRIM(RTRIM(d.ITEM_BIEN))
            JOIN SIG_ORDEN_ITEM_PPTO op
                ON op.ANO_EJE = oi.ANO_EJE AND op.SEC_EJEC = oi.SEC_EJEC
               AND op.NRO_ORDEN = oi.NRO_ORDEN AND op.TIPO_BIEN = oi.TIPO_BIEN
               AND op.TIPO_PPTO = oi.TIPO_PPTO AND op.SEC_ORDEN = oi.SEC_ORDEN
               AND op.SEC_ITEM = oi.SEC_ITEM
               AND op.SEC_FUNC = p.sec_func
               AND ROUND(op.VALOR_SOLES, 2) = ROUND(
                     CASE WHEN COALESCE(d.VALOR_TOTAL, 0) > 0 THEN d.VALOR_TOTAL
                          ELSE COALESCE(d.CANT_SOLICITADA, 0)
                               * COALESCE(d.PRECIO_UNIT, 0) END, 2)
            WHERE {w('d')}
            GROUP BY d.TIPO_BIEN, d.NRO_PEDIDO, d.TIPO_PEDIDO
        )
        SELECT du.TIPO_BIEN,
               COUNT(*)                                            AS pedidos_ambas_rutas,
               SUM(CASE WHEN du.orden_dura = co.orden_composite
                        THEN 1 ELSE 0 END)                         AS coinciden,
               SUM(CASE WHEN du.orden_dura <> co.orden_composite
                        THEN 1 ELSE 0 END)                         AS difieren
        FROM dura du
        JOIN composite co
            ON co.TIPO_BIEN = du.TIPO_BIEN
           AND co.NRO_PEDIDO = du.nro_pedido
           AND co.TIPO_PEDIDO = du.tipo_pedido
        GROUP BY du.TIPO_BIEN
    """))

    rep.h("Casos donde difieren (muestra)", 3)
    rep.tabla(q(cur, f"""
        WITH dura AS (
            SELECT bc.TIPO_BIEN, bc.nro_pedido, bc.tipo_pedido,
                   MIN(o.NRO_ORDEN) AS orden_dura
            FROM SIG_DETALLE_BSERV_CUADRO bc
            JOIN SIG_ORDEN_ADQUISICION o
                ON o.ANO_EJE = bc.ANO_EJE AND o.SEC_EJEC = bc.SEC_EJEC
               AND o.TIPO_BIEN = bc.TIPO_BIEN AND o.SEC_CUADRO = bc.SEC_CUADRO
            WHERE {w('bc')} AND bc.nro_pedido > 0
            GROUP BY bc.TIPO_BIEN, bc.nro_pedido, bc.tipo_pedido
        ),
        composite AS (
            SELECT d.TIPO_BIEN, d.NRO_PEDIDO, d.TIPO_PEDIDO,
                   MIN(oi.NRO_ORDEN) AS orden_composite
            FROM SIG_DETALLE_PEDIDOS d
            JOIN SIG_PEDIDOS p
                ON p.ANO_EJE = d.ANO_EJE AND p.SEC_EJEC = d.SEC_EJEC
               AND p.TIPO_BIEN = d.TIPO_BIEN AND p.NRO_PEDIDO = d.NRO_PEDIDO
            JOIN SIG_ORDEN_ITEM oi
                ON oi.ANO_EJE = d.ANO_EJE AND oi.SEC_EJEC = d.SEC_EJEC
               AND oi.TIPO_BIEN = d.TIPO_BIEN
               AND LTRIM(RTRIM(oi.GRUPO_BIEN)) = LTRIM(RTRIM(d.GRUPO_BIEN))
               AND LTRIM(RTRIM(oi.CLASE_BIEN)) = LTRIM(RTRIM(d.CLASE_BIEN))
               AND LTRIM(RTRIM(oi.FAMILIA_BIEN)) = LTRIM(RTRIM(d.FAMILIA_BIEN))
               AND LTRIM(RTRIM(oi.ITEM_BIEN)) = LTRIM(RTRIM(d.ITEM_BIEN))
            JOIN SIG_ORDEN_ITEM_PPTO op
                ON op.ANO_EJE = oi.ANO_EJE AND op.SEC_EJEC = oi.SEC_EJEC
               AND op.NRO_ORDEN = oi.NRO_ORDEN AND op.TIPO_BIEN = oi.TIPO_BIEN
               AND op.TIPO_PPTO = oi.TIPO_PPTO AND op.SEC_ORDEN = oi.SEC_ORDEN
               AND op.SEC_ITEM = oi.SEC_ITEM
               AND op.SEC_FUNC = p.sec_func
               AND ROUND(op.VALOR_SOLES, 2) = ROUND(
                     CASE WHEN COALESCE(d.VALOR_TOTAL, 0) > 0 THEN d.VALOR_TOTAL
                          ELSE COALESCE(d.CANT_SOLICITADA, 0)
                               * COALESCE(d.PRECIO_UNIT, 0) END, 2)
            WHERE {w('d')}
            GROUP BY d.TIPO_BIEN, d.NRO_PEDIDO, d.TIPO_PEDIDO
        )
        SELECT TOP 15 du.TIPO_BIEN, du.nro_pedido,
               du.orden_dura, co.orden_composite
        FROM dura du
        JOIN composite co
            ON co.TIPO_BIEN = du.TIPO_BIEN AND co.NRO_PEDIDO = du.nro_pedido
           AND co.TIPO_PEDIDO = du.tipo_pedido
        WHERE du.orden_dura <> co.orden_composite
        ORDER BY du.nro_pedido
    """), max_rows=15)

    rep.guardar()
    cn.close()


if __name__ == "__main__":
    main()
