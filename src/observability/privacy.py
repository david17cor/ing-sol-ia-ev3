# src/observability/privacy.py
import re

PATRONES = [
    (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"), "[RUT]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"\+?\d[\d\s-]{7,}\d"), "[TELEFONO]"),
]

def enmascarar(texto):
    if not texto:
        return texto
    for patron, reemplazo in PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto