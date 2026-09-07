#!/usr/bin/env python3
"""
Extrae el cuadro oficial de vacantes por carrera y modalidad de ingreso.

Este documento es el denominador que falta en las listas de resultados: dice
cuantas plazas se reservan a cada via de ingreso antes de que empiece el
proceso. Con el se puede calcular ocupacion de plazas y comparar la oferta
declarada contra los ingresantes reales.

Columnas del cuadro:
  CENTRO PREUNIVERSITARIO (CEPRE I-II-III) | EXAMENES ORDINARIOS |
  TRASLADO INTERNO | CONCURSO EXTRAORDINARIO | VACANTES PRONABEC | TOTAL

Salida: data/vacantes.csv
"""
import csv, os, re, zlib

RAIZ = os.path.dirname(os.path.abspath(__file__))
COLS = ["cepre", "ordinarios", "traslado_interno", "extraordinario", "pronabec", "total"]


def paginas_texto(ruta):
    """Este PDF usa arrays TJ con kerning, no Tj sueltos."""
    raw = open(ruta, "rb").read()
    fuera = []
    for s in re.findall(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            d = zlib.decompress(s).decode("latin-1")
        except Exception:
            continue
        if not re.search(r"\bT[jJ]\b", d):
            continue
        toks = []
        for m in re.finditer(r"\[(.*?)\]\s*TJ", d, re.S):
            s2 = "".join(re.findall(r"\(((?:[^()\\]|\\.)*)\)", m.group(1)))
            if s2.strip():
                toks.append(s2.strip())
        for m in re.finditer(r"\(((?:[^()\\]|\\.)*)\)\s*Tj", d):
            if m.group(1).strip():
                toks.append(m.group(1).strip())
        if toks:
            fuera.append(toks)
    return fuera


def es_numero(t):
    return bool(re.fullmatch(r"\d{1,4}", t))


def es_carrera(t):
    """Los nombres de carrera vienen en Capitalizado, no en MAYUSCULAS."""
    if len(t) < 5 or es_numero(t):
        return False
    if t.upper() == t:          # encabezados y titulos van en mayusculas
        return False
    return bool(re.match(r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]", t))


def extraer(ruta):
    filas, seccion = [], ""
    for toks in paginas_texto(ruta):
        texto_pag = " ".join(toks).upper()
        if "DISTANCIA" in texto_pag or "SEMIPRESENCIAL" in texto_pag:
            seccion = "distancia"
        elif "PRESENCIAL" in texto_pag:
            seccion = "presencial"
        i = 0
        nombre_parcial = ""
        while i < len(toks):
            t = toks[i]
            if es_carrera(t):
                # los nombres largos se parten en dos tokens
                nombre = (nombre_parcial + " " + t).strip() if nombre_parcial else t
                nums = []
                j = i + 1
                while j < len(toks) and len(nums) < 6:
                    if es_numero(toks[j]):
                        nums.append(int(toks[j]))
                        j += 1
                    elif es_carrera(toks[j]):
                        break
                    else:
                        j += 1
                if len(nums) == 6 and nums[5] == sum(nums[:5]):
                    filas.append(dict(zip(["carrera"] + COLS, [nombre] + nums),
                                      seccion=seccion))
                    nombre_parcial = ""
                    i = j
                    continue
                nombre_parcial = nombre if t.endswith(("y", "de", "en")) or len(t) > 28 else ""
            i += 1
    return filas


def main():
    ruta = os.path.join(RAIZ, "data", "contexto", "vacantes_2027.pdf")
    filas = extraer(ruta)
    destino = os.path.join(RAIZ, "data", "vacantes.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["carrera", "seccion"] + COLS)
        w.writeheader()
        w.writerows(filas)
    print(f"vacantes -> data/vacantes.csv  ({len(filas)} carreras)")
    if filas:
        tot = {c: sum(r[c] for r in filas) for c in COLS}
        print("  total de vacantes 2027 por modalidad:")
        for c in COLS:
            print(f"    {c:<18}{tot[c]:>6}")
    return filas


if __name__ == "__main__":
    main()
