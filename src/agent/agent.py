# src/agent/agent.py
import json, re
from src.agent.llm import llamar
from src.agent.tools import consultar_pedido
from src.agent.config import CATEGORIAS, PRIORIDADES
from src.observability.logger import registrar


RESPUESTA_SIN_NUMERO = "Para ayudarte necesito el número de tu pedido (formato PED-XXXX)."
RESPUESTA_NO_ENCONTRADO = ("No encontramos un pedido asociado a tu cuenta con ese número. "
                           "Revisa el número o escríbenos para ayudarte.")
PATRON_NUMERO_FLEXIBLE = re.compile(r"(?i)(?:ped|pedido)\D{0,3}(\d{4})")
PATRON_NUMERO_POSIBLE = re.compile(r"\d{4}")
ERRORES_TECNICOS = {"clasificacion_fallida", "redaccion_fallida"}


def extraer_pedido_flexible(mensaje):
    """Respaldo determinista: solo se usa si el extractor LLM devuelve null."""
    m = PATRON_NUMERO_FLEXIBLE.search(mensaje)
    return f"PED-{m.group(1)}" if m else None


def parsear_json(texto, paso, caso_id):
    """Convierte la respuesta del modelo en dict. Si falla, lo registra y devuelve None."""
    if texto is None:
        return None
    limpio = re.sub(r"```(?:json)?|```", "", texto).strip()
    try:
        datos = json.loads(limpio)
    except json.JSONDecodeError:
        registrar({"paso": paso, "caso_id": caso_id, "ok": False, "error": "json_invalido"})
        return None
    if not isinstance(datos, dict):
        registrar({"paso": paso, "caso_id": caso_id, "ok": False, "error": "json_no_es_objeto"})
        return None
    return datos


def clasificar(caso_id, mensaje):
    prompt = [
        {"role": "system", "content":
         "Eres el clasificador de atención al cliente de una tienda online. "
         "Asigna una intención y una prioridad al mensaje del cliente.\n\n"
         "Intenciones:\n"
         "- envio: pregunta dónde está el pedido o cuándo llega, sin expresar queja.\n"
         "- pedido: pregunta general sobre la compra (confirmación, producto, cantidad).\n"
         "- devolucion: pide devolver o cambiar un producto.\n"
         "- reclamo: expresa insatisfacción o un problema (retraso con queja, daño, pérdida).\n"
         "- otro: no corresponde a ninguna de las anteriores.\n\n"
         "Reglas de desempate, en orden:\n"
         "1. Si pide devolver o cambiar, es devolucion, aunque mencione un retraso.\n"
         "2. Si hay una queja explícita, es reclamo, aunque también pregunte por la ubicación.\n"
         "3. Si solo pregunta por ubicación o fecha, es envio.\n"
         "4. Si es una consulta sobre la compra sin queja ni acción, es pedido.\n\n"
         "Prioridades:\n"
         "- alta: daño, pérdida, cobro indebido o pide hablar con una persona.\n"
         "- media: retraso o devolución.\n"
         "- baja: consultas informativas.\n\n"
         f"Valores válidos: intencion en {CATEGORIAS}, prioridad en {PRIORIDADES}.\n"
         "Responde SOLO con JSON: {\"intencion\": \"...\", \"prioridad\": \"...\"}"},
        {"role": "user", "content": mensaje},
    ]
    datos = parsear_json(llamar("clasificador", caso_id, prompt, json_mode=True), "clasificador", caso_id)
    if not datos or datos.get("intencion") not in CATEGORIAS or datos.get("prioridad") not in PRIORIDADES:
        return None
    return datos

def extraer_pedido(caso_id, mensaje):
    prompt = [
        {"role": "system", "content":
         "Extrae el número de pedido del mensaje del cliente. Formato esperado: PED-XXXX. "
         "Responde SOLO con JSON: {\"numero_pedido\": \"PED-XXXX\" o null}"},
        {"role": "user", "content": mensaje},
    ]
    datos = parsear_json(llamar("extractor", caso_id, prompt, json_mode=True), "extractor", caso_id)
    return datos.get("numero_pedido") if datos else None


def redactar(caso_id, mensaje, intencion, pedido):
    prompt = [
        {"role": "system", "content":
         "Eres un agente de atención al cliente. Responde en español, cordial y breve, "
         "usando solo los datos del pedido entregados. No inventes información."},
        {"role": "user", "content":
         f"Intención: {intencion}\nMensaje: {mensaje}\nDatos del pedido: {json.dumps(pedido, ensure_ascii=False)}"},
    ]
    return llamar("redactor", caso_id, prompt, temperatura=0.3)


def procesar(caso_id, mensaje, cliente_id):
    """Ejecuta el flujo completo y devuelve el resultado del caso."""
    clasificacion = clasificar(caso_id, mensaje)
    if clasificacion is None:
        resultado = {"caso_id": caso_id, "estado": "escalado", "motivo": "clasificacion_fallida"}
    else:
        numero = extraer_pedido(caso_id, mensaje) or extraer_pedido_flexible(mensaje)
        pedido, motivo = consultar_pedido(numero, cliente_id)

        if motivo == "sin_numero_pedido":
            if PATRON_NUMERO_POSIBLE.search(mensaje):
                registrar({"paso": "extractor", "caso_id": caso_id, "ok": False,
                           "error": "posible_numero_no_extraido"})
            resultado = {"caso_id": caso_id, "estado": "pendiente_datos", "motivo": motivo,
                         **clasificacion, "numero_pedido": None, "respuesta": RESPUESTA_SIN_NUMERO}

        elif motivo:  # no encontrado o no autorizado: misma respuesta al cliente
            resultado = {"caso_id": caso_id, "estado": "escalado", "motivo": motivo,
                         **clasificacion, "numero_pedido": numero, "respuesta": RESPUESTA_NO_ENCONTRADO}

        else:
            respuesta = redactar(caso_id, mensaje, clasificacion["intencion"], pedido)
            resultado = {"caso_id": caso_id, "estado": "resuelto" if respuesta else "escalado",
                         "motivo": None if respuesta else "redaccion_fallida",
                         **clasificacion, "numero_pedido": numero, "respuesta": respuesta}

    registrar({"paso": "caso", "caso_id": caso_id,
               "ok": resultado.get("motivo") not in ERRORES_TECNICOS,
               "estado": resultado["estado"], "motivo": resultado.get("motivo")})
    return resultado
