#!/usr/bin/env python3
"""
Mide el costo real de extraer caracteres con coordenadas del corpus completo.

La pregunta que responde: cuanto tarda la etapa Bronze -> Silver y con cuantos
procesos conviene correrla. De ahi sale si el paralelismo distribuido tiene
algo que aportar o si sobra con la maquina local.

Uso: python ExtraccionPDF/bench_paralelismo.py [n_muestra]
"""
import glob, os, statistics, sys, time
from concurrent.futures import ProcessPoolExecutor

import pdfplumber

RAIZ = os.path.dirname(os.path.abspath(__file__))
CORPUS = sorted(glob.glob(os.path.join(RAIZ, "data", "raw", "*", "*.pdf")))


def extraer_chars(ruta):
    """Trabajo real del parser: cada caracter con su posicion en la pagina.

    Es lo que hace falta para reconstruir filas, y es la operacion cara:
    pdfplumber resuelve la fuente, decodifica el CMap y calcula la caja de
    cada glifo.
    """
    n = 0
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            n += len(pagina.chars)
    return n


def medir(fn, rutas, procesos=None):
    t0 = time.perf_counter()
    if procesos:
        with ProcessPoolExecutor(procesos) as ex:
            total = sum(ex.map(fn, rutas))
    else:
        total = sum(fn(r) for r in rutas)
    return time.perf_counter() - t0, total


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    muestra = CORPUS[:n]
    nucleos = os.cpu_count()
    peso = sum(os.path.getsize(p) for p in muestra) / 1024 / 1024

    print(f"corpus completo   {len(CORPUS)} PDFs")
    print(f"muestra medida    {len(muestra)} PDFs, {peso:.1f} MB")
    print(f"nucleos           {nucleos}\n")

    t_serial, chars = medir(extraer_chars, muestra)
    por_pdf = t_serial / len(muestra)
    print(f"serial            {t_serial:7.2f} s   {por_pdf * 1000:7.1f} ms/PDF   {chars:,} caracteres")
    print(f"  corpus completo estimado: {por_pdf * len(CORPUS):.1f} s\n")

    mejor = (1, t_serial)
    for w in (2, 4, 8, nucleos):
        if w > nucleos:
            continue
        t, _ = medir(extraer_chars, muestra, procesos=w)
        acel = t_serial / t
        eficiencia = acel / w
        print(f"pool x{w:<2}          {t:7.2f} s   aceleracion {acel:4.2f}x   eficiencia {eficiencia:4.0%}")
        if t < mejor[1]:
            mejor = (w, t)

    print(f"\nmejor configuracion: {mejor[0]} procesos, "
          f"{mejor[1] / len(muestra) * len(CORPUS):.1f} s para el corpus completo")


if __name__ == "__main__":
    main()
