"""Tests del alcance por CC de anotaciones (permisos_anotaciones_service).

Cubre las ramas que NO tocan SIGA (parseo del entidad_id y las decisiones de
alcance para admin / tipos transversales). La resolución real del CC de un
pedido contra SIGA se prueba manualmente (requiere la BD SIGA); aquí se aísla
la lógica de decisión.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.models.enums import CodigoRol
from app.security.deps import CurrentUser
from app.services import permisos_anotaciones_service as svc


def _user(centros: list[str] | None, rol: CodigoRol = CodigoRol.operativo) -> CurrentUser:
    return CurrentUser(
        id=uuid.uuid4(),
        usuario="tester",
        nombre_completo="Tester",
        rol=rol,
        centros_permitidos=centros,
    )


# ─── Parseo del entidad_id ("{nro}-{TIPO_BIEN}") ────────────────────────────

@pytest.mark.parametrize(
    "entidad_id, esperado",
    [
        ("1234-S", (1234, "S")),
        ("77-B", (77, "B")),
        ("1234-s", (1234, "S")),  # normaliza a mayúscula
    ],
)
def test_parsear_id_valido(entidad_id, esperado):
    assert svc._parsear_id(entidad_id) == esperado


@pytest.mark.parametrize(
    "entidad_id",
    ["1234", "1234-X", "abc-S", "-S", "1234-", "", "12.5-S"],
)
def test_parsear_id_invalido(entidad_id):
    assert svc._parsear_id(entidad_id) is None


# ─── verificar_alcance_entidad: ramas sin SIGA ──────────────────────────────

def test_admin_siempre_permitido():
    """Admin (centros_permitidos None) no se bloquea nunca, ni consulta SIGA."""
    admin = _user(None, rol=CodigoRol.admin)
    # No debe lanzar aunque el pedido sería inaccesible para un restringido.
    svc.verificar_alcance_entidad(admin, "pedido", "9999-S")


@pytest.mark.parametrize("tipo", ["meta", "obra", "contrato", "orden"])
def test_tipos_transversales_no_se_bloquean(tipo):
    """meta/obra/contrato/orden no tienen CC propio verificado → se permiten."""
    restringido = _user(["01.02"])
    svc.verificar_alcance_entidad(restringido, tipo, "cualquier-id")


def test_pedido_con_id_invalido_niega_a_restringido():
    """Un entidad_id de pedido que no resuelve CC se niega (preferir negar)."""
    restringido = _user(["01.02"])
    with pytest.raises(HTTPException) as exc:
        # id no parseable → resolver_cc_entidad devuelve None → 403.
        svc.verificar_alcance_entidad(restringido, "pedido", "no-parseable")
    assert exc.value.status_code == 403


def test_resolver_cc_entidad_tipo_no_soportado_es_none():
    assert svc.resolver_cc_entidad("meta", "123-S") is None
