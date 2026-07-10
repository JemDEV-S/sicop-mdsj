"""Test de integración de `sync_catalogos_siga` contra PostgreSQL real.

Mockea la lectura de SIGA con datos fixture; el resto del pipeline (staging,
swap, ltree, log) corre contra la BD PostgreSQL de dev.

Requiere:
- PostgreSQL corriendo (docker-compose up postgres) con `alembic upgrade head`.

Se usa `monkeypatch` para reemplazar las 3 funciones lectoras. Después de la
sincronización, se restaura el estado ejecutando el job real (si `RESTORE_SIGA=1`)
o dejando el snapshot fixture (útil para debug local).
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.database import SessionLocal
from app.jobs import sync_catalogos_siga

FIXTURE_CC = [
    {
        "codigo": "01",
        "nombre": "MUNICIPALIDAD DISTRITAL",
        "abreviado": "MUNI",
        "centro_padre": None,
        "sede": 1,
        "tipo_dependencia": "D",
        "nro_personal": 10,
        "flag_cn": True,
        "flag_presupuesto": True,
        "flag_ppr": False,
        "activo": True,
    },
    {
        "codigo": "01.01",
        "nombre": "GERENCIA MUNICIPAL",
        "abreviado": "GM",
        "centro_padre": "01",
        "sede": 1,
        "tipo_dependencia": "G",
        "nro_personal": 5,
        "flag_cn": True,
        "flag_presupuesto": True,
        "flag_ppr": False,
        "activo": True,
    },
    {
        "codigo": "01.01.02",
        "nombre": "OFICINA DE TECNOLOGIA",
        "abreviado": "OTI",
        "centro_padre": "01.01",
        "sede": 1,
        "tipo_dependencia": "O",
        "nro_personal": 3,
        "flag_cn": True,
        "flag_presupuesto": False,
        "flag_ppr": False,
        "activo": True,
    },
]

FIXTURE_METAS = [
    {
        "sec_func": 999901,
        "ano_eje": 2026,
        "meta": "00001",
        "nombre": "META TEST 1",
        "funcion": "03",
        "programa": "006",
        "sub_programa": "0007",
        "act_proy": "3999999",
        "componente": "3999999",
        "finalidad": "0000001",
        "unidad_med": "064",
        "activo": True,
        "tipo_meta": "actividad_generica",
    },
    {
        "sec_func": 999902,
        "ano_eje": 2026,
        "meta": "00002",
        "nombre": "PROYECTO INVERSION TEST",
        "funcion": "15",
        "programa": "047",
        "sub_programa": "0110",
        "act_proy": "2669624",
        "componente": "0163020",
        "finalidad": "0140026",
        "unidad_med": "004",
        "activo": True,
        "tipo_meta": "proyecto_inversion",
    },
]

FIXTURE_MXC = [
    {
        "sec_func": 999901,
        "centro_costo": "01.01.02",
        "secuencia": 1,
        "fuente_financ": "1",
        "tipo_recurso": "00",
        "porc_techo": 100.0,
    },
    {
        "sec_func": 999902,
        "centro_costo": "01.01",
        "secuencia": 1,
        "fuente_financ": "5",
        "tipo_recurso": "18",
        "porc_techo": 100.0,
    },
]


@pytest.fixture
def mock_siga(monkeypatch):
    """Reemplaza los 3 lectores SIGA con datos fixture."""
    monkeypatch.setattr(
        sync_catalogos_siga, "leer_centros_costo", lambda ano: list(FIXTURE_CC)
    )
    monkeypatch.setattr(
        sync_catalogos_siga, "leer_metas", lambda ano: list(FIXTURE_METAS)
    )
    monkeypatch.setattr(
        sync_catalogos_siga, "leer_metas_centro_costo", lambda ano: list(FIXTURE_MXC)
    )


def test_sync_completo_con_mock(mock_siga):
    """El job pobla las 3 tablas y construye la jerarquía ltree correcta."""
    resultado = sync_catalogos_siga.sync_catalogos(ano=2026)

    assert resultado.centros_costo == 3
    assert resultado.metas == 2
    assert resultado.metas_centro_costo == 2

    with SessionLocal() as db:
        # Volúmenes
        n_cc = db.execute(text("SELECT COUNT(*) FROM ref.centros_costo")).scalar()
        n_m = db.execute(text("SELECT COUNT(*) FROM ref.metas")).scalar()
        n_mxc = db.execute(text("SELECT COUNT(*) FROM ref.metas_centro_costo")).scalar()
        assert n_cc == 3
        assert n_m == 2
        assert n_mxc == 2

        # Jerarquía ltree: descendientes de 01 = 3 (incluido él mismo)
        descendientes = db.execute(
            text("SELECT COUNT(*) FROM ref.centros_costo WHERE ruta <@ 'root.01'::ltree")
        ).scalar()
        assert descendientes == 3

        # Solo OTI cuelga de GERENCIA MUNICIPAL
        bajo_gm = db.execute(
            text(
                "SELECT COUNT(*) FROM ref.centros_costo "
                "WHERE ruta <@ 'root.01.01_01'::ltree AND codigo <> '01.01'"
            )
        ).scalar()
        assert bajo_gm == 1

        # Log de sincronización tiene una fila de éxito
        estado = db.execute(
            text(
                "SELECT estado FROM logs.sincronizacion "
                "WHERE job = 'catalogos_siga:2026' "
                "ORDER BY inicio DESC LIMIT 1"
            )
        ).scalar()
        assert estado == "exito"

        # tipo_meta se clasifica correctamente
        tipos = dict(
            db.execute(text("SELECT sec_func, tipo_meta FROM ref.metas")).all()
        )
        assert tipos[999901] == "actividad_generica"
        assert tipos[999902] == "proyecto_inversion"

        # El puente respeta las FK (integridad relacional)
        huerfanos = db.execute(
            text(
                """
                SELECT COUNT(*) FROM ref.metas_centro_costo mxc
                LEFT JOIN ref.metas m ON m.sec_func = mxc.sec_func
                LEFT JOIN ref.centros_costo cc ON cc.codigo = mxc.centro_costo
                WHERE m.sec_func IS NULL OR cc.codigo IS NULL
                """
            )
        ).scalar()
        assert huerfanos == 0
