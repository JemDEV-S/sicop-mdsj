"""Job de deteccion de resoluciones manuales obsoletas (§5.1, punto 9).

El comportamiento contra BD se verifico end-to-end (marca / idempotencia /
desmarca / nunca revoca). Estos tests fijan la logica de comparacion con la
BD mockeada: que la marca dependa de si los candidatos cambiaron, y que el job
JAMAS revoque — quitar el juicio de un humano sin avisar es el fallo que toda
la refactorizacion evita.

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §5.1
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.jobs import revisar_resoluciones_ccmn as job


def _resolucion(candidatos_al_crear, revision=None, **kw):
    base = {
        "id": uuid4(),
        "tipo_bien": "S",
        "tipo_pedido": "2",
        "nro_pedido": 232,
        "nro_consolid": 2266,
        "candidatos_al_crear": candidatos_al_crear,
        "revision_pendiente_desde": revision,
    }
    base.update(kw)
    return base


def _correr(resolucion, candidatos_actuales):
    """Corre _revisar_una con la BD y SIGA mockeados. Devuelve (db, res)."""
    db = MagicMock()
    res = job.ResultadoRevision()
    ctx = {"candidatos": candidatos_actuales}
    with patch.object(job.pipeline_repo, "contexto_pedido_bolsa", lambda *a, **k: ctx):
        job._revisar_una(db, resolucion, 2026, res)
    return db, res


def _sql_de(db):
    """Concatena todos los UPDATE que el job ejecuto."""
    return " ".join(str(c.args[0]) for c in db.execute.call_args_list)


# ─── Marca cuando la bolsa cambio ────────────────────────────────────────


def test_marca_cuando_aparece_un_candidato():
    r = _resolucion([2266, 2281, 3532])
    db, res = _correr(r, [2266, 2281, 3532, 9999])

    assert res.marcadas == 1
    assert "revision_pendiente_desde = now()" in _sql_de(db)
    assert res.detalle[0]["aparecieron"] == [9999]


def test_no_marca_cuando_la_bolsa_no_cambio():
    r = _resolucion([2266, 2281, 3532])
    db, res = _correr(r, [2266, 2281, 3532])

    assert res.marcadas == 0
    assert "revision_pendiente_desde = now()" not in _sql_de(db)


def test_el_orden_de_los_candidatos_no_cuenta_como_cambio():
    """SIGA puede devolverlos en otro orden; eso no es un cambio real."""
    r = _resolucion([2266, 2281, 3532])
    db, res = _correr(r, [3532, 2266, 2281])
    assert res.marcadas == 0


# ─── Idempotencia y desmarcado ───────────────────────────────────────────


def test_no_re_marca_si_ya_estaba_marcada():
    r = _resolucion([2266, 2281, 3532], revision="2026-07-24T00:00:00Z")
    db, res = _correr(r, [2266, 2281, 3532, 9999])
    # Sigue obsoleta: refresca la foto pero no vuelve a contar como marcada.
    assert res.marcadas == 0


def test_desmarca_si_la_bolsa_vuelve_a_coincidir():
    r = _resolucion([2266, 2281, 3532], revision="2026-07-24T00:00:00Z")
    db, res = _correr(r, [2266, 2281, 3532])

    assert res.resueltas == 1
    assert "revision_pendiente_desde = NULL" in _sql_de(db)


# ─── Nunca revoca (la regla que no se negocia) ───────────────────────────


def test_el_job_nunca_revoca():
    for actuales in ([2266], [2266, 9999], []):
        r = _resolucion([2266, 2281, 3532])
        db, _ = _correr(r, actuales)
        sql = _sql_de(db)
        assert "revocado_en = now()" not in sql
        assert "DELETE" not in sql.upper()


# ─── Siembra de la foto en resoluciones previas a la migracion ───────────


def test_siembra_foto_si_estaba_vacia_sin_marcar():
    """Resoluciones creadas antes de esta migracion tienen la foto vacia: no
    hay con que comparar, se siembra sin generar un aviso falso."""
    r = _resolucion([])
    db, res = _correr(r, [2266, 2281, 3532])

    assert res.marcadas == 0
    assert "candidatos_al_crear = :actuales" in _sql_de(db)
