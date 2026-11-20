# src/analysis/comparar_versiones.py
import json, collections
import sys

def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

def resumen(rows):
    acum = collections.defaultdict(lambda: {"n": 0, "estado": 0, "motivo": 0, "intencion": 0})
    for r in rows:
        a = acum[r["categoria"]]
        a["n"] += 1
        a["estado"] += bool(r["estado_ok"])
        a["motivo"] += bool(r["motivo_ok"])
        a["intencion"] += bool(r["intencion_ok"])
    return acum

def celda(a, b, clave):
    return f"{a[clave]}/{a['n']} -> {b[clave]}/{b['n']}"

def main():
    v_antes = resumen(cargar(sys.argv[1]))
    v_despues = resumen(cargar(sys.argv[2]))
    vacio = {"n": 0, "estado": 0, "motivo": 0, "intencion": 0}
    print(f"{'categoria':<15}{'estado':<22}{'motivo':<22}{'intencion'}")
    for cat in sorted(set(v_antes) | set(v_despues)):
        a, b = v_antes.get(cat, vacio), v_despues.get(cat, vacio)
        print(f"{cat:<15}{celda(a, b, 'estado'):<22}{celda(a, b, 'motivo'):<22}{celda(a, b, 'intencion')}")

if __name__ == "__main__":
    main()