import pytest
from unittest.mock import MagicMock
from app.services import semaforo_service

class _MockRow:
    def __init__(self, modulo, metrica, verde, amarillo, direccion):
        self.modulo = modulo
        self.metrica = metrica
        self.umbral_verde = verde
        self.umbral_amarillo = amarillo
        self.direccion = direccion

def _mock_db_with_umbrales(umbrales):
    db = MagicMock()
    # Mocking db.execute(...).all()
    execute_result = MagicMock()
    execute_result.all.return_value = umbrales
    db.execute.return_value = execute_result
    return db

def test_semaforo_portal_obras_resolves_correctly():
    # Simulate the row present in the database:
    # "portal_obras", "avance_fisico", verde > 80, amarillo > 50, direccion = "mayor"
    db = _mock_db_with_umbrales([
        _MockRow("portal_obras", "avance_fisico", 80.0, 50.0, "mayor")
    ])
    
    # We must clear cache because the module caches thresholds
    semaforo_service._CACHE.clear()
    
    # Assert colors based on the mocked threshold
    color_verde = semaforo_service.color(db, modulo="portal_obras", metrica="avance_fisico", valor=85.0)
    assert color_verde == "verde"
    
    color_amarillo = semaforo_service.color(db, modulo="portal_obras", metrica="avance_fisico", valor=65.0)
    assert color_amarillo == "amarillo"
    
    color_rojo = semaforo_service.color(db, modulo="portal_obras", metrica="avance_fisico", valor=20.0)
    assert color_rojo == "rojo"

def test_semaforo_portal_obras_fallback_desconocido():
    db = _mock_db_with_umbrales([
        _MockRow("portal_obras", "avance_fisico", 80.0, 50.0, "mayor")
    ])
    semaforo_service._CACHE.clear()
    
    # Bad module ("obras") -> return "desconocido" instead of crashing
    color_bad_module = semaforo_service.color(db, modulo="obras", metrica="avance_fisico", valor=60.0)
    assert color_bad_module == "desconocido"
    
    # Missing value -> return "desconocido"
    color_none = semaforo_service.color(db, modulo="portal_obras", metrica="avance_fisico", valor=None)
    assert color_none == "desconocido"

