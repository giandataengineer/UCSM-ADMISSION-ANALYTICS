#!/usr/bin/env python3
"""
Descarga los documentos de requisitos e indicaciones para ingresantes.

Cada proceso publica dos documentos: la lista de resultados y un instructivo
para quien ingreso. El segundo vive en /admision/Requisitos_Ingresantes/ y
sirve para dos cosas.

La primera es completar la trazabilidad del ciclo: si existe el instructivo de
un proceso pero no su lista de resultados, eso prueba que el proceso ocurrio y
que lo que falta es la publicacion, no el examen. Asi se detecto que Precatolica
2026-II se realizo pero su resultado nunca se subio.

La segunda es documental: los instructivos declaran plazos de matricula y
requisitos de expediente, que dan contexto a las fechas del cronograma.

Salida: data/requisitos/<ciclo>/  +  data/requisitos.csv
"""
import csv, hashlib, os, re, time, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RAIZ, "data", "requisitos")
BASE = "https://ucsm.edu.pe/wp-content/uploads/admision/Requisitos_Ingresantes/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
CICLO_MINIMO = "2021"

# Leidos del DOM de ucsm.edu.pe/resultados-de-pregrado con navegador: el WAF
# devuelve 403 a cualquier cliente que no lo sea.
ARCHIVOS = [
    "INDICACIONES_IORDINARIO_ESPECIAL_2026.pdf",
    "INDICACIONES_2026_ORDINARIO_ESPECIAL.pdf",
    "INDICACIONES_2027_ORDINARIO_ESPECIAL.pdf",
    "INDICACIONES%20INGRESANTES%20PRECAT%C3%93LICA%202027-I.pdf",
    "INDICACIONES_2027_POSTULANTES_SELECCIONADO_RENDIMIENTO_SUPERIOR.pdf",
    "INDICACIONES_PARA_INGRESANTES_EXTRAORDINARIO_II.pdf",
    "INDICACIONES_BECA_ESPERANZA_2026.pdf",
    "ANEXO_BECA_ESPERANZA_JOVEN_2026.pdf",
    "REQ_2027_CCI.pdf",
    "REQ_2026_I-EG.pdf",
    "REQ_2026_II-EG.pdf",
    "REQ_2026_IIIORDINARIO.pdf",
    "REQ_2026_I-DISTANCIA.pdf",
    "REQ_2026_II-EAV.pdf",
    "REQ_2026_III-EDS.pdf",
    "REQ_2026_PRECA_I.pdf",
    "REQ_2026_PRECA_II.pdf",
    "REQ_2026_PRECAIII.pdf",
    "REQ_2026_RSUP.pdf",
    "REQ_2026_CCI.pdf",
    "REQ_2025_EXTRA-IIf.pdf",
    "REQ_2026_EXTRA-I.pdf",
]


def ciclo_de(nombre):
    m = re.search(r"20\d{2}", urllib.parse.unquote(nombre))
    return m.group(0) if m else "sin_ciclo"


def descargar(nombre, intentos=4):
    for i in range(intentos):
        try:
            req = urllib.request.Request(BASE + nombre, headers={"User-Agent": UA})
            d = urllib.request.urlopen(req, timeout=90).read()
            return d if d.startswith(b"%PDF") else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (i + 1))
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (i + 1))
    return None


def main():
    filas = []
    for nombre in ARCHIVOS:
        ciclo = ciclo_de(nombre)
        if ciclo < CICLO_MINIMO:
            continue
        limpio = urllib.parse.unquote(nombre).replace(" ", "_")
        ruta = os.path.join(DESTINO, ciclo, limpio)
        if os.path.exists(ruta):
            datos, origen = open(ruta, "rb").read(), "cache"
        else:
            datos, origen = descargar(nombre), "sitio"
            if not datos:
                print(f"  no disponible  {limpio[:52]}")
                continue
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "wb") as f:
                f.write(datos)
            time.sleep(1)
        filas.append(dict(ciclo=ciclo, archivo=limpio, fuente=origen, bytes=len(datos),
                          sha256=hashlib.sha256(datos).hexdigest()[:16],
                          ruta=os.path.relpath(ruta, RAIZ)))
        print(f"  {ciclo}  {len(datos)//1024:>5} KB  {limpio[:54]}  ({origen})")

    destino_csv = os.path.join(RAIZ, "data", "requisitos.csv")
    with open(destino_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ciclo", "archivo", "fuente", "bytes",
                                          "sha256", "ruta"])
        w.writeheader()
        w.writerows(sorted(filas, key=lambda r: (r["ciclo"], r["archivo"])))
    print(f"\n{len(filas)} documentos -> data/requisitos/<ciclo>/")
    return filas


if __name__ == "__main__":
    main()
