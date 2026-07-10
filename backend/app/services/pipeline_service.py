"""Servicio pipeline: agrega deteccion de estancados (RN-02).

RN-02 default: pedido estancado si lleva > 15 dias en la etapa actual sin cambio.
El umbral se lee de `sistema.umbrales_alertas` (codigo_alerta='pedido_estancado').
Si no existe, usa `DEFAULT_DIAS`.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories import pipeline_repo

DEFAULT_DIAS = 15


def _umbral_dias(db: Session) -> int:
    row = db.execute(
        text(
            """
            SELECT parametros
              FROM sistema.umbrales_alertas
             WHERE codigo_alerta = 'pedido_estancado'
            """
        )
    ).first()
    if row is None:
        return DEFAULT_DIAS
    params = row[0]
    if isinstance(params, str):
        params = json.loads(params)
    return int(params.get("dias", DEFAULT_DIAS))


def _fecha_etapa(fila: dict[str, Any]) -> date | None:
    """Devuelve la fecha del cambio a la etapa actual (la mas reciente conocida)."""
    if fila["etapa"] == "cerrado":
        return fila.get("FECHA_ATENC") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if fila["etapa"] in ("devengado", "conformidad"):
        return fila.get("FECHA_ATENC") or fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    if fila["etapa"] == "con_orden":
        return fila.get("FECHA_APROB") or fila.get("FECHA_PEDIDO")
    return fila.get("FECHA_PEDIDO")


def _enriquecer(fila: dict[str, Any], hoy: date, umbral: int) -> dict[str, Any]:
    f = _fecha_etapa(fila)
    if f is not None:
        # SQL Server DATETIME llega como datetime; normalizamos a date.
        if isinstance(f, datetime):
            f = f.date()
        dias = (hoy - f).days
        fila["dias_en_etapa"] = dias
        fila["estancado"] = dias > umbral and fila["etapa"] not in ("cerrado", "devengado")
    return fila


def _renombrar(fila: dict[str, Any]) -> dict[str, Any]:
    """Renombra keys mayusculas de SQL Server a snake_case Pydantic + coerce tipos."""
    mapping = {
        "ANO_EJE": "ano_eje",
        "SEC_EJEC": "sec_ejec",
        "NRO_PEDIDO": "nro_pedido",
        "TIPO_BIEN": "tipo_bien",
        "CENTRO_COSTO": "centro_costo",
        "FECHA_PEDIDO": "fecha_pedido",
        "FECHA_APROB": "fecha_aprob",
        "FECHA_ATENC": "fecha_atenc",
    }
    out: dict[str, Any] = {}
    for k, v in fila.items():
        nk = mapping.get(k, k)
        if isinstance(v, datetime):
            v = v.date()
        elif nk == "sec_ejec" and v is not None:
            v = str(v)
        elif nk == "monto_total" and v is not None:
            v = float(v)
        out[nk] = v
    # Strip whitespace en campos varchar del centro_costo (CHAR con padding).
    cc = out.get("centro_costo")
    if isinstance(cc, str):
        out["centro_costo"] = cc.strip()
    return out


def kanban(
    db: Session, *, ano: int, centros: list[str] | None
) -> dict[str, list[dict[str, Any]]]:
    kanban_raw = pipeline_repo.pipeline_kanban(ano, centros)
    umbral = _umbral_dias(db)
    hoy = date.today()
    return {
        etapa: [_renombrar(_enriquecer(f, hoy, umbral)) for f in filas]
        for etapa, filas in kanban_raw.items()
    }


def estancados(
    db: Session, *, ano: int, centros: list[str] | None
) -> list[dict[str, Any]]:
    """Solo los pedidos marcados como estancado (para el widget de alertas)."""
    kb = kanban(db, ano=ano, centros=centros)
    todos = [f for lst in kb.values() for f in lst]
    return sorted(
        [f for f in todos if f.get("estancado")],
        key=lambda f: f.get("dias_en_etapa") or 0,
        reverse=True,
    )
