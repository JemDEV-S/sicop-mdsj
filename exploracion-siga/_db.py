"""Utilidad compartida de los scripts de exploración SIGA.

Solo lectura. Conexión directa pyodbc (no depende del backend) para que los
scripts corran aislados del proyecto.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import pyodbc

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=.;DATABASE=SIGA_300687;Trusted_Connection=yes;"
)

SEC_EJEC = 300687
ANO = 2026

RESULTADOS = Path(__file__).parent / "resultados"


def connect() -> pyodbc.Connection:
    return pyodbc.connect(CONN_STR, timeout=60)


def q(cur: pyodbc.Cursor, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Ejecuta un SELECT y devuelve lista de dicts."""
    cur.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def md_table(rows: list[dict[str, Any]], max_rows: int = 200) -> str:
    """Render simple de lista de dicts a tabla markdown."""
    if not rows:
        return "_(sin filas)_\n"
    cols = list(rows[0].keys())
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows[:max_rows]:
        vals = []
        for c in cols:
            v = r[c]
            if v is None:
                v = ""
            s = str(v).replace("\n", " ").replace("|", "\\|")
            if len(s) > 80:
                s = s[:77] + "..."
            vals.append(s)
        out.append("| " + " | ".join(vals) + " |")
    if len(rows) > max_rows:
        out.append(f"\n_... {len(rows) - max_rows} filas más omitidas_")
    return "\n".join(out) + "\n"


class Reporte:
    """Acumula secciones markdown y las escribe a resultados/<nombre>.md."""

    def __init__(self, nombre: str, titulo: str):
        self.nombre = nombre
        self.buf = io.StringIO()
        self.buf.write(f"# {titulo}\n\n")
        self.buf.write("_Generado por el script homónimo; no editar a mano._\n\n")

    def h(self, texto: str, nivel: int = 2) -> None:
        self.buf.write(f"\n{'#' * nivel} {texto}\n\n")

    def p(self, texto: str) -> None:
        self.buf.write(texto + "\n\n")

    def tabla(self, rows: list[dict[str, Any]], max_rows: int = 200) -> None:
        self.buf.write(md_table(rows, max_rows) + "\n")

    def guardar(self) -> Path:
        RESULTADOS.mkdir(exist_ok=True)
        destino = RESULTADOS / f"{self.nombre}.md"
        destino.write_text(self.buf.getvalue(), encoding="utf-8")
        print(f"[ok] {destino}")
        return destino


def salida_utf8() -> None:
    """Windows: fuerza stdout utf-8 para que los prints no revienten."""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
