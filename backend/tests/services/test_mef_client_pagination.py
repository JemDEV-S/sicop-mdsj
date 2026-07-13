import pytest
from typing import Any
from unittest.mock import patch, MagicMock
from app.services.mef_client import MefClient

def test_paginar_json_corte_exacto():
    """
    Simula una paginacion realista:
    - Pagina 1: 100 registros (limit)
    - Pagina 2: 100 registros (limit)
    - Pagina 3: 13 registros (< limit)
    Verifica que el generador hace exactamente 3 llamadas, concatena todo y termina.
    """
    
    # Creamos un mock del metodo `datastore_search` para no tener que mockear HTTPX
    # y simular la capa de respuesta json limpia.
    mock_datastore_search = MagicMock()
    
    # Definimos lo que devuelve en cada iteracion
    mock_datastore_search.side_effect = [
        [{"id": i} for i in range(100)], # Pagina 1
        [{"id": i} for i in range(100, 200)], # Pagina 2
        [{"id": i} for i in range(200, 213)], # Pagina 3 (parcial, debe cortar)
        [{"id": i} for i in range(213, 300)] # Esto no debería llamarse!
    ]

    # Usamos patch on datastore_search over an instance of MefClient
    client = MefClient()
    client.datastore_search = mock_datastore_search
    
    # Para no retrasar el test, ponemos delay_seconds=0
    todas_las_filas = []
    
    # Consumimos el generador
    for bloque in client.paginar_json(
        resource_id="fake_uuid", 
        filters={"SEC_EJEC": "300687"}, 
        page_size=100,
        delay_seconds=0
    ):
        todas_las_filas.extend(bloque)
        
    # Verificaciones
    # 1. Se hicieron exactamente 3 llamadas (100, 100, 13)
    assert mock_datastore_search.call_count == 3
    
    # 2. Se obtuvieron las 213 filas exactamente
    assert len(todas_las_filas) == 213
    
    # 3. Validar parametros enviados a datastore_search en cada llamada
    # (offset va incrementando de a 100)
    llamadas = mock_datastore_search.call_args_list
    assert llamadas[0].kwargs["offset"] == 0
    assert llamadas[1].kwargs["offset"] == 100
    assert llamadas[2].kwargs["offset"] == 200

def test_paginar_json_corte_multiplo_exacto():
    """
    Simula una paginacion con un total de registros que es múltiplo exacto del limit:
    - Pagina 1: 100 registros (limit)
    - Pagina 2: 100 registros (limit)
    - Pagina 3: 0 registros (vacía)
    Verifica que el generador hace exactamente 3 llamadas, concatena todo y termina al recibir 0.
    """
    mock_datastore_search = MagicMock()
    
    mock_datastore_search.side_effect = [
        [{"id": i} for i in range(100)], # Pagina 1
        [{"id": i} for i in range(100, 200)], # Pagina 2
        [], # Pagina 3 (vacía, debe cortar por "not filas")
        [{"id": i} for i in range(200, 300)] # Esto no debería llamarse
    ]

    client = MefClient()
    client.datastore_search = mock_datastore_search
    
    todas_las_filas = []
    
    for bloque in client.paginar_json(
        resource_id="fake_uuid", 
        filters={"SEC_EJEC": "300687"}, 
        page_size=100,
        delay_seconds=0
    ):
        todas_las_filas.extend(bloque)
        
    assert mock_datastore_search.call_count == 3
    assert len(todas_las_filas) == 200
    
    llamadas = mock_datastore_search.call_args_list
    assert llamadas[0].kwargs["offset"] == 0
    assert llamadas[1].kwargs["offset"] == 100
    assert llamadas[2].kwargs["offset"] == 200
