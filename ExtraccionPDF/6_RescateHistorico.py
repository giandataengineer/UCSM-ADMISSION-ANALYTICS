#!/usr/bin/env python3
"""
Rescata los documentos de admision que no siguen ninguna convencion de nombre.

Los scripts 1 y 5 cubren lo que sigue un patron. Este cubre el resto: archivos
sueltos de epocas en que la UCSM no tenia convencion, encontrados barriendo los
5041 PDFs del dominio en el indice de Wayback y filtrando los que hablan de
admision.

Entre ellos estan los tres examenes generales de 2020, que el script 1 no
encontraba porque se llaman primer-EXAMEN_GENERAL_2020.pdf en vez de EG2020I.pdf.

Salida: data/raw/<ciclo>/ y data/documentos_base/<año>/ segun corresponda,
mas data/rescate.csv con lo que se pudo recuperar y lo que no.
"""
import csv, hashlib, json, os, re, time, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# destino -> nombre de archivo en el servidor.
# "resultado" va a data/raw/<ciclo>, "base" va a data/documentos_base/<año>.
RESCATE = [
    ("resultado", "2020", "primer-EXAMEN_GENERAL_2020.pdf"),
    ("resultado", "2020", "segundo-EXAMEN_GENERAL_2020.pdf"),
    ("resultado", "2020", "tercer-EXAMEN_GENERAL_2020.pdf"),
    ("resultado", "sin_ciclo", "tercio-superior.pdf"),
    ("resultado", "sin_ciclo", "traslado-interno.pdf"),
    ("resultado", "sin_ciclo", "traslado-externo-nacional.pdf"),
    ("resultado", "sin_ciclo", "traslado-externo-internacional.pdf"),
    ("resultado", "2015", "ingresantes_ucsm_2014_2015.pdf"),
    ("base", "2024", "Vacantes-2024.pdf"),
    ("base", "2023", "ucsm-vacantes-pronabec-2023.pdf"),
    ("base", "2016", "reglamento_admision_2016.pdf"),
    ("base", "2021", "ucsm-regalemento-admision-virtual.pdf"),
]

CARPETAS = [
    "https://ucsm.edu.pe/wp-content/uploads/admision/archivos/",
    "https://ucsm.edu.pe/wp-content/uploads/admision/",
    "https://ucsm.edu.pe/wp-content/uploads/admision/resultados/",
]


def descargar(url, intentos=5):
    """El servidor devuelve 429 con facilidad, asi que el backoff es generoso."""
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            d = urllib.request.urlopen(req, timeout=90).read()
            return d if d.startswith(b"%PDF") else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(6 * (i + 1))
        except (urllib.error.URLError, TimeoutError):
            time.sleep(6 * (i + 1))
    return None


def desde_wayback(nombre):
    for carpeta in CARPETAS:
        u = ("http://archive.org/wayback/available?url=" +
             urllib.parse.quote(carpeta.replace("https://", "") + nombre))
        try:
            r = json.load(urllib.request.urlopen(u, timeout=40))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
        snap = r.get("archived_snapshots", {}).get("closest", {})
        if snap.get("available"):
            d = descargar(snap["url"].replace("http://", "https://"), intentos=2)
            if d:
                return d
        time.sleep(1)
    return None


def main():

    filas = []
    for destino, anio, nombre in RESCATE:
        datos, fuente = None, ""
        for carpeta in CARPETAS:
            datos = descargar(carpeta + nombre)
            if datos:
                fuente = "sitio"
                break
            time.sleep(1)
        if not datos:
            datos = desde_wayback(nombre)
            fuente = "wayback" if datos else ""
        if not datos:
            print(f"  no recuperado   {nombre}")
            filas.append(dict(destino=destino, anio=anio, archivo=nombre,
                              fuente="", bytes=0, sha256="", ruta=""))
            continue

        sub = "raw" if destino == "resultado" else "documentos_base"
        carpeta_final = os.path.join(RAIZ, "data", sub, anio)
        os.makedirs(carpeta_final, exist_ok=True)
        ruta = os.path.join(carpeta_final, nombre)
        with open(ruta, "wb") as f:
            f.write(datos)
        filas.append(dict(destino=destino, anio=anio, archivo=nombre, fuente=fuente,
                          bytes=len(datos), sha256=hashlib.sha256(datos).hexdigest()[:16],
                          ruta=os.path.relpath(ruta, RAIZ)))
        print(f"  {fuente:<8} {len(datos)//1024:>6} KB  {anio}  {nombre}")
        time.sleep(2)

    destino_csv = os.path.join(RAIZ, "data", "rescate.csv")
    with open(destino_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["destino", "anio", "archivo", "fuente",
                                          "bytes", "sha256", "ruta"])
        w.writeheader()
        w.writerows(filas)
    rec = sum(1 for x in filas if x["bytes"])
    print(f"\n{rec}/{len(filas)} recuperados -> data/rescate.csv")
    return filas


if __name__ == "__main__":
    main()
