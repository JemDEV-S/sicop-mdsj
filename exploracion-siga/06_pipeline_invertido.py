"""Prototipo del PIPELINE INVERTIDO: seguir el proceso desde la orden, no
adivinar desde el pedido.

NOTA (regla del proyecto): el presupuesto NO se maneja en SIGA — los montos
autoritativos (PIA/PIM/devengado/etc.) vienen SIEMPRE de la API MEF. Aquí solo
se miden VÍNCULOS entre documentos y LLAVES DE CRUCE hacia MEF; ningún monto
SIGA se propone como autoritativo.

Idea: del CCMN hacia adelante TODO es cadena dura y verificable:

    CCMN → solicitud cotización → cuadro adquisición → orden
         → certificación (NRO_CERTIFICA_SIAF) → expediente (EXP_SIAF)
         → compromiso (INTF_CAB estado aprobado)

La única frontera difusa es pedido→CCMN. Este script mide:

  1. ¿Las dos rutas orden→CCMN (cuadro.NRO_CONS_PAAC vs cert_fase.NRO_CONSOLID)
     concuerdan? Si concuerdan al 100%, el CCMN de cada orden es un HECHO.
  2. ¿Cuántos CCMN tienen exactamente 1 pedido en su bolsa? (si la mayoría,
     el pipeline se puede armar desde el CCMN y la ambigüedad queda acotada)
  3. Cobertura end-to-end: ordenes 2026 con CCMN + certificación + EXP_SIAF.
  4. Llaves de cruce hacia MEF por orden: SEC_FUNC + CLASIFICADOR + EXP_SIAF.

Salida: resultados/06-pipeline-invertido.md
"""

from __future__ import annotations

from _db import ANO, SEC_EJEC, Reporte, connect, q, salida_utf8

W = f"ANO_EJE = {ANO} AND SEC_EJEC = {SEC_EJEC}"


def main() -> None:
    salida_utf8()
    rep = Reporte("06-pipeline-invertido", "Pipeline invertido: de la orden al pedido")
    cn = connect()
    cur = cn.cursor()

    # 1. Concordancia de las dos rutas orden→CCMN.
    rep.h("1. Orden→CCMN: ruta cuadro vs ruta certificación")
    rep.tabla(q(cur, f"""
        WITH via_cuadro AS (
            SELECT o.TIPO_BIEN, o.NRO_ORDEN, ca.NRO_CONS_PAAC AS ccmn_cuadro
            FROM SIG_ORDEN_ADQUISICION o
            JOIN SIG_CUADRO_ADQUISICION ca
                ON ca.ANO_EJE = o.ANO_EJE AND ca.SEC_EJEC = o.SEC_EJEC
               AND ca.TIPO_BIEN = o.TIPO_BIEN AND ca.SEC_CUADRO = o.SEC_CUADRO
            WHERE o.ANO_EJE = {ANO} AND o.SEC_EJEC = {SEC_EJEC}
        ),
        via_cert AS (
            SELECT cf.TIPO_BIEN, cf.NRO_ORDEN,
                   MIN(cf.NRO_CONSOLID) AS ccmn_cert,
                   COUNT(DISTINCT cf.NRO_CONSOLID) AS n_ccmn_cert
            FROM SIG_CERTIFICACION_FASE cf
            WHERE cf.ANO_EJE = {ANO} AND cf.SEC_EJEC = {SEC_EJEC}
              AND cf.NRO_ORDEN > 0
            GROUP BY cf.TIPO_BIEN, cf.NRO_ORDEN
        )
        SELECT c.TIPO_BIEN,
               COUNT(*)                                              AS ordenes,
               SUM(CASE WHEN ce.NRO_ORDEN IS NOT NULL THEN 1 ELSE 0 END) AS con_cert,
               SUM(CASE WHEN ce.ccmn_cert = c.ccmn_cuadro THEN 1 ELSE 0 END) AS concuerdan,
               SUM(CASE WHEN ce.NRO_ORDEN IS NOT NULL
                         AND ce.ccmn_cert <> c.ccmn_cuadro THEN 1 ELSE 0 END) AS difieren
        FROM via_cuadro c
        LEFT JOIN via_cert ce
            ON ce.TIPO_BIEN = c.TIPO_BIEN AND ce.NRO_ORDEN = c.NRO_ORDEN
        GROUP BY c.TIPO_BIEN
    """))

    # 2. Bolsas: ¿cuántos pedidos comparten cada CCMN?
    rep.h("2. Distribución de pedidos por CCMN (tamaño de bolsa real)")
    rep.tabla(q(cur, f"""
        WITH pedidos_ccmn AS (
            SELECT cmn.TIPO_BIEN, cmn.NRO_CONSOLID,
                   COUNT(DISTINCT dp.NRO_PEDIDO) AS n_pedidos
            FROM SIG_CUADRO_MODIFICADO_CMN cmn
            JOIN SIG_DETALLE_PEDIDOS dp
                ON dp.ANO_EJE = cmn.ANNO_EJEC AND dp.SEC_EJEC = cmn.SEC_EJEC
               AND dp.TIPO_BIEN = cmn.TIPO_BIEN
               AND dp.SEC_CUA_MOD_SAL = cmn.SEC_CUA_MOD_SAL
            WHERE cmn.ANNO_EJEC = {ANO} AND cmn.SEC_EJEC = {SEC_EJEC}
            GROUP BY cmn.TIPO_BIEN, cmn.NRO_CONSOLID
        )
        SELECT TIPO_BIEN, n_pedidos, COUNT(*) AS ccmn
        FROM pedidos_ccmn
        GROUP BY TIPO_BIEN, n_pedidos
        ORDER BY TIPO_BIEN, n_pedidos
    """), max_rows=40)

    # 2b. Y al revés: pedidos con N CCMN candidatos (ya se conocía, verificar).
    rep.h("Pedidos según nº de CCMN candidatos en su bolsa", 3)
    rep.tabla(q(cur, f"""
        WITH cand AS (
            SELECT dp.TIPO_BIEN, dp.NRO_PEDIDO,
                   COUNT(DISTINCT cmn.NRO_CONSOLID) AS n_ccmn
            FROM SIG_DETALLE_PEDIDOS dp
            LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
                ON cmn.ANNO_EJEC = dp.ANO_EJE AND cmn.SEC_EJEC = dp.SEC_EJEC
               AND cmn.TIPO_BIEN = dp.TIPO_BIEN
               AND cmn.SEC_CUA_MOD_SAL = dp.SEC_CUA_MOD_SAL
            WHERE dp.ANO_EJE = {ANO} AND dp.SEC_EJEC = {SEC_EJEC}
            GROUP BY dp.TIPO_BIEN, dp.NRO_PEDIDO
        )
        SELECT TIPO_BIEN, n_ccmn, COUNT(*) AS pedidos
        FROM cand
        GROUP BY TIPO_BIEN, n_ccmn
        ORDER BY TIPO_BIEN, n_ccmn
    """), max_rows=40)

    # 3. Cobertura end-to-end de la cadena dura desde la orden.
    rep.h("3. Cadena dura completa por orden (2026)")
    rep.tabla(q(cur, f"""
        SELECT o.TIPO_BIEN,
               COUNT(DISTINCT o.NRO_ORDEN) AS ordenes,
               COUNT(DISTINCT CASE WHEN ca.NRO_CONS_PAAC IS NOT NULL
                     THEN o.NRO_ORDEN END) AS con_ccmn,
               COUNT(DISTINCT CASE WHEN cf.NRO_CERTIFICA_SIAF IS NOT NULL
                     THEN o.NRO_ORDEN END) AS con_ccp_siaf,
               COUNT(DISTINCT CASE WHEN op.EXP_SIAF IS NOT NULL AND op.EXP_SIAF > 0
                     THEN o.NRO_ORDEN END) AS con_exp_siaf,
               COUNT(DISTINCT CASE WHEN exd.FECHA_INTERFASE IS NOT NULL
                     THEN o.NRO_ORDEN END) AS con_interfase
        FROM SIG_ORDEN_ADQUISICION o
        LEFT JOIN SIG_CUADRO_ADQUISICION ca
            ON ca.ANO_EJE = o.ANO_EJE AND ca.SEC_EJEC = o.SEC_EJEC
           AND ca.TIPO_BIEN = o.TIPO_BIEN AND ca.SEC_CUADRO = o.SEC_CUADRO
        LEFT JOIN SIG_CERTIFICACION_FASE cf
            ON cf.ANO_EJE = o.ANO_EJE AND cf.SEC_EJEC = o.SEC_EJEC
           AND cf.TIPO_BIEN = o.TIPO_BIEN AND cf.NRO_ORDEN = o.NRO_ORDEN
        LEFT JOIN SIG_ORDEN_PRESUPUESTO op
            ON op.ANO_EJE = o.ANO_EJE AND op.SEC_EJEC = o.SEC_EJEC
           AND op.TIPO_BIEN = o.TIPO_BIEN AND op.NRO_ORDEN = o.NRO_ORDEN
        LEFT JOIN SIG_EXP_SIGA_DOCU exd
            ON exd.ANO_EJE = o.ANO_EJE AND exd.SEC_EJEC = o.SEC_EJEC
           AND exd.EXP_SIGA = o.EXP_SIGA
        WHERE o.ANO_EJE = {ANO} AND o.SEC_EJEC = {SEC_EJEC}
        GROUP BY o.TIPO_BIEN
    """))

    # 4. Llaves de cruce hacia MEF por orden. Los montos autoritativos viven
    #    en la API MEF (por meta+clasificador+mes); lo que SIGA aporta es la
    #    llave para asignar esa ejecución a documentos concretos.
    rep.h("4. Llaves de cruce orden→MEF: SEC_FUNC + CLASIFICADOR + EXP_SIAF")
    rep.tabla(q(cur, f"""
        SELECT op.TIPO_BIEN,
               COUNT(DISTINCT op.NRO_ORDEN) AS ordenes,
               COUNT(DISTINCT CASE WHEN op.SEC_FUNC IS NOT NULL
                     THEN op.NRO_ORDEN END) AS con_sec_func,
               COUNT(DISTINCT CASE WHEN op.CLASIFICADOR IS NOT NULL
                     AND LTRIM(RTRIM(op.CLASIFICADOR)) <> ''
                     THEN op.NRO_ORDEN END) AS con_clasificador,
               COUNT(DISTINCT CASE WHEN op.EXP_SIAF IS NOT NULL AND op.EXP_SIAF > 0
                     THEN op.NRO_ORDEN END) AS con_exp_siaf
        FROM SIG_ORDEN_PRESUPUESTO op
        WHERE op.ANO_EJE = {ANO} AND op.SEC_EJEC = {SEC_EJEC}
        GROUP BY op.TIPO_BIEN
    """))

    # Granularidad del cruce: ¿cuántas combinaciones meta+clasificador tienen
    # UNA sola orden? Ahí el devengado MEF de esa celda es atribuible 1:1.
    rep.h("Celdas meta+clasificador según nº de órdenes (atribución 1:1)", 3)
    rep.tabla(q(cur, f"""
        WITH celdas AS (
            SELECT op.SEC_FUNC, LTRIM(RTRIM(op.CLASIFICADOR)) AS clasificador,
                   COUNT(DISTINCT CONCAT(op.TIPO_BIEN, '-', op.NRO_ORDEN)) AS n_ordenes
            FROM SIG_ORDEN_PRESUPUESTO op
            WHERE op.ANO_EJE = {ANO} AND op.SEC_EJEC = {SEC_EJEC}
            GROUP BY op.SEC_FUNC, LTRIM(RTRIM(op.CLASIFICADOR))
        )
        SELECT CASE WHEN n_ordenes = 1 THEN '1 orden (atribuible 1:1)'
                    WHEN n_ordenes <= 5 THEN '2-5 ordenes'
                    ELSE '6+ ordenes' END AS celda,
               COUNT(*) AS celdas,
               SUM(n_ordenes) AS ordenes
        FROM celdas
        GROUP BY CASE WHEN n_ordenes = 1 THEN '1 orden (atribuible 1:1)'
                      WHEN n_ordenes <= 5 THEN '2-5 ordenes'
                      ELSE '6+ ordenes' END
    """))

    rep.guardar()
    cn.close()


if __name__ == "__main__":
    main()
