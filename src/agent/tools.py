import json
from src.agent.config import RUTA_PEDIDOS

def _cargar_pedidos():
    with open(RUTA_PEDIDOS, encoding="utf-8") as f:
        return json.load(f)

def consultar_pedido(numero_pedido, cliente_id):
    """Devuelve (pedido, motivo). Si hay motivo, pedido es None.
    Motivos: sin_numero_pedido, pedido_no_encontrado, pedido_no_autorizado."""
    if not numero_pedido:
        return None, "sin_numero_pedido"
    pedido = _cargar_pedidos().get(numero_pedido)
    if pedido is None:
        return None, "pedido_no_encontrado"
    if pedido["cliente"] != cliente_id:
        return None, "pedido_no_autorizado"
    # Se quita el campo cliente para que nunca llegue al redactor
    return {k: v for k, v in pedido.items() if k != "cliente"}, None