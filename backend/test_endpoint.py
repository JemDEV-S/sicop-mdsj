from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post(
    "/api/v1/publico/exportar/excel",
    json={"reporte": "ejecucion_detalle", "filtros": {"ano": 2026, "funcion": "03"}}
)
print("Status:", response.status_code)
if response.status_code == 200:
    with open("test_export.xlsx", "wb") as f:
        f.write(response.content)
    print("Exported to test_export.xlsx")
else:
    print(response.json())
