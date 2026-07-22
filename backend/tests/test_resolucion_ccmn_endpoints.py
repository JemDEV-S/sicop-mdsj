"""Endpoints de bolsa y resolucion manual pedido <-> CCMN (punto 5 del plan).

Se prueba la capa HTTP: permisos por rol, alcance por CC (RN-04), validacion
del candidato y auditoria. SIGA y Postgres se mockean — las queries reales ya
se verificaron contra BD, y aqui interesa la logica de autorizacion.

Quien puede asociar (§13 item 6, decidido 2026-07-22): Operativo sobre sus CC,
Decisor sobre su jerarquia, Admin sin filtro. Revocar sigue la misma regla y
NO exige ser el autor.

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.enums import CodigoRol
from app.repositories import pipeline_repo, resolucion_ccmn_repo
from app.security.deps import CurrentUser, get_current_user
from app.services import auditoria_service

BASE = "/api/v1/interno/pedidos"

# Testigo 232/S (§10): bolsa 11553 con 3 candidatos, el correcto es 2266.
CTX_TESTIGO = {
    "NRO_PEDIDO": 232,
    "TIPO_BIEN": "S",
    "TIPO_PEDIDO": "2",
    "CENTRO_COSTO": "01.03.07.04",
    "centro_costo": "01.03.07.04",
    "sec_func": 57,
    "estado_pedido": "1",
    "bolsas": [11553],
    "candidatos": [2266, 2281, 3532],
}


def _usuario(rol: CodigoRol, centros: list[str] | None) -> CurrentUser:
    return CurrentUser(
        id=uuid.uuid4(),
        usuario="tester",
        rol=rol,
        nombre_completo="Tester",
        centros_permitidos=centros,
    )


@pytest.fixture
def cliente(monkeypatch):
    """TestClient con `get_db` y SIGA mockeados. `como(...)` fija el usuario."""
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    monkeypatch.setattr(
        pipeline_repo, "contexto_pedido_bolsa", lambda *a, **k: dict(CTX_TESTIGO)
    )
    # La auditoria se verifica por llamada, no por escritura real.
    registradas: list[dict] = []
    monkeypatch.setattr(
        auditoria_service, "registrar_desde_request",
        lambda db, req, **kw: registradas.append(kw),
    )

    c = TestClient(app)
    c.registradas = registradas  # type: ignore[attr-defined]
    c.db = db  # type: ignore[attr-defined]

    def como(rol: CodigoRol, centros: list[str] | None = None):
        app.dependency_overrides[get_current_user] = lambda: _usuario(rol, centros)
        return c

    c.como = como  # type: ignore[attr-defined]
    yield c
    app.dependency_overrides.clear()


# ─── Quien puede asociar (§13 item 6) ────────────────────────────────────


@pytest.mark.parametrize(
    "rol", [CodigoRol.admin, CodigoRol.decisor, CodigoRol.operativo]
)
def test_roles_autorizados_pueden_asociar(cliente, monkeypatch, rol):
    monkeypatch.setattr(
        resolucion_ccmn_repo, "crear_resolucion",
        lambda db, **kw: {
            "id": uuid.uuid4(), "nro_consolid": kw["nro_consolid"],
            "creado_en": "2026-07-22T10:00:00Z",
        },
    )
    r = cliente.como(rol, ["01.03.07.04"]).post(
        f"{BASE}/232/S/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 2266},
    )
    assert r.status_code == 201, r.text
    assert r.json()["nro_consolid"] == 2266


def test_ciudadano_no_puede_asociar(cliente):
    r = cliente.como(CodigoRol.ciudadano, []).post(
        f"{BASE}/232/S/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 2266},
    )
    assert r.status_code == 403
    assert "rol" in r.json()["detail"]


# ─── Alcance por CC (RN-04) ──────────────────────────────────────────────


def test_operativo_fuera_de_su_cc_recibe_403(cliente):
    r = cliente.como(CodigoRol.operativo, ["09.99.99.99"]).post(
        f"{BASE}/232/S/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 2266},
    )
    assert r.status_code == 403
    assert "alcance" in r.json()["detail"]


def test_admin_no_tiene_filtro_de_cc(cliente, monkeypatch):
    monkeypatch.setattr(
        resolucion_ccmn_repo, "crear_resolucion",
        lambda db, **kw: {
            "id": uuid.uuid4(), "nro_consolid": 2266,
            "creado_en": "2026-07-22T10:00:00Z",
        },
    )
    r = cliente.como(CodigoRol.admin, None).post(
        f"{BASE}/232/S/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 2266},
    )
    assert r.status_code == 201


# ─── Validacion del candidato ────────────────────────────────────────────


def test_ccmn_fuera_de_los_candidatos_se_rechaza(cliente):
    """Asociar un CCMN que no esta en la bolsa no seria resolver: seria
    inventar un dato. Se rechaza con el listado de candidatos reales."""
    r = cliente.como(CodigoRol.operativo, ["01.03.07.04"]).post(
        f"{BASE}/232/S/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 9999},
    )
    assert r.status_code == 422
    assert "9999" in r.json()["detail"]
    assert "2266" in r.json()["detail"]  # muestra los candidatos validos


def test_tipo_bien_invalido(cliente):
    r = cliente.como(CodigoRol.admin, None).post(
        f"{BASE}/232/X/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 2266},
    )
    assert r.status_code == 400


def test_pedido_inexistente_da_404(cliente, monkeypatch):
    monkeypatch.setattr(
        pipeline_repo, "contexto_pedido_bolsa", lambda *a, **k: None
    )
    r = cliente.como(CodigoRol.admin, None).post(
        f"{BASE}/999999/S/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 2266},
    )
    assert r.status_code == 404


# ─── Auditoria (regla 8) ─────────────────────────────────────────────────


def test_asociar_deja_rastro_en_auditoria(cliente, monkeypatch):
    monkeypatch.setattr(
        resolucion_ccmn_repo, "crear_resolucion",
        lambda db, **kw: {
            "id": uuid.uuid4(), "nro_consolid": 2266,
            "creado_en": "2026-07-22T10:00:00Z",
        },
    )
    cliente.como(CodigoRol.operativo, ["01.03.07.04"]).post(
        f"{BASE}/232/S/resoluciones",
        json={"tipo_pedido": "2", "nro_consolid": 2266, "nota": "confirmado"},
    )
    assert len(cliente.registradas) == 1
    reg = cliente.registradas[0]
    assert reg["accion"] == auditoria_service.Accion.RESOLUCION_CCMN_CREADA
    # Guardar los candidatos del momento permite detectar despues si SIGA
    # agrego CCMN a la bolsa (obsolescencia silenciosa, §5.1).
    assert reg["detalle"]["candidatos_al_momento"] == [2266, 2281, 3532]
    assert reg["detalle"]["nro_consolid"] == 2266


def test_revocar_deja_rastro_con_el_autor_original(cliente, monkeypatch):
    autor = uuid.uuid4()
    rid = uuid.uuid4()
    monkeypatch.setattr(
        resolucion_ccmn_repo, "obtener_resolucion",
        lambda db, **kw: {
            "id": rid, "ano_eje": 2026, "tipo_bien": "S", "tipo_pedido": "2",
            "nro_pedido": 232, "nro_consolid": 2266, "usuario_id": autor,
        },
    )
    monkeypatch.setattr(
        resolucion_ccmn_repo, "revocar_resolucion", lambda db, **kw: True
    )
    r = cliente.como(CodigoRol.decisor, ["01.03.07.04"]).delete(
        f"{BASE}/resoluciones/{rid}"
    )
    assert r.status_code == 204
    reg = cliente.registradas[0]
    assert reg["accion"] == auditoria_service.Accion.RESOLUCION_CCMN_REVOCADA
    assert reg["detalle"]["autor_original"] == str(autor)


# ─── Revocar: reglas propias ─────────────────────────────────────────────


def test_revocar_no_exige_ser_el_autor(cliente, monkeypatch):
    """Una asociacion equivocada no debe quedar congelada porque su autor
    roto o esta de licencia (decision del usuario 2026-07-22)."""
    monkeypatch.setattr(
        resolucion_ccmn_repo, "obtener_resolucion",
        lambda db, **kw: {
            "id": uuid.uuid4(), "ano_eje": 2026, "tipo_bien": "S",
            "tipo_pedido": "2", "nro_pedido": 232, "nro_consolid": 2266,
            "usuario_id": uuid.uuid4(),  # otro autor
        },
    )
    monkeypatch.setattr(
        resolucion_ccmn_repo, "revocar_resolucion", lambda db, **kw: True
    )
    r = cliente.como(CodigoRol.operativo, ["01.03.07.04"]).delete(
        f"{BASE}/resoluciones/{uuid.uuid4()}"
    )
    assert r.status_code == 204


def test_revocar_dos_veces_da_409(cliente, monkeypatch):
    monkeypatch.setattr(
        resolucion_ccmn_repo, "obtener_resolucion",
        lambda db, **kw: {
            "id": uuid.uuid4(), "ano_eje": 2026, "tipo_bien": "S",
            "tipo_pedido": "2", "nro_pedido": 232, "nro_consolid": 2266,
            "usuario_id": uuid.uuid4(),
        },
    )
    monkeypatch.setattr(
        resolucion_ccmn_repo, "revocar_resolucion", lambda db, **kw: False
    )
    r = cliente.como(CodigoRol.admin, None).delete(
        f"{BASE}/resoluciones/{uuid.uuid4()}"
    )
    assert r.status_code == 409


def test_revocar_resolucion_inexistente_da_404(cliente, monkeypatch):
    monkeypatch.setattr(
        resolucion_ccmn_repo, "obtener_resolucion", lambda db, **kw: None
    )
    r = cliente.como(CodigoRol.admin, None).delete(
        f"{BASE}/resoluciones/{uuid.uuid4()}"
    )
    assert r.status_code == 404


# ─── Vista de bolsa ──────────────────────────────────────────────────────


def test_bolsa_devuelve_pedidos_y_candidatos(cliente, monkeypatch):
    monkeypatch.setattr(
        pipeline_repo, "obtener_bolsa",
        lambda *a, **k: {
            "sec_cua_mod_sal": 11553,
            "pedidos": [
                {"NRO_PEDIDO": 232, "TIPO_BIEN": "S", "TIPO_PEDIDO": "2",
                 "valor_soles": 4800.0, "item": "07-11-0043-1207"},
            ],
            "candidatos": [
                {"NRO_CONSOLID": 2266, "VALOR_PLAN": 4800.0},
                {"NRO_CONSOLID": 2281, "VALOR_PLAN": 1485.0},
            ],
        },
    )
    monkeypatch.setattr(
        resolucion_ccmn_repo, "resoluciones_de_pedido",
        lambda db, **kw: [{"nro_consolid": 2266}],
    )
    r = cliente.como(CodigoRol.operativo, ["01.03.07.04"]).get(
        f"{BASE}/232/S/2/bolsa"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sec_cua_mod_sal"] == 11553
    assert len(body["candidatos"]) == 2
    # El CCMN resuelto manualmente se marca; los demas no.
    marcados = {c["nro_consolid"]: c["asociado_manual"] for c in body["candidatos"]}
    assert marcados == {2266: True, 2281: False}


def test_bolsa_de_pedido_sin_programar_no_falla(cliente, monkeypatch):
    """`sin_ccmn`: el pedido aun no entro a la bolsa. No es un error."""
    monkeypatch.setattr(
        pipeline_repo, "contexto_pedido_bolsa",
        lambda *a, **k: {**CTX_TESTIGO, "bolsas": [], "candidatos": []},
    )
    r = cliente.como(CodigoRol.admin, None).get(f"{BASE}/232/S/2/bolsa")
    assert r.status_code == 200
    assert r.json()["candidatos"] == []


def test_bolsa_respeta_alcance_de_cc(cliente):
    r = cliente.como(CodigoRol.operativo, ["09.99.99.99"]).get(
        f"{BASE}/232/S/2/bolsa"
    )
    assert r.status_code == 403
