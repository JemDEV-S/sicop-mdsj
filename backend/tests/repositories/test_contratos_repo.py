"""Tests de `contratos_repo.contratos_por_vencer` contra un mock de Session.

Iteración 4 (Docs/consolidacion-backend-presupuestal.md): la ventana de
vencimiento se mide contra una `fecha_referencia` parametrizable (default = hoy
del servidor), para que el widget tenga sentido también en desarrollo sobre el
backup del SIGA. Verifican la forma de la query y los binds — no golpean la BD.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock

from app.repositories import contratos_repo


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return self._rows


def _mock_conn(rows: list[Any] | None = None) -> MagicMock:
    conn = MagicMock()
    conn.execute.return_value = _Result(rows or [])
    ctx = MagicMock()
    ctx.__enter__.return_value = conn
    ctx.__exit__.return_value = False
    return ctx, conn


def test_sin_fecha_referencia_usa_getdate(monkeypatch):
    ctx, conn = _mock_conn()
    monkeypatch.setattr(contratos_repo, "get_connection", lambda: ctx)

    contratos_repo.contratos_por_vencer(dias=30)

    sql = str(conn.execute.call_args[0][0])
    binds = conn.execute.call_args[0][1]
    assert "GETDATE()" in sql               # referencia = hoy del servidor
    assert ":fref" not in sql               # no se bindea fecha
    assert "fref" not in binds


def test_con_fecha_referencia_bindea_y_no_usa_getdate(monkeypatch):
    ctx, conn = _mock_conn()
    monkeypatch.setattr(contratos_repo, "get_connection", lambda: ctx)

    ref = date(2024, 5, 1)
    contratos_repo.contratos_por_vencer(dias=60, fecha_referencia=ref)

    sql = str(conn.execute.call_args[0][0])
    binds = conn.execute.call_args[0][1]
    assert "GETDATE()" not in sql           # ya no depende del reloj del servidor
    assert ":fref" in sql                   # usa la fecha parametrizada
    assert binds["fref"] == ref
    assert binds["dias"] == 60


def test_fija_sec_ejec(monkeypatch):
    ctx, conn = _mock_conn()
    monkeypatch.setattr(contratos_repo, "get_connection", lambda: ctx)

    contratos_repo.contratos_por_vencer()
    binds = conn.execute.call_args[0][1]
    # RN-01: toda query SIGA fija SEC_EJEC.
    assert "sec_ejec" in binds
