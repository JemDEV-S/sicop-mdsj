"""Tests de `saldos_service`: cadena oficial SIAF/MEF + semáforo temporal.

Verifican el rediseño (Docs/consolidacion-backend-presupuestal.md, enriquecimiento):
  - Toda cifra presupuestal y todo saldo/% sale del SIAF/MEF (el PIM SIGA no es
    presupuesto). Los campos SIGA quedan como referencia `*_siga`.
  - Saldos entre fases (por certificar/comprometer/devengar/ejecutar/pagar) y
    % por fase se calculan sobre la cadena MEF.
  - El semáforo es TEMPORAL: compara el avance real vs. el esperado por el mes de
    corte, no un corte fijo. Rezago (esperado − real) decide el color.
  - El drill-down arma el árbol Fuente → Clasificadores con TODOS los
    clasificadores (incluidos los de PIM 0, marcados `sin_pim`).

Se mockean saldos_repo, ejecucion_mef_repo y semaforo_service — no golpean BD.
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


def _ctx(color="verde", esperado=58.33, real=None, rezago=None, mes=7):
    return {"color": color, "esperado": esperado, "real": real,
            "rezago": rezago, "mes_corte": mes}


# ─── listar_saldos ───────────────────────────────────────────────────────

@patch("app.services.saldos_service.semaforo_service.color_temporal", return_value=_ctx())
@patch("app.services.saldos_service.ejecucion_mef_repo.mes_maximo_ejecutado", return_value=7)
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.contar_saldos", return_value=1)
@patch("app.services.saldos_service.saldos_repo.listar_saldos")
def test_listar_cadena_y_saldos_desde_mef(
    m_listar, _m_contar, m_mef, _m_mes, _m_color
):
    m_listar.return_value = [{
        "sec_func": 2100, "nombre_meta": "Meta A", "act_proy": "AC",
        "pim": 400.0, "certificado": 300.0, "comprometido_anual": 250.0,
        "comprometido_mensual": 0.0, "saldo_disponible": 0.0,
        "reservado_pedido": 0.0, "filas_clasificador": 9, "pia": 0.0,
    }]
    # MEF: PIM 500, cert 450, compr 400, dev 200, girado 150.
    m_mef.return_value = {
        2100: _mef(pim=500.0, dev=200.0, cert=450.0, compr=400.0, girado=150.0)
    }

    items, total = saldos_service.listar_saldos(None, ano=2026, centros=None)
    fila = items[0]

    assert total == 1
    # Cifra presupuestal y cadena vienen del MEF.
    assert fila["pim_mef"] == 500.0
    assert fila["devengado_mef"] == 200.0
    assert fila["porcentaje_devengado"] == 40.0        # 200/500
    # Saldos entre fases.
    assert fila["saldo_por_certificar"] == 50.0        # 500 − 450
    assert fila["saldo_por_comprometer_mef"] == 50.0   # 450 − 400
    assert fila["saldo_por_devengar"] == 200.0         # 400 − 200
    assert fila["saldo_por_ejecutar"] == 300.0         # 500 − 200 (clave)
    assert fila["saldo_por_pagar"] == 50.0             # 200 − 150
    # % por fase sobre PIM.
    assert fila["porcentaje_certificado"] == 90.0
    assert fila["porcentaje_girado"] == 30.0
    # El PIM SIGA se conserva como referencia, NO como presupuesto.
    assert fila["pim_siga"] == 400.0
    assert "pim" not in fila                            # ya no hay PIM plano SIGA


@patch("app.services.saldos_service.semaforo_service.color_temporal",
       return_value=_ctx(color="desconocido"))
@patch("app.services.saldos_service.ejecucion_mef_repo.mes_maximo_ejecutado", return_value=7)
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.contar_saldos", return_value=1)
@patch("app.services.saldos_service.saldos_repo.listar_saldos")
def test_listar_meta_sin_cruce_mef_no_inventa(m_listar, _m_contar, m_mef, _m_mes, _m_color):
    m_listar.return_value = [{
        "sec_func": 999, "nombre_meta": "Sin MEF", "act_proy": None,
        "pim": 100.0, "certificado": 50.0, "comprometido_anual": 40.0,
        "comprometido_mensual": 0.0, "saldo_disponible": 0.0,
        "reservado_pedido": 0.0, "filas_clasificador": 1, "pia": 0.0,
    }]
    m_mef.return_value = {}  # no cruza

    items, _ = saldos_service.listar_saldos(None, ano=2026, centros=None)
    fila = items[0]
    assert fila["pim_mef"] is None
    assert fila["porcentaje_devengado"] is None
    assert fila["saldo_por_ejecutar"] is None
    assert fila["semaforo"] == "desconocido"


# ─── semáforo temporal ───────────────────────────────────────────────────

def test_avance_esperado_lineal():
    from app.services import semaforo_service
    assert semaforo_service.avance_esperado(0) == 0.0
    assert semaforo_service.avance_esperado(7) == 58.33
    assert semaforo_service.avance_esperado(12) == 100.0
    assert semaforo_service.avance_esperado(99) == 100.0  # acotado


@patch("app.services.semaforo_service.cargar_umbrales")
def test_color_temporal_usa_rezago(_m_cargar):
    from app.services import semaforo_service
    semaforo_service._CACHE[("saldos", "avance_vs_esperado")] = {
        "verde": 10.0, "amarillo": 25.0, "direccion": "menor",
    }
    # esperado a mes 7 = 58.33
    verde = semaforo_service.color_temporal(None, modulo="saldos", porcentaje_real=55, mes_corte=7)
    assert verde["color"] == "verde"        # rezago 3.33 ≤ 10
    amar = semaforo_service.color_temporal(None, modulo="saldos", porcentaje_real=40, mes_corte=7)
    assert amar["color"] == "amarillo"      # rezago 18.33 ≤ 25
    rojo = semaforo_service.color_temporal(None, modulo="saldos", porcentaje_real=20, mes_corte=7)
    assert rojo["color"] == "rojo"          # rezago 38.33 > 25
    # Adelantado (real > esperado) siempre verde.
    adel = semaforo_service.color_temporal(None, modulo="saldos", porcentaje_real=70, mes_corte=7)
    assert adel["color"] == "verde" and adel["rezago"] < 0
    # Sin dato real → desconocido.
    nd = semaforo_service.color_temporal(None, modulo="saldos", porcentaje_real=None, mes_corte=7)
    assert nd["color"] == "desconocido"
    semaforo_service._CACHE.clear()


# ─── detalle_meta (árbol jerárquico) ─────────────────────────────────────

@patch("app.services.saldos_service.semaforo_service.color_temporal", return_value=_ctx())
@patch("app.services.saldos_service.ejecucion_mef_repo.mes_maximo_ejecutado", return_value=7)
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.detalle_meta_jerarquico")
@patch("app.services.saldos_service.saldos_repo.cabecera_meta")
def test_detalle_meta_arma_arbol_por_fuente(m_cab, m_det, m_mef, _m_mes, _m_color):
    m_cab.return_value = {
        "sec_func": 57, "nombre_meta": "Meta 57", "act_proy": "AC",
        "pim": 100.0, "certificado": 30.0, "comprometido": 20.0,
        "saldo_disponible": 0.0, "reservado_pedido": 0.0,
        "filas_clasificador": 26, "n_clasificadores": 12, "n_fuentes": 3,
    }
    # Filas planas fuente × clasificador (incluye uno con PIM 0).
    m_det.return_value = [
        {"fuente_codigo": "09", "fuente_nombre": "RDR", "codigo": "2.6.6.1.3.2",
         "nombre": "SOFTWARES", "pim": 45000.0, "certificado": 15000.0,
         "comprometido": 10000.0, "saldo_disponible": 0.0, "reservado_pedido": 0.0, "filas": 3},
        {"fuente_codigo": "09", "fuente_nombre": "RDR", "codigo": "2.3.1.5.1.2",
         "nombre": "PAPELERIA", "pim": 0.0, "certificado": 0.0,
         "comprometido": 0.0, "saldo_disponible": 0.0, "reservado_pedido": 0.0, "filas": 3},
        {"fuente_codigo": "07", "fuente_nombre": "FONCOMUN", "codigo": "2.1.3.1.1.6",
         "nombre": "CONTRIB", "pim": 2131.0, "certificado": 0.0,
         "comprometido": 0.0, "saldo_disponible": 0.0, "reservado_pedido": 0.0, "filas": 1},
    ]
    m_mef.return_value = {57: _mef(pim=500.0, dev=200.0)}

    data = saldos_service.detalle_meta(None, ano=2026, sec_func=57, centros=None)

    # Cabecera con cadena oficial.
    assert data["cabecera"]["porcentaje_devengado"] == 40.0
    # Dos fuentes; la 09 primero (mayor PIM).
    assert [f["fuente_codigo"] for f in data["fuentes"]] == ["09", "07"]
    fuente09 = data["fuentes"][0]
    assert fuente09["n_clasificadores"] == 2
    # El clasificador con PIM 0 se muestra (no se oculta) y se marca.
    codigos = {c["codigo"]: c for c in fuente09["clasificadores"]}
    assert codigos["2.3.1.5.1.2"]["sin_pim"] is True
    assert codigos["2.6.6.1.3.2"]["sin_pim"] is False
    # Saldo por comprometer por línea.
    assert codigos["2.6.6.1.3.2"]["saldo_por_comprometer"] == 35000.0  # 45000 − 10000


@patch("app.services.saldos_service.saldos_repo.cabecera_meta", return_value=None)
def test_detalle_meta_inexistente_devuelve_none(_m_cab):
    assert saldos_service.detalle_meta(None, ano=2026, sec_func=99999, centros=None) is None


# ─── resumen_saldos ──────────────────────────────────────────────────────

@patch("app.services.saldos_service.semaforo_service.color_temporal")
@patch("app.services.saldos_service.ejecucion_mef_repo.mes_maximo_ejecutado", return_value=7)
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.resumen_saldos")
def test_resumen_criticas_por_rezago_temporal(m_resumen, m_mef, _m_mes, m_color):
    m_resumen.return_value = {
        "pia": 0, "pim": 1000, "certificado": 400, "comprometido": 300,
        "saldo_disponible": 0, "reservado_pedido": 0, "metas_total": 2,
        "metas": [
            {"sec_func": 11, "nombre_meta": "A", "pim": 600, "certificado": 0, "comprometido": 0},
            {"sec_func": 22, "nombre_meta": "B", "pim": 400, "certificado": 0, "comprometido": 0},
        ],
    }
    m_mef.return_value = {
        11: _mef(pim=600, dev=300),   # 50% → rezago 8.33 → verde
        22: _mef(pim=400, dev=40),    # 10% → rezago 48.33 → rojo
    }
    # color_temporal: rojo solo para la meta 22 (baja), verde para 11 y global.
    def color(_db, *, modulo, porcentaje_real, mes_corte):
        c = "rojo" if (porcentaje_real is not None and porcentaje_real < 20) else "verde"
        return _ctx(color=c, real=porcentaje_real, rezago=58.33 - (porcentaje_real or 0))
    m_color.side_effect = color

    res = saldos_service.resumen_saldos(None, ano=2026, centros=["01.03"])

    assert res["mef"]["devengado"] == 340        # 300 + 40
    assert res["mes_corte"] == 7
    assert res["avance_esperado"] == 58.33
    # Solo la 22 es crítica (rojo por rezago), no la 11.
    assert res["metas_criticas"] == 1
    assert res["top_metas_criticas"][0]["sec_func"] == 22


# ─── metas_rezagadas ─────────────────────────────────────────────────────

@patch("app.services.saldos_service.semaforo_service.color_temporal", return_value=_ctx(color="rojo"))
@patch("app.services.saldos_service.ejecucion_mef_repo.mes_maximo_ejecutado", return_value=7)
@patch("app.services.saldos_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.saldos_service.saldos_repo.metas_con_saldo")
def test_metas_rezagadas_filtra_por_devengado_mef(m_metas, m_mef, _m_mes, _m_color):
    m_metas.return_value = [
        {"sec_func": 11, "nombre_meta": "Rezagada", "act_proy": None,
         "pim": 100, "certificado": 90, "comprometido": 80},
        {"sec_func": 22, "nombre_meta": "Al día", "act_proy": None,
         "pim": 100, "certificado": 0, "comprometido": 0},
    ]
    m_mef.return_value = {
        11: _mef(pim=100, dev=20),   # 20% < 50 → rezagada
        22: _mef(pim=100, dev=80),   # 80% → NO
    }
    res = saldos_service.metas_rezagadas(
        None, ano=2026, centros=None, umbral_porcentaje=50.0
    )
    assert [m["sec_func"] for m in res] == [11]
    assert res[0]["porcentaje_devengado"] == 20.0
