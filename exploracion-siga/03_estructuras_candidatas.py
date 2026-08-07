"""Estructura + muestra de las tablas candidatas que el backend no usa.

Objetivo: encontrar (a) un vínculo duro pedido↔cuadro/orden que la cascada
actual no conoce, y (b) la cadena de montos SIAF dentro de SIGA
(certificado → comprometido → devengado → girado por expediente).

Salida: resultados/03-estructuras-candidatas.md
"""

from __future__ import annotations

from _db import ANO, SEC_EJEC, Reporte, connect, q, salida_utf8

CANDIDATAS = [
    # posible vínculo pedido -> cuadro de adquisición (detalle)
    "SIG_DETALLE_METAS_CUADRO",
    "SIG_DETALLE_BSERV_CUADRO",
    "SIG_DEPEN_META_CUADRO",
    "SIG_CUADRO_NECESIDAD",
    "SIG_CUADRO_NECESIDAD_DET",
    # pecosa / almacén con detalle presupuestal
    "SIG_DETALLE_PECOSA",
    "SIG_DETALLE_MOVIM_PPTO",
    # cadena orden -> expediente -> SIAF
    "SIG_ORDEN_INTERFASE",
    "SIG_ORDEN_PRESUPUESTO",
    "SIG_ORDEN_SECUENCIA",
    "SIG_EXP_SIGA",
    "SIG_EXP_SIGA_PPTO",
    "SIG_EXP_SIGA_SECU",
    "SIG_EXP_SIGA_DOCU",
    "INTF_CAB",
    "INTF_CAB_RET",
    "INTF_DET",
    # certificación con fases
    "SIG_CERTIFICACION_FASE",
    "SIG_CERTIFICACION_PPTO",
    "SIG_CERTIFICACION_OPERACION",
    # techo (autoritativo de PIM/saldo según Docs)
    "SIG_TECHO_PRESUPUESTO",
    # contratos
    "SIG_CONTRATOS",
    "SIG_CONTRATO_ITEM",
]


def main() -> None:
    salida_utf8()
    rep = Reporte("03-estructuras-candidatas",
                  "Estructura y muestra de tablas candidatas")
    cn = connect()
    cur = cn.cursor()

    for t in CANDIDATAS:
        rep.h(t)
        cols = q(cur, """
            SELECT c.name AS columna, ty.name AS tipo
            FROM sys.columns c
            JOIN sys.types ty ON ty.user_type_id = c.user_type_id
            WHERE c.object_id = OBJECT_ID(?)
            ORDER BY c.column_id
        """, (t,))
        if not cols:
            rep.p("_(no existe)_")
            continue
        rep.p("Columnas: " + ", ".join(f"`{c['columna']}`" for c in cols))
        # Muestra 2026 si tiene columna de año; si no, muestra general.
        nombres = {c["columna"].upper() for c in cols}
        col_ano = next((c for c in ("ANO_EJE", "ANNO_EJEC") if c in nombres), None)
        try:
            if col_ano:
                filas = q(cur, f"""
                    SELECT TOP 4 * FROM [{t}]
                    WHERE [{col_ano}] = {ANO} AND SEC_EJEC = {SEC_EJEC}
                    ORDER BY 1
                """)
            else:
                filas = q(cur, f"SELECT TOP 4 * FROM [{t}]")
            rep.tabla(filas, max_rows=4)
        except Exception as e:  # noqa: BLE001
            rep.p(f"_error muestreando: {e}_")

    rep.guardar()
    cn.close()


if __name__ == "__main__":
    main()
