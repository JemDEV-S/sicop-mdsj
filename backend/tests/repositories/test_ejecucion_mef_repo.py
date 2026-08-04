"""Tests de `ejecucion_mef_repo` contra un mock de Session.

Verifican la forma de las queries, los bindings y los cálculos derivados
(saldo_disponible, porcentaje_devengado) — no golpean PostgreSQL. La regresión
end-to-end contra la BD real (que la vista suma igual que el portal público)
queda para el smoke manual documentado en
Docs/consolidacion-backend-presupuestal.md §5.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from app.repositories import ejecucion_mef_repo


class _Result:
    def __init__(self, rows: list[Any], one: Any = None) -> None:
        self._rows = rows
        self._one = one

    def mappings(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def one_or_none(self) -> Any:
        return self._one


def _mock_db(rows: list[Any] | None = None, one: Any = None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value = _Result(rows or [], one=one)
    return db


# ─── resumen_mef ─────────────────────────────────────────────────────────

def test_resumen_mef_lee_de_la_vista_unica():
    db = _mock_db(one={
        "pia": 65116324, "pim": 69500489, "certificado": 43406692,
        "comprometido": 40000000, "devengado": 30798719, "girado": 30133083,
        "sincronizado_en": None,
    })
    ejecucion_mef_repo.resumen_mef(db, ano=2026)

    sql = str(db.execute.call_args[0][0])
    binds = db.execute.call_args[0][1]
    # Fuente única: la vista, no la tabla base (evita duplicar la regla SIAF).
    assert "siaf.v_ejecucion_meta_anual" in sql
    assert "ano_eje = :ano" in sql
    assert "sec_ejec = :sec_ejec" in sql
    assert binds["ano"] == 2026


def test_resumen_mef_calcula_derivados():
    db = _mock_db(one={
        "pia": 100.0, "pim": 200.0, "certificado": 150.0,
        "comprometido": 120.0, "devengado": 50.0, "girado": 40.0,
        "sincronizado_en": None,
    })
    r = ejecucion_mef_repo.resumen_mef(db, ano=2026)
    assert r["saldo_disponible"] == 150.0            # pim - devengado
    assert r["porcentaje_devengado"] == 25.0         # 50/200 * 100
    # El % se calcula sobre el devengado REAL, nunca sobre cert+compr.
    assert r["certificado"] == 150.0
    assert r["comprometido"] == 120.0


def test_resumen_mef_sin_datos_devuelve_ceros():
    db = _mock_db(one=None)
    r = ejecucion_mef_repo.resumen_mef(db, ano=2099)
    assert r["pim"] == 0.0
    assert r["devengado"] == 0.0
    assert r["porcentaje_devengado"] == 0.0
    assert r["sincronizado_en"] is None


def test_resumen_mef_pim_cero_no_divide():
    db = _mock_db(one={
        "pia": 0, "pim": 0, "certificado": 0, "comprometido": 0,
        "devengado": 0, "girado": 0, "sincronizado_en": None,
    })
    r = ejecucion_mef_repo.resumen_mef(db, ano=2026)
    assert r["porcentaje_devengado"] == 0.0          # sin ZeroDivisionError


# ─── ejecucion_por_meta ──────────────────────────────────────────────────

def test_ejecucion_por_meta_indexa_por_sec_func():
    db = _mock_db([
        {"sec_func": 111, "pia": 10, "pim": 20, "certificado": 15,
         "comprometido": 12, "devengado": 8, "girado": 7, "sincronizado_en": None},
        {"sec_func": 222, "pia": 0, "pim": 100, "certificado": 50,
         "comprometido": 40, "devengado": 30, "girado": 25, "sincronizado_en": None},
    ])
    res = ejecucion_mef_repo.ejecucion_por_meta(db, ano=2026)
    assert set(res.keys()) == {111, 222}
    assert res[222]["devengado"] == 30.0
    assert res[222]["porcentaje_devengado"] == 30.0  # 30/100
    assert res[111]["saldo_disponible"] == 12.0      # 20 - 8


def test_ejecucion_por_meta_filtra_por_sec_funcs_con_binds():
    db = _mock_db([])
    ejecucion_mef_repo.ejecucion_por_meta(db, ano=2026, sec_funcs=[111, 222])

    sql = str(db.execute.call_args[0][0])
    binds = db.execute.call_args[0][1]
    assert "sec_func IN (:sf0, :sf1)" in sql
    assert binds["sf0"] == 111
    assert binds["sf1"] == 222


def test_ejecucion_por_meta_lista_vacia_no_consulta():
    db = _mock_db([])
    res = ejecucion_mef_repo.ejecucion_por_meta(db, ano=2026, sec_funcs=[])
    assert res == {}
    db.execute.assert_not_called()  # sin alcance = no golpear la BD


def test_ejecucion_por_meta_none_trae_todas():
    db = _mock_db([])
    ejecucion_mef_repo.ejecucion_por_meta(db, ano=2026, sec_funcs=None)
    sql = str(db.execute.call_args[0][0])
    assert "sec_func IN" not in sql  # sin restricción de metas
