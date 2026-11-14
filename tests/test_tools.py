from src.agent.tools import consultar_pedido

def test_pedido_propio_resuelve_y_oculta_cliente():
    pedido, motivo = consultar_pedido("PED-1001", "CLI-001")
    assert motivo is None
    assert "cliente" not in pedido

def test_pedido_ajeno_no_autorizado():
    pedido, motivo = consultar_pedido("PED-1002", "CLI-001")
    assert pedido is None
    assert motivo == "pedido_no_autorizado"

def test_pedido_inexistente():
    pedido, motivo = consultar_pedido("PED-1010", "CLI-001")
    assert pedido is None
    assert motivo == "pedido_no_encontrado"

def test_sin_numero():
    pedido, motivo = consultar_pedido(None, "CLI-001")
    assert motivo == "sin_numero_pedido"