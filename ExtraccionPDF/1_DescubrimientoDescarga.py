#!/usr/bin/env python3
"""
Descarga y cataloga el corpus de resultados de admision de la UCSM.

Tres vias de descubrimiento porque ninguna sola alcanza:
  - Wayback CDX  : cubre lo historico, pero esta desactualizado en 2026-2027
  - sondeo       : rellena huecos con nombres predecibles (EG2025III, etc.)
  - pagina web   : unica via que ve los nombres nuevos (RESULT_ORDINARIO_2027)

Salida:
  data/raw/<ciclo>/<archivo>.pdf
  data/manifest.csv
"""
import csv, hashlib, json, os, re, shutil, sys, time, urllib.request, zlib
from concurrent.futures import ThreadPoolExecutor

RAIZ = os.path.dirname(os.path.abspath(__file__))
CRUDO = os.path.join(RAIZ, "data", "raw")
CACHE = "/tmp/ucsm/raw"
BASE = "https://ucsm.edu.pe/wp-content/uploads/admision/resultados/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Documentos de contexto que no son listas de resultados pero valen oro
EXTRA = {
    "https://ucsm.edu.pe/wp-content/uploads/2026/05/9813-CU-2026-cuadro-de-vacantes-2027.pdf":
        "vacantes_2027.pdf",
    "https://ucsm.edu.pe/wp-content/uploads/2026/06/9807-CU-2026-CRONOGRAMA-2027.pdf":
        "cronograma_2027.pdf",
    "https://ucsm.edu.pe/wp-content/uploads/2026/05/9786-CU-2026-Nuevo-TUO-Texto-Unico-Ordenado-Reglamento-de-Admision.pdf":
        "tuo_reglamento_admision.pdf",
    "https://ucsm.edu.pe/wp-content/uploads/2026/04/9785-CU-2026-PERFIL-DE-INGRESO.pdf":
        "perfil_de_ingreso.pdf",
}

# Hallados leyendo ucsm.edu.pe/resultados-de-pregrado con navegador.
# Invisibles a Wayback y al sondeo: la convencion de nombres cambio en 2026.
WEB = """Resultados_2026_IEOE.pdf RESULT_ORDINARIO_2026.pdf RESULT_ORDINARIO_2027.pdf
Resultados_Final_Preca2027-I.pdf RESULT_EXTRAORDINARIO_2026.pdf RESULT_EXTRAORDINARIO_2027.pdf
RESULT_RENDIMIENTO_SUP.pdf RESULT_2027_CCI.pdf Resultados_Final_EO2026II.pdf
RESULT_BECA_ESPERANZA2026.pdf RESULT_BECA_ESPERANZA_COMUNIDADES2026.pdf RESULT_BECA_TISUR2026.pdf
EG2026I.pdf EG2026II.pdf Resultados_2026_IIIORDINARIO.pdf DISTANCIA_E2026I.pdf
EDYS2026OII.pdf RESULT_EGEDS2026III.pdf precatolica2026-I_final.pdf Resul_PrecaIII.pdf
RendimientoSuperior2026.pdf 2026CCI-I.pdf 2026CCI-I_medicina.pdf
Extraordinario2025II.pdf Extraordinario2026I.pdf""".split()

SONDEO = """2026CCI-I.pdf 2026CCI-I_medicina.pdf Aptos2026CCI.pdf Aptos2026RS.pdf
DISTANCIA_E2025II.pdf DISTANCIA_E2026I.pdf EG2025III.pdf EG2026I.pdf Extraordinario2025I.pdf
Extraordinario2025II.pdf Extraordinario2026I.pdf NoAptos2026RS.pdf RendimientoSuperior2026.pdf
Resultados_Final_Primer_Exa_General2027.pdf precatolica2025-III.pdf
precatolica2026-I_final.pdf EG2024III.pdf""".split()

CDX = ("http://web.archive.org/cdx/search/cdx?url=ucsm.edu.pe/wp-content/uploads/"
       "admision/resultados*&output=text&fl=original&collapse=urlkey&limit=5000")


def descubrir():
    """Une las tres vias y anota de cual vino cada archivo."""
    origen = {}
    try:
        d = urllib.request.urlopen(CDX, timeout=90).read().decode("utf-8", "replace")
        for linea in d.split("\n"):
            linea = linea.strip()
            if linea.lower().endswith(".pdf"):
                origen.setdefault(linea.split("resultados/")[-1], "wayback")
    except Exception as e:
        print(f"  aviso: Wayback no respondio ({e}); sigo con las otras vias")
    for n in SONDEO:
        origen.setdefault(n, "sondeo")
    for n in WEB:
        origen.setdefault(n, "web")
    return origen


def bajar(url, destino, intentos=5):
    """Descarga con backoff. El servidor devuelve 429 si se le insiste."""
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            datos = urllib.request.urlopen(req, timeout=90).read()
            if not datos.startswith(b"%PDF"):
                return None, "no es PDF"
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, "wb") as f:
                f.write(datos)
            return datos, "ok"
        except Exception as e:
            if "404" in str(e):
                return None, "404"
            time.sleep(3 * (i + 1))
    return None, "fallo tras reintentos"


def leer_cabecera(raw):
    """Saca proceso, fecha y estructura del PDF sin librerias externas.

    Dos familias de generador:
      DEVEXP    -> sistema de admision, fuentes subset con ToUnicode. Esquema rico.
      MS-OFFICE -> exportado de Excel/Word, usa object streams. Esquema pobre.
    """
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

    tok = []
    for d in paginas[:2]:
        tok += [dec(m.group(1)) for m in re.finditer(r"<([0-9A-Fa-f]+)>\s*Tj", d)]
        tok += [m.group(1) for m in re.finditer(r"\(((?:[^()\\]|\\.)*)\)\s*Tj", d)]

    proceso = next((t for t in tok if re.search(
        r"EXAMEN|PRECAT|CEPRE|TRASLADO|EXTRAORD|BECA|ADMISION|CONCURSO|ORDINARIO", t, re.I)), "")
    fecha = next((t for t in tok if re.fullmatch(r"\d{2}/\d{2}/\d{4}", t)), "")
    modalidad = tok[0].strip() if tok else ""
    if modalidad == proceso:
        modalidad = ""

    familia = "DEVEXP" if cmap else ("MS-OFFICE" if b"/ObjStm" in raw else "OTRO")
    paginas_pdf = len(re.findall(rb"/Type\s*/Page[^s]", raw))

    # Condiciones presentes: dice si el PDF trae rechazados o solo ingresantes
    texto = " ".join(tok)
    cond = [c for c in ("INGRESO", "NO INGRESO", "NSP", "NC") if c in texto]
    return familia, paginas_pdf, modalidad, proceso, fecha, "|".join(cond)


def ciclo_de(proceso, fecha, nombre):
    """El ciclo de admision es el año del PROCESO, no el de la fecha del examen.

    EG2023I.pdf dice 'PRIMER EXAMEN ORDINARIO 2023' pero se rindio el 29/08/2022.
    """
    m = re.search(r"20\d{2}", proceso or "")
    if m:
        return m.group(0)
    m = re.search(r"20(\d{2})", nombre)
    return "20" + m.group(1) if m else "sin_ciclo"


def tipo_de(proceso, nombre):
    """Clasifica el proceso. Ojo: UCSM renombro 'EXAMEN GENERAL' a 'EXAMEN
    ORDINARIO' alrededor de 2022, y el sufijo 'salud' marca la lista aparte de
    carreras de ciencias de la salud, que es el mismo examen."""
    t = ((proceso or "") + " " + nombre).upper()
    if "PRECAT" in t or "PRECA" in t:                  return "precatolica"
    if "DISTANCIA" in t or "SEMIPRESENCIAL" in t or "EDS" in t or "EDYS" in t:
                                                       return "distancia"
    if "BECA" in t or "PRONABEC" in t or "TISUR" in t: return "beca"
    if "TERCIO SUPERIOR" in t or "TSUP" in t:          return "tercio_superior"
    if "RENDIMIENTO" in t or "RS" in t.split():        return "rendimiento_superior"
    if "TRASLADO" in t or "TEN" in t or "TEI" in t:    return "traslado"
    if "CCI" in t or "CONVENIO" in t or "COBER" in t:  return "convenio_cci"
    if "EXTRAORD" in t:                                return "extraordinario"
    if "COMPLEMENT" in t or "NIVELACION" in t:         return "complementario"
    if "APTO" in t:                                    return "lista_aptos"
    # EXAMEN GENERAL (2016-2022) y EXAMEN ORDINARIO (2022+) son el mismo proceso
    if "ORDINARIO" in t or "EXAMEN GENERAL" in t or re.match(r"^(PUNTAJES_)?EG\d{4}", t):
        return "ordinario"
    return "otro"


def main():
    print("1. Descubriendo archivos por las tres vias...")
    origen = descubrir()
    print(f"   {len(origen)} archivos unicos\n")

    print("2. Descargando (con throttle; el servidor corta con 429 si se abusa)...")
    os.makedirs(CRUDO, exist_ok=True)
    tmp = os.path.join(RAIZ, "data", ".tmp")
    os.makedirs(tmp, exist_ok=True)

    def obtener(nombre):
        plano = nombre.replace("/", "__")
        destino = os.path.join(tmp, plano)
        cacheado = os.path.join(CACHE, plano)
        if os.path.exists(destino) and os.path.getsize(destino) > 1000:
            return nombre, open(destino, "rb").read(), "cache"
        if os.path.exists(cacheado) and os.path.getsize(cacheado) > 1000:
            shutil.copy2(cacheado, destino)
            return nombre, open(destino, "rb").read(), "cache"
        datos, estado = bajar(BASE + nombre, destino)
        time.sleep(0.4)
        return nombre, datos, estado

    resultados = []
    nombres = sorted(origen)
    with ThreadPoolExecutor(4) as ex:
        for i, r in enumerate(ex.map(obtener, nombres), 1):
            resultados.append(r)
            if i % 40 == 0:
                print(f"   {i}/{len(nombres)}")

    ok = [r for r in resultados if r[1]]
    print(f"   descargados: {len(ok)}/{len(nombres)}\n")

    print("3. Leyendo cabecera interna de cada PDF y organizando por ciclo...")
    filas = []
    for nombre, datos, estado in resultados:
        if not datos:
            filas.append(dict(archivo=nombre, ciclo="", tipo="", proceso="", fecha_examen="",
                              familia="", paginas="", modalidad="", condiciones="",
                              bytes=0, sha256="", origen=origen[nombre],
                              ruta="", estado=estado))
            continue
        fam, npag, moda, proc, fec, cond = leer_cabecera(datos)
        ciclo = ciclo_de(proc, fec, nombre)
        tipo = tipo_de(proc, nombre)
        carpeta = os.path.join(CRUDO, ciclo)
        os.makedirs(carpeta, exist_ok=True)
        final = os.path.join(carpeta, nombre.replace("/", "__"))
        with open(final, "wb") as f:
            f.write(datos)
        filas.append(dict(
            archivo=nombre, ciclo=ciclo, tipo=tipo, proceso=proc, fecha_examen=fec,
            familia=fam, paginas=npag, modalidad=moda, condiciones=cond,
            bytes=len(datos), sha256=hashlib.sha256(datos).hexdigest()[:16],
            origen=origen[nombre], ruta=os.path.relpath(final, RAIZ), estado="ok"))

    shutil.rmtree(tmp, ignore_errors=True)

    campos = ["archivo", "ciclo", "tipo", "proceso", "fecha_examen", "familia",
              "paginas", "modalidad", "condiciones", "bytes", "sha256", "origen",
              "ruta", "estado"]
    destino_csv = os.path.join(RAIZ, "data", "manifest.csv")
    with open(destino_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(sorted(filas, key=lambda r: (r["ciclo"], r["fecha_examen"], r["archivo"])))
    print(f"   manifiesto: {os.path.relpath(destino_csv, RAIZ)}")
    print(f"   PDFs en:    data/raw/<ciclo>/\n")
    return filas


if __name__ == "__main__":
    main()
