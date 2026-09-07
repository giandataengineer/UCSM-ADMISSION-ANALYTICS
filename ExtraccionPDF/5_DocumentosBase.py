#!/usr/bin/env python3
"""
Descarga los documentos normativos del proceso de admision, año por año.

Las listas de resultados dicen quien entro. Estos documentos dicen las reglas
del juego: cuantas vacantes se ofertaron por carrera y modalidad, en que fechas,
bajo que reglamento y con que temario. Sin ellos no se puede calcular ocupacion
de plazas ni interpretar un cambio de nota de corte.

Series encontradas:
  <año>_VACANTES.pdf     cuadro de vacantes por carrera y modalidad
  <año>_REGLAMENTO.pdf   reglamento de admision vigente
  <año>_TEMARIO.pdf      temario del examen
  <año>_CRONOGRAMA.pdf   calendario del proceso

Salida: data/documentos_base/<año>/<tipo>.pdf  +  data/documentos_base.csv
"""
import csv, hashlib, json, os, re, time, urllib.error, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RAIZ, "data", "documentos_base")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Rutas donde UCSM ha guardado estos documentos a lo largo de los años
CARPETAS = [
    "https://ucsm.edu.pe/wp-content/uploads/admision/archivos/",
    "https://ucsm.edu.pe/wp-content/uploads/admision/",
    "https://www.ucsm.edu.pe/wp-content/uploads/admision/archivos/",
]
TIPOS = ["VACANTES", "REGLAMENTO", "TEMARIO", "CRONOGRAMA"]
ANIOS = [str(a) for a in range(2016, 2028)]

# Documentos del ciclo 2027, que viven fuera de /admision/ con nombre de acuerdo
SUELTOS = {
    "2027/vacantes.pdf":
        "https://ucsm.edu.pe/wp-content/uploads/2026/05/9813-CU-2026-cuadro-de-vacantes-2027.pdf",
    "2027/cronograma.pdf":
        "https://ucsm.edu.pe/wp-content/uploads/2026/06/9807-CU-2026-CRONOGRAMA-2027.pdf",
    "2027/reglamento.pdf":
        "https://ucsm.edu.pe/wp-content/uploads/2026/05/9786-CU-2026-Nuevo-TUO-Texto-Unico-Ordenado-Reglamento-de-Admision.pdf",
    "2027/temario.pdf":
        "https://ucsm.edu.pe/wp-content/uploads/2026/05/TEMARIO-DE-ADMISION-2027.pdf",
    "2027/perfil_de_ingreso.pdf":
        "https://ucsm.edu.pe/wp-content/uploads/2026/04/9785-CU-2026-PERFIL-DE-INGRESO.pdf",
}


def intentar(url, intentos=3):
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            d = urllib.request.urlopen(req, timeout=60).read()
            return d if d.startswith(b"%PDF") else None
        except Exception as e:
            if "404" in str(e):
                return None
            time.sleep(3 * (i + 1))
    return None


def wayback(nombre):
    """Si el sitio vivo ya no lo tiene, se busca la copia archivada."""
    u = ("http://archive.org/wayback/available?url=" +
         urllib.parse.quote(f"ucsm.edu.pe/wp-content/uploads/admision/archivos/{nombre}"))
    try:
        r = json.load(urllib.request.urlopen(u, timeout=40))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"    wayback no respondio por {nombre}: {e}")
        return None
    snap = r.get("archived_snapshots", {}).get("closest", {})
    if not snap.get("available"):
        return None
    return intentar(snap["url"].replace("http://", "https://"))


def main():

    filas = []
    for anio in ANIOS:
        for tipo in TIPOS:
            nombre = f"{anio}_{tipo}.pdf"
            datos, fuente = None, ""
            for carpeta in CARPETAS:
                datos = intentar(carpeta + nombre)
                if datos:
                    fuente = "sitio"
                    break
                time.sleep(0.2)
            if not datos:
                datos = wayback(nombre)
                fuente = "wayback" if datos else ""
            if not datos:
                continue
            carpeta_anio = os.path.join(DESTINO, anio)
            os.makedirs(carpeta_anio, exist_ok=True)
            ruta = os.path.join(carpeta_anio, tipo.lower() + ".pdf")
            with open(ruta, "wb") as f:
                f.write(datos)
            filas.append(dict(anio=anio, tipo=tipo.lower(), archivo_origen=nombre,
                              fuente=fuente, bytes=len(datos),
                              sha256=hashlib.sha256(datos).hexdigest()[:16],
                              ruta=os.path.relpath(ruta, RAIZ)))
            print(f"  {anio} {tipo.lower():<11} {len(datos)//1024:>5} KB  ({fuente})")

    for rel, url in SUELTOS.items():
        ruta = os.path.join(DESTINO, rel)
        # Si ya esta en disco se reusa, pero igual entra al manifiesto: el CSV
        # describe el corpus completo, no solo lo descargado en esta corrida.
        if os.path.exists(ruta):
            datos, origen = open(ruta, "rb").read(), "cache"
        else:
            datos, origen = intentar(url), "sitio"
            if not datos:
                continue
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "wb") as f:
                f.write(datos)
        anio, tipo = rel.split("/")[0], rel.split("/")[1].replace(".pdf", "")
        filas.append(dict(anio=anio, tipo=tipo, archivo_origen=url.split("/")[-1],
                          fuente=origen, bytes=len(datos),
                          sha256=hashlib.sha256(datos).hexdigest()[:16],
                          ruta=os.path.relpath(ruta, RAIZ)))
        print(f"  {anio} {tipo:<11} {len(datos)//1024:>5} KB  ({origen})")

    destino_csv = os.path.join(RAIZ, "data", "documentos_base.csv")
    with open(destino_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["anio", "tipo", "archivo_origen", "fuente",
                                          "bytes", "sha256", "ruta"])
        w.writeheader()
        w.writerows(sorted(filas, key=lambda r: (r["anio"], r["tipo"])))
    print(f"\n{len(filas)} documentos -> data/documentos_base/<año>/")
    return filas


if __name__ == "__main__":
    main()
