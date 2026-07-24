"""Parseo de las fuentes declarativas pedido <-> CCMN (doc §3.3).

SIGA no vincula pedido y CCMN (§1). Lo unico que queda es el texto libre de
la orden y de la certificacion, donde el usuario escribe de que pedido viene.
Estos tests fijan los formatos reales observados en 2026 para que un cambio
del regex no degrade la cobertura en silencio.
"""

from app.repositories.pipeline_repo import (
    _agrupar_declaraciones,
    _elegir_declarado,
    parsear_nro_pedido,
)


# ─── Formatos reales observados (§3.3) ───────────────────────────────────


def test_formatos_reales_de_2026():
    casos = {
        "PEDIDO 76": 76,
        "PEDIDO 0225": 225,
        "PEDIDO DE COMPRA N°000026-2026": 26,
        "PEDIDO DE SERVICIO N°228-2026 ACTUALIZADO": 228,
        "PEDIOD 0041": None,  # typo real: no parsea, y esta bien
        "SEGUN PEDIDO DE SERVICIO N° 00232, CVR N°00263, CCMN N° 022": 232,
    }
    for texto, esperado in casos.items():
        assert parsear_nro_pedido(texto) == esperado, texto


def test_no_inventa_cuando_el_texto_no_nombra_un_pedido():
    """Un informe no es un pedido. Preferible no parsear que parsear mal."""
    assert parsear_nro_pedido("INFORME 275-2026-MDSJ") is None
    assert parsear_nro_pedido("") is None
    assert parsear_nro_pedido(None) is None


def test_segun_contrato_se_descarta():
    """`SEGUN CONTRATO` no declara pedido aunque el texto siga con numeros."""
    assert parsear_nro_pedido("SEGUN CONTRATO N° 0012 - PEDIDO 45") is None


# ─── Eleccion del declarado contra los candidatos de la bolsa ────────────


def test_declarado_dentro_de_candidatos():
    decl = {("S", 232): {2266}}
    assert _elegir_declarado(decl, "S", 232, frozenset({2266, 2281, 3532})) == 2266


def test_declarado_fuera_de_candidatos_se_devuelve_para_marcar_conflicto():
    """No se silencia: la cascada lo convierte en `conflicto` (19 casos reales)."""
    decl = {("S", 458): {2688}}
    assert _elegir_declarado(decl, "S", 458, frozenset({2817})) == 2688


def test_varios_declarados_dentro_de_candidatos_no_desambigua():
    """Elegir uno seria el 'ganador por parecido' que la cascada evita (§2)."""
    decl = {("S", 232): {2266, 2281}}
    assert _elegir_declarado(decl, "S", 232, frozenset({2266, 2281, 3532})) is None


def test_prefiere_el_candidato_cuando_hay_ruido_fuera_de_la_bolsa():
    decl = {("S", 232): {2266, 9999}}
    assert _elegir_declarado(decl, "S", 232, frozenset({2266, 2281})) == 2266


def test_sin_declaracion_devuelve_none():
    assert _elegir_declarado({}, "S", 232, frozenset({2266})) is None


# ─── Agrupacion desde filas crudas ───────────────────────────────────────


def test_agrupar_separa_por_tipo_bien():
    """El numero de pedido se repite entre B y S: agrupar sin TIPO_BIEN
    mezclaria declaraciones de pedidos distintos (§6, 446 colisiones)."""
    filas = [
        {"TIPO_BIEN": "S", "ccmn": 2266, "texto": "PEDIDO 232"},
        {"TIPO_BIEN": "B", "ccmn": 5000, "texto": "PEDIDO 232"},
    ]
    out = _agrupar_declaraciones(filas)
    assert out[("S", 232)] == {2266}
    assert out[("B", 232)] == {5000}


def test_agrupar_ignora_filas_sin_pedido_o_sin_ccmn():
    filas = [
        {"TIPO_BIEN": "S", "ccmn": None, "texto": "PEDIDO 232"},
        {"TIPO_BIEN": "S", "ccmn": 2266, "texto": "INFORME 275-2026"},
    ]
    assert _agrupar_declaraciones(filas) == {}


# ─── VALOR_TOTAL en 0: la trampa que inflaba el match composite ──────────


def test_sql_usa_fallback_de_monto_en_el_composite():
    """`VALOR_TOTAL` viene en 0.00 en el 100% de los servicios y el 55% de los
    bienes (medido en 2026). El composite tiene un escape `valor_soles = 0` que
    acepta CUALQUIER monto: con el valor en 0 un pedido matchea las ordenes de
    los otros pedidos de su bolsa.

    Verificado contra BD: con el fallback, los 3 pedidos de la bolsa 11553
    matchean una orden cada uno (232->132, 278->155, 1005->802) en vez de las
    tres cada uno. El testigo 232/S->OC 132 es la respuesta del doc §10.

    Este test fija el fallback en el SQL para que no se revierta por descuido.
    """
    from app.repositories.pipeline_repo import _SQL_KANBAN

    assert "CANT_SOLICITADA" in _SQL_KANBAN and "PRECIO_UNIT" in _SQL_KANBAN, (
        "el CTE `det` debe calcular el monto como CANT_SOLICITADA * PRECIO_UNIT "
        "cuando VALOR_TOTAL es 0"
    )
