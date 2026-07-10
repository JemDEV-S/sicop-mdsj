"""Tests unitarios de la construcción de rutas ltree.

No requieren PostgreSQL ni SIGA — puro Python.
"""

from app.jobs.ltree_builder import construir_rutas


def test_una_sola_raiz_con_dos_hijos():
    centros = [
        {"codigo": "01", "centro_padre": None},
        {"codigo": "01.01", "centro_padre": "01"},
        {"codigo": "01.02", "centro_padre": "01"},
    ]
    rutas = construir_rutas(centros)
    assert rutas["01"] == ("root.01", 1)
    assert rutas["01.01"] == ("root.01.01_01", 2)
    assert rutas["01.02"] == ("root.01.01_02", 2)


def test_arbol_tres_niveles():
    centros = [
        {"codigo": "01", "centro_padre": None},
        {"codigo": "01.01", "centro_padre": "01"},
        {"codigo": "01.01.02", "centro_padre": "01.01"},
    ]
    rutas = construir_rutas(centros)
    assert rutas["01.01.02"] == ("root.01.01_01.01_01_02", 3)


def test_padre_huerfano_se_trata_como_raiz():
    # El nodo B apunta a un padre "Z" que no existe en el input.
    centros = [
        {"codigo": "A", "centro_padre": None},
        {"codigo": "B", "centro_padre": "Z"},
    ]
    rutas = construir_rutas(centros)
    assert rutas["A"] == ("root.A", 1)
    # B queda como raíz porque su padre no está en el dataset
    assert rutas["B"] == ("root.B", 1)


def test_todos_los_nodos_reciben_ruta_no_null():
    centros = [
        {"codigo": "01", "centro_padre": None},
        {"codigo": "01.01", "centro_padre": "01"},
        {"codigo": "01.01.02", "centro_padre": "01.01"},
        {"codigo": "01.02", "centro_padre": "01"},
    ]
    rutas = construir_rutas(centros)
    for c in centros:
        assert c["codigo"] in rutas
        assert rutas[c["codigo"]][0].startswith("root.")
        assert rutas[c["codigo"]][1] >= 1
