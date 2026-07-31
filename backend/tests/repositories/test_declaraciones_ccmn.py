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


# ─── Cadena dura CCMN -> orden en el detalle (§07: el composite se retiro) ─
#
# El kanban dejo de usar el composite por monto: ahora clasifica desde el
# snapshot (siga.ordenes trae la orden por la cadena dura CCMN via
# certificacion_fase, 100% medida). El detalle (`obtener_pedido`) conserva la
# cadena dura con su gate `unico` para no traer ordenes ajenas en bolsas
# compartidas -- el fallo silencioso de §2/§7.


def test_detalle_orden_por_cadena_ccmn_solo_en_bolsa_de_un_ccmn():
    import inspect
    from app.repositories import pipeline_repo

    fuente_detalle = inspect.getsource(pipeline_repo.obtener_pedido)
    assert "cadena_ccmn" in fuente_detalle, (
        "obtener_pedido: debe traer la orden por la FK dura CCMN -> cuadro -> orden"
    )
    assert "HAVING COUNT(DISTINCT" in fuente_detalle, (
        "obtener_pedido: la cadena dura debe limitarse a bolsas de un solo CCMN "
        "(gate `unico`); sin ese HAVING traeria ordenes ajenas en bolsas "
        "compartidas -- el fallo silencioso de §2/§7"
    )
