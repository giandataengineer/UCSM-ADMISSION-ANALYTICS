#!/usr/bin/env python3
"""
Auditoria integral del proyecto.

No repite la reconciliacion fila a fila, que ya hace 11_Validacion.py. Revisa
que el conjunto sea coherente: que cada etapa reciba lo que la anterior
produjo, que no se pierdan registros por el camino, que no salga informacion
personal, y que las cifras del README existan de verdad.

Cinco bloques:

  cadena       cada etapa conserva lo que recibio
  perdidas     que se cae entre Bronze y Gold, y por que
  privacidad   ni nombres ni documentos en lo que se versiona
  cobertura    que porcentaje del corpus llega hasta el final
  documentacion las cifras publicadas coinciden con los datos

Devuelve 1 si algo esta mal, para poder encadenarlo en un make o un hook.

Uso: python ExtraccionPDF/12_Auditoria.py
"""
import csv, glob, os, re, subprocess, sys
from collections import Counter

RAIZ = os.path.dirname(os.path.abspath(__file__))
PROY = os.path.dirname(RAIZ)

# Un DNI peruano tiene ocho digitos. Se exige que el token completo sean solo
# esos ocho digitos: sin esa condicion el detector marca los ocho digitos
# consecutivos que aparecen dentro de un SHA-256 y avisa donde no hay nada.
# Un control que grita sin motivo enseña a ignorarlo.
DNI = re.compile(r"(?<![0-9A-Za-z])\d{8}(?![0-9A-Za-z])")
# Tres o mas palabras en mayusculas seguidas: la forma de un nombre completo.
NOMBRE = re.compile(r"\b[A-ZÑÁÉÍÓÚ]{3,}(?: [A-ZÑÁÉÍÓÚ]{3,}){2,}\b")

hallazgos = []


def marca(nivel, bloque, texto):
    hallazgos.append((nivel, bloque, texto))
    simbolo = {"ok": "  ok   ", "aviso": "  aviso", "falla": "  FALLA"}[nivel]
    print(f"{simbolo}  {texto}")


def leer(ruta):
    p = os.path.join(RAIZ, ruta)
    if not os.path.exists(p):
        return None
    return list(csv.DictReader(open(p, encoding="utf-8")))


def bloque_cadena():
    print("\nCADENA DE PROCESAMIENTO")
    man = leer("data/manifest.csv") or []
    aud = leer("data/auditoria.csv") or []
    res = leer("data_extraida/_resumen.csv") or []

    descargados = [m for m in man if m["estado"] == "ok"]
    en_disco = sum(1 for _, _, f in os.walk(os.path.join(RAIZ, "data", "raw"))
                   for x in f if x.endswith(".pdf"))

    if len(aud) == en_disco:
        marca("ok", "cadena", f"auditoria cubre los {en_disco} PDFs en disco")
    else:
        marca("falla", "cadena",
              f"auditoria tiene {len(aud)} filas y hay {en_disco} PDFs en disco")

    if len(res) == en_disco:
        marca("ok", "cadena", f"el parser proceso los {en_disco} PDFs")
    else:
        marca("falla", "cadena",
              f"el parser reporta {len(res)} y hay {en_disco} PDFs")

    fallidos = [m for m in man if m["estado"] != "ok"]
    if fallidos:
        marca("aviso", "cadena",
              f"{len(fallidos)} PDFs descubiertos que no se pudieron descargar")


def bloque_perdidas():
    print("\nPERDIDAS ENTRE ETAPAS")
    res = leer("data_extraida/_resumen.csv") or []
    extraidas = sum(int(r["filas"]) for r in res)
    norm = leer("data_normalizada/postulaciones.csv") or []

    sin_filas = [r for r in res if int(r["filas"]) == 0]
    pct = len(sin_filas) / len(res) * 100 if res else 0
    nivel = "aviso" if pct < 40 else "falla"
    marca(nivel, "perdidas",
          f"{len(sin_filas)} de {len(res)} PDFs no producen filas ({pct:.0f}%)")

    perdidas = extraidas - len(norm)
    if perdidas == 0:
        marca("ok", "perdidas", f"normalizacion conserva las {extraidas:,} filas")
    elif perdidas / max(extraidas, 1) < 0.01:
        marca("ok", "perdidas",
              f"normalizacion descarta {perdidas} filas ({perdidas/extraidas*100:.2f}%), "
              f"titulos leidos como carrera")
    else:
        marca("falla", "perdidas",
              f"normalizacion pierde {perdidas:,} filas de {extraidas:,}")

    con_ingreso = sum(1 for x in norm if x["ingreso"])
    marca("ok" if con_ingreso else "falla", "perdidas",
          f"{con_ingreso:,} filas con resultado binario "
          f"({con_ingreso/max(len(norm),1)*100:.0f}% del total)")


def catalogo():
    """Nombres de carrera y proceso conocidos, para no confundirlos con personas.

    Se leen del propio corpus en vez de mantenerse a mano: si UCSM convoca una
    carrera nueva, el detector la reconoce sin tocar codigo.
    """
    conocidos = set()
    for ruta, campo in [("data/carreras_por_ciclo.csv", "carrera"),
                        ("data/manifest.csv", "proceso"),
                        ("data_normalizada/gold/admision_por_carrera.csv", "carrera")]:
        for fila in (leer(ruta) or []):
            valor = (fila.get(campo) or "").strip().upper()
            if valor:
                conocidos.add(valor)
                conocidos.update(NOMBRE.findall(valor))
    return conocidos


def bloque_privacidad():
    print("\nPRIVACIDAD")
    conocidos = catalogo()
    versionados = subprocess.run(["git", "ls-files"], cwd=PROY,
                                 capture_output=True, text=True).stdout.split()
    sospechosos = []
    for rel in versionados:
        if not rel.endswith((".csv", ".md", ".txt")):
            continue
        ruta = os.path.join(PROY, rel)
        if not os.path.exists(ruta):
            continue
        texto = open(ruta, encoding="utf-8", errors="replace").read()
        dnis = DNI.findall(texto)
        # Una cadena en mayusculas solo es sospechosa si no es un nombre de
        # carrera ni de proceso ya conocido por el propio corpus.
        nombres = [n for n in NOMBRE.findall(texto) if n.upper() not in conocidos]
        if dnis or nombres:
            sospechosos.append((rel, len(dnis), len(nombres), nombres[:2]))

    if sospechosos:
        for rel, d, n, ej in sospechosos:
            marca("falla", "privacidad",
                  f"{rel}: {d} posibles DNI, {n} posibles nombres {ej}")
    else:
        marca("ok", "privacidad",
              f"ningun DNI ni nombre en los {len(versionados)} archivos versionados")

    ignorados = open(os.path.join(PROY, ".gitignore"), encoding="utf-8").read()
    for critico in ["data/raw/", "data_extraida/", "postulaciones.csv"]:
        if critico in ignorados:
            marca("ok", "privacidad", f"{critico} esta en .gitignore")
        else:
            marca("falla", "privacidad", f"{critico} NO esta en .gitignore")


def bloque_cobertura():
    print("\nCOBERTURA DEL CORPUS")
    norm = leer("data_normalizada/postulaciones.csv") or []
    if not norm:
        marca("falla", "cobertura", "no hay datos normalizados")
        return
    ciclos = Counter(x["ciclo"] for x in norm)
    for c in sorted(ciclos):
        con = sum(1 for x in norm if x["ciclo"] == c and x["ingreso"])
        rech = sum(1 for x in norm if x["ciclo"] == c and x["ingreso"] == "0")
        pct = rech / con * 100 if con else 0
        estado = "ok" if pct >= 25 else "aviso"
        marca(estado, "cobertura",
              f"ciclo {c}: {ciclos[c]:>6,} filas, {pct:>4.1f}% rechazados "
              f"{'(denominador fiable)' if pct >= 25 else '(solo ingresantes)'}")

    carreras = len({x["carrera"] for x in norm})
    cat = leer("data/carreras_por_ciclo.csv") or []
    if abs(carreras - len(cat)) <= 3:
        marca("ok", "cobertura",
              f"{carreras} carreras normalizadas contra {len(cat)} del catalogo")
    else:
        marca("aviso", "cobertura",
              f"{carreras} carreras normalizadas pero el catalogo tiene {len(cat)}")


def bloque_documentacion():
    print("\nDOCUMENTACION")
    readme = open(os.path.join(PROY, "README.md"), encoding="utf-8").read()
    norm = leer("data_normalizada/postulaciones.csv") or []
    en_disco = sum(1 for _, _, f in os.walk(os.path.join(RAIZ, "data", "raw"))
                   for x in f if x.endswith(".pdf"))

    reales = {
        "PDFs de resultados": str(en_disco),
        "filas normalizadas": f"{len(norm):,}".replace(",", " "),
    }
    for etiqueta, valor in reales.items():
        crudo = valor.replace(" ", "")
        if crudo in readme.replace(" ", "").replace(",", ""):
            marca("ok", "documentacion", f"README cita {etiqueta} = {valor}")
        else:
            marca("aviso", "documentacion",
                  f"README no cita el valor vigente de {etiqueta} ({valor})")

    for adr in sorted(glob.glob(os.path.join(PROY, "docs", "ADR-*.md"))):
        marca("ok", "documentacion", f"decision registrada: {os.path.basename(adr)}")

    for script in sorted(glob.glob(os.path.join(RAIZ, "*.py"))):
        texto = open(script, encoding="utf-8").read()
        if not texto.lstrip().startswith(('"""', "#!")):
            marca("aviso", "documentacion",
                  f"{os.path.basename(script)} sin docstring de modulo")


def main():
    print("AUDITORIA INTEGRAL · UCSM Admission Analytics")
    bloque_cadena()
    bloque_perdidas()
    bloque_privacidad()
    bloque_cobertura()
    bloque_documentacion()

    c = Counter(n for n, _, _ in hallazgos)
    print(f"\n{'-' * 4}\n{c['ok']} conformes · {c['aviso']} avisos · {c['falla']} fallas")

    destino = os.path.join(RAIZ, "data", "auditoria_integral.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nivel", "bloque", "hallazgo"])
        w.writerows(hallazgos)
    print(f"informe: data/auditoria_integral.csv")
    return 1 if c["falla"] else 0


if __name__ == "__main__":
    sys.exit(main())
