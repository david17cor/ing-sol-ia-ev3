from src.observability.privacy import enmascarar

def test_enmascara_rut():
    assert "[RUT]" in enmascarar("Mi RUT es 12.345.678-5")

def test_enmascara_correo():
    assert "[EMAIL]" in enmascarar("escribe a ana@correo.cl por favor")

def test_no_toca_texto_sin_datos():
    assert enmascarar("pedido PED-1001") == "pedido PED-1001"

def test_acepta_none():
    assert enmascarar(None) is None