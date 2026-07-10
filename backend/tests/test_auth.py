"""Tests de integración de /auth/*.

Requiere PostgreSQL corriendo con las migraciones aplicadas.

Se crea un usuario de prueba por test (con teardown) para no interferir con
el admin del seed. La contraseña se conoce, así los flujos se pueden probar
sin secretos externos.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal
from app.main import app
from app.security.passwords import hash_password


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def usuario_test() -> Iterator[dict[str, str]]:
    """Crea un usuario 'test_<uuid>' con rol operativo y devuelve credenciales.

    Se elimina en teardown (junto con sus refresh tokens y filas de auditoría).
    """
    usuario = f"test_{uuid.uuid4().hex[:8]}"
    password = "Pa55word!ok"
    with SessionLocal() as db:
        rol_id = db.execute(
            text("SELECT id FROM auth.roles WHERE codigo = 'operativo'")
        ).scalar_one()
        db.execute(
            text(
                """
                INSERT INTO auth.usuarios (
                    usuario, password_hash, nombre_completo, rol_id,
                    debe_cambiar_password
                )
                VALUES (:u, :h, :n, :rol, false)
                """
            ),
            {"u": usuario, "h": hash_password(password), "n": "Test User", "rol": rol_id},
        )
        db.commit()

    yield {"usuario": usuario, "password": password}

    with SessionLocal() as db:
        row = db.execute(
            text("SELECT id FROM auth.usuarios WHERE usuario = :u"), {"u": usuario}
        ).first()
        if row:
            uid = row.id
            db.execute(
                text("DELETE FROM auth.refresh_tokens WHERE usuario_id = :id"),
                {"id": uid},
            )
            db.execute(
                text("DELETE FROM logs.auditoria WHERE usuario_id = :id"),
                {"id": uid},
            )
            db.execute(
                text("DELETE FROM auth.usuarios WHERE id = :id"), {"id": uid}
            )
            db.commit()


# ─── Login ──────────────────────────────────────────────────────────────

def test_login_exitoso_devuelve_access_token_y_setea_cookie(cliente, usuario_test):
    r = cliente.post("/api/v1/auth/login", json=usuario_test)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["expira_en_segundos"] > 0
    assert data["debe_cambiar_password"] is False
    # Refresh cookie httpOnly
    assert "refresh_token" in r.cookies


def test_login_password_incorrecto_401(cliente, usuario_test):
    r = cliente.post(
        "/api/v1/auth/login",
        json={"usuario": usuario_test["usuario"], "password": "malo"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "credenciales_invalidas"


def test_login_usuario_inexistente_401(cliente):
    r = cliente.post(
        "/api/v1/auth/login",
        json={"usuario": f"no_existe_{uuid.uuid4().hex[:8]}", "password": "x"},
    )
    assert r.status_code == 401


def test_login_bloqueo_tras_5_intentos_fallidos(cliente, usuario_test):
    for i in range(4):
        r = cliente.post(
            "/api/v1/auth/login",
            json={"usuario": usuario_test["usuario"], "password": "malo"},
        )
        assert r.status_code == 401, f"intento {i+1}"
    # El 5to devuelve 423 Locked
    r5 = cliente.post(
        "/api/v1/auth/login",
        json={"usuario": usuario_test["usuario"], "password": "malo"},
    )
    assert r5.status_code == 423
    assert r5.json()["detail"]["code"] == "usuario_bloqueado"
    # Incluso con password correcto queda bloqueado
    r6 = cliente.post("/api/v1/auth/login", json=usuario_test)
    assert r6.status_code == 423


# ─── Refresh ────────────────────────────────────────────────────────────

def test_refresh_emite_nuevo_access_token(cliente, usuario_test):
    r = cliente.post("/api/v1/auth/login", json=usuario_test)
    assert r.status_code == 200
    r2 = cliente.post("/api/v1/auth/refresh")
    assert r2.status_code == 200
    assert r2.json()["access_token"]


def test_refresh_sin_cookie_401(cliente):
    # Cliente nuevo, sin cookies previas
    with TestClient(app) as fresh:
        r = fresh.post("/api/v1/auth/refresh")
    assert r.status_code == 401


# ─── Logout ─────────────────────────────────────────────────────────────

def test_logout_revoca_refresh_y_borra_cookie(cliente, usuario_test):
    cliente.post("/api/v1/auth/login", json=usuario_test)
    r = cliente.post("/api/v1/auth/logout")
    assert r.status_code == 204
    # Tras logout, el refresh queda revocado → refresh futuro falla
    r2 = cliente.post("/api/v1/auth/refresh")
    assert r2.status_code == 401


# ─── /me + cambio password ──────────────────────────────────────────────

def test_me_con_access_token(cliente, usuario_test):
    r = cliente.post("/api/v1/auth/login", json=usuario_test)
    access = r.json()["access_token"]
    r2 = cliente.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r2.status_code == 200
    perfil = r2.json()
    assert perfil["usuario"] == usuario_test["usuario"]
    assert perfil["rol"] == "operativo"


def test_me_sin_token_401(cliente):
    r = cliente.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_cambiar_password_correcto(cliente, usuario_test):
    r = cliente.post("/api/v1/auth/login", json=usuario_test)
    access = r.json()["access_token"]
    nueva = "OtraPass!!456"
    r2 = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "password_actual": usuario_test["password"],
            "password_nueva": nueva,
        },
    )
    assert r2.status_code == 204
    # Login con la nueva contraseña funciona
    r3 = cliente.post(
        "/api/v1/auth/login",
        json={"usuario": usuario_test["usuario"], "password": nueva},
    )
    assert r3.status_code == 200


def test_cambiar_password_actual_incorrecta_400(cliente, usuario_test):
    r = cliente.post("/api/v1/auth/login", json=usuario_test)
    access = r.json()["access_token"]
    r2 = cliente.post(
        "/api/v1/auth/cambiar-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"password_actual": "malo", "password_nueva": "NuevaPass123"},
    )
    assert r2.status_code == 400
    assert r2.json()["detail"]["code"] == "password_actual_incorrecta"
