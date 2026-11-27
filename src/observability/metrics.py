# src/observability/metrics.py
import json, sys, collections

PASOS_LLM = {"clasificador", "extractor", "redactor"}

# Precios por millón de tokens en USD. Completar con los precios vigentes del modelo
# en la página de precios de Groq. Mientras sean None, el costo no se calcula.
PRECIO_ENTRADA_USD_M = None
PRECIO_SALIDA_USD_M = None


def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def es_prueba(e):
    """Excluye las llamadas de la prueba de compatibilidad (PRUEBA-*)."""
    return e["caso_id"].startswith("PRUEBA")


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
                if e.get("paso") in PASOS_LLM and "latencia_ms" in e and not es_prueba(e)]
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


def costo_estimado(tokens_in, tokens_out, precio_in, precio_out):
    """Costo en USD. Devuelve None si no se han definido los precios."""
    if precio_in is None or precio_out is None:
        return None
    return round(tokens_in / 1e6 * precio_in + tokens_out / 1e6 * precio_out, 6)


def uso_tokens(eventos):
    """Tokens y costo estimado. Cada ejecución se identifica por su caso_id (p. ej. N-01-r1)."""
    llamadas = [e for e in eventos
                if e.get("paso") in PASOS_LLM and "tokens_in" in e and not es_prueba(e)]
    ejecuciones = {e["caso_id"] for e in llamadas}
    n = len(ejecuciones)
    tin = sum(e["tokens_in"] for e in llamadas)
    tout = sum(e["tokens_out"] for e in llamadas)

    acum = collections.defaultdict(lambda: {"in": 0, "out": 0, "llamadas": 0})
    for e in llamadas:
        a = acum[e["paso"]]
        a["in"] += e["tokens_in"]
        a["out"] += e["tokens_out"]
        a["llamadas"] += 1

    return {
        "ejecuciones_con_llamadas": n,
        "tokens_in_total": tin,
        "tokens_out_total": tout,
        "tokens_in_por_ejecucion": round(tin / n, 1) if n else None,
        "tokens_out_por_ejecucion": round(tout / n, 1) if n else None,
        "costo_total_usd": costo_estimado(tin, tout, PRECIO_ENTRADA_USD_M, PRECIO_SALIDA_USD_M),
        "costo_por_ejecucion_usd": (costo_estimado(tin, tout, PRECIO_ENTRADA_USD_M, PRECIO_SALIDA_USD_M) / n
                                    if n and PRECIO_ENTRADA_USD_M is not None else None),
        "por_paso": {p: {"tokens_in_prom": round(a["in"] / a["llamadas"], 1),
                         "tokens_out_prom": round(a["out"] / a["llamadas"], 1),
                         "llamadas": a["llamadas"]}
                     for p, a in acum.items()},
    }


def main():
    eventos = cargar(sys.argv[1])
    resultados = cargar(sys.argv[2])

    print("== Latencia y errores por paso ==")
    for paso, m in metricas_llamadas(eventos).items():
        print(paso, m)

    print("\n== Consistencia entre repeticiones ==")
    print(consistencia(resultados))

    print("\n== Uso de recursos ==")
    u = uso_tokens(eventos)
    for k, v in u.items():
        if k != "por_paso":
            print(f"{k}: {v}")
    if u["costo_total_usd"] is None:
        print("costo: no calculado (completar PRECIO_ENTRADA_USD_M y PRECIO_SALIDA_USD_M)")
    print("por paso:")
    for paso, v in u["por_paso"].items():
        print(f"  {paso}: {v}")


if __name__ == "__main__":
    main()