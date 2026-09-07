#!/usr/bin/env python3
"""
Extrae el catalogo de carreras que aparece en cada ciclo de admision.

La oferta no es fija: aparecen carreras nuevas y otras dejan de convocarse.
Para una serie temporal por carrera hay que saber en que ciclos existio cada
una, si no se confunde "no habia vacantes" con "nadie postulo".

En la familia DEVEXP el nombre de la carrera es el token que va entre el
encabezado 'Nombre' y el encabezado 'Total' de cada bloque.

Salida: data/carreras_por_ciclo.csv
"""
import csv, os, re, unicodedata, zlib, collections

RAIZ = os.path.dirname(os.path.abspath(__file__))
NO_CARRERA = {
    "PRIMERA POSTULACION", "SEGUNDA POSTULACION", "INGRESO", "NO INGRESO",
    "Dirección de Admisión", "Universidad Católica de Santa María",
}


def normalizar(s):
    """Clave estable para unir la misma carrera escrita distinto entre años."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9 ]", " ", s.upper())
    s = re.sub(r"\s+", " ", s).strip()
    # variantes conocidas
    s = s.replace("INGENIERIA DE SISTEMAS Y ", "INGENIERIA DE SISTEMAS ")
    return s


def carreras_de(ruta):
    raw = open(ruta, "rb").read()
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
    if not cmap:
        return []  # familia Office: la lee pdfplumber, no este extractor

    def dec(h):
        h = h.upper()
        return "".join(cmap.get(h[i:i + 4], "") for i in range(0, len(h), 4))

    fuera = []
    for d in paginas:
        t = [dec(m.group(1)) for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*Tj", d)]
        for i, x in enumerate(t):
            # el bloque de cabecera es: 'Nombre', <CARRERA>, 'Total'
            if x == "Total" and i >= 1 and t[i - 1] not in NO_CARRERA:
                cand = t[i - 1].strip()
                if len(cand) >= 5 and cand.upper() == cand and not re.search(r"\d", cand):
                    fuera.append(cand)
    return fuera


def main():
    man = list(csv.DictReader(open(os.path.join(RAIZ, "data", "manifest.csv"), encoding="utf-8")))
    por_ciclo = collections.defaultdict(collections.Counter)
    etiqueta = {}
    for m in man:
        if m["estado"] != "ok" or not m["ruta"]:
            continue
        ruta = os.path.join(RAIZ, m["ruta"])
        if not os.path.exists(ruta):
            continue
        for c in carreras_de(ruta):
            k = normalizar(c)
            por_ciclo[m["ciclo"]][k] += 1
            etiqueta.setdefault(k, c)

    ciclos = sorted(por_ciclo)
    todas = sorted({k for c in por_ciclo.values() for k in c})
    destino = os.path.join(RAIZ, "data", "carreras_por_ciclo.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["carrera"] + ciclos + ["primer_ciclo", "ultimo_ciclo", "n_ciclos"])
        for k in todas:
            fila = [1 if por_ciclo[c][k] else 0 for c in ciclos]
            presentes = [c for c, v in zip(ciclos, fila) if v]
            w.writerow([etiqueta[k]] + fila +
                       [presentes[0], presentes[-1], len(presentes)])
    print(f"catalogo -> data/carreras_por_ciclo.csv  ({len(todas)} carreras, {len(ciclos)} ciclos)")
    return por_ciclo, etiqueta, ciclos


if __name__ == "__main__":
    main()
