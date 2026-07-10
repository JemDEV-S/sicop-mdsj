"""Reconstrucción de la columna `ruta` (ltree) de ref.centros_costo.

Estrategia: BFS desde las raíces (`centro_padre IS NULL`) hacia las hojas.
Cada nodo hereda la ruta del padre + su propio label.

Convención de labels:
- Los códigos SIGA usan `.` como separador visual (`01.01.02`). ltree usa
  `.` como separador de niveles, así que dentro del label se reemplaza por
  `_`. Ejemplo: `01.01.02` → label `01_01_02`.
- La ruta arranca en `root` para poder consultar toda la jerarquía con
  `ruta <@ 'root'` (sinónimo de "todos los centros de costo").

Retorna un diccionario codigo → (ruta_ltree, nivel) que el job usa para
actualizar cada fila tras el INSERT SELECT del swap.
"""

from collections import deque
from collections.abc import Iterable
from typing import Any


def _codigo_a_label(codigo: str) -> str:
    """Convierte un código SIGA en un label válido para ltree.

    ltree acepta `[A-Za-z0-9_]` en cada label; los `.` se sustituyen por `_`.
    """
    return codigo.replace(".", "_").replace("-", "_")


def construir_rutas(
    centros: Iterable[dict[str, Any]],
) -> dict[str, tuple[str, int]]:
    """Construye la ruta ltree y el nivel para cada centro.

    Args:
        centros: iterable de dicts con al menos `codigo` y `centro_padre`.

    Returns:
        dict `codigo → (ruta, nivel)` con:
        - `ruta` en formato `root.<label_1>.<label_2>...` (str, no ltree)
        - `nivel` = profundidad desde root (root=0, hijo directo=1, ...)

    Nodos con padre no encontrado en el input (padres huérfanos) se tratan
    como raíces adicionales bajo `root` — nunca deben quedar sin ruta,
    porque `ref.centros_costo.ruta` es NOT NULL.
    """
    por_codigo: dict[str, dict[str, Any]] = {c["codigo"]: c for c in centros}

    hijos_por_padre: dict[str | None, list[str]] = {}
    for codigo, cc in por_codigo.items():
        padre = cc.get("centro_padre")
        # Los padres que no existan en el input se convierten a "raíz" (None).
        if padre is not None and padre not in por_codigo:
            padre = None
        hijos_por_padre.setdefault(padre, []).append(codigo)

    rutas: dict[str, tuple[str, int]] = {}
    cola: deque[tuple[str, str, int]] = deque()  # (codigo, ruta_prefijo, nivel_padre)

    # Semillas: todos los nodos raíz (padre == None) parten con prefijo "root"
    for codigo in hijos_por_padre.get(None, []):
        cola.append((codigo, "root", 0))

    while cola:
        codigo, prefijo, nivel_padre = cola.popleft()
        label = _codigo_a_label(codigo)
        ruta = f"{prefijo}.{label}"
        nivel = nivel_padre + 1
        rutas[codigo] = (ruta, nivel)
        for hijo in hijos_por_padre.get(codigo, []):
            cola.append((hijo, ruta, nivel))

    # Detección de ciclos u orfandad no cubierta: si algún código no obtuvo
    # ruta, forzamos como raíz para garantizar NOT NULL.
    for codigo in por_codigo:
        if codigo not in rutas:
            rutas[codigo] = (f"root.{_codigo_a_label(codigo)}", 1)

    return rutas
