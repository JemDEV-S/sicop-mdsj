"""Generacion de PDF con reportlab.

WeasyPrint queda documentado en pyproject.toml para produccion (Docker Linux),
pero en dev Windows falla al cargar libgobject-2.0. `reportlab` es puro Python
y funciona sin dependencias nativas.
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.exportar.reportes import Reporte


def _formato_valor(valor: Any, formato: str) -> str:
    if valor is None:
        return ""
    if formato == "moneda":
        try:
            return f"S/ {float(valor):,.2f}"
        except (TypeError, ValueError):
            return str(valor)
    if formato == "numero":
        try:
            return f"{int(valor):,}"
        except (TypeError, ValueError):
            return str(valor)
    if formato == "porcentaje":
        try:
            return f"{float(valor):.2f}%"
        except (TypeError, ValueError):
            return str(valor)
    if formato == "fecha":
        if isinstance(valor, datetime):
            return valor.date().isoformat()
        if isinstance(valor, date):
            return valor.isoformat()
        return str(valor)
    s = str(valor)
    return s if len(s) <= 60 else s[:57] + "..."


def generar(
    reporte: Reporte,
    datos: list[dict[str, Any]],
    *,
    filtros: dict[str, Any] | None = None,
    usuario_nombre: str | None = None,
) -> bytes:
    buf = BytesIO()

    # Landscape para tablas anchas.
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=reporte.titulo,
        author="SICOP-MDSJ",
    )
    styles = getSampleStyleSheet()
    story = []

    # Encabezado
    story.append(Paragraph(
        "Municipalidad Distrital de San Jer&oacute;nimo (Cusco)",
        styles["Title"],
    ))
    story.append(Paragraph(reporte.titulo, styles["Heading2"]))

    generado = f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    if usuario_nombre:
        generado += f" por {usuario_nombre}"
    story.append(Paragraph(generado, styles["Normal"]))

    if filtros:
        filtro_str = " · ".join(
            f"{k}={v}" for k, v in filtros.items() if v not in (None, "")
        )
        if filtro_str:
            story.append(Paragraph(f"Filtros: {filtro_str}", styles["Italic"]))

    story.append(Spacer(1, 6 * mm))

    # Tabla de datos
    header = [c.label for c in reporte.columnas]
    tabla_datos: list[list[Any]] = [header]
    for fila in datos:
        tabla_datos.append([
            _formato_valor(fila.get(c.key), c.formato) for c in reporte.columnas
        ])

    if reporte.con_totales and reporte.columnas_totalizables and datos:
        total_row: list[Any] = []
        for c in reporte.columnas:
            if c.key in reporte.columnas_totalizables:
                total = sum(
                    float(f.get(c.key) or 0)
                    for f in datos
                    if f.get(c.key) is not None
                )
                total_row.append(_formato_valor(total, c.formato))
            elif c is reporte.columnas[0]:
                total_row.append("TOTAL")
            else:
                total_row.append("")
        tabla_datos.append(total_row)

    tabla = Table(tabla_datos, repeatRows=1)
    estilo = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B7B7B7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2 if reporte.con_totales else -1),
         [colors.white, colors.HexColor("#F2F2F2")]),
    ])
    if reporte.con_totales and datos:
        estilo.add("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D9E1F2"))
        estilo.add("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
    tabla.setStyle(estilo)
    story.append(tabla)

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        f"Total de registros: {len(datos)}", styles["Normal"]
    ))

    doc.build(story)
    return buf.getvalue()
