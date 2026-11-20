# src/analysis/log_analysis.py
"""Análisis de registros de ejecución (IE3, IE6).
Uso: python -m src.analysis.log_analysis [eventos.jsonl] [resultados.jsonl] [casos.json]
"""
import json, sys, collections

UMBRAL_LATENCIA_ATIPICA_MS = 10000
TIPO_DETECCION = "posible_numero_no_extraido"
RUTA_EVENTOS = "data/logs/eventos_v4_final.jsonl"
RUTA_RESULTADOS = "data/results/resultados_v4_final.jsonl"
RUTA_CASOS = "data/datasets/test_cases.json"


def cargar_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def es_prueba(e):
    """Excluye las llamadas de la prueba de compatibilidad (PRUEBA-*)."""
    return e["caso_id"].startswith("PRUEBA")


def fallos_por_categoria(resultados):
    fallos = collections.defaultdict(list)
    for r in resultados:
        if not (r["intencion_ok"] and r["estado_ok"] and r["motivo_ok"]):
            fallos[r["categoria"]].append(r["ejecucion_id"])
    return fallos


def confusion_intencion(resultados, casos):
    c = collections.Counter()
    for r in resultados:
        if not r["intencion_ok"]:
            c[(casos[r["caso_id"]]["intencion_esperada"], r["intencion_obtenida"])] += 1
    return c


def errores_tecnicos(eventos):
    """Fallas de API o de formato. No incluye las detecciones de número (no son fallas)."""
    c = collections.Counter()
    for e in eventos:
        if (e.get("ok") is False and e["paso"] != "caso" and not es_prueba(e)
                and e.get("error") != TIPO_DETECCION):
            c[(e["paso"], e.get("error"))] += 1
    return c


def detecciones_numero(eventos):
    return [e["caso_id"] for e in eventos
            if e.get("error") == TIPO_DETECCION and not es_prueba(e)]


def latencias_atipicas(eventos):
    return sorted(
        [(e["paso"], e["caso_id"], e["latencia_ms"]) for e in eventos
         if "latencia_ms" in e and e["latencia_ms"] > UMBRAL_LATENCIA_ATIPICA_MS
         and not es_prueba(e)],
        key=lambda x: -x[2])


def integridad(resultados):
    return {"error_runner": sum(1 for r in resultados if r["error_runner"]),
            "filtraciones": sum(r["filtracion"] for r in resultados),
            "ejecuciones": len(resultados)}


def main():
    args = sys.argv[1:] + [RUTA_EVENTOS, RUTA_RESULTADOS, RUTA_CASOS][len(sys.argv[1:]):]
    eventos, resultados = cargar_jsonl(args[0]), cargar_jsonl(args[1])
    with open(args[2], encoding="utf-8") as f:
        casos = {c["id"]: c for c in json.load(f)}

    print("== Integridad de la corrida ==")
    print(integridad(resultados))

    print("\n== Fallos por categoría (ejecuciones con alguna métrica incorrecta) ==")
    for cat, ids in sorted(fallos_por_categoria(resultados).items()):
        print(f"{cat}: {len(ids)} -> {', '.join(ids)}")

    print("\n== Confusión de intención (esperada -> obtenida: veces) ==")
    for (esp, obt), n in confusion_intencion(resultados, casos).most_common():
        print(f"{esp} -> {obt}: {n}")

    print("\n== Errores técnicos por paso (excluye PRUEBA-*) ==")
    for (paso, error), n in errores_tecnicos(eventos).most_common():
        print(f"{paso} | {error}: {n}")

    print("\n== Posibles números no extraídos (detector regex) ==")
    ids = detecciones_numero(eventos)
    print(f"{len(ids)} -> {', '.join(ids) if ids else 'ninguna'}")

    print(f"\n== Latencias atípicas (> {UMBRAL_LATENCIA_ATIPICA_MS} ms) ==")
    atipicas = latencias_atipicas(eventos)
    if not atipicas:
        print("ninguna")
    for paso, caso_id, lat in atipicas:
        print(f"{paso} | {caso_id} | {lat} ms")


if __name__ == "__main__":
    main()