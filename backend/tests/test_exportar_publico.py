import pytest
from fastapi.testclient import TestClient
from typing import Iterator
from app.main import app
from app.database import get_db

@pytest.fixture
def cliente() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c

def test_exportar_publico_rate_limit(cliente: TestClient):
    payload = {"reporte": "ejecucion_detalle", "filtros": {"ano": 2026, "funcion": "03"}}
    
    r1 = cliente.post("/api/v1/publico/exportar/excel", json=payload)
    assert r1.status_code == 200
    
    r2 = cliente.post("/api/v1/publico/exportar/excel", json=payload)
    assert r2.status_code == 200
    
    r3 = cliente.post("/api/v1/publico/exportar/excel", json=payload)
    assert r3.status_code == 429
    assert "demasiadas solicitudes" in r3.json()["detail"].lower()
