"""Modulo de exportacion (Excel + PDF).

Cada "reporte" se registra en `reportes.py` con:
- codigo (identificador)
- titulo (para header)
- funcion `obtener_datos(db, filtros, user)` que devuelve `list[dict]`
- lista de columnas `[{key, label, formato}]`

Los formatters (`excel.py`, `pdf.py`) reciben esos datos + metadata y generan
el binario.
"""
