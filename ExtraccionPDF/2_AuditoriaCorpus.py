#!/usr/bin/env python3
"""
Auditoria del corpus: recorre TODAS las paginas de cada PDF y cuenta lo que
realmente hay dentro, no solo lo que dice la cabecera.

Responde tres preguntas por archivo:
  1. cuantos registros de postulante contiene
  2. trae rechazados (denominador) o solo la lista de ingresantes
  3. que columnas tiene, porque el esquema cambia entre años

Salida: data/auditoria.csv
"""
import csv, os, re, zlib

RAIZ = os.path.dirname(os.path.abspath(__file__))
COND = ("INGRESO", "NO INGRESO", "NSP", "NC")
# Cabeceras conocidas de la familia DEVEXP. El orden varia entre años.
COLUMNAS = ("Nombre", "Código", "Total", "Ord.", "Condición", "Nota 01", "Nota 02")


def tokens(raw):
    """Devuelve (lista de paginas, cada una lista de textos) para ambas familias."""
    cmap, paginas = {}, []
    for s in re.findall(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            d = zlib.decompress(s).decode("latin-1")
        except Exception:
            continue
        if "beginbfchar" in d:
            for blq in re.findall(r"beginbfchar(.*?)endbfchar", d, re.S):
                for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blq):
                    cmap[a.upper()] = chr(int(b[:4], 16))
        if "Tj" in d:
            paginas.append(d)

    def dec(h):
        h = h.upper()
        return "".join(cmap.get(h[i:i + 4], "") for i in range(0, len(h), 4))

    fuera = []
    for d in paginas:
        t = [dec(m.group(1)) for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*Tj", d)]
        t += [m.group(1) for m in re.finditer(r"\(((?:[^()\\]|\\.)*)\)\s*Tj", d)]
        fuera.append(t)
    return fuera, bool(cmap)


def auditar(ruta):
    raw = open(ruta, "rb").read()
    paginas, es_devexp = tokens(raw)
    plano = [t for p in paginas for t in p]

    cond = sorted({t for t in plano if t in COND})
    cols = sorted({t for t in plano if t in COLUMNAS})
    # un puntaje es un decimal con 2+ decimales; los enteros son ordenes de merito
    puntajes = [t for t in plano if re.fullmatch(r"\d{1,3}\.\d{2,}", t)]
    # documentos de identidad: 8 digitos
    codigos = [t for t in plano if re.fullmatch(r"\d{8}", t)]
    # notas minimas de corte, una por bloque de carrera
    cortes = sum(1 for t in plano if t.startswith("Nota M"))
    # nombres: cadena larga en mayusculas con al menos dos palabras
    nombres = [t for t in plano
               if re.fullmatch(r"[A-ZÑÁÉÍÓÚÜ]{2,}(?: [A-ZÑÁÉÍÓÚÜ.]{1,}){1,5}", t or "")]

    if not plano:
        util = "vacio_para_regex"
    elif "NO INGRESO" in cond:
        util = "con_denominador"
    elif "INGRESO" in cond:
        util = "solo_ingresantes"
    elif puntajes:
        util = "puntajes_sin_condicion"
    else:
        util = "sin_datos_tabulares"

    return dict(
        paginas_texto=len(paginas),
        familia="DEVEXP" if es_devexp else "MS-OFFICE",
        condiciones="|".join(cond),
        columnas="|".join(cols),
        n_puntajes=len(puntajes),
        n_codigos=len(codigos),
        n_nombres=len(nombres),
        n_cortes=cortes,
        utilidad=util,
    )


def inventario():
    """La fuente de verdad son los archivos en disco, no el manifiesto.

    El script 1 descubre por patron y el 6 rescata archivos sueltos, asi que
    ningun manifiesto por si solo describe todo el corpus. Recorrer data/raw
    garantiza que ninguna descarga quede fuera de la auditoria.
    """
    meta = {}
    ruta_man = os.path.join(RAIZ, "data", "manifest.csv")
    if os.path.exists(ruta_man):
        for m in csv.DictReader(open(ruta_man, encoding="utf-8")):
            if m["estado"] == "ok" and m["ruta"]:
                meta[os.path.basename(m["ruta"])] = m

    base = os.path.join(RAIZ, "data", "raw")
    fuera = []
    for ciclo in sorted(os.listdir(base)):
        carpeta = os.path.join(base, ciclo)
        if not os.path.isdir(carpeta):
            continue
        for archivo in sorted(os.listdir(carpeta)):
            if not archivo.lower().endswith(".pdf"):
                continue
            ruta = os.path.join(carpeta, archivo)
            m = meta.get(archivo, {})
            fuera.append(dict(
                archivo=m.get("archivo", archivo), ciclo=ciclo,
                tipo=m.get("tipo", ""), proceso=m.get("proceso", ""),
                fecha_examen=m.get("fecha_examen", ""), paginas=m.get("paginas", ""),
                ruta=os.path.relpath(ruta, RAIZ)))
    return fuera


def main():
    man = inventario()
    filas = []
    for i, m in enumerate(man, 1):
        ruta = os.path.join(RAIZ, m["ruta"])
        if not os.path.exists(ruta):
            continue
        try:
            a = auditar(ruta)
        except Exception as e:
            a = dict(paginas_texto=0, familia="ERROR", condiciones="", columnas="",
                     n_puntajes=0, n_codigos=0, n_nombres=0, n_cortes=0,
                     utilidad=f"error: {str(e)[:40]}")
        filas.append({**{k: m[k] for k in ("archivo", "ciclo", "tipo", "proceso",
                                           "fecha_examen", "paginas", "ruta")}, **a})
        if i % 40 == 0:
            print(f"   {i}/{len(man)}")

    campos = list(filas[0].keys())
    destino = os.path.join(RAIZ, "data", "auditoria.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)
    print(f"\nauditoria -> data/auditoria.csv  ({len(filas)} archivos)")
    return filas


if __name__ == "__main__":
    main()
