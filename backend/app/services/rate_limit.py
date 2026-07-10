"""Rate limiter in-memory (por proceso).

Para el MVP alcanza. Si mas adelante hay >1 worker uvicorn hara falta Redis;
el reemplazo es interno a este modulo (misma firma).
"""

from __future__ import annotations

import threading
from collections import deque
from time import monotonic

_lock = threading.Lock()
_buckets: dict[str, deque[float]] = {}


def permitir(clave: str, *, max_hits: int, ventana_seg: int) -> bool:
    """Devuelve True si el request cabe dentro del limite.

    `clave` incluye el nombre del endpoint + IP para no mezclar buckets. La
    ventana es deslizante — al recibir un hit se descartan los timestamps
    fuera de la ventana.
    """
    ahora = monotonic()
    limite_inf = ahora - ventana_seg
    with _lock:
        cola = _buckets.setdefault(clave, deque())
        while cola and cola[0] < limite_inf:
            cola.popleft()
        if len(cola) >= max_hits:
            return False
        cola.append(ahora)
    return True


def reset_para_tests() -> None:
    with _lock:
        _buckets.clear()
