import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
r = client.get("/api/v1/publico/ejecucion/detalle?ano=2026&page=1&size=5")
print(json.dumps(r.json(), indent=2))
