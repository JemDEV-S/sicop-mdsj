"""Tests de la clasificacion v2 (Guia Pipeline v2 §02).

Pura logica sobre dicts, sin BD: verifica que la etapa se calcula por FECHA
cierta, que el avance de la bolsa se muestra aunque el puente no resuelva, y
que las alertas son honestas (rojo solo estancado_real). El caso guia 232/S es
el smoke test de aceptacion (§03.5).
"""

from __future__ import annotations

from datetime import date

from app.services import pipeline_v2
from app.schemas.pipeline import (
    ETAPA_CIERRE,
    ETAPA_CUADRO_NECESIDAD,
    ETAPA_DESPACHO_PECOSA,
    ETAPA_DEVENGADO,
    ETAPA_ORDEN_EMITIDA,
    ETAPA_PEDIDO_APROBADO,
    ETAPA_PEDIDO_REGISTRADO,
)

HOY = date(2026, 7, 31)


def _fila(**kw):
    """Fila base tipo vista materializada; se sobreescriben campos por test."""
    base = {
        "ano_eje": 2026, "sec_ejec": 300687, "nro_pedido": 1, "tipo_bien": "S",
        "tipo_pedido": "2", "estado": "1", "centro_costo": "01",
        "fecha_pedido": date(2026, 2, 5), "fecha_aprob": date(2026, 2, 5),
        "tiene_cuadro_neces": 1, "n_candidatos_ccmn": 1,
        "ccmn_candidatos_csv": "100", "bolsa_n_ordenes": 0,
    }
    base.update(kw)
    return base


# ─── Etapa por fecha cierta ──────────────────────────────────────────────


def test_pedido_registrado_sin_avance():
    f = _fila(estado="0", tiene_cuadro_neces=0, fecha_aprob=None,
              n_candidatos_ccmn=0, ccmn_candidatos_csv=None)
    etapa, fecha = pipeline_v2.clasificar_etapa(f, "sin_ccmn")
    assert etapa == ETAPA_PEDIDO_REGISTRADO
    assert fecha == date(2026, 2, 5)


def test_aprobado_sin_cuadro():
    f = _fila(tiene_cuadro_neces=0, n_candidatos_ccmn=0, ccmn_candidatos_csv=None)
    etapa, _ = pipeline_v2.clasificar_etapa(f, "sin_ccmn")
    assert etapa == ETAPA_PEDIDO_APROBADO


def test_puente_no_resuelto_no_hereda_avance_bolsa():
    """Con puente ambiguo, la etapa NO pasa de cuadro de necesidad aunque la
    bolsa tenga orden: el avance es del grupo, no atribuible (§02.1)."""
    f = _fila(
        n_candidatos_ccmn=3, ccmn_candidatos_csv="100,200,300",
        bolsa_n_ordenes=2, bolsa_fecha_orden=date(2026, 3, 1),
        bolsa_fecha_ejecucion=date(2026, 3, 10),
    )
    etapa, _ = pipeline_v2.clasificar_etapa(f, "ambiguo")
    assert etapa == ETAPA_CUADRO_NECESIDAD


def test_puente_resuelto_hereda_avance_bolsa():
    f = _fila(
        bolsa_n_ordenes=1, bolsa_fecha_orden=date(2026, 3, 1),
        bolsa_fecha_ejecucion=date(2026, 3, 10),
        bolsa_fecha_devengado=date(2026, 3, 12),
    )
    etapa, fecha = pipeline_v2.clasificar_etapa(f, "unico")
    assert etapa == ETAPA_DEVENGADO
    assert fecha == date(2026, 3, 12)


def test_bienes_pecosa_es_etapa_propia():
    """La pecosa (bienes) es llave dura del pedido, no depende del puente."""
    f = _fila(tipo_bien="B", n_candidatos_ccmn=3, ccmn_candidatos_csv="1,2,3",
              tiene_pecosa=1, fecha_pecosa=date(2026, 4, 1))
    etapa, fecha = pipeline_v2.clasificar_etapa(f, "ambiguo")
    assert etapa == ETAPA_DESPACHO_PECOSA
    assert fecha == date(2026, 4, 1)


def test_cierre_estado_7():
    f = _fila(estado="7", fecha_atenc=date(2026, 5, 1))
    etapa, fecha = pipeline_v2.clasificar_etapa(f, "unico")
    assert etapa == ETAPA_CIERRE
    assert fecha == date(2026, 5, 1)


# ─── Avance de la bolsa (cierto aunque el puente no resuelva) ─────────────


def test_avance_bolsa_lista_ordenes():
    f = _fila(bolsa_n_ordenes=3, bolsa_ordenes_csv="132,155,802",
              bolsa_fecha_orden=date(2026, 2, 16),
              bolsa_fecha_devengado=date(2026, 2, 20))
    ab = pipeline_v2.avance_bolsa(f)
    assert ab["n_ordenes"] == 3
    assert [o["nro_orden"] for o in ab["ordenes"]] == [132, 155, 802]
    assert ab["max_etapa"] == ETAPA_DEVENGADO


# ─── Alertas honestas ────────────────────────────────────────────────────


def test_puente_pendiente_no_es_estancado():
    """Caso 232/S: bolsa con avance, puente sin resolver -> puente_pendiente
    (ambar), NUNCA estancado (rojo)."""
    f = _fila(
        n_candidatos_ccmn=3, ccmn_candidatos_csv="2266,2281,3532",
        bolsa_n_ordenes=3, bolsa_ordenes_csv="132,155,802",
        bolsa_fecha_orden=date(2026, 2, 16),
        bolsa_fecha_ejecucion=date(2026, 2, 20),
    )
    etapa, fecha = pipeline_v2.clasificar_etapa(f, "ambiguo")
    alerta = pipeline_v2.calcular_alerta(f, etapa, fecha, "ambiguo", HOY, 15)
    assert alerta is not None
    assert alerta["tipo"] == "puente_pendiente"
    assert alerta["severidad"] == "ambar"


def test_estancado_real_solo_sin_avance_bolsa():
    """Estancado real: etapa vieja, sin avance de bolsa. Rojo."""
    f = _fila(
        n_candidatos_ccmn=0, ccmn_candidatos_csv=None, tiene_cuadro_neces=0,
        bolsa_n_ordenes=0, fecha_aprob=date(2026, 1, 1),
    )
    etapa, fecha = pipeline_v2.clasificar_etapa(f, "sin_ccmn")
    alerta = pipeline_v2.calcular_alerta(f, etapa, fecha, "sin_ccmn", HOY, 15)
    assert alerta is not None
    assert alerta["tipo"] in ("estancado_real", "sin_consolidar")
    # Con avance de bolsa, el mismo pedido NO estancaria.
    f2 = dict(f, bolsa_n_ordenes=1, n_candidatos_ccmn=2,
              ccmn_candidatos_csv="1,2", bolsa_fecha_orden=date(2026, 3, 1))
    a2 = pipeline_v2.calcular_alerta(f2, ETAPA_CUADRO_NECESIDAD,
                                     date(2026, 1, 1), "ambiguo", HOY, 15)
    assert a2 is None or a2["tipo"] != "estancado_real"


def test_cierre_nunca_alerta():
    f = _fila(estado="7", fecha_atenc=date(2026, 1, 1))
    alerta = pipeline_v2.calcular_alerta(f, ETAPA_CIERRE, date(2026, 1, 1),
                                         "unico", HOY, 15)
    assert alerta is None


def test_conflicto_puente():
    f = _fila(n_candidatos_ccmn=2, ccmn_candidatos_csv="1,2")
    alerta = pipeline_v2.calcular_alerta(f, ETAPA_CUADRO_NECESIDAD,
                                         date(2026, 5, 1), "conflicto", HOY, 15)
    assert alerta is not None
    assert alerta["tipo"] == "conflicto_puente"


def test_desfase_devengado():
    f = _fila(
        bolsa_n_ordenes=1, bolsa_fecha_orden=date(2026, 2, 1),
        bolsa_fecha_compromiso=date(2026, 2, 1), devengado_mef=0,
    )
    alerta = pipeline_v2.calcular_alerta(f, ETAPA_ORDEN_EMITIDA,
                                         date(2026, 2, 1), "unico", HOY, 30)
    assert alerta is not None
    assert alerta["tipo"] == "desfase_devengado"


# ─── Identificadores (§00 principio 2) ───────────────────────────────────


def test_identificadores_orden_solo_si_puente_resuelto():
    f = _fila(tipo_bien="S", nro_pedido=232, bolsa_ordenes_csv="132,155,802")
    ids_res = pipeline_v2.identificadores(f, "unico")
    assert ids_res["pedido"] == "232-2026/S"
    assert ids_res["orden"] == "O/S 132"
    ids_amb = pipeline_v2.identificadores(f, "ambiguo")
    assert ids_amb["orden"] is None  # sin resolver, no se atribuye la orden
