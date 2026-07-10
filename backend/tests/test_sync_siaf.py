"""Test del cliente MEF con respuestas simuladas.

No golpeamos la base — solo validamos:
- Parseo de la respuesta datastore_search_sql (success/records).
- Paginacion con LIMIT/OFFSET termina cuando llega < page_size.
- Reintentos con 5xx y aborto con 409.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest

from app.services import mef_client as mef_module
from app.services.mef_client import MefApiError, MefApiTransientError, MefClient


def _mock_response(
    status: int, payload: dict[str, Any] | None = None, texto: str = ""
) -> httpx.Response:
    if payload is not None:
        return httpx.Response(status, json=payload)
    return httpx.Response(status, text=texto)


def test_datastore_search_sql_devuelve_records():
    payload = {"success": True, "result": {"records": [{"A": 1}, {"A": 2}]}}
    with patch.object(httpx.Client, "get", return_value=_mock_response(200, payload)):
        with MefClient() as c:
            filas = c.datastore_search_sql("SELECT 1")
    assert filas == [{"A": 1}, {"A": 2}]


def test_datastore_success_false_lanza_error():
    payload = {"success": False, "error": {"message": "boom"}}
    with patch.object(httpx.Client, "get", return_value=_mock_response(200, payload)):
        with MefClient() as c:
            with pytest.raises(MefApiError):
                c.datastore_search_sql("SELECT 1")


def test_http_409_es_no_recuperable():
    """La API MEF devuelve 409 con SQL invalido — no se debe reintentar."""
    calls = {"n": 0}

    def fake_get(self, url, params=None):
        calls["n"] += 1
        return _mock_response(409, texto="Too many columns")

    with patch.object(httpx.Client, "get", fake_get):
        with MefClient() as c:
            with pytest.raises(MefApiError):
                c.datastore_search_sql("SELECT *")
    assert calls["n"] == 1  # sin reintentos


def test_http_500_reintenta_y_luego_falla(monkeypatch):
    """5xx dispara reintentos con backoff; tras 3 intentos falla."""
    calls = {"n": 0}

    def fake_get(self, url, params=None):
        calls["n"] += 1
        return _mock_response(500, texto="internal")

    # Anular el sleep de tenacity para que el test sea instantaneo.
    monkeypatch.setattr(
        "app.services.mef_client.wait_exponential",
        lambda **_: (lambda _rs: 0),
    )
    # Igual monkeypatch al modulo tenacity subyacente por si acaso.
    import tenacity

    monkeypatch.setattr(tenacity, "nap", type("N", (), {"sleep": lambda _s: None})())

    with patch.object(httpx.Client, "get", fake_get):
        with MefClient() as c:
            with pytest.raises(MefApiTransientError):
                c.datastore_search_sql("SELECT 1")
    assert calls["n"] == 3  # 3 intentos


def test_paginacion_termina_cuando_pagina_incompleta():
    """paginar_sql corta la iteracion cuando la pagina trae < page_size filas."""

    calls = {"n": 0}

    def paginado(*, limit, offset):
        # 3 filas → menos que page_size (100) → termina tras la primera.
        return [{"SEC_FUNC": 1}, {"SEC_FUNC": 2}, {"SEC_FUNC": 3}]

    def fake_get(self, url, params=None):
        calls["n"] += 1
        return _mock_response(
            200,
            payload={
                "success": True,
                "result": {"records": paginado(limit=100, offset=0)},
            },
        )

    with patch.object(httpx.Client, "get", fake_get):
        with MefClient() as c:
            paginas = list(
                c.paginar_sql("SELECT ... LIMIT {limit} OFFSET {offset}")
            )
    assert calls["n"] == 1
    assert len(paginas) == 1
    assert len(paginas[0]) == 3


def test_paginacion_continua_si_pagina_completa():
    """Cuando una pagina trae exactamente page_size, se pide la siguiente."""

    devoluciones = [
        [{"SEC_FUNC": i} for i in range(3)],   # completa (page_size=3)
        [{"SEC_FUNC": 99}],                     # incompleta → termina
    ]
    calls = {"n": 0}

    def fake_get(self, url, params=None):
        idx = calls["n"]
        calls["n"] += 1
        return _mock_response(
            200,
            payload={"success": True, "result": {"records": devoluciones[idx]}},
        )

    with patch.object(httpx.Client, "get", fake_get):
        with MefClient() as c:
            paginas = list(
                c.paginar_sql("SELECT ... LIMIT {limit} OFFSET {offset}", page_size=3)
            )
    assert calls["n"] == 2
    assert sum(len(p) for p in paginas) == 4


def test_helpers_sql_generan_placeholders():
    """Los SQL helpers deben mantener los placeholders para paginar_sql."""
    sql = mef_module.sql_ejecucion_por_mes("rsrc", 2026, 5)
    assert "{limit}" in sql and "{offset}" in sql
    assert "'300687'" in sql  # SEC_EJEC fijo
    assert "'2026'" in sql
    assert "'5'" in sql
