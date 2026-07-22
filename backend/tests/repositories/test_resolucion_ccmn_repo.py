"""Tests de `resolucion_ccmn_repo` y de su inyeccion en el pipeline.

Los repos se prueban contra un mock de Session (convencion del proyecto, ver
`tests/test_metas_repo.py`): verifican la forma de la query y los bindings.
Las constraints reales (uq_par_activo, NULLS NOT DISTINCT, los CHECK) se
verificaron contra PostgreSQL al aplicar la migracion b7c1d2e3f4a5.

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories import resolucion_ccmn_repo
from app.services import pipeline_service


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


def _mock_db(rows: list[Any] | None = None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value = _Result(rows or [])
    return db


# ─── resoluciones_activas ────────────────────────────────────────────────


def test_activas_agrupa_por_llave_completa_del_pedido():
    """La llave es TIPO_BIEN+TIPO_PEDIDO+NRO_PEDIDO (§6): el mismo nro_pedido
    con distinto tipo_pedido son pedidos DISTINTOS (446 colisiones en 2026)."""
    db = _mock_db([
        ("S", "2", 232, 2266),
        ("B", "2", 232, 5000),
        ("B", "1", 232, 5001),
    ])
    out = resolucion_ccmn_repo.resoluciones_activas(db, ano=2026, sec_ejec=300687)

    assert out[("S", "2", 232)] == [2266]
    assert out[("B", "2", 232)] == [5000]
    assert out[("B", "1", 232)] == [5001]


def test_activas_devuelve_lista_por_pedido_para_la_relacion_NM():
    """Un pedido puede consolidar varios CCMN (§5, confirmado por el usuario)."""
    db = _mock_db([("S", "2", 232, 2266), ("S", "2", 232, 2281)])
    out = resolucion_ccmn_repo.resoluciones_activas(db, ano=2026, sec_ejec=300687)
    assert out[("S", "2", 232)] == [2266, 2281]


def test_activas_normaliza_espacios_de_siga():
    """SIGA devuelve char(1)/varchar con padding; la llave debe cruzar igual."""
    db = _mock_db([(" S ", " 2 ", 232, 2266)])
    out = resolucion_ccmn_repo.resoluciones_activas(db, ano=2026, sec_ejec=300687)
    assert ("S", "2", 232) in out


def test_activas_filtra_revocadas_en_sql():
    """La revocacion no se filtra en Python: debe estar en el WHERE."""
    db = _mock_db([])
    resolucion_ccmn_repo.resoluciones_activas(db, ano=2026, sec_ejec=300687)
    sql = str(db.execute.call_args[0][0])
    assert "revocado_en IS NULL" in sql


# ─── revocar ─────────────────────────────────────────────────────────────


def test_revocar_no_borra_y_es_idempotente():
    """Nunca se borra, se revoca (§5). Revocar dos veces devuelve False."""
    db = _mock_db([])  # UPDATE ... RETURNING sin filas = ya estaba revocada
    assert resolucion_ccmn_repo.revocar_resolucion(
        db, resolucion_id=uuid4(), usuario_id=uuid4()
    ) is False

    sql = str(db.execute.call_args[0][0])
    assert "UPDATE" in sql and "DELETE" not in sql
    assert "revocado_en IS NULL" in sql  # no re-revoca


# ─── Inyeccion de la resolucion manual en el pipeline ────────────────────


def _fila(**kw):
    base = {"TIPO_BIEN": "S", "TIPO_PEDIDO": "2", "NRO_PEDIDO": 232}
    base.update(kw)
    return base


def test_inyecta_ccmn_manual_en_la_fila_del_pedido(monkeypatch):
    monkeypatch.setattr(
        resolucion_ccmn_repo, "resoluciones_activas",
        lambda db, **kw: {("S", "2", 232): [2266, 2281]},
    )
    filas = [_fila(), _fila(NRO_PEDIDO=278)]
    pipeline_service._aplicar_resoluciones_manuales(MagicMock(), filas, ano=2026)

    assert filas[0]["ccmn_manual"] == 2266
    assert filas[0]["ccmn_manual_todos"] == [2266, 2281]
    assert "ccmn_manual" not in filas[1] or filas[1].get("ccmn_manual") is None


def test_resolucion_manual_gana_en_la_cascada(monkeypatch):
    """Un pedido `ambiguo` pasa a `resuelto_manual` cuando hay resolucion."""
    fila = _fila(n_candidatos_ccmn=3, ccmn_candidatos=(2266, 2281, 3532))
    assert pipeline_service.confianza_match(fila) == "ambiguo"

    monkeypatch.setattr(
        resolucion_ccmn_repo, "resoluciones_activas",
        lambda db, **kw: {("S", "2", 232): [2266]},
    )
    pipeline_service._aplicar_resoluciones_manuales(MagicMock(), [fila], ano=2026)
    assert pipeline_service.confianza_match(fila) == "resuelto_manual"


def test_pipeline_sobrevive_si_postgres_falla(monkeypatch):
    """La resolucion manual es referencial (§5): si la tabla no responde, el
    pipeline sigue con la cascada automatica en vez de romperse."""
    def _explota(db, **kw):
        raise RuntimeError("postgres caido")

    monkeypatch.setattr(resolucion_ccmn_repo, "resoluciones_activas", _explota)
    fila = _fila(n_candidatos_ccmn=1)
    pipeline_service._aplicar_resoluciones_manuales(MagicMock(), [fila], ano=2026)

    assert fila.get("ccmn_manual") is None
    assert pipeline_service.confianza_match(fila) == "unico"


def test_sin_resoluciones_no_toca_las_filas(monkeypatch):
    monkeypatch.setattr(
        resolucion_ccmn_repo, "resoluciones_activas", lambda db, **kw: {}
    )
    fila = _fila(n_candidatos_ccmn=3)
    pipeline_service._aplicar_resoluciones_manuales(MagicMock(), [fila], ano=2026)
    assert fila.get("ccmn_manual") is None
    assert pipeline_service.confianza_match(fila) == "ambiguo"
