"""Tests de `pipeline_reporte_service`: zona crítica de montos.

Verifican la regla anti-inflado (Docs/pipeline-vista-profesional-v2.md §2, §7)
y el reparto del devengado por celda de clasificador (§9.1/§9.7):

  - El total MEF es el devengado real por meta distinta, 1× — NUNCA repetido
    por fila-pedido (el error que infla ×34.9).
  - El devengado por pedido es una estimación proporcional al monto SIGA de los
    pedidos CON orden de su celda; la suma del reparto de una celda = devengado
    real de esa celda (no la excede).
  - Celda de 1 pedido → atribución directa (sin reparto).
  - Pedido sin orden → sin monto de ejecución atribuido.
  - El monto SIGA se suma por pedido (informativo).

Se mockean `clasificar_pedidos`, los repos MEF y el semáforo — no golpean BD.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services import pipeline_reporte_service as svc


def _card(nro, sec_func, cc="CC1", macrofase="ejecucion", monto=100.0,
          tiene_orden=True, n_cand=1, tipo_bien="B", tipo_pedido="2"):
    """Card mínima como la que devuelve pipeline_service.clasificar_pedidos."""
    return {
        "nro_pedido": nro, "tipo_bien": tipo_bien, "tipo_pedido": tipo_pedido,
        "centro_costo": cc, "sec_func": sec_func, "motivo": f"pedido {nro}",
        "identificadores": {"pedido": f"{nro}-2026/{tipo_bien}", "orden": None,
                            "exp_siaf": None, "ccp_siaf": None},
        "fechas": {}, "etapa": "ejecucion", "etapa_label": "Ejecución",
        "macrofase": macrofase, "dias_en_etapa": 5, "estancado": False,
        "alerta": None, "monto_total": monto, "n_candidatos_ccmn": n_cand,
        "confianza_ccmn": "unico" if n_cand == 1 else "ambiguo",
        "puente": {"avance_bolsa": {"n_ordenes": 1 if tiene_orden else 0}},
    }


def _mef_meta(pim, compr, dev):
    return {"pim": pim, "comprometido": compr, "devengado": dev,
            "porcentaje_devengado": round(dev / pim * 100, 2) if pim else None}


def _mef_celda(pim, compr, dev, nombre="Clasif X"):
    return {"pim": pim, "comprometido": compr, "devengado": dev,
            "clasificador_nombre": nombre}


def _ctx(color="verde"):
    return {"color": color, "esperado": 58.33, "real": 50.0,
            "rezago": 8.33, "mes_corte": 7}


def _patchers(cards, clasif, mef_meta, mef_celda):
    """Aplica todos los mocks; devuelve el resultado del reporte."""
    with patch.object(svc.pipeline_service, "clasificar_pedidos", return_value=cards), \
         patch.object(svc.pipeline_read_repo, "clasificador_por_pedido", return_value=clasif), \
         patch.object(svc.ejecucion_mef_repo, "ejecucion_por_meta", return_value=mef_meta), \
         patch.object(svc.ejecucion_mef_repo, "ejecucion_por_celda_clasificador", return_value=mef_celda), \
         patch.object(svc.ejecucion_mef_repo, "mes_maximo_ejecutado", return_value=7), \
         patch.object(svc.semaforo_service, "color_temporal", return_value=_ctx()), \
         patch.object(svc.semaforo_service, "avance_esperado", return_value=58.33), \
         patch.object(svc, "_nombres_meta", return_value={73: "Meta 73"}), \
         patch.object(svc, "_catalogo_cc", return_value=[]), \
         patch.object(svc, "_sincronizado", return_value={"siga": None, "mef": None}):
        return svc.reporte_profesional(db=None, ano=2026, centros=None)


# ─── Anti-inflado: el devengado MEF se cuenta 1× por meta ────────────────

def test_total_mef_es_devengado_por_meta_distinta():
    # Meta 73 con 3 pedidos en la MISMA celda. El devengado de la meta es 900;
    # si se sumara por fila daría 2700 (×3). El total debe ser 900.
    cards = [_card(1, 73), _card(2, 73), _card(3, 73)]
    clasif = {
        ("B", "2", 1): {"clasificador": "3.1.1.1.1", "monto": 100.0},
        ("B", "2", 2): {"clasificador": "3.1.1.1.1", "monto": 100.0},
        ("B", "2", 3): {"clasificador": "3.1.1.1.1", "monto": 100.0},
    }
    mef_meta = {73: _mef_meta(2000, 1200, 900)}
    mef_celda = {(73, "3.1.1.1.1"): _mef_celda(2000, 1200, 900)}

    r = _patchers(cards, clasif, mef_meta, mef_celda)

    assert r["totales"]["total_mef_devengado"] == 900.0
    assert r["totales"]["n_pedidos"] == 3
    assert r["totales"]["total_siga_pedidos"] == 300.0  # 3 × 100 SIGA


# ─── Reparto proporcional dentro de la celda ─────────────────────────────

def test_reparto_proporcional_al_monto_siga_con_orden():
    # Celda con 3 pedidos con orden, montos 100/200/300 (base 600). Devengado
    # de celda 600 → cada uno recibe dev * monto/base = 100/200/300.
    cards = [_card(1, 73, monto=100), _card(2, 73, monto=200), _card(3, 73, monto=300)]
    clasif = {(("B", "2", n)): {"clasificador": "3.1.1.1.1", "monto": m}
              for n, m in [(1, 100), (2, 200), (3, 300)]}
    mef_meta = {73: _mef_meta(2000, 700, 600)}
    mef_celda = {(73, "3.1.1.1.1"): _mef_celda(2000, 700, 600)}

    r = _patchers(cards, clasif, mef_meta, mef_celda)
    celda = r["metas"][0]["celdas"][0]
    devs = {p["nro_pedido"]: p["devengado_estimado"] for p in celda["pedidos"]}

    assert devs == {1: 100.0, 2: 200.0, 3: 300.0}
    # La suma del reparto no excede el devengado real de la celda.
    assert round(sum(devs.values()), 2) == 600.0
    assert all(p["atribucion"] == "estimado" for p in celda["pedidos"])


# ─── Celda de 1 pedido: atribución directa (sin reparto) ─────────────────

def test_celda_un_pedido_es_directa():
    cards = [_card(1, 73, monto=100)]
    clasif = {("B", "2", 1): {"clasificador": "3.1.1.1.1", "monto": 100.0}}
    mef_meta = {73: _mef_meta(500, 200, 150)}
    mef_celda = {(73, "3.1.1.1.1"): _mef_celda(500, 200, 150)}

    r = _patchers(cards, clasif, mef_meta, mef_celda)
    celda = r["metas"][0]["celdas"][0]
    p = celda["pedidos"][0]

    assert celda["atribucion_directa"] is True
    assert p["atribucion"] == "directo"
    assert p["devengado_estimado"] == 150.0      # el devengado de la celda ES suyo
    assert p["comprometido_pedido"] == 200.0
    assert r["metas"][0]["n_celdas_directas"] == 1


# ─── Pedido sin orden: no recibe monto de ejecución ──────────────────────

def test_pedido_sin_orden_sin_devengado():
    # Dos pedidos en la celda; solo el 1 tiene orden. El devengado (500) se
    # reparte SOLO entre los con orden → todo al pedido 1; el 2 queda sin dato.
    cards = [_card(1, 73, monto=100, tiene_orden=True, n_cand=2),
             _card(2, 73, monto=100, tiene_orden=False, n_cand=2)]
    clasif = {("B", "2", 1): {"clasificador": "3.1.1.1.1", "monto": 100.0},
              ("B", "2", 2): {"clasificador": "3.1.1.1.1", "monto": 100.0}}
    mef_meta = {73: _mef_meta(2000, 600, 500)}
    mef_celda = {(73, "3.1.1.1.1"): _mef_celda(2000, 600, 500)}

    r = _patchers(cards, clasif, mef_meta, mef_celda)
    peds = {p["nro_pedido"]: p for p in r["metas"][0]["celdas"][0]["pedidos"]}

    assert peds[1]["devengado_estimado"] == 500.0
    assert peds[1]["atribucion"] == "estimado"
    assert peds[2]["devengado_estimado"] is None
    assert peds[2]["atribucion"] is None


# ─── Pedido sin clasificador cruzable: celda "(sin clasificador)" ────────

def test_pedido_sin_clasificador_va_a_celda_sin_clasificador():
    cards = [_card(1, 73, monto=100)]
    clasif = {}  # el pedido no cruza con genérica 3/6
    mef_meta = {73: _mef_meta(500, 200, 150)}
    mef_celda = {}

    r = _patchers(cards, clasif, mef_meta, mef_celda)
    celda = r["metas"][0]["celdas"][0]

    assert celda["clasificador"] == svc._SIN_CLASIF
    assert celda["mef"] is None                  # no cruza → sin dinero de celda
    assert celda["atribucion_directa"] is False  # sin celda MEF no hay directa
    assert celda["pedidos"][0]["devengado_estimado"] is None


# ─── Conteo por fase para el resumen ─────────────────────────────────────

def test_conteo_en_contratacion_y_ejecucion():
    cards = [
        _card(1, 73, macrofase="contratacion"),
        _card(2, 73, macrofase="certificacion"),
        _card(3, 73, macrofase="ejecucion"),
        _card(4, 73, macrofase="cierre"),
    ]
    clasif = {("B", "2", n): {"clasificador": "3.1.1.1.1", "monto": 100.0}
              for n in (1, 2, 3, 4)}
    mef_meta = {73: _mef_meta(2000, 1000, 800)}
    mef_celda = {(73, "3.1.1.1.1"): _mef_celda(2000, 1000, 800)}

    r = _patchers(cards, clasif, mef_meta, mef_celda)
    meta = r["metas"][0]

    assert meta["en_contratacion"] == 2  # contratacion + certificacion
    assert meta["en_ejecucion"] == 2     # ejecucion + cierre
    assert meta["n_pedidos"] == 4


# ─── Catálogo de CC en la respuesta (nombre/sigla para filtro y tabla) ───

def test_catalogo_cc_se_incluye_en_la_respuesta():
    # El catálogo lo resuelve _catalogo_cc a partir de los CC de los pedidos.
    cards = [_card(1, 73, cc="080104")]
    clasif = {("B", "2", 1): {"clasificador": "3.1.1.1.1", "monto": 100.0}}
    mef_meta = {73: _mef_meta(500, 200, 150)}
    mef_celda = {(73, "3.1.1.1.1"): _mef_celda(500, 200, 150)}

    cc_info = [{"codigo": "080104", "nombre": "Gerencia Municipal", "sigla": "GM"}]
    with patch.object(svc.pipeline_service, "clasificar_pedidos", return_value=cards), \
         patch.object(svc.pipeline_read_repo, "clasificador_por_pedido", return_value=clasif), \
         patch.object(svc.ejecucion_mef_repo, "ejecucion_por_meta", return_value=mef_meta), \
         patch.object(svc.ejecucion_mef_repo, "ejecucion_por_celda_clasificador", return_value=mef_celda), \
         patch.object(svc.ejecucion_mef_repo, "mes_maximo_ejecutado", return_value=7), \
         patch.object(svc.semaforo_service, "color_temporal", return_value=_ctx()), \
         patch.object(svc.semaforo_service, "avance_esperado", return_value=58.33), \
         patch.object(svc, "_nombres_meta", return_value={73: "Meta 73"}), \
         patch.object(svc, "_catalogo_cc", return_value=cc_info) as cat, \
         patch.object(svc, "_sincronizado", return_value={"siga": None, "mef": None}):
        r = svc.reporte_profesional(db=None, ano=2026, centros=None)

    # Se pidió el catálogo con el código de CC presente en los pedidos.
    cat.assert_called_once()
    assert cat.call_args.args[1] == ["080104"]
    assert r["centros_costo"] == cc_info
