"""Decodifica la semántica de SIG_SEGUIMIENTO por TIPO_TRANSACCION.

El script 01 mostró que el seguimiento cubre el 100% de los pedidos 2026 y
que la fila trae NRO_PEDIDO y NRO_CONSOLID juntos. Preguntas:

  A. ¿Qué documento representa cada TIPO_TRANSACCION? (muestras por tipo)
  B. ¿Hay eventos con NRO_PEDIDO + NRO_CONSOLID poblados a la vez?
     -> sería el VÍNCULO DIRECTO pedido↔CCMN que la cascada intenta inferir.
  C. ¿El evento tipo 9 (orden?) trae NRO_TRANSACCION = NRO_ORDEN y a la vez
     NRO_PEDIDO? -> sería el vínculo directo pedido↔orden, sin composite.
  D. ¿Qué guarda SIG_SEGUIMIENTO_SECUENCIA (grafo doc origen → doc destino)?

Salida: resultados/02-decodificar-seguimiento.md
"""

from __future__ import annotations

from _db import ANO, SEC_EJEC, Reporte, connect, q, salida_utf8

W = f"ANO_EJE = {ANO} AND SEC_EJEC = {SEC_EJEC}"


def main() -> None:
    salida_utf8()
    rep = Reporte("02-decodificar-seguimiento",
                  "Semántica de SIG_SEGUIMIENTO por TIPO_TRANSACCION")
    cn = connect()
    cur = cn.cursor()

    # A. Muestras por tipo (campos no vacíos que caracterizan al documento).
    tipos = [r["TIPO_TRANSACCION"] for r in q(cur, f"""
        SELECT DISTINCT TIPO_TRANSACCION FROM SIG_SEGUIMIENTO WHERE {W}
    """)]
    rep.h("Muestras por TIPO_TRANSACCION (5 c/u)")
    for t in sorted(tipos):
        rep.h(f"TIPO_TRANSACCION = {t}", 3)
        rep.tabla(q(cur, f"""
            SELECT TOP 5 NRO_ORIGEN, CENTRO_COSTO, TIPO_BIEN, TIPO_PEDIDO,
                   TIPO_CONSOLID, NRO_TRANSACCION, NRO_PEDIDO, NRO_CONSOLID,
                   FECHA_TRANSACCION, ESTADO_TRANSACCION, CUSER_ID
            FROM SIG_SEGUIMIENTO WHERE {W} AND TIPO_TRANSACCION = {t}
            ORDER BY FECHA_TRANSACCION DESC
        """))

    # B. Densidad de campos por tipo: cuántas filas traen pedido/consolid/transac.
    rep.h("Densidad de llaves por tipo")
    rep.tabla(q(cur, f"""
        SELECT TIPO_TRANSACCION,
               COUNT(*) AS filas,
               SUM(CASE WHEN NRO_PEDIDO IS NOT NULL AND LTRIM(NRO_PEDIDO) <> ''
                        THEN 1 ELSE 0 END) AS con_pedido,
               SUM(CASE WHEN NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END) AS con_consolid,
               SUM(CASE WHEN NRO_TRANSACCION IS NOT NULL THEN 1 ELSE 0 END) AS con_transac,
               SUM(CASE WHEN NRO_PEDIDO IS NOT NULL AND LTRIM(NRO_PEDIDO) <> ''
                         AND NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END) AS pedido_y_consolid
        FROM SIG_SEGUIMIENTO WHERE {W}
        GROUP BY TIPO_TRANSACCION ORDER BY TIPO_TRANSACCION
    """))

    # C. Hipótesis orden: tipo 8/9 con NRO_TRANSACCION = NRO_ORDEN.
    rep.h("¿NRO_TRANSACCION de los tipos 8/9 es un NRO_ORDEN real?")
    for t in (8, 9):
        rep.tabla(q(cur, f"""
            SELECT '{t}' AS tipo,
                   COUNT(*) AS eventos,
                   SUM(CASE WHEN o.NRO_ORDEN IS NOT NULL THEN 1 ELSE 0 END) AS matchea_orden,
                   SUM(CASE WHEN s.NRO_PEDIDO IS NOT NULL
                             AND LTRIM(s.NRO_PEDIDO) <> '' THEN 1 ELSE 0 END) AS con_pedido
            FROM SIG_SEGUIMIENTO s
            LEFT JOIN SIG_ORDEN_ADQUISICION o
                ON o.ANO_EJE = s.ANO_EJE AND o.SEC_EJEC = s.SEC_EJEC
               AND o.TIPO_BIEN = s.TIPO_BIEN AND o.NRO_ORDEN = s.NRO_TRANSACCION
            WHERE s.ANO_EJE = {ANO} AND s.SEC_EJEC = {SEC_EJEC}
              AND s.TIPO_TRANSACCION = {t}
        """))

    # C2. Si matchea: ¿cuántos pedidos 2026 obtienen su orden vía seguimiento?
    rep.h("Cobertura pedido→orden vía seguimiento (tipos 8/9)")
    rep.tabla(q(cur, f"""
        SELECT s.TIPO_BIEN,
               COUNT(DISTINCT TRY_CAST(s.NRO_PEDIDO AS INT)) AS pedidos_con_orden_seg
        FROM SIG_SEGUIMIENTO s
        JOIN SIG_ORDEN_ADQUISICION o
            ON o.ANO_EJE = s.ANO_EJE AND o.SEC_EJEC = s.SEC_EJEC
           AND o.TIPO_BIEN = s.TIPO_BIEN AND o.NRO_ORDEN = s.NRO_TRANSACCION
        WHERE s.ANO_EJE = {ANO} AND s.SEC_EJEC = {SEC_EJEC}
          AND s.TIPO_TRANSACCION IN (8, 9)
          AND s.NRO_PEDIDO IS NOT NULL AND LTRIM(s.NRO_PEDIDO) <> ''
        GROUP BY s.TIPO_BIEN
    """))

    # B2. Vínculo directo pedido↔CCMN: eventos con ambos poblados.
    rep.h("Vínculo directo pedido↔CCMN en el seguimiento")
    rep.tabla(q(cur, f"""
        SELECT TIPO_TRANSACCION, TIPO_BIEN,
               COUNT(DISTINCT TRY_CAST(NRO_PEDIDO AS INT)) AS pedidos,
               COUNT(DISTINCT NRO_CONSOLID)                AS consolidados
        FROM SIG_SEGUIMIENTO
        WHERE {W} AND NRO_PEDIDO IS NOT NULL AND LTRIM(NRO_PEDIDO) <> ''
          AND NRO_CONSOLID IS NOT NULL
        GROUP BY TIPO_TRANSACCION, TIPO_BIEN
    """))
    rep.h("Muestra de eventos con pedido + consolidado", 3)
    rep.tabla(q(cur, f"""
        SELECT TOP 25 TIPO_TRANSACCION, TIPO_BIEN, TIPO_CONSOLID,
               NRO_PEDIDO, NRO_CONSOLID, NRO_TRANSACCION, NRO_ORIGEN,
               FECHA_TRANSACCION, ESTADO_TRANSACCION
        FROM SIG_SEGUIMIENTO
        WHERE {W} AND NRO_PEDIDO IS NOT NULL AND LTRIM(NRO_PEDIDO) <> ''
          AND NRO_CONSOLID IS NOT NULL
        ORDER BY FECHA_TRANSACCION DESC
    """), max_rows=25)

    # D. Grafo origen→destino.
    rep.h("SIG_SEGUIMIENTO_SECUENCIA (grafo documento→documento, todos los años)")
    rep.tabla(q(cur, """
        SELECT ANO_EJE, TIPO_TRANSACCION, TIPO_TRANSACCION_DESTINO, COUNT(*) AS filas
        FROM SIG_SEGUIMIENTO_SECUENCIA
        GROUP BY ANO_EJE, TIPO_TRANSACCION, TIPO_TRANSACCION_DESTINO
        ORDER BY ANO_EJE DESC, COUNT(*) DESC
    """), max_rows=60)

    # E. NRO_ORIGEN de tipo 2 (aprobación?): ¿a qué apunta? comparar con pedido.
    rep.h("Tipo 2: relación NRO_ORIGEN vs NRO_PEDIDO (25 muestras)")
    rep.tabla(q(cur, f"""
        SELECT TOP 25 NRO_ORIGEN, NRO_PEDIDO, NRO_TRANSACCION, TIPO_BIEN,
               TIPO_PEDIDO, ESTADO_TRANSACCION, FECHA_TRANSACCION
        FROM SIG_SEGUIMIENTO WHERE {W} AND TIPO_TRANSACCION = 2
        ORDER BY FECHA_TRANSACCION DESC
    """), max_rows=25)

    rep.guardar()
    cn.close()


if __name__ == "__main__":
    main()
