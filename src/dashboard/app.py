# src/dashboard/app.py
import json, sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from src.observability.metrics import metricas_llamadas  # noqa: E402
from src.analysis.log_analysis import (  # noqa: E402
    UMBRAL_LATENCIA_ATIPICA_MS, confusion_intencion, detecciones_numero,
    errores_tecnicos, fallos_por_categoria, integridad, latencias_atipicas)

RUTA_RESULTADOS = RAIZ / "data/results/resultados_v4_final.jsonl"
RUTA_EVENTOS = RAIZ / "data/logs/eventos_v4_final.jsonl"
RUTA_CASOS = RAIZ / "data/datasets/test_cases.json"

ESTILO = """
<style>
h1 {font-size: 2.6rem !important; font-weight: 700;}
h2 {font-size: 2rem !important; border-bottom: 3px solid #2F80ED;
    padding-bottom: .3rem; margin-top: 2.5rem;}
h3 {font-size: 1.4rem !important; margin-top: 1.5rem;}
[data-testid="stMetricValue"] {font-size: 2.4rem;}
[data-testid="stMetricLabel"] p {font-size: 1.1rem; font-weight: 600;}
</style>
"""


@st.cache_data
def cargar_jsonl(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


@st.cache_data
def cargar_casos(ruta):
    with open(ruta, encoding="utf-8") as f:
        return {c["id"]: c for c in json.load(f)}


def pct(ok, total):
    return f"{ok / total:.1%}" if total else "—"


st.set_page_config(page_title="Observabilidad del agente", layout="wide")
st.markdown(ESTILO, unsafe_allow_html=True)

filas = cargar_jsonl(RUTA_RESULTADOS)
eventos = cargar_jsonl(RUTA_EVENTOS)
casos = cargar_casos(RUTA_CASOS)

df = pd.DataFrame(filas)
df["intencion_esperada"] = df["caso_id"].map(lambda c: casos[c]["intencion_esperada"])
df["estado_esperado"] = df["caso_id"].map(lambda c: casos[c]["estado_esperado"])
df["con_fallo"] = ~(df["intencion_ok"] & df["estado_ok"] & df["motivo_ok"])
N = len(df)

# ---------- Encabezado ----------
st.title("Monitoreo del agente de atención al cliente")
st.markdown(
    f"**Corrida:** versión 4 final · **Casos:** {df['caso_id'].nunique()} · "
    f"**Repeticiones por caso:** {df['repeticion'].max()} · **Ejecuciones totales:** {N}")

with st.expander("📖 Cómo leer este panel", expanded=False):
    st.markdown("""
- **Ejecución:** una vez que el agente procesa un mensaje de prueba. Cada caso se ejecuta 3 veces.
- **Intención correcta:** el agente identificó el tipo de consulta (envío, reclamo, devolución, etc.) igual que la etiqueta esperada.
- **Estado correcto:** el caso terminó como debía (`resuelto`, `pendiente_datos` o `escalado`).
- **Motivo correcto:** la razón del estado coincide con la esperada (por ejemplo, `pedido_no_autorizado`).
- **Filtración de datos:** respuesta que revela información de otro cliente o identificadores internos. Debe ser 0.
- **Mediana (p50):** la mitad de las llamadas tarda menos que este valor.
- **p95:** el 95% de las llamadas tarda menos que este valor. Mide la lentitud en los casos más lentos, sin contar los extremos.
""")

# ---------- 1. Calidad ----------
st.header("1. Calidad del agente")
st.caption("Cada porcentaje indica cuántas ejecuciones cumplieron el criterio, sobre el total de ejecuciones.")

ok_int = int(df["intencion_ok"].sum())
ok_est = int(df["estado_ok"].sum())
ok_mot = int(df["motivo_ok"].sum())
ok_fil = int((df["filtracion"] == False).sum())  # noqa: E712

c1, c2, c3, c4 = st.columns(4)
c1.metric("Intención correcta", pct(ok_int, N), f"{ok_int} de {N} ejecuciones",
          delta_color="off",
          help="Ejecuciones en que la intención asignada coincide con la etiqueta del dataset.")
c2.metric("Estado correcto", pct(ok_est, N), f"{ok_est} de {N} ejecuciones",
          delta_color="off",
          help="Ejecuciones que terminaron en el estado esperado: resuelto, pendiente_datos o escalado.")
c3.metric("Motivo correcto", pct(ok_mot, N), f"{ok_mot} de {N} ejecuciones",
          delta_color="off",
          help="Ejecuciones con el motivo de escalamiento o de pendiente esperado.")
c4.metric("Filtraciones de datos", f"{N - int(df['filtracion'].sum())}/{N} S/F",
          "Verificación automática", delta_color="off",
          help="Respuestas sin identificadores de otros clientes ni pedidos ajenos.")

it = integridad(filas)
if it["error_runner"] == 0 and it["filtraciones"] == 0:
    st.success(f"Integridad de la corrida: {it['ejecuciones']} ejecuciones completas, "
               f"0 errores del runner y 0 filtraciones.")
else:
    st.error(f"Integridad de la corrida: {it['error_runner']} errores del runner · "
             f"{it['filtraciones']} filtraciones. Revisar antes de interpretar los resultados.")
st.info("La verificación de filtraciones es automática. Las respuestas de los casos J-04 y V-13 "
        "se revisaron a mano y se documentan por separado en el informe.")

# ---------- 2. Errores ----------
st.header("2. Errores y fallos a revisar")
st.caption("Todo lo que no salió como se esperaba, agrupado por tipo. Es la base del análisis de registros.")

st.subheader("2.1 Fallos técnicos (API o formato de respuesta)")
et = errores_tecnicos(eventos)
if et:
    st.error(f"Se registraron {sum(et.values())} fallos técnicos.")
    st.dataframe(pd.DataFrame([{"Paso": p, "Tipo de error": e, "Veces": n}
                               for (p, e), n in et.items()]), hide_index=True)
else:
    st.success("No hubo fallos técnicos en la corrida.")

st.subheader("2.2 Ejecuciones con fallo, por categoría")
fc = fallos_por_categoria(filas)
total_cat = df["categoria"].value_counts()
if fc:
    st.warning(f"{sum(len(v) for v in fc.values())} ejecuciones con al menos una métrica incorrecta.")
    st.dataframe(pd.DataFrame([{
        "Categoría": cat,
        "Con fallo": len(ids),
        "Total de la categoría": int(total_cat[cat]),
        "Ejecuciones": ", ".join(ids),
    } for cat, ids in sorted(fc.items())]), hide_index=True)
else:
    st.success("Todas las ejecuciones cumplieron los criterios.")

st.subheader("2.3 Confusiones de intención")
st.caption("Se lee como: *esperada → obtenida*. Por ejemplo, `reclamo → envio` significa que el cliente "
           "se quejaba y el agente lo tomó como una consulta de envío.")
conf = confusion_intencion(filas, casos)
if conf:
    st.dataframe(pd.DataFrame([{
        "Intención esperada": esp,
        "Intención obtenida": obt if obt is not None else "sin clasificar",
        "Veces": n,
    } for (esp, obt), n in conf.most_common()]), hide_index=True)
else:
    st.success("No hubo confusiones de intención.")

st.subheader("2.4 Números de pedido no extraídos")
det = detecciones_numero(eventos)
st.metric("Casos con número sospechoso sin extraer", len(det),
          help="Mensajes con un número de 4 dígitos que el extractor no reconoció como pedido.")
if det:
    st.caption(f"Casos: {', '.join(det)}")

st.subheader(f"2.5 Latencias atípicas (mayores a {UMBRAL_LATENCIA_ATIPICA_MS // 1000} segundos)")
la = latencias_atipicas(eventos)
if la:
    st.warning("Estas llamadas tardaron mucho más que el resto. Se documentan como hallazgo; "
               "no representan el comportamiento típico del agente.")
    st.dataframe(pd.DataFrame([{"Paso": p, "Caso": c, "Latencia (ms)": lat}
                               for p, c, lat in la]), hide_index=True)
else:
    st.success("No hubo latencias atípicas.")

# ---------- 3. Rendimiento ----------
st.header("3. Desempeño por paso del pipeline")
st.caption("Tiempo de respuesta de cada llamada al modelo. La mediana (p50) describe el caso típico; "
           "el p95 describe los casos lentos sin contar los extremos.")

lat = pd.DataFrame(metricas_llamadas(eventos)).T.reset_index().rename(columns={"index": "paso"})
st.dataframe(lat.rename(columns={
    "paso": "Paso", "llamadas": "Llamadas", "errores": "Errores", "tasa_error_%": "% error",
    "p50_ms": "Mediana (ms)", "p95_ms": "p95 (ms)", "max_ms": "Máximo (ms)"}), hide_index=True)

graf = lat.melt(id_vars="paso", value_vars=["p50_ms", "p95_ms"],
                var_name="Medida", value_name="Milisegundos")
graf["Medida"] = graf["Medida"].map({"p50_ms": "Mediana", "p95_ms": "p95"})
fig_lat = px.bar(graf, x="paso", y="Milisegundos", color="Medida", barmode="group",
                 text_auto=".0f", title="Mediana y p95 de latencia por paso (ms)")
st.plotly_chart(fig_lat)

# ---------- 4. Por categoría ----------
st.header("4. Resultados por categoría de caso")
st.caption("Cada celda muestra aciertos sobre total y el porcentaje correspondiente. "
           "Permite identificar en qué tipo de mensaje falla el agente.")

agg = df.groupby("categoria").agg(
    ejecuciones=("ejecucion_id", "size"),
    intencion=("intencion_ok", "sum"),
    estado=("estado_ok", "sum"),
    motivo=("motivo_ok", "sum"),
).reset_index()

tabla_cat = pd.DataFrame({"Categoría": agg["categoria"], "Ejecuciones": agg["ejecuciones"]})
for col, nombre in [("intencion", "Intención"), ("estado", "Estado"), ("motivo", "Motivo")]:
    tabla_cat[nombre] = [f"{int(o)}/{int(n)} ({o / n:.0%})"
                         for o, n in zip(agg[col], agg["ejecuciones"])]
st.dataframe(tabla_cat, hide_index=True)

agg["% intención correcta"] = agg["intencion"] / agg["ejecuciones"] * 100
fig_cat = px.bar(agg, x="categoria", y="% intención correcta", text_auto=".0f",
                 range_y=[0, 100], title="% de intención correcta por categoría")
st.plotly_chart(fig_cat)

# ---------- 5. Detalle ----------
st.header("5. Detalle por ejecución")
st.caption("Use los filtros para revisar ejecuciones concretas.")

col_a, col_b = st.columns([3, 1])
categorias = sorted(df["categoria"].unique())
elegidas = col_a.multiselect("Filtrar por categoría", categorias, default=categorias)
solo_fallos = col_b.checkbox("Solo ejecuciones con fallo", value=False)

vista = df[df["categoria"].isin(elegidas)]
if solo_fallos:
    vista = vista[vista["con_fallo"]]
vista = vista.assign(intencion_obtenida=vista["intencion_obtenida"].fillna("sin clasificar"))

st.dataframe(vista[[
    "ejecucion_id", "categoria", "intencion_esperada", "intencion_obtenida",
    "estado_esperado", "estado_obtenido", "motivo_obtenido", "latencia_total_ms",
]].rename(columns={
    "ejecucion_id": "Ejecución", "categoria": "Categoría",
    "intencion_esperada": "Intención esperada", "intencion_obtenida": "Intención obtenida",
    "estado_esperado": "Estado esperado", "estado_obtenido": "Estado obtenido",
    "motivo_obtenido": "Motivo obtenido", "latencia_total_ms": "Latencia total (ms)",
}), hide_index=True)
st.caption(f"Mostrando {len(vista)} de {N} ejecuciones.")