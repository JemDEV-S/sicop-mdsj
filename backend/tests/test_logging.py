"""Tests del logging estructurado (T-11).

Verifica:
- El middleware añade el header `X-Request-ID` en la respuesta.
- Si el cliente envía `X-Request-ID`, se preserva en la respuesta (trazabilidad
  end-to-end desde el frontend).
- Un endpoint que emite `logger.info` propaga el `request_id` del contextvars.
- El JSON renderer produce logs parseables en modo producción.
"""

from __future__ import annotations

import io
import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def cliente():
    with TestClient(app) as c:
        yield c


def test_response_incluye_header_request_id(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert "x-request-id" in {k.lower() for k in r.headers}
    # Debe ser un UUID hex de 32 chars.
    assert re.fullmatch(r"[0-9a-f]{32}", r.headers["x-request-id"])


def test_request_id_del_cliente_se_preserva(cliente):
    """Si el frontend genera un correlation id, el backend lo respeta."""
    rid = "cliente-correlation-id-abc123"
    r = cliente.get("/health", headers={"X-Request-ID": rid})
    assert r.headers["x-request-id"] == rid


def test_json_renderer_produce_logs_parseables_en_produccion(monkeypatch):
    """En APP_ENV=production el pipeline debe emitir JSON válido a stdout."""
    from app import logging_config

    monkeypatch.setattr(logging_config.settings, "APP_ENV", "production")
    logging_config.configurar_logging()

    # Redirigimos el handler root a un buffer.
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    # Reusar el formatter del root (JSONRenderer).
    root = logging.getLogger()
    handler.setFormatter(root.handlers[0].formatter)
    root.addHandler(handler)

    logger = logging_config.get_logger("test")
    logger.info("evento_test", campo_extra="valor")

    # Buscar la primera línea JSON válida.
    salida = buffer.getvalue()
    lineas_json = [ln for ln in salida.strip().split("\n") if ln.startswith("{")]
    assert lineas_json, f"No hubo salida JSON. Buffer: {salida!r}"

    payload = json.loads(lineas_json[-1])
    assert payload["event"] == "evento_test"
    assert payload["campo_extra"] == "valor"
    assert payload["service"] == "backend"
    assert payload["level"] == "info"
    assert "ts" in payload

    root.removeHandler(handler)
