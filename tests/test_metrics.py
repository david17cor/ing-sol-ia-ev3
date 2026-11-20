# tests/test_metrics.py
from src.observability.metrics import percentil, consistencia

def test_percentil_mediana():
    assert percentil([1, 2, 3], 50) == 2

def test_percentil_lista_vacia():
    assert percentil([], 50) is None

def test_consistencia_detecta_cambio_de_intencion():
    rows = [
        {"caso_id": "A", "intencion_obtenida": "envio", "estado_obtenido": "resuelto"},
        {"caso_id": "A", "intencion_obtenida": "pedido", "estado_obtenido": "resuelto"},
    ]
    r = consistencia(rows)
    assert r["consistencia_intencion_%"] == 0.0
    assert r["consistencia_estado_%"] == 100.0