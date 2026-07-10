"""Tests de resolución de permisos por CC (T-09).

Verifica la regla RN-04 (arquitectura §7 / requerimientos §2):
- Operativo → solo sus CC directamente asignados.
- Decisor   → sus CC + descendientes vía ltree.
- Admin     → None (sin filtro).
- Ciudadano → [] (sin acceso).

También cubre:
- Dependency `get_current_user` protegiendo un endpoint dummy (401 / 200).
- Factory `require_role` (403 con rol insuficiente, 200 con rol permitido).

Requiere PostgreSQL corriendo con las migraciones aplicadas y datos SIGA
sincronizados (T-06.5) — usa CCs reales de `ref.centros_costo`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal
from app.models.enums import CodigoRol
from app.security.deps import CurrentUser, get_current_user, require_role
from app.security.passwords import hash_password
from app.services import permisos_service

# CCs de la jerarquía real (verificados en la BD):
# 01 (raíz) → 01.02 → 01.02.02 → {01.02.02.01, 01.02.02.02, 01.02.02.03}
CC_RAIZ = "01"
CC_RAMA = "01.02.02"
CC_HOJA_1 = "01.02.02.01"
CC_HOJA_2 = "01.02.02.02"

_CC_REQUERIDOS = [CC_RAIZ, CC_RAMA, CC_HOJA_1, CC_HOJA_2]


@pytest.fixture(autouse=True)
def _skip_si_faltan_ccs():
    """Si los CC de fixture no están (BD post-mock de test_sync_catalogos),
    saltar los tests que los necesitan — no son responsabilidad de este módulo.
    """
    with SessionLocal() as db:
        faltantes = [
            cc
            for cc in _CC_REQUERIDOS
            if not db.execute(
                text("SELECT 1 FROM ref.centros_costo WHERE codigo = :c"),
                {"c": cc},
            ).first()
        ]
    if faltantes:
        pytest.skip(
            f"Faltan CCs {faltantes} en ref.centros_costo — "
            "correr `python -m app.jobs.sync_catalogos_siga` o `pytest tests/test_permisos.py`"
        )


# ─── Fixtures ───────────────────────────────────────────────────────────

def _crear_usuario(rol_codigo: str, ccs: list[str]) -> tuple[uuid.UUID, str]:
    """Inserta usuario con `rol_codigo` y asigna `ccs`. Devuelve (id, usuario)."""
    usuario = f"perm_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        rol_id = db.execute(
            text("SELECT id FROM auth.roles WHERE codigo = :c"), {"c": rol_codigo}
        ).scalar_one()
        uid = db.execute(
            text(
                """
                INSERT INTO auth.usuarios
                       (usuario, password_hash, nombre_completo, rol_id,
                        debe_cambiar_password)
                VALUES (:u, :h, :n, :r, false)
                RETURNING id
                """
            ),
            {"u": usuario, "h": hash_password("x"), "n": "Perm Test", "r": rol_id},
        ).scalar_one()
        for cc in ccs:
            db.execute(
                text(
                    """
                    INSERT INTO auth.usuarios_centros_costo
                           (usuario_id, centro_costo, es_raiz_jerarquia)
                    VALUES (:u, :c, false)
                    """
                ),
                {"u": str(uid), "c": cc},
            )
        db.commit()
    return uid, usuario


def _eliminar_usuario(uid: uuid.UUID) -> None:
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM auth.usuarios_centros_costo WHERE usuario_id = :u"),
            {"u": str(uid)},
        )
        db.execute(
            text("DELETE FROM auth.refresh_tokens WHERE usuario_id = :u"),
            {"u": str(uid)},
        )
        db.execute(
            text("DELETE FROM logs.auditoria WHERE usuario_id = :u"),
            {"u": str(uid)},
        )
        db.execute(text("DELETE FROM auth.usuarios WHERE id = :u"), {"u": str(uid)})
        db.commit()


@pytest.fixture
def usuario_operativo() -> Iterator[uuid.UUID]:
    uid, _ = _crear_usuario("operativo", [CC_HOJA_1, CC_HOJA_2])
    yield uid
    _eliminar_usuario(uid)


@pytest.fixture
def usuario_decisor() -> Iterator[uuid.UUID]:
    uid, _ = _crear_usuario("decisor", [CC_RAMA])  # raíz de sub-jerarquía
    yield uid
    _eliminar_usuario(uid)


@pytest.fixture
def usuario_admin() -> Iterator[uuid.UUID]:
    uid, _ = _crear_usuario("admin", [])
    yield uid
    _eliminar_usuario(uid)


# ─── permisos_service (unitarios sobre DB real) ─────────────────────────

def test_operativo_ve_solo_sus_cc_directos(usuario_operativo):
    with SessionLocal() as db:
        ccs = permisos_service.resolver_centros_permitidos(
            db, usuario_operativo, CodigoRol.operativo
        )
    assert ccs == sorted([CC_HOJA_1, CC_HOJA_2])


def test_decisor_ve_su_cc_y_descendientes(usuario_decisor):
    with SessionLocal() as db:
        ccs = permisos_service.resolver_centros_permitidos(
            db, usuario_decisor, CodigoRol.decisor
        )
    assert ccs is not None
    # Debe incluir su CC raíz de gerencia + al menos 3 hojas.
    assert CC_RAMA in ccs
    assert CC_HOJA_1 in ccs
    assert CC_HOJA_2 in ccs
    # No debe incluir CCs fuera de la jerarquía (ej. el raíz global "01").
    assert CC_RAIZ not in ccs


def test_admin_no_tiene_filtro(usuario_admin):
    with SessionLocal() as db:
        ccs = permisos_service.resolver_centros_permitidos(
            db, usuario_admin, CodigoRol.admin
        )
    assert ccs is None


def test_ciudadano_sin_acceso():
    # No necesita usuario en DB — el rol solo condiciona el retorno.
    with SessionLocal() as db:
        ccs = permisos_service.resolver_centros_permitidos(
            db, uuid.uuid4(), CodigoRol.ciudadano
        )
    assert ccs == []


# ─── Endpoint protegido: get_current_user + require_role ────────────────

@pytest.fixture
def app_con_endpoint_dummy() -> FastAPI:
    """FastAPI con un endpoint protegido para verificar dependencies.

    Usa la app real para heredar middlewares y config; añade un router
    específico para tests.
    """
    from app.main import app

    from fastapi import APIRouter

    dummy = APIRouter(prefix="/dummy", tags=["_test"])

    @dummy.get("/mi-perfil")
    def perfil(user: CurrentUser = Depends(get_current_user)) -> dict:
        return {
            "usuario": user.usuario,
            "rol": user.rol.value,
            "centros_count": (
                -1 if user.centros_permitidos is None else len(user.centros_permitidos)
            ),
        }

    @dummy.get(
        "/solo-admin",
        dependencies=[Depends(require_role(CodigoRol.admin))],
    )
    def solo_admin() -> dict:
        return {"ok": True}

    @dummy.get("/decisor-o-admin")
    def decisor_o_admin(
        user: CurrentUser = Depends(require_role(CodigoRol.decisor, CodigoRol.admin)),
    ) -> dict:
        return {"rol": user.rol.value}

    # Solo montar una vez, aunque el fixture se llame varias veces.
    ya_montado = any(
        getattr(r, "path", "").startswith("/api/v1/dummy") for r in app.routes
    )
    if not ya_montado:
        app.include_router(dummy, prefix="/api/v1")

    return app


def _obtener_access_token(cliente: TestClient, usuario: str, password: str) -> str:
    r = cliente.post("/api/v1/auth/login", json={"usuario": usuario, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_endpoint_sin_token_401(app_con_endpoint_dummy):
    with TestClient(app_con_endpoint_dummy) as c:
        r = c.get("/api/v1/dummy/mi-perfil")
    assert r.status_code == 401


def test_endpoint_con_token_valido_200(app_con_endpoint_dummy):
    uid, usuario = _crear_usuario("operativo", [CC_HOJA_1])
    try:
        # Reset password para poder loguear (necesitamos conocerlo).
        with SessionLocal() as db:
            db.execute(
                text("UPDATE auth.usuarios SET password_hash = :h WHERE id = :u"),
                {"h": hash_password("Test!23456"), "u": str(uid)},
            )
            db.commit()
        with TestClient(app_con_endpoint_dummy) as c:
            token = _obtener_access_token(c, usuario, "Test!23456")
            r = c.get(
                "/api/v1/dummy/mi-perfil",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["rol"] == "operativo"
        assert data["centros_count"] == 1
    finally:
        _eliminar_usuario(uid)


def test_require_role_admin_rechaza_operativo(app_con_endpoint_dummy):
    uid, usuario = _crear_usuario("operativo", [])
    try:
        with SessionLocal() as db:
            db.execute(
                text("UPDATE auth.usuarios SET password_hash = :h WHERE id = :u"),
                {"h": hash_password("Test!23456"), "u": str(uid)},
            )
            db.commit()
        with TestClient(app_con_endpoint_dummy) as c:
            token = _obtener_access_token(c, usuario, "Test!23456")
            r = c.get(
                "/api/v1/dummy/solo-admin",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "rol_insuficiente"
    finally:
        _eliminar_usuario(uid)


def test_require_role_decisor_aceptado_en_decisor_o_admin(app_con_endpoint_dummy):
    uid, usuario = _crear_usuario("decisor", [CC_RAMA])
    try:
        with SessionLocal() as db:
            db.execute(
                text("UPDATE auth.usuarios SET password_hash = :h WHERE id = :u"),
                {"h": hash_password("Test!23456"), "u": str(uid)},
            )
            db.commit()
        with TestClient(app_con_endpoint_dummy) as c:
            token = _obtener_access_token(c, usuario, "Test!23456")
            r = c.get(
                "/api/v1/dummy/decisor-o-admin",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200
        assert r.json()["rol"] == "decisor"
    finally:
        _eliminar_usuario(uid)
