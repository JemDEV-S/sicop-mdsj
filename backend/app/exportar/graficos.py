"""Gráficos para los PDF de reportes (reportlab.graphics, puro Python).

Se dibujan con primitivas de `reportlab.graphics.shapes` en vez de las clases de
`charts` para tener control fino del estilo institucional (colores de la paleta,
tipografía, etiquetas legibles) y evitar la estética "por defecto" de reportlab.

Un gráfico es un dict-spec independiente de datos de BD; el reporte lo arma en
`reportes.py` a partir de sus filas y `pdf.generar()` lo renderiza. Así el
generador no sabe de negocio y el reporte no sabe de dibujo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.units import mm

# ── Paleta institucional (misma que globals.css del frontend) ────────────
AZUL = colors.HexColor("#3484A5")       # primary
AZUL_CLARO = colors.HexColor("#7FB3C8")  # primary aclarado (comprometido)
VERDE = colors.HexColor("#2CA792")      # secondary / semáforo ok
AMARILLO = colors.HexColor("#F0C84F")   # accent / semáforo alerta
ROJO = colors.HexColor("#C0392B")       # destructive / semáforo crítico
GRIS = colors.HexColor("#8B98A3")       # texto tenue / sin dato
GRIS_BARRA = colors.HexColor("#E3E9EC")  # fondo de barra
TEXTO = colors.HexColor("#1F2933")


@dataclass(frozen=True)
class SegmentoGrafico:
    """Una barra (en 'barras') o un segmento (en 'apilada')."""

    etiqueta: str
    valor: float
    color: colors.Color = AZUL
    # Texto a la derecha de la barra (monto formateado, % o conteo).
    valor_texto: str = ""


@dataclass(frozen=True)
class Grafico:
    tipo: Literal["barras", "apilada"]
    titulo: str
    segmentos: list[SegmentoGrafico] = field(default_factory=list)
    # Solo 'apilada': texto bajo la barra que explica el reparto.
    nota: str = ""


def _titulo(dibujo: Drawing, texto: str, ancho: float, y: float) -> None:
    dibujo.add(String(0, y, texto, fontName="Helvetica-Bold", fontSize=9, fillColor=TEXTO))


def dibujar_barras(g: Grafico, ancho: float) -> Drawing:
    """Barras horizontales etiqueta → barra → valor. Ancho proporcional al máx."""
    fila_h = 6 * mm
    margen_top = 7 * mm
    n = len(g.segmentos)
    alto = margen_top + n * fila_h + 2 * mm
    d = Drawing(ancho, alto)
    _titulo(d, g.titulo, ancho, alto - 4 * mm)

    label_w = 42 * mm
    valor_w = 30 * mm
    barra_x = label_w
    barra_w_max = max(10 * mm, ancho - label_w - valor_w)
    max_val = max((abs(s.valor) for s in g.segmentos), default=0) or 1

    for i, s in enumerate(g.segmentos):
        y = alto - margen_top - (i + 1) * fila_h + 1.5 * mm
        # Etiqueta (recortada).
        etq = s.etiqueta if len(s.etiqueta) <= 34 else s.etiqueta[:31] + "…"
        d.add(String(0, y + 0.8 * mm, etq, fontName="Helvetica", fontSize=7.5, fillColor=TEXTO))
        # Riel de fondo.
        d.add(Rect(barra_x, y, barra_w_max, 3.4 * mm, fillColor=GRIS_BARRA, strokeColor=None))
        # Barra.
        w = barra_w_max * (abs(s.valor) / max_val)
        if w > 0:
            d.add(Rect(barra_x, y, w, 3.4 * mm, fillColor=s.color, strokeColor=None))
        # Valor a la derecha.
        if s.valor_texto:
            d.add(String(
                barra_x + barra_w_max + 2 * mm, y + 0.8 * mm, s.valor_texto,
                fontName="Helvetica", fontSize=7.5, fillColor=TEXTO,
            ))
    return d


def dibujar_apilada(g: Grafico, ancho: float) -> Drawing:
    """Una barra horizontal segmentada por estado + leyenda debajo."""
    barra_h = 6 * mm
    margen_top = 7 * mm
    leyenda_h = 5 * mm
    alto = margen_top + barra_h + leyenda_h + (4 * mm if g.nota else 0) + 2 * mm
    d = Drawing(ancho, alto)
    _titulo(d, g.titulo, ancho, alto - 4 * mm)

    total = sum(max(0.0, s.valor) for s in g.segmentos) or 1
    y_barra = alto - margen_top - barra_h
    x = 0.0
    # Riel de fondo (por si el total no llena, no debería).
    d.add(Rect(0, y_barra, ancho, barra_h, fillColor=GRIS_BARRA, strokeColor=None))
    for s in g.segmentos:
        w = ancho * (max(0.0, s.valor) / total)
        if w > 0:
            d.add(Rect(x, y_barra, w, barra_h, fillColor=s.color, strokeColor=None))
            x += w

    # Leyenda: cuadrito de color + etiqueta + conteo/%, repartida en el ancho.
    presentes = [s for s in g.segmentos if s.valor > 0]
    n = max(1, len(presentes))
    celda_w = ancho / n
    y_ley = y_barra - leyenda_h + 1 * mm
    for i, s in enumerate(presentes):
        cx = i * celda_w
        d.add(Rect(cx, y_ley, 2.4 * mm, 2.4 * mm, fillColor=s.color, strokeColor=None))
        txt = f"{s.etiqueta}: {s.valor_texto}" if s.valor_texto else s.etiqueta
        d.add(String(cx + 3.5 * mm, y_ley + 0.3 * mm, txt, fontName="Helvetica", fontSize=7, fillColor=TEXTO))

    if g.nota:
        d.add(String(0, 1 * mm, g.nota, fontName="Helvetica-Oblique", fontSize=6.5, fillColor=GRIS))
    return d
