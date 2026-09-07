#!/usr/bin/env python3
"""
Pruebas de calidad sobre las capas Silver y Gold.

La reconciliacion de 11_Validacion.py compara cada fila contra el PDF del que
salio. Estas pruebas miran mas arriba: que las capas derivadas sean coherentes
entre si y con el mundo.

  referencial   toda fila apunta a un archivo y ciclo que existen
  temporal      la fecha del examen cae en la ventana de su ciclo
  reconciliacion los agregados de Gold suman lo mismo que Silver
  seudonimo     un codigo da siempre el mismo hash y no hay colisiones
  distribucion  los puntajes no dan saltos imposibles entre ciclos
  idempotencia  reejecutar la normalizacion produce el mismo archivo

Las cinco primeras se apoyan en los cinco pilares de observabilidad de Moses,
Gavish y Vorwerck: frescura, volumen, esquema, linaje y distribucion.

Uso: python ExtraccionPDF/13_PruebasCalidad.py
"""
import csv, hashlib, os, statistics, subprocess, sys
from collections import Counter, defaultdict

RAIZ = os.path.dirname(os.path.abspath(__file__))
SILVER = os.path.join(RAIZ, "data_normalizada", "postulaciones.csv")
GOLD = os.path.join(RAIZ, "data_normalizada", "gold")

resultados = []


def prueba(nombre, incumplen, detalle=""):
    ok = not incumplen
    resultados.append((nombre, len(incumplen) if incumplen else 0))
    print(f"  {'ok    ' if ok else 'FALLA '} {nombre}")
    if not ok:
        print(f"         {len(incumplen)} casos{'  ' + detalle if detalle else ''}")
        for x in list(incumplen)[:3]:
            print(f"           {x}")


def leer(ruta):
    return list(csv.DictReader(open(ruta, encoding="utf-8"))) if os.path.exists(ruta) else []


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def referencial(silver, manifiesto):
    archivos = {m["archivo"] for m in manifiesto}
    prueba("referencial: cada fila viene de un archivo del manifiesto",
           {x["archivo"] for x in silver if x["archivo"] not in archivos})

    ciclos_validos = {m["ciclo"] for m in manifiesto if m["ciclo"]}
    prueba("referencial: cada ciclo existe en el manifiesto",
           {x["ciclo"] for x in silver if x["ciclo"] not in ciclos_validos})


def temporal(silver):
    """El examen de un ciclo se rinde entre abril del año anterior y agosto del
    propio. Fuera de esa ventana, o el ciclo esta mal asignado o la fecha se
    leyo de otra parte de la pagina."""
    fuera = set()
    for x in silver:
        f, c = x["fecha_examen"], x["ciclo"]
        if not f or not c or len(f) != 10:
            continue
        anio, mes = int(f[6:]), int(f[3:5])
        objetivo = int(c)
        if anio == objetivo - 1 and mes >= 4:
            continue
        if anio == objetivo and mes <= 8:
            continue
        fuera.add((x["archivo"], f, c))
    prueba("temporal: la fecha del examen cae en la ventana de su ciclo", fuera)


def reconciliacion(silver):
    """Gold no puede tener mas ingresantes que Silver ni inventar carreras."""
    gold = leer(os.path.join(GOLD, "admision_por_carrera.csv"))
    if not gold:
        prueba("reconciliacion: existe el agregado por carrera", ["falta el archivo"])
        return

    real = Counter()
    for x in silver:
        if x["ingreso"] == "1":
            real[(x["ciclo"], x["carrera"])] += 1

    desvios = set()
    for g in gold:
        clave = (g["ciclo"], g["carrera"])
        if int(g["ingresantes"]) != real.get(clave, 0):
            desvios.add((clave, g["ingresantes"], real.get(clave, 0)))
    prueba("reconciliacion: los ingresantes de Gold coinciden con Silver", desvios)

    carreras_gold = {g["carrera"] for g in gold}
    carreras_silver = {x["carrera"] for x in silver}
    prueba("reconciliacion: Gold no inventa carreras",
           carreras_gold - carreras_silver)


def seudonimizacion(silver):
    """El hash debe ser estable y no debe colisionar.

    Se comprueba que cada seudonimo aparezca siempre con el mismo largo y que
    el numero de seudonimos distintos sea plausible frente al de filas: una
    colision masiva se veria como muchas menos personas de las esperadas.
    """
    seudos = {x["postulante"] for x in silver if x["postulante"]}
    prueba("seudonimo: todos tienen el largo esperado",
           {s for s in seudos if len(s) != 16})

    con = sum(1 for x in silver if x["postulante"])
    ratio = len(seudos) / con if con else 0
    # Una persona postula varias veces, asi que el ratio esperado esta bien
    # por debajo de 1. Por debajo de 0.3 habria que sospechar de colisiones.
    prueba("seudonimo: proporcion de personas unicas plausible",
           [] if ratio >= 0.3 else [f"ratio {ratio:.2f}"])

    prueba("seudonimo: ningun nombre sobrevive en la salida",
           [c for c in (silver[0].keys() if silver else []) if "nombre" in c.lower()])


def distribucion(silver):
    """La mediana de puntaje de una carrera no puede multiplicarse de un ciclo
    al siguiente sin que haya cambiado la escala. Se avisa donde ocurre para
    que el tablero lo anote, no para bloquear."""
    por = defaultdict(list)
    for x in silver:
        t = num(x["total"])
        if t is not None and x["modalidad"] == "ordinario":
            por[(x["carrera"], x["ciclo"])].append(t)

    saltos = set()
    carreras = {c for c, _ in por}
    for carrera in carreras:
        ciclos = sorted(c for ca, c in por if ca == carrera)
        for a, b in zip(ciclos, ciclos[1:]):
            ma = statistics.median(por[(carrera, a)])
            mb = statistics.median(por[(carrera, b)])
            if ma > 0 and (mb / ma > 1.8 or mb / ma < 0.55):
                saltos.add((carrera[:28], f"{a}->{b}", round(ma, 1), round(mb, 1)))
    prueba("distribucion: sin saltos de mediana entre ciclos consecutivos",
           saltos, "(cambio de escala de calificacion)")


def idempotencia():
    """Reejecutar la normalizacion debe producir un archivo identico.

    Si no lo hace, hay algo no determinista en el pipeline (orden de lectura,
    hash sin sal fija, iteracion sobre un set) y los resultados dejan de ser
    reproducibles.
    """
    if not os.path.exists(SILVER):
        prueba("idempotencia: la normalizacion es reproducible", ["falta Silver"])
        return
    antes = hashlib.sha256(open(SILVER, "rb").read()).hexdigest()
    subprocess.run([sys.executable, os.path.join(RAIZ, "9_NormalizacionDatos.py")],
                   capture_output=True)
    despues = hashlib.sha256(open(SILVER, "rb").read()).hexdigest()
    prueba("idempotencia: la normalizacion es reproducible",
           [] if antes == despues else [f"{antes[:12]} != {despues[:12]}"])


def main():
    silver = leer(SILVER)
    manifiesto = leer(os.path.join(RAIZ, "data", "manifest.csv"))
    if not silver:
        print("no hay datos normalizados")
        return 1

    print(f"PRUEBAS DE CALIDAD · {len(silver):,} filas en Silver\n")
    referencial(silver, manifiesto)
    temporal(silver)
    reconciliacion(silver)
    seudonimizacion(silver)
    distribucion(silver)
    idempotencia()

    fallidas = sum(1 for _, n in resultados if n)
    print(f"\n{len(resultados) - fallidas}/{len(resultados)} pruebas aprobadas")

    destino = os.path.join(RAIZ, "data_normalizada", "_calidad.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prueba", "casos_que_incumplen"])
        w.writerows(resultados)
    print(f"informe: data_normalizada/_calidad.csv")
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main())
