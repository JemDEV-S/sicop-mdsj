"""Cascada de confianza del match pedido <-> CCMN.

SIGA no registra que CCMN corresponde a que pedido (logistica copia los datos
y no los vincula). Cuando la bolsa agrupa varios pedidos hay N candidatos, y
tomar cualquiera como "el del pedido" pinta avance ajeno.

Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §4
"""

from datetime import datetime

from app.services.pipeline_service import confianza_match


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


def test_sin_candidatos_pero_orden_declara_es_declarado():
    """Caso 69/S: la bolsa no tiene fila en SIG_CUADRO_MODIFICADO_CMN (0
    candidatos), pero la orden nombra el pedido en sus especificaciones y su
    cadena apunta a un CCMN. La declaracion de la orden es un hecho de SIGA:
    resuelve a `declarado` en vez de decir "sin CCMN"."""
    fila = _fila(n_candidatos_ccmn=0, ccmn_declarado_orden=2094)
    assert confianza_match(fila) == "declarado"


def test_sin_candidatos_con_declaracion_de_certificacion():
    fila = _fila(n_candidatos_ccmn=0, ccmn_declarado_cert=2094)
    assert confianza_match(fila) == "declarado_cert"


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


# ─── Estados del timeline del detalle (punto 6) ──────────────────────────


def _ficha(**kw):
    """Ficha del detalle (obtener_pedido) con avance de programacion.

    Las etapas 4-7 se declaran ahora por flags de la cadena del CCMN
    (`_flags_programacion`), no por las listas `cuadros`/`certificaciones`
    (que solo existen tras la orden). Ver el fix del caso 311/S.
    """
    base = {
        "TIPO_BIEN": "S",
        "estado_pedido": "1",
        "FECHA_PEDIDO": datetime(2026, 2, 5),
        "items": [{"SEC_CUA_MOD_SAL": 11553}],
        "cuadros": [{"FECHA_CUADRO": None}],
        "certificaciones": [{"FECHA": None}],
        "ordenes": [],
        "expedientes": [],
        "conformidades": [],
        "movimientos_almacen": [],
        "n_candidatos_ccmn": 1,
        # Avance de programacion: llego hasta el cuadro de adquisicion (7).
        "tiene_puente_paac": 1,
        "tiene_ccmn": 1,
        "tiene_cotizacion": 1,
        "tiene_cuadro_adq": 1,
    }
    base.update(kw)
    return base


def _por_etapa(ficha):
    from app.services.pipeline_service import construir_timeline
    return {h["etapa_numero"]: h for h in construir_timeline(ficha)}


def test_timeline_marca_grupo_en_etapas_4_a_7_si_es_ambiguo():
    """El caso que motivo la refactorizacion: avance de OTRO pedido de la
    bolsa se pintaba como un verde indistinguible del real (§7)."""
    hitos = _por_etapa(_ficha(n_candidatos_ccmn=3))
    for n in (4, 5, 6, 7):
        assert hitos[n]["estado"] == "grupo", n
        # No cuenta como alcanzada: un avance ajeno no es de este pedido.
        assert hitos[n]["alcanzada"] is False, n


def test_timeline_marca_directo_en_etapas_de_evidencia_propia():
    """Las etapas 1-3 y 8 no pasan por el CCMN: son dato duro del pedido."""
    hitos = _por_etapa(_ficha(n_candidatos_ccmn=3))
    assert hitos[1]["estado"] == "directo"
    assert hitos[3]["estado"] == "directo"
    assert hitos[8]["estado"] == "directo"  # certificacion, tabla propia


def test_timeline_marca_via_ccmn_cuando_una_fuente_declara():
    hitos = _por_etapa(_ficha(
        n_candidatos_ccmn=3,
        ccmn_candidatos=(2266, 2281, 3532),
        ccmn_declarado_orden=2266,
    ))
    for n in (4, 5, 6, 7):
        assert hitos[n]["estado"] == "via_ccmn", n
        assert hitos[n]["alcanzada"] is True, n


def test_timeline_marca_manual_con_resolucion_del_funcionario():
    hitos = _por_etapa(_ficha(n_candidatos_ccmn=3, ccmn_manual=2266))
    assert hitos[4]["estado"] == "manual"
    assert hitos[4]["alcanzada"] is True


def test_timeline_candidato_unico_es_directo():
    hitos = _por_etapa(_ficha(n_candidatos_ccmn=1))
    for n in (4, 5, 6, 7):
        assert hitos[n]["estado"] == "directo", n


def test_timeline_sin_avance_es_sin_dato():
    """Una etapa no alcanzada nunca hereda el estado de la cascada."""
    hitos = _por_etapa(_ficha(
        n_candidatos_ccmn=3, cuadros=[], certificaciones=[],
        tiene_puente_paac=0, tiene_ccmn=0,
        tiene_cotizacion=0, tiene_cuadro_adq=0,
    ))
    for n in (4, 5, 6, 7):
        assert hitos[n]["estado"] == "sin_dato", n


def test_timeline_detenido_en_estudio_de_mercado():
    """Caso 311/S: el pedido llego al estudio de mercado y a cotizacion, pero
    no tiene cuadro de adquisicion ni orden. Antes se cortaba en "cuadro de
    necesidades" porque el detalle solo miraba la cadena hacia abajo desde la
    orden. Ahora las etapas 4-6 se alcanzan y la 7 no."""
    hitos = _por_etapa(_ficha(
        n_candidatos_ccmn=1,
        tiene_puente_paac=1, tiene_ccmn=1, tiene_cotizacion=1,
        tiene_cuadro_adq=0,          # no llego al cuadro de adquisicion
        cuadros=[], certificaciones=[], ordenes=[],  # ni orden ni cert
        nro_est_mdo=352,
    ))
    for n in (4, 5, 6):
        assert hitos[n]["alcanzada"] is True, n
    assert hitos[7]["estado"] == "sin_dato"      # cuadro de adquisicion: no
    assert hitos[8]["estado"] == "sin_dato"      # certificacion: no
    # El numero del estudio de mercado se muestra como identificador de la 5.
    docs = {d["etiqueta"]: d["valor"] for d in hitos[5]["documentos"]}
    assert docs.get("Estudio de mercado") == "352"
