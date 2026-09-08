#!/usr/bin/env python3
"""
Contraste independiente: cuenta las filas del PDF sin usar el parser.

Las suites de 11 y 13 comprueban que la salida sea coherente consigo misma y
con las redundancias que el documento publica. Esta prueba responde otra
pregunta: si un segundo metodo, que no comparte una linea de codigo con el
parser, cuenta lo mismo.

El parser reconstruye la tabla por coordenadas de caracter. Aqui se usa el
texto plano que pdfplumber entrega por linea y una expresion regular por
esquema, que es la forma tosca y directa de hacerlo. Si los dos caminos llegan
al mismo numero pagina por pagina, el desacuerdo tendria que ser una
coincidencia en 4 963 paginas.

La comparacion es por pagina y no por archivo a proposito: dos errores que se
compensan entre paginas dan el mismo total y distinto detalle.

Uso: python ExtraccionPDF/14_ContrasteIndependiente.py
"""
import csv, glob, os, re, sys
from collections import Counter
from multiprocessing import Pool

import pdfplumber

RAIZ = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(RAIZ, "data", "raw")
EXTRAIDA = os.path.join(RAIZ, "data_extraida")
PROCESOS = 8

# Cada esquema del corpus arranca la fila de una forma distinta. Una linea
# cuenta como dato si encaja en cualquiera de ellos.
#
# Se probo antes elegir por archivo el esquema que mas lineas explicara, y
# subestimaba: una tabla que sigue en la pagina siguiente pierde la columna de
# codigo al no repetir el encabezado, asi que las paginas de continuacion
# usaban otro esquema que el del archivo y contaban cero.
ESQUEMAS = [
    re.compile(r"^\d{1,4}\s+\d{6,12}\s+\S"),           # orden y codigo
    re.compile(r"^\d{6,12}\s+[A-ZÑÁÉÍÓÚ]"),             # documento al inicio
    # Orden y nombre. El nombre se acepta con cualquier caracter porque la
    # fuente trae su codificacion rota de formas distintas: 'MU?OZ' donde va
    # una eñe, 'RAM?REZ' donde va una tilde y hasta 'ZU&NTILDE;IGA', que es una
    # entidad HTML sin convertir. Solo se exige que el token traiga dos letras
    # mayusculas seguidas, que descarta titulos como '2021 - I'.
    re.compile(r"^\d{1,4}\s+\S*[A-ZÑÁÉÍÓÚÜ]{2,}"),
    re.compile(r"^\d{1,4}\s+\d{6,12}[A-ZÑÁÉÍÓÚ]"),        # codigo pegado al nombre
    # Las listas de aptitud no numeran: la fila arranca por el apellido y se
    # reconoce porque termina en puntajes.
    re.compile(r"^[A-ZÑÁÉÍÓÚ][A-ZÑÁÉÍÓÚ'´ ]{6,}.*\d+\.\d+"),
]


def contar(ruta):
    """Filas por pagina segun el esquema que mejor explique el documento."""
    try:
        with pdfplumber.open(ruta) as pdf:
            paginas = [(p.page_number, (p.extract_text() or "").split("\n"))
                       for p in pdf.pages]
    except Exception as e:
        return os.path.basename(ruta), None, f"{type(e).__name__}: {e}"

    cuenta = {n: sum(1 for l in lineas
                     if any(p.match(l.strip()) for p in ESQUEMAS))
              for n, lineas in paginas}
    return os.path.basename(ruta), cuenta, None


def extraidas_por_pagina():
    fuera = {}
    for ruta in glob.glob(os.path.join(EXTRAIDA, "*", "*.csv")):
        if os.path.basename(ruta).startswith("_"):
            continue
        for f in csv.DictReader(open(ruta, encoding="utf-8")):
            clave = (f["archivo"], int(f["pagina"]))
            fuera[clave] = fuera.get(clave, 0) + 1
    return fuera


def main():
    rutas = sorted(glob.glob(os.path.join(RAW, "*", "*.pdf")))
    with Pool(PROCESOS) as pool:
        resultados = pool.map(contar, rutas)

    extraido = extraidas_por_pagina()
    con_datos = {a for a, _ in extraido}
    # Las listas de aptitud se contrastan aparte. No forman parte del conjunto
    # analitico, no cuentan como admision y su maquetacion cambia de un año a
    # otro, asi que mezclarlas diluia el unico numero que importa: si las actas
    # de resultados coinciden.
    clase = {r["archivo"]: r.get("clase", "resultados")
             for r in csv.DictReader(open(os.path.join(EXTRAIDA, "_resumen.csv"),
                                          encoding="utf-8"))}

    paginas = Counter()
    iguales = Counter()
    difieren, errores = [], []
    for archivo, cuenta, error in resultados:
        if error:
            errores.append((archivo, error))
            continue
        # Un PDF que no produjo filas no se contrasta aqui: por que no las
        # produjo lo verifica 12_Auditoria.py leyendo el documento.
        if archivo not in con_datos:
            continue
        for pagina, n in cuenta.items():
            if n == 0 and extraido.get((archivo, pagina), 0) == 0:
                continue
            c = clase.get(archivo, "resultados")
            paginas[c] += 1
            if n == extraido.get((archivo, pagina), 0):
                iguales[c] += 1
            else:
                difieren.append((archivo, pagina, n,
                                 extraido.get((archivo, pagina), 0), c))

    print("CONTRASTE INDEPENDIENTE · texto plano contra reconstruccion por coordenadas\n")
    print(f"  PDFs contrastados : {len(con_datos)}")
    for c in ("resultados", "lista_aptitud"):
        if paginas[c]:
            print(f"  {c:16}: {iguales[c]:>5,} de {paginas[c]:>5,} paginas "
                  f"coinciden ({iguales[c] / paginas[c] * 100:.2f}%)")

    fallas = [d for d in difieren if d[4] == "resultados"]
    avisos = [d for d in difieren if d[4] != "resultados"]
    if fallas:
        print(f"\n  FALLA  {len(fallas)} paginas de resultados no coinciden")
        for a, p, n, e, _ in sorted(fallas, key=lambda x: -abs(x[2] - x[3]))[:10]:
            print(f"           {a} pag {p}: texto plano {n}, parser {e}")
    else:
        print(f"\n  ok     los dos metodos cuentan lo mismo en cada pagina "
              f"de resultados")
    if avisos:
        peor = Counter(a for a, _, _, _, _ in avisos)
        print(f"  aviso  {len(avisos)} paginas de listas de aptitud difieren, "
              f"en {len(peor)} documentos")

    for a, e in errores:
        print(f"  aviso  {a}: {e}")

    destino = os.path.join(EXTRAIDA, "_contraste.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "pagina", "texto_plano", "parser", "clase"])
        w.writerows(sorted(difieren))
    print(f"\ninforme: data_extraida/_contraste.csv")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
