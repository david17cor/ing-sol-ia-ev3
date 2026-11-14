# src/agent/llm.py
import time
from groq import Groq
from src.observability.logger import registrar
from src.observability.privacy import enmascarar

client = Groq()  # lee GROQ_API_KEY del entorno
MODELO = "openai/gpt-oss-120b"  # verificar disponibilidad en console.groq.com

def llamar(paso, caso_id, mensajes, temperatura=0):
    inicio = time.perf_counter()
    evento = {"paso": paso, "caso_id": caso_id}
    try:
        resp = client.chat.completions.create(
            model=MODELO, messages=mensajes, temperature=temperatura)
        texto = resp.choices[0].message.content
        evento.update(ok=True, tokens_in=resp.usage.prompt_tokens,
                      tokens_out=resp.usage.completion_tokens,
                      salida_cruda=enmascarar(texto))
        return texto
    except Exception as e:
        evento.update(ok=False, error=type(e).__name__)
        return None
    finally:
        evento["latencia_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
        registrar(evento)