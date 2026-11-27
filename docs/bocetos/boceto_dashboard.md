# Boceto de diseño: Dashboard de monitoreo del agente

**Herramienta:** Streamlit + Plotly · **Fuente de datos:** `resultados_v4_final.jsonl` y `eventos_v4_final.jsonl`
**Usuario objetivo:** docente evaluador que debe entender el desempeño del agente sin conocer el código.

> Nota para el informe: este boceto documenta el diseño final del panel. Se elaboró después de implementarlo para dejar explícita la jerarquía de la información. No debe presentarse como boceto previo a la implementación.

---

## 1. Principios de diseño

1. **Orden de lectura de arriba hacia abajo:** primero la calidad global, luego los errores, luego el desempeño y por último el detalle.
2. **Cada porcentaje muestra su origen:** numerador, denominador y unidad (ejecuciones, llamadas o casos).
3. **Separar lo que es calidad de lo que es fallo:** los errores tienen una sección propia para que no se confundan con los indicadores generales.
4. **Explicar antes de mostrar:** un bloque colapsable al inicio define cada término.
5. **Detalle opcional:** la tabla por ejecución está al final y se filtra, para no saturar la vista principal.

---

## 2. Estructura general

```
┌─────────────────────────────────────────────────────────────┐
│  TÍTULO · Corrida, casos, repeticiones, ejecuciones          │
│  [ Cómo leer este panel ▸ ]  (colapsable)                    │
├─────────────────────────────────────────────────────────────┤
│  1. CALIDAD DEL AGENTE                                       │
│  [Intención] [Estado] [Motivo] [Filtraciones]                │
│  ✔ Integridad de la corrida                                  │
├─────────────────────────────────────────────────────────────┤
│  2. ERRORES Y FALLOS A REVISAR                               │
│  2.1 Fallos técnicos   2.2 Fallos por categoría              │
│  2.3 Confusiones       2.4 Números no extraídos              │
│  2.5 Latencias atípicas                                      │
├─────────────────────────────────────────────────────────────┤
│  3. DESEMPEÑO POR PASO                                       │
│  [Tabla: llamadas · errores · % error · p50 · p95 · máx]     │
│  [Gráfico: mediana y p95 por paso]                           │
├─────────────────────────────────────────────────────────────┤
│  4. RESULTADOS POR CATEGORÍA                                 │
│  [Tabla: aciertos/total por intención, estado y motivo]      │
│  [Gráfico: % intención correcta por categoría]               │
├─────────────────────────────────────────────────────────────┤
│  5. DETALLE POR EJECUCIÓN                                    │
│  [Filtro categoría ▾] [☐ solo fallos]                        │
│  [Tabla filtrable]                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Descripción por sección

### Encabezado
- **Contenido:** título, versión de la corrida, número de casos, repeticiones y ejecuciones totales.
- **Motivo:** permite identificar a qué corrida corresponde el panel sin revisar los archivos.
- **Elemento colapsable:** glosario de términos (ejecución, intención, estado, motivo, filtración, p50, p95).

### 1. Calidad del agente
- **Cuatro indicadores en fila**, cada uno con porcentaje y fracción debajo (por ejemplo, "131 de 144 ejecuciones").
- **Intención, estado y motivo:** son las tres métricas que el docente compara contra el dataset.
- **Filtraciones:** se muestra como "144/144 sin filtración" para que el cero no se lea como dato faltante.
- **Barra de integridad:** verde si hay cero errores del runner y cero filtraciones; roja en caso contrario.
- **Pie de sección:** aclara que la verificación de filtraciones es automática y que dos casos se revisaron a mano.

### 2. Errores y fallos a revisar
- **Propósito:** concentrar todo lo que no salió bien, separado por tipo, para que el docente vea de un vistazo dónde está el problema.
- **2.1 Fallos técnicos:** tabla con paso, tipo de error y cantidad. Corresponde a fallas de la API o de formato.
- **2.2 Fallos por categoría:** total de la categoría, cantidad con fallo y lista de ejecuciones afectadas.
- **2.3 Confusiones de intención:** tabla "esperada → obtenida" con frecuencia. Es la lectura más útil para identificar sesgos del clasificador.
- **2.4 Números no extraídos:** indicador simple con la lista de casos.
- **2.5 Latencias atípicas:** solo aparecen las llamadas que superan el umbral. Incluye un aviso que aclara que no representan el comportamiento típico.

### 3. Desempeño por paso
- **Tabla:** llamadas, errores, tasa de error, mediana, p95 y máximo por paso (clasificador, extractor, redactor).
- **Gráfico:** barras agrupadas de mediana y p95. Se eligió barras y no líneas porque cada paso es una categoría, no una serie temporal.
- **Caption explicativo:** define qué mide la mediana y qué mide el p95.

### 4. Resultados por categoría
- **Tabla con formato "aciertos/total (porcentaje)"** por intención, estado y motivo. Se eligió este formato para que el número absoluto siempre sea visible.
- **Gráfico:** porcentaje de intención correcta por categoría, con eje fijo de 0 a 100 para que las categorías sean comparables.
- **Propósito:** identificar en qué tipo de mensaje falla el agente (por ejemplo, tipeo o reclamos largos).

### 5. Detalle por ejecución
- **Filtros:** selector múltiple de categorías y casilla para mostrar solo fallos.
- **Columnas:** ejecución, categoría, intención esperada y obtenida, estado esperado y obtenido, motivo y latencia.
- **Pie de tabla:** muestra cuántas ejecuciones se están viendo sobre el total.

---

## 4. Decisiones de visualización

| Decisión | Motivo |
|---|---|
| Indicadores con fracción debajo del porcentaje | El docente puede verificar el cálculo sin consultar otros archivos |
| Errores en sección propia | Evita que los fallos se confundan con las métricas de calidad |
| Escala fija de 0 a 100 en gráficos de porcentaje | Permite comparar categorías sin que la escala engañe |
| Glosario colapsable | Explica los términos sin ocupar espacio cuando no se necesita |
| Tablas con `hide_index` y encabezados en español | Lectura directa para un evaluador no técnico |
| Títulos de sección con separador | Facilita la navegación en la captura del informe |

---

## 5. Flujo de uso esperado

1. El docente lee el encabezado y el glosario para ubicar la corrida.
2. Revisa la sección 1 para conocer la calidad general.
3. Si algún indicador le parece bajo, pasa a la sección 2 para ver la causa.
4. Usa la sección 3 para evaluar el costo de latencia de cada paso.
5. Usa la sección 4 para comparar categorías.
6. Llega al detalle (sección 5) solo si quiere verificar una ejecución concreta.

---

## 6. Limitaciones del diseño

- El panel muestra una sola corrida; no compara versiones dentro de la misma interfaz. La comparación se documenta en `docs/pruebas/comparacion_v3_v4.txt`.
- La validación de 14 casos no tiene panel propio. Se reporta en el informe.
- El costo en USD no aparece hasta completar los precios en `metrics.py`.
