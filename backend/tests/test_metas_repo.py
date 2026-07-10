"""Tests de `metas_repo` y `centros_costo_repo` contra un mock de Session.

Verifican la forma de las queries y los bindings — no golpean PostgreSQL.
Un test end-to-end con la BD queda para el smoke manual (`alembic upgrade head`
+ sync_catalogos + consulta).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from app.repositories import centros_costo_repo, metas_repo


class _Result:
    def __init__(self, rows: list[Any], scalar_value: Any = None) -> None:
        self._rows = rows
        self._scalar = scalar_value

    def mappings(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any:
        return self._rows[0] if self._rows else None

    def scalar_one(self) -> Any:
        return self._scalar


def _mock_db(rows: list[Any] | None = None, scalar_value: Any = None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value = _Result(rows or [], scalar_value=scalar_value)
    return db


# ─── metas_repo ──────────────────────────────────────────────────────────

def test_listar_metas_pasa_filtros_como_binds():
    db = _mock_db([{"sec_func": 1, "nombre": "M1"}])
    metas_repo.listar_metas(db, ano=2026, tipo_meta="proyecto", funcion="15")

    args, kwargs = db.execute.call_args
    sql = str(args[0])
    binds = args[1]
    assert "ano_eje = :ano" in sql
    assert "tipo_meta = :tipo" in sql
    assert "funcion = :funcion" in sql
    assert binds == {"ano": 2026, "tipo": "proyecto", "funcion": "15"}


def test_listar_metas_incluye_solo_activas_por_defecto():
    db = _mock_db([])
    metas_repo.listar_metas(db, ano=2026)
    sql = str(db.execute.call_args.args[0])
    assert "activo = true" in sql


def test_listar_metas_paginacion():
    db = _mock_db([])
    metas_repo.listar_metas(db, ano=2026, limit=10, offset=20)
    sql = str(db.execute.call_args.args[0])
    binds = db.execute.call_args.args[1]
    assert "LIMIT :limit OFFSET :offset" in sql
    assert binds["limit"] == 10 and binds["offset"] == 20


def test_obtener_meta_devuelve_dict_o_none():
    db = _mock_db([{"sec_func": 42, "nombre": "M42"}])
    assert metas_repo.obtener_meta(db, sec_func=42) == {
        "sec_func": 42, "nombre": "M42"
    }
    db2 = _mock_db([])
    assert metas_repo.obtener_meta(db2, sec_func=99) is None


def test_contar_metas_devuelve_int():
    db = _mock_db([], scalar_value=741)
    assert metas_repo.contar_metas(db, ano=2025) == 741


# ─── centros_costo_repo ─────────────────────────────────────────────────

def test_descendientes_cc_usa_ltree_operator_correcto():
    """La query debe usar `<@ CAST(:raiz AS ltree)` para aprovechar el GIST."""

    class Row:
        def __init__(self, codigo: str) -> None:
            self.codigo = codigo

    db = _mock_db([Row("0700"), Row("0700.01"), Row("0700.02")])
    codigos = centros_costo_repo.descendientes_cc(db, codigo_raiz="0700")

    sql = str(db.execute.call_args.args[0])
    binds = db.execute.call_args.args[1]
    assert "ruta <@ CAST(:raiz AS ltree)" in sql
    assert binds["raiz"] == "root.0700"
    assert codigos == ["0700", "0700.01", "0700.02"]


def test_descendientes_cc_puede_incluir_inactivos():
    db = _mock_db([])
    centros_costo_repo.descendientes_cc(db, codigo_raiz="0700", solo_activos=False)
    sql = str(db.execute.call_args.args[0])
    assert "activo = true" not in sql


def test_listar_centros_costo_flag_presupuesto():
    db = _mock_db([])
    centros_costo_repo.listar_centros_costo(db, solo_con_presupuesto=True)
    sql = str(db.execute.call_args.args[0])
    assert "flag_presupuesto = true" in sql


def test_metas_de_centro_joina_puente():
    db = _mock_db([{"sec_func": 100, "meta": "00001", "nombre": "X"}])
    resultado = centros_costo_repo.metas_de_centro(db, codigo_cc="0700", ano=2026)

    sql = str(db.execute.call_args.args[0])
    binds = db.execute.call_args.args[1]
    assert "ref.metas_centro_costo mcc" in sql
    assert "mcc.centro_costo = :cc" in sql
    assert binds == {"cc": "0700", "ano": 2026}
    assert resultado == [{"sec_func": 100, "meta": "00001", "nombre": "X"}]
