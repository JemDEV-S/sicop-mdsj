"""Tests del helper transversal de auditoría (T-10).

Verifica que:
- `auditoria_service.registrar` inserta la fila esperada (accion, detalle,
  ip, user_agent).
- Una falla al insertar (por ejemplo, IP inválida) no propaga excepción —
  la auditoría es best-effort.
- Un login exitoso vía HTTP deja fila en `logs.auditoria` con IP y user-agent
  correctos (integración end-to-end con `auth_service` refactorizado).
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
from app.services import auditoria_service


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def usuario_test() -> Iterator[dict[str, str]]:
    """Usuario efímero para no ensuciar el admin del seed."""
    usuario = f"aud_{uuid.uuid4().hex[:8]}"
    password = "Pa55word!ok"
    with SessionLocal() as db:
        rol_id = db.execute(
            text("SELECT id FROM auth.roles WHERE codigo = 'operativo'")
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
            {"u": usuario, "h": hash_password(password), "n": "Aud Test", "r": rol_id},
        ).scalar_one()
        db.commit()

    yield {"usuario": usuario, "password": password, "id": str(uid)}

    with SessionLocal() as db:
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


# ─── Unitarios del helper ───────────────────────────────────────────────

def test_registrar_inserta_fila_con_ip_y_user_agent(usuario_test):
    uid = uuid.UUID(usuario_test["id"])
    with SessionLocal() as db:
        auditoria_service.registrar(
            db,
            accion=auditoria_service.Accion.EXPORTACION_REPORTE,
            usuario_id=uid,
            detalle={"formato": "excel", "filas": 42},
            ip="10.0.0.5",
            user_agent="pytest/1.0",
        )
        db.commit()

    with SessionLocal() as db:
        fila = db.execute(
            text(
                """
                SELECT accion, detalle, ip::text, user_agent
                  FROM logs.auditoria
                 WHERE usuario_id = :u
                   AND accion = 'exportacion_reporte'
                """
            ),
            {"u": str(uid)},
        ).first()
    assert fila is not None
    assert fila.accion == "exportacion_reporte"
    assert fila.detalle == {"formato": "excel", "filas": 42}
    # Postgres devuelve inet con máscara: "10.0.0.5/32"
    assert fila.ip.startswith("10.0.0.5")
    assert fila.user_agent == "pytest/1.0"


def test_registrar_es_best_effort_no_propaga_error(usuario_test):
    """Si el INSERT falla (ej. IP inválida en columna inet), no debe explotar."""
    uid = uuid.UUID(usuario_test["id"])
    with SessionLocal() as db:
        # No debe lanzar — solo logea warning.
        auditoria_service.registrar(
            db,
            accion=auditoria_service.Accion.LOGIN_EXITOSO,
            usuario_id=uid,
            ip="esto-no-es-una-ip",  # SqlAlchemy/Postgres lo rechazará
        )
        # La sesión pudo quedar en estado failed; rollback para limpiar.
        db.rollback()


# ─── End-to-end: login deja fila con IP y UA ────────────────────────────

def test_login_exitoso_registra_auditoria_con_ip_y_user_agent(cliente, usuario_test):
    ua = "SICOP-Test/1.0"
    xff = "203.0.113.99"  # IP TEST-NET-3 (RFC 5737), válida para inet
    r = cliente.post(
        "/api/v1/auth/login",
        json={"usuario": usuario_test["usuario"], "password": usuario_test["password"]},
        headers={"User-Agent": ua, "X-Forwarded-For": xff},
    )
    assert r.status_code == 200, r.text

    with SessionLocal() as db:
        fila = db.execute(
            text(
                """
                SELECT accion, detalle, ip::text, user_agent
                  FROM logs.auditoria
                 WHERE usuario_id = :u
                   AND accion = 'login_exitoso'
                 ORDER BY creado_en DESC
                 LIMIT 1
                """
            ),
            {"u": usuario_test["id"]},
        ).first()
    assert fila is not None
    assert fila.ip.startswith(xff)  # inet incluye máscara /32
    assert fila.user_agent == ua
    assert fila.detalle["rol"] == "operativo"


def test_login_fallido_tambien_deja_auditoria(cliente, usuario_test):
    cliente.post(
        "/api/v1/auth/login",
        json={"usuario": usuario_test["usuario"], "password": "malo"},
        headers={"User-Agent": "AttackerBot/9.0"},
    )
    with SessionLocal() as db:
        fila = db.execute(
            text(
                """
                SELECT accion, detalle, user_agent
                  FROM logs.auditoria
                 WHERE usuario_id = :u
                   AND accion = 'login_fallido'
                 ORDER BY creado_en DESC
                 LIMIT 1
                """
            ),
            {"u": usuario_test["id"]},
        ).first()
    assert fila is not None
    assert fila.user_agent == "AttackerBot/9.0"
    assert fila.detalle["motivo"] == "password_incorrecto"
