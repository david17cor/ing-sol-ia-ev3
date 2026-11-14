# src/observability/logger.py
import json, os, time

RUTA_LOG = "data/logs/eventos.jsonl"

def registrar(evento: dict):
    os.makedirs(os.path.dirname(RUTA_LOG), exist_ok=True)
    evento["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(RUTA_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")