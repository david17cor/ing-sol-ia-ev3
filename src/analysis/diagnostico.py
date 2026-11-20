# src/analysis/diagnostico.py
import json, collections

casos = {c["id"]: c for c in json.load(open("data/datasets/test_cases.json", encoding="utf-8"))}
rows = [json.loads(l) for l in open("data/results/resultados.jsonl", encoding="utf-8")]

print("=== Confusión de intención (esperada -> obtenida: veces) ===")
conf = collections.Counter(
    (casos[r["caso_id"]]["intencion_esperada"], r["intencion_obtenida"])
    for r in rows if not r["intencion_ok"])
for (esp, obt), n in conf.most_common():
    print(f"{esp} -> {obt}: {n}")

print("\n=== Ejecuciones con estado o motivo incorrecto ===")
for r in rows:
    if not r["estado_ok"] or not r["motivo_ok"]:
        print(r["ejecucion_id"], "| estado:", r["estado_obtenido"],
              "| motivo:", r["motivo_obtenido"],
              "| intencion:", r["intencion_obtenida"],
              "| numero:", r["numero_obtenido"])