"""Censo completo de la BD SIGA_300687.

Responde:
  1. ¿Qué tablas tienen datos? (rowcount via sys.partitions — instantáneo)
  2. ¿Cuáles tienen movimiento en 2026? (para tablas con columna de año)
  3. ¿Qué tablas con datos NO usa el backend actual? (candidatas a explorar)

Salida: resultados/00-inventario.md
"""

from __future__ import annotations

import re
from pathlib import Path

from _db import ANO, Reporte, connect, q, salida_utf8

BACKEND = Path(__file__).parent.parent / "backend" / "app"

# Columnas que funcionan como "año" en SIGA (varía por tabla).
COLS_ANO = ("ANO_EJE", "ANNO_EJEC", "ANO_ORDEN", "ANO_PROCESO", "ANO")


def tablas_usadas_en_backend() -> set[str]:
    """Extrae los nombres SIG_* referenciados en el código del backend."""
    usadas: set[str] = set()
    for py in BACKEND.rglob("*.py"):
        texto = py.read_text(encoding="utf-8", errors="ignore")
        usadas.update(m.upper() for m in re.findall(r"\bSIG_[A-Z_0-9]+", texto))
    return usadas


def main() -> None:
    salida_utf8()
    rep = Reporte("00-inventario", "Inventario de tablas SIGA_300687")
    cn = connect()
    cur = cn.cursor()

    # 1. Rowcount de todas las tablas (metadata, no escanea).
    tablas = q(cur, """
        SELECT t.name AS tabla, SUM(p.rows) AS filas
        FROM sys.tables t
        JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
        GROUP BY t.name
        ORDER BY SUM(p.rows) DESC
    """)
    con_datos = [t for t in tablas if t["filas"] > 0]
    rep.p(f"**{len(tablas)}** tablas; **{len(con_datos)}** con al menos una fila.")

    rep.h("Top 60 por volumen")
    rep.tabla(con_datos[:60])

    # 2. Columnas de cada tabla con datos (para saber cuáles filtran por año).
    cols = q(cur, """
        SELECT t.name AS tabla, c.name AS columna
        FROM sys.tables t
        JOIN sys.columns c ON c.object_id = t.object_id
    """)
    cols_por_tabla: dict[str, list[str]] = {}
    for r in cols:
        cols_por_tabla.setdefault(r["tabla"], []).append(r["columna"].upper())

    # 3. Cobertura 2026 por tabla (solo tablas con columna de año y datos).
    rep.h(f"Tablas con movimiento en {ANO}")
    con_2026: list[dict] = []
    sin_col_ano: list[str] = []
    for t in con_datos:
        nombre = t["tabla"]
        col_ano = next(
            (c for c in COLS_ANO if c in cols_por_tabla.get(nombre, [])), None
        )
        if col_ano is None:
            sin_col_ano.append(nombre)
            continue
        try:
            cur.execute(
                f"SELECT COUNT(*) FROM [{nombre}] WHERE [{col_ano}] = ?", (ANO,)
            )
            n = cur.fetchone()[0]
        except Exception:
            continue
        if n > 0:
            con_2026.append({
                "tabla": nombre, "col_ano": col_ano,
                "filas_2026": n, "filas_total": t["filas"],
            })
    con_2026.sort(key=lambda r: -r["filas_2026"])
    rep.p(f"**{len(con_2026)}** tablas tienen filas en {ANO}.")
    rep.tabla(con_2026, max_rows=250)

    # 4. Qué usa el backend hoy vs qué existe con datos 2026.
    usadas = tablas_usadas_en_backend()
    rep.h("Tablas con datos 2026 que el backend NO usa")
    no_usadas = [r for r in con_2026 if r["tabla"].upper() not in usadas]
    rep.p(
        f"El backend referencia **{len(usadas)}** tablas SIG_*. "
        f"De las {len(con_2026)} con datos {ANO}, **{len(no_usadas)}** no se usan:"
    )
    rep.tabla(no_usadas, max_rows=250)

    rep.h("Tablas maestras/config con datos pero sin columna de año")
    rep.p(", ".join(sorted(sin_col_ano)))

    rep.guardar()
    cn.close()


if __name__ == "__main__":
    main()
