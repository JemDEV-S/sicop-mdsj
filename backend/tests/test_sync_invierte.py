"""Tests unitarios de conversores y merge por CODIGO_UNICO en sync_invierte."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import httpx

from app.jobs import sync_invierte as m
from app.services.mef_client import MefClient


def test_fecha_parsea_formatos_comunes():
    assert m._fecha("2026-03-15") == date(2026, 3, 15)
    assert m._fecha("2026-03-15T00:00:00") == date(2026, 3, 15)
    assert m._fecha("") is None
    assert m._fecha(None) is None


def test_si_no_normaliza():
    assert m._si_no("SI") == "SI"
    assert m._si_no("no") == "NO"
    assert m._si_no("Otra") is None
    assert m._si_no(None) is None


def test_num_o_none_maneja_strings_vacios():
    assert m._num_o_none("") is None
    assert m._num_o_none("1.5") == 1.5
    assert m._num_o_none("abc") is None
    assert m._num_o_none(3) == 3.0


def test_leer_todo_consolida_por_codigo():
    """Simula respuestas de los 7 SQL y verifica el merge."""

    respuestas = iter([
        # sql_inversiones
        [{"CODIGO_UNICO": "2100", "NOMBRE_INVERSION": "Obra A"}],
        # avance
        [{"CODIGO_UNICO": "2100", "AVANCE_FISICO": "50.5", "TIENE_AVAN_FISICO": "SI"}],
        # costo
        [{"CODIGO_UNICO": "2100", "COSTO_ACTUALIZADO": "1000"}],
        # etapa
        [{"CODIGO_UNICO": "2100", "DES_TIPOLOGIA": "PISTAS"}],
        # cronograma
        [{"CODIGO_UNICO": "2100", "FEC_INI_EJECUCION": "2026-01-15"}],
        # geo
        [{"CODIGO_UNICO": "2100", "LATITUD": "-13.5", "LONGITUD": "-71.9",
          "UBIGEO": "080104"}],
        # unidades
        [{"CODIGO_UNICO": "2100", "NOMBRE_UF": "UF-1"}],
    ])

    def fake_get(self, url, params=None):
        return httpx.Response(
            200,
            json={"success": True, "result": {"records": next(respuestas)}},
        )

    with patch.object(httpx.Client, "get", fake_get):
        with MefClient() as client:
            consolidado = m._leer_todo(client)

    assert set(consolidado.keys()) == {"2100"}
    fila = consolidado["2100"]
    assert fila["nombre_inversion"] == "Obra A"
    assert fila["avance_fisico"] == 50.5
    assert fila["tiene_avan_fisico"] == "SI"
    assert fila["costo_actualizado"] == 1000.0
    assert fila["des_tipologia"] == "PISTAS"
    assert fila["fec_ini_ejecucion"] == date(2026, 1, 15)
    assert fila["latitud"] == -13.5
    assert fila["longitud"] == -71.9
    assert fila["nombre_uf"] == "UF-1"
