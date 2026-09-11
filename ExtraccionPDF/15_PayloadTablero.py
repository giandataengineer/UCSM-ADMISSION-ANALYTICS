#!/usr/bin/env python3
"""Arma el payload JSON que consume el tablero web.

Lee la capa Gold (agregados) y, solo para la caja de cuartiles, la capa Silver
(puntajes individuales ya seudonimizados). Escribe un unico JSON en
tablero/src/data/gold.json; el navegador no toca ningun CSV.
"""
import csv, json, os, re, unicodedata
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD = os.path.join(RAIZ, "ExtraccionPDF", "data_normalizada", "gold")
SALIDA = os.path.join(RAIZ, "tablero", "src", "data", "gold.json")

# Agrupacion editorial por area, para la navegacion lateral. UCSM no publica
# esta clasificacion: se arma por afinidad academica y se rotula como tal.
AREAS = [
    ("A", "Ciencias de la Salud", [
        "MEDICINA HUMANA", "ENFERMERIA", "FARMACIA Y BIOQUIMICA", "ODONTOLOGIA",
        "OBSTETRICIA Y PUERICULTURA", "PSICOLOGIA", "MEDICINA VETERINARIA Y ZOOTECNIA",
        "TECNOLOGIA MEDICA EN TERAPIA FISICA Y REHABILITACION", "NUTRICION"]),
    ("B", "Ciencias Basicas y Biotecnologia", [
        "INGENIERIA BIOTECNOLOGICA", "INGENIERIA BIOMEDICA",
        "INGENIERIA DE INDUSTRIA ALIMENTARIA", "INGENIERIA AGRONOMICA Y AGRICOLA",
        "INGENIERIA AMBIENTAL"]),
    ("C", "Ingenierias", [
        "INGENIERIA CIVIL", "INGENIERIA DE SISTEMAS", "INGENIERIA INDUSTRIAL",
        "INGENIERIA MECANICA", "INGENIERIA MECANICA ELECTRICA", "INGENIERIA MECATRONICA",
        "INGENIERIA ELECTRONICA", "INGENIERIA DE MINAS", "ARQUITECTURA",
        "INGENIERIA EN INTELIGENCIA ARTIFICIAL", "INGENIERIA DE SEGURIDAD INDUSTRIAL Y MINERA",
        "INGENIERIA EN TELECOMUNICACIONES, REDES Y CONECTIVIDAD"]),
    ("D", "Ciencias Economico Empresariales", [
        "ADMINISTRACION DE EMPRESAS", "CONTABILIDAD", "INGENIERIA COMERCIAL",
        "ECONOMIA Y FINANZAS", "MARKETING DIGITAL", "MARKETING Y GESTION COMERCIAL",
        "ADMINISTRACION Y NEGOCIOS INTERNACIONALES", "ADMINISTRACION Y MARKETING",
        "ADMINISTRACION Y GESTION PUBLICA", "TURISMO Y GASTRONOMIA", "TURISMO Y HOTELERIA"]),
    ("E", "Ciencias Sociales y Humanidades", [
        "DERECHO", "COMUNICACION SOCIAL", "PUBLICIDAD Y MULTIMEDIA",
        "CIENCIA POLITICA Y GOBIERNO", "TRABAJO SOCIAL", "TEOLOGIA",
        "DISENO GRAFICO PUBLICITARIO", "EDUCACION INICIAL", "EDUCACION PRIMARIA",
        "EDUCACION SECUNDARIA", "APRESTAMIENTO"]),
]
AREA_DE = {c: (cod, nom) for cod, nom, cs in AREAS for c in cs}


def num(v, entero=False):
    if v is None or v == "":
        return None
    try:
        return int(float(v)) if entero else round(float(v), 2)
    except ValueError:
        return None


def clave_carrera(nombre):
    """Normaliza el nombre para cruzar tablas.

    admision_por_carrera.csv escribe MAYUSCULAS sin tilde y ocupacion_vacantes.csv
    Capitalizado con tilde. Sin esto el cruce no encuentra nada.
    """
    t = unicodedata.normalize("NFKD", nombre or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.upper().split())


def leer(nombre):
    with open(os.path.join(GOLD, nombre), encoding="utf-8") as f:
        return list(csv.DictReader(f))


carrera_rows = leer("admision_por_carrera.csv")
modalidad_rows = leer("comparador_modalidad.csv")
distrib_rows = leer("distribucion_puntajes.csv")
cercanos_rows = leer("cercanos_al_corte.csv")

ciclos = sorted({r["ciclo"] for r in carrera_rows})
carreras = sorted({r["carrera"] for r in carrera_rows})
sin_area = [c for c in carreras if c not in AREA_DE]

# --- por carrera y ciclo -----------------------------------------------------
porCarrera = []
for r in carrera_rows:
    cod, _ = AREA_DE.get(r["carrera"], ("Z", "Sin clasificar"))
    porCarrera.append([
        r["ciclo"], r["carrera"], cod,
        num(r["postulaciones"], True), num(r["ingresantes"], True),
        num(r["tasa_ingreso"]), 1 if r["denominador_fiable"] == "si" else 0,
        num(r["nota_corte_ordinario"]), r["escala"],
        num(r["puntaje_min"]), num(r["puntaje_max"]), num(r["puntaje_mediana"]),
    ])

# variacion de postulaciones contra el ciclo anterior, por carrera
post = defaultdict(dict)
for r in carrera_rows:
    post[r["carrera"]][r["ciclo"]] = int(r["postulaciones"])
delta = {}
for carrera, serie in post.items():
    años = sorted(serie)
    for i, c in enumerate(años):
        if i == 0 or serie[años[i - 1]] == 0:
            continue
        prev = serie[años[i - 1]]
        delta[f"{c}|{carrera}"] = round((serie[c] - prev) / prev * 100, 1)

# --- modalidades -------------------------------------------------------------
PRINCIPALES = ["ordinario", "precatolica", "distancia", "rendimiento_superior", "beca"]
porModalidad = defaultdict(lambda: defaultdict(int))
for r in modalidad_rows:
    if r["modalidad"] == "lista_aptos":
        continue
    m = r["modalidad"] if r["modalidad"] in PRINCIPALES else "otras"
    porModalidad[f'{r["ciclo"]}|{r["carrera"]}'][m] += int(r["ingresantes"] or 0)
modalidades = PRINCIPALES + ["otras"]

# --- distribucion de puntajes ------------------------------------------------
distrib = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for r in distrib_rows:
    clave = f'{r["ciclo"]}|{r["carrera"]}'
    idx = 0 if r["resultado"] == "ingresante" else 1
    distrib[clave][int(float(r["tramo_desde"]))][idx] += int(r["postulantes"])
distribOut = {k: sorted([[t, v[0], v[1]] for t, v in d.items()]) for k, d in distrib.items()}

# --- cercanos al corte -------------------------------------------------------
cercanos = {f'{r["ciclo"]}|{r["carrera"]}': [int(r["no_ingresantes"]),
            int(r["a_menos_de_un_punto"]), float(r["porcentaje"])] for r in cercanos_rows}


# --- boxplot de puntajes de ingresantes, desde la capa silver -----------------
SILVER = os.path.join(RAIZ, "ExtraccionPDF", "data_normalizada", "postulaciones.csv")

def cuantil(orden, p):
    if not orden:
        return None
    k = (len(orden) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(orden) - 1)
    return round(orden[lo] + (orden[hi] - orden[lo]) * (k - lo), 1)

puntajes = defaultdict(list)
with open(SILVER, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["ingreso"] != "1":
            continue
        try:
            t = float(r["total"])
        except (TypeError, ValueError):
            continue
        puntajes[f'{r["ciclo"]}|{r["carrera"]}'].append(t)

MAX_PUNTOS = 40
caja = {}
for clave, vals in puntajes.items():
    vals.sort()
    n = len(vals)
    if n < 5:
        continue
    # muestreo por cuantiles: conserva la forma de la distribucion sin llevar
    # las 69 652 filas al navegador.
    paso = max(1, n // MAX_PUNTOS)
    puntos = [round(v, 1) for v in vals[::paso]][:MAX_PUNTOS]
    caja[clave] = {
        "n": n,
        "min": round(vals[0], 1),
        "q1": cuantil(vals, 0.25),
        "med": cuantil(vals, 0.5),
        "q3": cuantil(vals, 0.75),
        "max": round(vals[-1], 1),
        "puntos": puntos,
    }

carreras_norm = {clave_carrera(c): c for c in carreras}
vacantes = {}
vacantes_sin_cruce = []
with open(os.path.join(GOLD, "ocupacion_vacantes.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        v = num(r["ocupacion"])
        if v is None:
            continue
        oficial = carreras_norm.get(clave_carrera(r["carrera"]))
        if oficial is None:
            # El cuadro de vacantes trae nombres truncados ("Medicina Veterinaria y").
            # No se adivina a que carrera corresponden: se reportan y se dejan fuera.
            vacantes_sin_cruce.append(f'{r["ciclo"]}|{r["carrera"]}')
            continue
        vacantes[f'{r["ciclo"]}|{oficial}'] = [v, r["estado"]]

payload = {
    "ciclos": ciclos,
    "carreras": carreras,
    "areas": [{"cod": c, "nombre": n} for c, n, _ in AREAS],
    "modalidades": modalidades,
    "porCarrera": porCarrera,
    "delta": delta,
    "porModalidad": {k: [v.get(m, 0) for m in modalidades] for k, v in porModalidad.items()},
    "distrib": distribOut,
    "cercanos": cercanos,
    "caja": caja,
    "vacantes": vacantes,
}

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

print(f"ciclos      : {len(ciclos)}")
print(f"carreras    : {len(carreras)}  sin area: {sin_area or 'ninguna'}")
print(f"porCarrera  : {len(porCarrera)} filas")
print(f"modalidades : {len(porModalidad)} combinaciones")
print(f"distrib     : {len(distribOut)} combinaciones")
print(f"caja        : {len(caja)} combinaciones")
print(f"vacantes    : {len(vacantes)} cruzadas, {len(vacantes_sin_cruce)} sin cruce")
for x in vacantes_sin_cruce:
    print(f"  sin cruce : {x}")
print(f"bytes       : {os.path.getsize(SALIDA):,}")
