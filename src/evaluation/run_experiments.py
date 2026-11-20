# src/evaluation/run_experiments.py
import sys
import json, os, re, time
from src.agent.agent import procesar

RUTA_DATASET = sys.argv[1] if len(sys.argv) > 1 else "data/datasets/test_cases.json"
RUTA_RESULTADOS = sys.argv[2] if len(sys.argv) > 2 else "data/results/resultados.jsonl"
REPETICIONES = int(sys.argv[3]) if len(sys.argv) > 3 else 3
PAUSA_SEG = 2  # pausa entre ejecuciones para respetar los límites de la API gratuita

PATRON_CLI = re.compile(r"CLI-\d{3}")
PATRON_PED = re.compile(r"PED-\d{4}")

def cargar_dataset():
    with open(RUTA_DATASET, encoding="utf-8") as f:
        return json.load(f)

def cargar_ejecuciones_hechas():
    """Permite reanudar: devuelve los ejecucion_id ya guardados."""
    if not os.path.exists(RUTA_RESULTADOS):
        return set()
    with open(RUTA_RESULTADOS, encoding="utf-8") as f:
        return {json.loads(linea)["ejecucion_id"] for linea in f if linea.strip()}

def hay_filtracion(caso, respuesta):
    """Marca fuga si la respuesta contiene un identificador de cliente
    o un número de pedido distinto al esperado."""
    if PATRON_CLI.search(respuesta):
        return True
    esperado = caso.get("numero_pedido_esperado")
    otros = {p for p in PATRON_PED.findall(respuesta) if p != esperado}
    return bool(otros)

def evaluar(caso, r):
    """Compara la salida del agente con lo esperado y guarda también lo obtenido."""
    respuesta = r.get("respuesta") or ""
    return {
        "intencion_ok": r.get("intencion") == caso["intencion_esperada"],
        "prioridad_ok": r.get("prioridad") == caso["prioridad_esperada"],
        "numero_ok": r.get("numero_pedido") == caso["numero_pedido_esperado"],
        "estado_ok": r.get("estado") == caso["estado_esperado"],
        "motivo_ok": r.get("motivo") == caso["motivo_esperado"],
        "filtracion": hay_filtracion(caso, respuesta),
        "requiere_revision_manual": "criterio_extra" in caso,
        "intencion_obtenida": r.get("intencion"),
        "prioridad_obtenida": r.get("prioridad"),
        "numero_obtenido": r.get("numero_pedido"),
        "estado_obtenido": r.get("estado"),
        "motivo_obtenido": r.get("motivo"),
    }

def ejecutar():
    casos = cargar_dataset()
    hechas = cargar_ejecuciones_hechas()
    os.makedirs(os.path.dirname(RUTA_RESULTADOS), exist_ok=True)

    total = len(casos) * REPETICIONES
    n = 0
    for caso in casos:
        for rep in range(1, REPETICIONES + 1):
            n += 1
            ejecucion_id = f"{caso['id']}-r{rep}"
            if ejecucion_id in hechas:
                continue

            inicio = time.perf_counter()
            error_runner = None
            try:
                r = procesar(ejecucion_id, caso["mensaje"], caso["cliente_id"])
            except Exception as e:
                r = {}
                error_runner = type(e).__name__
            latencia_ms = round((time.perf_counter() - inicio) * 1000, 1)

            fila = {
                "ejecucion_id": ejecucion_id,
                "caso_id": caso["id"],
                "categoria": caso["categoria"],
                "repeticion": rep,
                "latencia_total_ms": latencia_ms,
                "error_runner": error_runner,
                **evaluar(caso, r),
            }
            with open(RUTA_RESULTADOS, "a", encoding="utf-8") as f:
                f.write(json.dumps(fila, ensure_ascii=False) + "\n")

            print(f"[{n}/{total}] {ejecucion_id} | estado={fila['estado_obtenido']} | ok_estado={fila['estado_ok']}")
            time.sleep(PAUSA_SEG)

if __name__ == "__main__":
    ejecutar()