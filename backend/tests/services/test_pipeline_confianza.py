"""Cascada de confianza del match pedido <-> CCMN.

SIGA no registra que CCMN corresponde a que pedido (logistica copia los datos
y no los vincula). Cuando la bolsa agrupa varios pedidos hay N candidatos, y
tomar cualquiera como "el del pedido" pinta avance ajeno.

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §4
"""

from app.schemas.pipeline import (
    ETAPA_CUADRO_ADQUISICION,
    ETAPA_CUADRO_NECESIDAD,
)
from app.services.pipeline_service import (
    _etapa_maxima,
    confianza_match,
    estado_etapa_programacion,
)


def _fila(**kw):
    """Fila del repo con los flags de programacion en 1 (avance observado)."""
    base = {
        "TIPO_BIEN": "S",
        "estado_pedido": "1",
        "tiene_cuadro_neces": 1,
        "tiene_puente_paac": 1,
        "tiene_ccmn": 1,
        "tiene_cotizacion": 1,
        "tiene_cuadro_adq": 1,
        "n_candidatos_ccmn": 1,
    }
    base.update(kw)
    return base


# ─── Niveles de la cascada ───────────────────────────────────────────────


def test_sin_candidatos_es_sin_ccmn():
    assert confianza_match(_fila(n_candidatos_ccmn=0)) == "sin_ccmn"


def test_un_candidato_es_unico():
    assert confianza_match(_fila(n_candidatos_ccmn=1)) == "unico"


def test_varios_candidatos_sin_declaracion_es_ambiguo():
    assert confianza_match(_fila(n_candidatos_ccmn=3)) == "ambiguo"


def test_declaracion_de_orden_dentro_de_candidatos_resuelve():
    fila = _fila(
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
        ccmn_declarado_orden=2266,
    )
    assert confianza_match(fila) == "declarado"


def test_declaracion_de_certificacion_resuelve():
    fila = _fila(
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
        ccmn_declarado_cert=2281,
    )
    assert confianza_match(fila) == "declarado_cert"


def test_orden_tiene_prioridad_sobre_certificacion():
    """La orden es posterior en el proceso y estuvo bajo mas escrutinio."""
    fila = _fila(
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
        ccmn_declarado_orden=2266,
        ccmn_declarado_cert=2281,
    )
    assert confianza_match(fila) == "declarado"


def test_declaracion_fuera_de_candidatos_es_conflicto():
    """Un typo no se acepta en silencio: se marca visible (19 casos en 2026)."""
    fila = _fila(
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
        ccmn_declarado_orden=9999,
    )
    assert confianza_match(fila) == "conflicto"


def test_manual_gana_sobre_la_cascada_automatica():
    """Referencial pero explicito: si el funcionario lo declaro, manda."""
    fila = _fila(n_candidatos_ccmn=3, ccmn_manual=2266)
    assert confianza_match(fila) == "resuelto_manual"


# ─── El bug corregido: avance del grupo no cuenta como propio ────────────


def test_ambiguo_no_marca_etapas_de_programacion():
    """El MAX(CASE...) del repo respondia '¿algun candidato llego?'.

    Los otros candidatos son de OTROS pedidos de la misma bolsa, asi que el
    pedido se mostraba en cuadro_adquisicion por avance ajeno.
    """
    fila = _fila(n_candidatos_ccmn=3)
    assert estado_etapa_programacion(fila) == "grupo"
    assert _etapa_maxima(fila) == ETAPA_CUADRO_NECESIDAD


def test_unico_si_marca_etapas_de_programacion():
    fila = _fila(n_candidatos_ccmn=1)
    assert estado_etapa_programacion(fila) == "directo"
    assert _etapa_maxima(fila) == ETAPA_CUADRO_ADQUISICION


def test_declarado_marca_etapas_via_ccmn():
    fila = _fila(
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
        ccmn_declarado_orden=2266,
    )
    assert estado_etapa_programacion(fila) == "via_ccmn"
    assert _etapa_maxima(fila) == ETAPA_CUADRO_ADQUISICION


def test_conflicto_no_marca_etapas():
    """Un conflicto no resuelve: se comporta como ambiguo, no como declarado."""
    fila = _fila(
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
        ccmn_declarado_orden=9999,
    )
    assert estado_etapa_programacion(fila) == "grupo"
    assert _etapa_maxima(fila) == ETAPA_CUADRO_NECESIDAD


# ─── Testigo 232/S · regresion obligatoria (doc §10) ─────────────────────


def test_testigo_232S():
    """Pedido 232/S: bolsa 11553 compartida con los pedidos 278 y 1005.

    3 candidatos (2266, 2281, 3532); la respuesta correcta es 2266, confirmada
    por dos fuentes independientes: el texto de la orden 132 y VALOR_PLAN=4800.
    """
    sin_declaracion = _fila(
        TIPO_BIEN="S",
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
    )
    assert confianza_match(sin_declaracion) == "ambiguo"

    con_orden = dict(sin_declaracion, ccmn_declarado_orden=2266)
    assert confianza_match(con_orden) == "declarado"
    assert estado_etapa_programacion(con_orden) == "via_ccmn"
