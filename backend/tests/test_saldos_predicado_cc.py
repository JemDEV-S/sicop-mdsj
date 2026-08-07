"""Tests del predicado de CC para el DETALLE de una meta (saldos_repo).

Blindan el fix del bug de la meta 57: el detalle de una meta elegible debe
incluir sus líneas de `CENTRO_COSTO IS NULL` (presupuesto de cabecera), pero
solo protegido por un EXISTS que evita fugas hacia metas ajenas.

Son unitarios puros (arman el SQL/binds), no golpean SIGA.
"""

from __future__ import annotations

from app.repositories.saldos_repo import _predicado_cc_detalle


def test_admin_sin_filtro_devuelve_none():
    params: dict = {}
    assert _predicado_cc_detalle(None, params) is None
    assert params == {}


def test_incluye_cc_del_usuario_y_nulos_con_exists():
    params: dict = {}
    sql = _predicado_cc_detalle(["01.03.07.04"], params)
    assert sql is not None
    # Debe permitir el CC del usuario…
    assert "t.CENTRO_COSTO IN (:ccd0)" in sql
    # …y los nulos, pero condicionados a un EXISTS sobre la misma meta.
    assert "t.CENTRO_COSTO IS NULL" in sql
    assert "EXISTS" in sql
    assert "t2.sec_func = t.sec_func" in sql
    # Bind del CC presente.
    assert params == {"ccd0": "01.03.07.04"}


def test_varios_cc_generan_un_bind_por_cada_uno():
    params: dict = {}
    sql = _predicado_cc_detalle(["01.01", "01.02", "01.03"], params)
    assert sql is not None
    assert params == {"ccd0": "01.01", "ccd1": "01.02", "ccd2": "01.03"}
    # La lista IN aparece dos veces (una para el CC directo, otra dentro del
    # EXISTS que valida elegibilidad de la meta).
    assert sql.count(":ccd0") == 2


def test_no_colisiona_con_binds_del_listado():
    """Usa prefijo `ccd` (no `cc`) para no chocar con otros binds de la query."""
    params: dict = {"sec_func": 57}
    _predicado_cc_detalle(["01.03.07.04"], params)
    assert "cc0" not in params  # el listado usa cc0; el detalle usa ccd0
    assert "ccd0" in params
