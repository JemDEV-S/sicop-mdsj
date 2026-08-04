"""Tests de `cruce_service`: consolidado de meta con devengado MEF real.

Iteración 3 (Docs/consolidacion-backend-presupuestal.md): el bloque presupuesto
del cruce deja de usar MNTO_ACUM_DEVGDO_SIGA (que daba devengado=0) y adjunta el
devengado OFICIAL del MEF desde la vista, cuadrando con saldos y el portal.

Se mockean cruce_repo y ejecucion_mef_repo — no golpean la BD.
"""

from __future__ import annotations

from unittest.mock import patch

from app.services import cruce_service


def _mef(pim, dev, cert=0, compr=0, pia=0, girado=0):
    return {
        "pia": pia, "pim": pim, "certificado": cert, "comprometido": compr,
        "devengado": dev, "girado": girado,
        "saldo_disponible": pim - dev,
        "porcentaje_devengado": round(dev / pim * 100, 2) if pim else 0.0,
        "sincronizado_en": None,
    }


def _consolidado_base():
    return {
        "meta": {"sec_func": 129, "ano_eje": 2026, "nombre": "Meta X"},
        "presupuesto": {
            "pia": 0, "pim": 5000.0, "certificado": 0, "comprometido": 0,
            "saldo_disponible": 0,
        },
        "ordenes": [],
        "pedidos": [],
        "certificaciones": [],
    }


@patch("app.services.cruce_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.cruce_service.cruce_repo.consolidado_por_meta")
def test_adjunta_devengado_mef_real(m_repo, m_mef):
    m_repo.return_value = _consolidado_base()
    m_mef.return_value = {129: _mef(pim=5400.0, dev=2423.0)}

    res = cruce_service.consolidado_por_meta(None, ano=2026, sec_func=129)
    p = res["presupuesto"]
    assert p["devengado_mef"] == 2423.0            # ya no es 0
    assert p["pim_mef"] == 5400.0
    assert p["porcentaje_devengado"] == 44.87      # 2423/5400
    assert p["saldo_disponible_mef"] == 5400.0 - 2423.0
    # El bloque SIGA operativo se conserva intacto.
    assert p["pim"] == 5000.0


@patch("app.services.cruce_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.cruce_service.cruce_repo.consolidado_por_meta")
def test_meta_sin_cruce_mef_no_inventa(m_repo, m_mef):
    m_repo.return_value = _consolidado_base()
    m_mef.return_value = {}  # la meta no está en el snapshot

    res = cruce_service.consolidado_por_meta(None, ano=2026, sec_func=129)
    p = res["presupuesto"]
    assert p["devengado_mef"] is None
    assert p["porcentaje_devengado"] is None
    assert p["saldo_disponible_mef"] is None


@patch("app.services.cruce_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.cruce_service.cruce_repo.consolidado_por_meta")
def test_meta_inexistente_devuelve_none(m_repo, m_mef):
    m_repo.return_value = None  # meta fuera de alcance o inexistente

    res = cruce_service.consolidado_por_meta(None, ano=2026, sec_func=99999)
    assert res is None
    m_mef.assert_not_called()  # no consulta MEF si la meta no existe


@patch("app.services.cruce_service.ejecucion_mef_repo.ejecucion_por_meta")
@patch("app.services.cruce_service.cruce_repo.consolidado_por_meta")
def test_pide_mef_solo_de_esa_meta(m_repo, m_mef):
    m_repo.return_value = _consolidado_base()
    m_mef.return_value = {}
    cruce_service.consolidado_por_meta(None, ano=2026, sec_func=129)
    assert m_mef.call_args.kwargs["sec_funcs"] == [129]
