"""¿Puede el pipeline salir de un LOG DE EVENTOS en vez de 12 LEFT JOIN?

Hipótesis: SIGA ya registra la historia de cada documento en tablas de
seguimiento que el backend actual casi no usa:

  - SIG_SEGUIMIENTO          (39k filas; hoy solo se usa TIPO_TRANSACCION=19)
  - SIG_SEGUIMIENTO_ESTADO   (99k filas; NO se usa)
  - SIG_DOCUMENTO_ESTADO     (21k filas; NO se usa; sin col. de año)
  - SIG_TRANSACCION_ESTADO   (catálogo: qué es cada TIPO_TRANSACCION)
  - SIG_PROCESO_ETAPAS       (catálogo: ¿etapas oficiales del proceso?)
  - SIG_MAESTRO_PROCESO      (¿cabecera de procesos?)

Si el seguimiento cubre los pedidos/órdenes de 2026, el pipeline se puede
reconstruir como TIMELINE REAL (evento + fecha + usuario) en lugar de
inferirlo con flags y heurísticas de match.

Salida: resultados/01-seguimiento-eventos.md
"""

from __future__ import annotations

from _db import ANO, SEC_EJEC, Reporte, connect, q, salida_utf8

TABLAS = [
    "SIG_SEGUIMIENTO",
    "SIG_SEGUIMIENTO_ESTADO",
    "SIG_DOCUMENTO_ESTADO",
    "SIG_TRANSACCION_ESTADO",
    "SIG_PROCESO_ETAPAS",
    "SIG_MAESTRO_PROCESO",
    "SIG_SEGUIMIENTO_SECUENCIA",
]


def columnas(cur, tabla: str) -> list[dict]:
    return q(cur, """
        SELECT c.name AS columna, ty.name AS tipo, c.max_length AS len
        FROM sys.columns c
        JOIN sys.types ty ON ty.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID(?)
        ORDER BY c.column_id
    """, (tabla,))


def main() -> None:
    salida_utf8()
    rep = Reporte("01-seguimiento-eventos", "SIG_SEGUIMIENTO como log de eventos")
    cn = connect()
    cur = cn.cursor()

    rep.h("Estructura de las tablas de seguimiento")
    for t in TABLAS:
        cols = columnas(cur, t)
        rep.h(t, 3)
        rep.tabla(cols)

    # Catálogo de transacciones: qué significa cada TIPO_TRANSACCION.
    rep.h("Catálogo SIG_TRANSACCION_ESTADO")
    rep.tabla(q(cur, "SELECT * FROM SIG_TRANSACCION_ESTADO"), max_rows=300)

    rep.h("Catálogo SIG_PROCESO_ETAPAS")
    rep.tabla(q(cur, "SELECT * FROM SIG_PROCESO_ETAPAS"), max_rows=300)

    rep.h("Catálogo SIG_MAESTRO_PROCESO (2026)")
    rep.tabla(q(cur, f"SELECT * FROM SIG_MAESTRO_PROCESO WHERE ANO_EJE = {ANO}"),
              max_rows=120)

    # Distribución de eventos 2026 en SIG_SEGUIMIENTO.
    rep.h(f"SIG_SEGUIMIENTO {ANO}: eventos por TIPO_TRANSACCION")
    rep.tabla(q(cur, f"""
        SELECT s.TIPO_TRANSACCION,
               COUNT(*)                          AS eventos,
               COUNT(DISTINCT s.NRO_PEDIDO)      AS pedidos_distintos,
               MIN(s.FECHA_TRANSACCION)          AS primera_fecha,
               MAX(s.FECHA_TRANSACCION)          AS ultima_fecha
        FROM SIG_SEGUIMIENTO s
        WHERE s.ANO_EJE = {ANO} AND s.SEC_EJEC = {SEC_EJEC}
        GROUP BY s.TIPO_TRANSACCION
        ORDER BY s.TIPO_TRANSACCION
    """))

    # Distribución 2026 en SIG_SEGUIMIENTO_ESTADO (la tabla grande sin usar).
    rep.h(f"SIG_SEGUIMIENTO_ESTADO {ANO}: por tipo de transacción/estado")
    cols_se = {c["columna"].upper() for c in columnas(cur, "SIG_SEGUIMIENTO_ESTADO")}
    grupo = [c for c in ("TIPO_TRANSACCION", "TIPO_TRANSAC", "ESTADO",
                         "TIPO_DOCUMENTO", "TIPO_MOVIMIENTO") if c in cols_se]
    if grupo:
        sel = ", ".join(grupo)
        rep.tabla(q(cur, f"""
            SELECT {sel}, COUNT(*) AS filas
            FROM SIG_SEGUIMIENTO_ESTADO
            WHERE ANO_EJE = {ANO} AND SEC_EJEC = {SEC_EJEC}
            GROUP BY {sel}
            ORDER BY COUNT(*) DESC
        """, ()), max_rows=100)
    rep.p(f"Columnas reales: {sorted(cols_se)}")

    # Muestra cruda de SIG_SEGUIMIENTO_ESTADO para entender el grano.
    rep.h("Muestra SIG_SEGUIMIENTO_ESTADO (20 filas 2026)")
    rep.tabla(q(cur, f"""
        SELECT TOP 20 * FROM SIG_SEGUIMIENTO_ESTADO
        WHERE ANO_EJE = {ANO} AND SEC_EJEC = {SEC_EJEC}
        ORDER BY 1
    """), max_rows=20)

    rep.h("Muestra SIG_DOCUMENTO_ESTADO (20 filas)")
    rep.tabla(q(cur, "SELECT TOP 20 * FROM SIG_DOCUMENTO_ESTADO"), max_rows=20)

    # Cobertura: ¿cuántos pedidos 2026 tienen al menos un evento de seguimiento?
    rep.h("Cobertura del seguimiento sobre los pedidos 2026")
    rep.tabla(q(cur, f"""
        SELECT
            p.TIPO_BIEN,
            COUNT(DISTINCT CAST(p.NRO_PEDIDO AS VARCHAR(10)))       AS pedidos,
            COUNT(DISTINCT CASE WHEN s.NRO_PEDIDO IS NOT NULL
                  THEN CAST(p.NRO_PEDIDO AS VARCHAR(10)) END)        AS con_seguimiento
        FROM SIG_PEDIDOS p
        LEFT JOIN SIG_SEGUIMIENTO s
            ON s.ANO_EJE = p.ANO_EJE AND s.SEC_EJEC = p.SEC_EJEC
           AND s.TIPO_BIEN = p.TIPO_BIEN
           AND TRY_CAST(s.NRO_PEDIDO AS INT) = p.NRO_PEDIDO
        WHERE p.ANO_EJE = {ANO} AND p.SEC_EJEC = {SEC_EJEC}
        GROUP BY p.TIPO_BIEN
    """))

    # Timeline completo de un pedido conocido (232/S se usó de referencia en Docs).
    rep.h("Timeline crudo del pedido 232/S vía SIG_SEGUIMIENTO")
    rep.tabla(q(cur, f"""
        SELECT * FROM SIG_SEGUIMIENTO
        WHERE ANO_EJE = {ANO} AND SEC_EJEC = {SEC_EJEC}
          AND TIPO_BIEN = 'S' AND TRY_CAST(NRO_PEDIDO AS INT) = 232
        ORDER BY FECHA_TRANSACCION
    """), max_rows=60)

    rep.guardar()
    cn.close()


if __name__ == "__main__":
    main()
