#!/usr/bin/env python3
"""Contrasta el payload del tablero contra los CSV de origen.

El tablero no lee CSV: lee un JSON. Esta etapa vuelve a calcular cada cifra
directamente desde Gold y Silver y la compara con lo que el JSON afirma. Si
algo se descuadra, el tablero esta mostrando un numero que no existe.
"""
import csv, json, os, unicodedata
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(RAIZ, "ExtraccionPDF", "data_normalizada", "gold")
SILVER = os.path.join(RAIZ, "ExtraccionPDF", "data_normalizada", "postulaciones.csv")
PAYLOAD = os.path.join(RAIZ, "tablero", "src", "data", "gold.json")

fallas, pruebas = [], []


def revisa(nombre, ok, detalle=""):
    pruebas.append((nombre, ok, detalle))
    if not ok:
        fallas.append(f"{nombre}: {detalle}")


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def norm(t):
    t = unicodedata.normalize("NFKD", t or "")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).upper().split())


p = json.load(open(PAYLOAD, encoding="utf-8"))
carrera_rows = leer(os.path.join(GOLD, "admision_por_carrera.csv"))
IDX = {n: i for i, n in enumerate(
    ["ciclo", "carrera", "area", "post", "ing", "tasa", "fiable", "corte", "escala", "min", "max", "med"])}
pc = {f"{r[IDX['ciclo']]}|{r[IDX['carrera']]}": r for r in p["porCarrera"]}

# 1. Una fila del payload por fila de Gold, y al reves
revisa("filas por carrera coinciden", len(p["porCarrera"]) == len(carrera_rows),
       f"payload {len(p['porCarrera'])} vs gold {len(carrera_rows)}")

# 2. Postulaciones, ingresantes y tasa fila a fila
desc = []
for r in carrera_rows:
    f = pc.get(f'{r["ciclo"]}|{r["carrera"]}')
    if f is None:
        desc.append(f'falta {r["ciclo"]}|{r["carrera"]}')
        continue
    if f[IDX["post"]] != int(r["postulaciones"]):
        desc.append(f'{r["ciclo"]}|{r["carrera"]} postulaciones {f[IDX["post"]]} vs {r["postulaciones"]}')
    if f[IDX["ing"]] != int(r["ingresantes"]):
        desc.append(f'{r["ciclo"]}|{r["carrera"]} ingresantes {f[IDX["ing"]]} vs {r["ingresantes"]}')
    esperado = 1 if r["denominador_fiable"] == "si" else 0
    if f[IDX["fiable"]] != esperado:
        desc.append(f'{r["ciclo"]}|{r["carrera"]} denominador_fiable')
revisa("cada carrera cuadra con Gold", not desc, "; ".join(desc[:4]))

# 3. Las 47 carreras estan clasificadas y ninguna cae en el cajon de sastre
sin = [f[IDX["carrera"]] for f in p["porCarrera"] if f[IDX["area"]] == "Z"]
revisa("todas las carreras tienen area", not sin, f"{len(sin)} sin clasificar")

# 4. La variacion interanual reproduce la division
mal = []
post = defaultdict(dict)
for r in carrera_rows:
    post[r["carrera"]][r["ciclo"]] = int(r["postulaciones"])
for carrera, serie in post.items():
    anios = sorted(serie)
    for i, c in enumerate(anios[1:], 1):
        prev = serie[anios[i - 1]]
        if prev == 0:
            continue
        esperado = round((serie[c] - prev) / prev * 100, 1)
        visto = p["delta"].get(f"{c}|{carrera}")
        if visto is None or abs(visto - esperado) > 0.05:
            mal.append(f"{c}|{carrera} {visto} vs {esperado}")
revisa("la variacion interanual cuadra", not mal, "; ".join(mal[:3]))

# 5. La caja de cuartiles describe solo a ingresantes, calculada de nuevo
vals = defaultdict(list)
with open(SILVER, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["ingreso"] != "1":
            continue
        try:
            vals[f'{r["ciclo"]}|{r["carrera"]}'].append(float(r["total"]))
        except (TypeError, ValueError):
            pass
malc = []
for clave, caja in p["caja"].items():
    v = sorted(vals.get(clave, []))
    if not v:
        malc.append(f"{clave} sin respaldo en silver")
        continue
    if caja["n"] != len(v):
        malc.append(f'{clave} n {caja["n"]} vs {len(v)}')
    if abs(caja["min"] - round(v[0], 1)) > 0.05 or abs(caja["max"] - round(v[-1], 1)) > 0.05:
        malc.append(f'{clave} rango {caja["min"]}-{caja["max"]} vs {v[0]:.1f}-{v[-1]:.1f}')
    if not (caja["min"] <= caja["q1"] <= caja["med"] <= caja["q3"] <= caja["max"]):
        malc.append(f"{clave} cuartiles desordenados")
revisa("la caja describe a los ingresantes", not malc, "; ".join(malc[:3]))

# 6. Ningun puntaje del tablero es menor al minimo de un ingresante real
bajos = [c for c, caja in p["caja"].items() if caja["min"] < 0]
revisa("no hay puntajes negativos", not bajos, str(bajos[:3]))

# 7. La ocupacion de vacantes cruza por nombre normalizado
vac = leer(os.path.join(GOLD, "ocupacion_vacantes.csv"))
oficial = {norm(f[IDX["carrera"]]): f[IDX["carrera"]] for f in p["porCarrera"]}
esperadas = sum(1 for r in vac if norm(r["carrera"]) in oficial and r["ocupacion"])
revisa("ocupacion cruzada sin perdidas", len(p["vacantes"]) == esperadas,
       f'payload {len(p["vacantes"])} vs cruzables {esperadas}')

# 8. Toda fila de vacantes en el payload existe en Gold con ese valor
malv = []
for clave, (pct, estado) in p["vacantes"].items():
    ciclo, carrera = clave.split("|", 1)
    hit = [r for r in vac if r["ciclo"] == ciclo and norm(r["carrera"]) == norm(carrera)]
    if not hit:
        malv.append(f"{clave} no existe en gold")
    elif abs(float(hit[0]["ocupacion"]) - pct) > 0.01:
        malv.append(f'{clave} {pct} vs {hit[0]["ocupacion"]}')
revisa("cada ocupacion cuadra con Gold", not malv, "; ".join(malv[:3]))

# 9. Los ingresantes por modalidad suman los del acta
mm = []
mod_rows = leer(os.path.join(GOLD, "comparador_modalidad.csv"))
suma = defaultdict(int)
for r in mod_rows:
    if r["modalidad"] != "lista_aptos":
        suma[f'{r["ciclo"]}|{r["carrera"]}'] += int(r["ingresantes"] or 0)
for clave, v in p["porModalidad"].items():
    if sum(v) != suma.get(clave, 0):
        mm.append(f"{clave} {sum(v)} vs {suma.get(clave, 0)}")
revisa("las modalidades suman lo del acta", not mm, "; ".join(mm[:3]))

# 10. El total por area del anillo reproduce la suma de sus carreras
ma = []
for ciclo in p["ciclos"]:
    total_area = defaultdict(int)
    for f in p["porCarrera"]:
        if f[IDX["ciclo"]] == ciclo:
            total_area[f[IDX["area"]]] += f[IDX["post"]]
    directo = sum(int(r["postulaciones"]) for r in carrera_rows if r["ciclo"] == ciclo)
    if sum(total_area.values()) != directo:
        ma.append(f"{ciclo} {sum(total_area.values())} vs {directo}")
revisa("el reparto por area suma el total", not ma, "; ".join(ma[:3]))

# 11. Toda carrera convocada en un ciclo tiene su fila en el payload
cat = leer(os.path.join(RAIZ, "ExtraccionPDF", "data", "carreras_por_ciclo.csv"))
convocadas = {(c, norm(r["carrera"])) for r in cat for c in p["ciclos"] if r.get(c) == "1"}
en_payload = {(f[IDX["ciclo"]], norm(f[IDX["carrera"]])) for f in p["porCarrera"]}
sin = sorted(convocadas - en_payload)
revisa("toda carrera convocada esta en el tablero", not sin,
       f"{len(sin)} faltan: {sin[:3]}")

# 12. Las 47 carreras del catalogo aparecen al menos una vez
catalogo = {norm(r["carrera"]) for r in cat}
vistas = {norm(f[IDX["carrera"]]) for f in p["porCarrera"]}
revisa("las 47 carreras del catalogo aparecen", not (catalogo - vistas),
       f"faltan {sorted(catalogo - vistas)[:3]}")

# 13. Ninguna fila del payload es inventada: toda existe en Gold
gold_pares = {(r["ciclo"], r["carrera"]) for r in carrera_rows}
inventadas = [k for k in pc if tuple(k.split("|", 1)) not in gold_pares]
revisa("ninguna fila es inventada", not inventadas, str(inventadas[:3]))

# 14. Los totales por ciclo cuadran con la suma directa de Gold
malt = []
for ciclo in p["ciclos"]:
    pt = sum(f[IDX["post"]] for f in p["porCarrera"] if f[IDX["ciclo"]] == ciclo)
    it = sum(f[IDX["ing"]] for f in p["porCarrera"] if f[IDX["ciclo"]] == ciclo)
    gp = sum(int(r["postulaciones"]) for r in carrera_rows if r["ciclo"] == ciclo)
    gi = sum(int(r["ingresantes"]) for r in carrera_rows if r["ciclo"] == ciclo)
    if (pt, it) != (gp, gi):
        malt.append(f"{ciclo} {pt}/{it} vs {gp}/{gi}")
revisa("los totales por ciclo cuadran", not malt, "; ".join(malt[:3]))

# 15. El histograma suma los postulantes del acta
malh = []
dist = leer(os.path.join(GOLD, "distribucion_puntajes.csv"))
suma_d = defaultdict(int)
for r in dist:
    suma_d[f'{r["ciclo"]}|{r["carrera"]}'] += int(r["postulantes"])
for clave, tramos in p["distrib"].items():
    total = sum(t[1] + t[2] for t in tramos)
    if total != suma_d.get(clave, 0):
        malh.append(f"{clave} {total} vs {suma_d.get(clave, 0)}")
revisa("el histograma suma lo del acta", not malh, "; ".join(malh[:3]))

print(f"{'PRUEBA':<44} RESULTADO")
for nombre, ok, detalle in pruebas:
    print(f"  {nombre:<42} {'conforme' if ok else 'FALLA  ' + detalle}")
print(f"\n{len(pruebas) - len(fallas)}/{len(pruebas)} conformes")
raise SystemExit(1 if fallas else 0)
