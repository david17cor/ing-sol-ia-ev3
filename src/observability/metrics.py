# src/observability/metrics.py
import json, sys, collections

PASOS_LLM = {"clasificador", "extractor", "redactor"}

def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

def percentil(valores, p):
    if not valores:
        return None
    s = sorted(valores)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return round(s[f] + (s[c] - s[f]) * (k - f), 1)

def metricas_llamadas(eventos):
    """Latencia y tasa de error por paso. Solo cuenta llamadas reales a la API."""
    llamadas = [e for e in eventos
                if e.get("paso") in PASOS_LLM and "latencia_ms" in e
                and not e["caso_id"].startswith("PRUEBA")]
    por_paso = collections.defaultdict(list)
    for e in llamadas:
        por_paso[e["paso"]].append(e)
    salida = {}
    for paso, evs in por_paso.items():
        lat = [e["latencia_ms"] for e in evs]
        errores = sum(1 for e in evs if not e["ok"])
        salida[paso] = {"llamadas": len(evs), "errores": errores,
                        "tasa_error_%": round(100 * errores / len(evs), 1),
                        "p50_ms": percentil(lat, 50), "p95_ms": percentil(lat, 95),
                        "max_ms": max(lat)}
    return salida

def consistencia(resultados):
    """Porcentaje de casos cuyas repeticiones dan la misma intención y el mismo estado."""
    por_caso = collections.defaultdict(list)
    for r in resultados:
        por_caso[r["caso_id"]].append(r)
    n = len(por_caso)
    intencion = sum(1 for rs in por_caso.values()
                    if len({r["intencion_obtenida"] for r in rs}) == 1)
    estado = sum(1 for rs in por_caso.values()
                 if len({r["estado_obtenido"] for r in rs}) == 1)
    return {"casos": n,
            "consistencia_intencion_%": round(100 * intencion / n, 1),
            "consistencia_estado_%": round(100 * estado / n, 1)}

def main():
    eventos = cargar(sys.argv[1])
    resultados = cargar(sys.argv[2])
    print("== Latencia y errores por paso ==")
    for paso, m in metricas_llamadas(eventos).items():
        print(paso, m)
    print("\n== Consistencia entre repeticiones ==")
    print(consistencia(resultados))

if __name__ == "__main__":
    main()