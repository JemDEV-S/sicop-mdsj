"""Tests de `saldos_service`: fusión SIGA (fases previas) + devengado MEF real.

Verifican la lógica de la Iteración 2 (Docs/consolidacion-backend-presupuestal.md):
  - El % y el semáforo se calculan sobre el devengado MEF, nunca sobre cert+compr.
  - El bloque MEF por meta no se multiplica por las filas clasificador×CC.
  - Metas sin cruce MEF quedan con % = None (no se inventa con cert+compr).
  - El bloque MEF del resumen aparece también con filtro de CC.
  - La criticidad usa el % devengado real.

Se mockean saldos_repo y ejecucion_mef_repo — no golpean la BD.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services import saldos_service


def _mef(pim, dev, cert=0, compr=0, pia=0, girado=0, sinc=None):
    return {
        "pia": pia, "pim": pim, "certificado": cert, "comprometido": compr,
        "devengado": dev, "girado": girado,
        "saldo_disponible": pim - dev,
        "porcentaje_devengado": round(dev / pim * 100, 2) if pim else 0.0,
        "sincronizado_en": sinc,
    }


# ─── listar_saldos ───────────────────────────────────────────────────────

@patch("app.services.saldos_service.semaforo_service.color", return_value="verde")
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.contar_saldos", return_value=1)
@patch("app.services.saldos_service.saldos_repo.listar_saldos")
def test_listar_calcula_porcentaje_sobre_devengado_mef(
    m_listar, _m_contar, m_mef, _m_color, db=None
):
    # SIGA: cert+compr altos (300+250=550) que ANTES habrían dado 110% falso.
    m_listar.return_value = [{
        "sec_func": 2100, "nombre_meta": "Meta A", "act_proy": "AC",
        "pim": 500.0, "certificado": 300.0, "comprometido_anual": 250.0,
        "comprometido_mensual": 0.0, "saldo_disponible": 0.0,
        "reservado_pedido": 0.0, "filas_clasificador": 9,
    }]
    # MEF: devengado real = 200 sobre PIM 500 → 40%.
    m_mef.return_value = {2100: _mef(pim=500.0, dev=200.0, cert=300.0, compr=250.0)}

    items, total = saldos_service.listar_saldos(None, ano=2026, centros=None)
    fila = items[0]

    assert total == 1
    # El % es el REAL (40%), no el inflado de cert+compr (110%).
    assert fila["porcentaje_devengado"] == 40.0
    assert fila["devengado_mef"] == 200.0
    # No existe un campo "devengado" plano que confunda cert+compr con devengado.
    assert "devengado" not in fila
    # Las fases previas se conservan con su nombre.
    assert fila["certificado"] == 300.0
    assert fila["comprometido_anual"] == 250.0


@patch("app.services.saldos_service.semaforo_service.color", return_value="desconocido")
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.contar_saldos", return_value=1)
@patch("app.services.saldos_service.saldos_repo.listar_saldos")
def test_listar_meta_sin_cruce_mef_no_inventa_devengado(
    m_listar, _m_contar, m_mef, _m_color
):
    m_listar.return_value = [{
        "sec_func": 999, "nombre_meta": "Sin MEF", "act_proy": None,
        "pim": 100.0, "certificado": 50.0, "comprometido_anual": 40.0,
        "comprometido_mensual": 0.0, "saldo_disponible": 0.0,
        "reservado_pedido": 0.0, "filas_clasificador": 1,
    }]
    m_mef.return_value = {}  # la meta no está en el snapshot MEF

    items, _ = saldos_service.listar_saldos(None, ano=2026, centros=None)
    fila = items[0]
    assert fila["devengado_mef"] is None
    assert fila["porcentaje_devengado"] is None      # no se inventa con cert+compr
    assert fila["semaforo"] == "desconocido"


@patch("app.services.saldos_service.semaforo_service.color", return_value="verde")
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.contar_saldos", return_value=2)
@patch("app.services.saldos_service.saldos_repo.listar_saldos")
def test_listar_pide_mef_solo_de_las_metas_de_la_pagina(
    m_listar, _m_contar, m_mef, _m_color
):
    m_listar.return_value = [
        {"sec_func": 11, "nombre_meta": "A", "act_proy": None, "pim": 10,
         "certificado": 0, "comprometido_anual": 0, "comprometido_mensual": 0,
         "saldo_disponible": 0, "reservado_pedido": 0, "filas_clasificador": 1},
        {"sec_func": 22, "nombre_meta": "B", "act_proy": None, "pim": 20,
         "certificado": 0, "comprometido_anual": 0, "comprometido_mensual": 0,
         "saldo_disponible": 0, "reservado_pedido": 0, "filas_clasificador": 1},
    ]
    m_mef.return_value = {}
    saldos_service.listar_saldos(None, ano=2026, centros=None)
    # el service pide MEF acotado a las metas visibles, no todo el pliego.
    assert m_mef.call_args.kwargs["sec_funcs"] == [11, 22]


# ─── resumen_saldos ──────────────────────────────────────────────────────

@patch("app.services.saldos_service.semaforo_service.color", return_value="rojo")
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.resumen_saldos")
def test_resumen_bloque_mef_existe_con_filtro_de_cc(m_resumen, m_mef, _m_color):
    # Usuario con CC (centros != None): antes el bloque MEF se ocultaba.
    m_resumen.return_value = {
        "pia": 0, "pim": 1000, "certificado": 400, "comprometido": 300,
        "saldo_disponible": 0, "reservado_pedido": 0, "metas_total": 2,
        "metas": [
            {"sec_func": 11, "nombre_meta": "A", "pim": 600, "certificado": 0, "comprometido": 0},
            {"sec_func": 22, "nombre_meta": "B", "pim": 400, "certificado": 0, "comprometido": 0},
        ],
    }
    m_mef.return_value = {
        11: _mef(pim=600, dev=120),   # 20%
        22: _mef(pim=400, dev=40),    # 10% → crítica
    }

    res = saldos_service.resumen_saldos(None, ano=2026, centros=["01.03.11.02"])

    assert res["mef"] is not None                     # ya NO se oculta
    assert res["mef"]["devengado"] == 160             # 120 + 40
    assert res["mef"]["pim"] == 1000
    assert res["porcentaje_devengado"] == 16.0        # 160/1000, sobre MEF real
    # Ambas están < umbral 30 → 2 críticas, priorizadas por PIM.
    assert res["metas_criticas"] == 2
    assert res["top_metas_criticas"][0]["sec_func"] == 11   # mayor PIM primero
    assert res["top_metas_criticas"][0]["porcentaje_devengado"] == 20.0


@patch("app.services.saldos_service.semaforo_service.color", return_value="rojo")
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.resumen_saldos")
def test_resumen_criticidad_usa_devengado_mef_no_cert_compr(m_resumen, m_mef, _m_color):
    # Meta con cert+compr = 550 (110% de PIM) pero devengado real bajo → crítica.
    m_resumen.return_value = {
        "pia": 0, "pim": 500, "certificado": 300, "comprometido": 250,
        "saldo_disponible": 0, "reservado_pedido": 0, "metas_total": 1,
        "metas": [{"sec_func": 2100, "nombre_meta": "A", "pim": 500,
                   "certificado": 300, "comprometido": 250}],
    }
    m_mef.return_value = {2100: _mef(pim=500, dev=50)}   # 10% real

    res = saldos_service.resumen_saldos(None, ano=2026, centros=None)
    # Si se usara cert+compr (110%) NO sería crítica. Con devengado real (10%) sí.
    assert res["metas_criticas"] == 1
    assert res["top_metas_criticas"][0]["porcentaje_devengado"] == 10.0


# ─── metas_rezagadas ─────────────────────────────────────────────────────

@patch("app.services.saldos_service.semaforo_service.color", return_value="rojo")
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.metas_con_saldo")
def test_metas_rezagadas_filtra_por_devengado_mef(m_metas, m_mef, _m_color):
    m_metas.return_value = [
        {"sec_func": 11, "nombre_meta": "Rezagada", "act_proy": None,
         "pim": 100, "certificado": 90, "comprometido": 80},   # cert+compr alto
        {"sec_func": 22, "nombre_meta": "Al día", "act_proy": None,
         "pim": 100, "certificado": 0, "comprometido": 0},
    ]
    m_mef.return_value = {
        11: _mef(pim=100, dev=20),   # 20% real → rezagada (< 50)
        22: _mef(pim=100, dev=80),   # 80% real → NO rezagada
    }

    res = saldos_service.metas_rezagadas(
        None, ano=2026, centros=None, umbral_porcentaje=50.0
    )
    # Solo la 11, aunque su cert+compr sea altísimo: el criterio es devengado real.
    assert [m["sec_func"] for m in res] == [11]
    assert res[0]["porcentaje_devengado"] == 20.0


@patch("app.services.saldos_service.semaforo_service.color", return_value="rojo")
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.metas_con_saldo")
def test_metas_rezagadas_ordena_por_porcentaje_ascendente(m_metas, m_mef, _m_color):
    m_metas.return_value = [
        {"sec_func": 11, "nombre_meta": "A", "act_proy": None, "pim": 100, "certificado": 0, "comprometido": 0},
        {"sec_func": 22, "nombre_meta": "B", "act_proy": None, "pim": 100, "certificado": 0, "comprometido": 0},
    ]
    m_mef.return_value = {11: _mef(pim=100, dev=40), 22: _mef(pim=100, dev=10)}
    res = saldos_service.metas_rezagadas(None, ano=2026, centros=None, umbral_porcentaje=50.0)
    assert [m["sec_func"] for m in res] == [22, 11]   # 10% antes que 40%
