#!/usr/bin/env python3
"""
Capa Gold: agregados listos para Tableau.

Tableau Public deja descargar el extracto a cualquiera que abra la
visualizacion, asi que el tablero nunca se conecta a la tabla de postulaciones.
Consume solo estos agregados, donde la unidad minima es la carrera y no la
persona.

Cada archivo responde una vista del tablero:

  admision_por_carrera.csv   evolucion de notas de corte y tasas
  comparador_modalidad.csv   que via de ingreso conviene, por carrera
  distribucion_puntajes.csv  perfil de admitidos y rechazados
  ocupacion_vacantes.csv     plazas ofertadas contra ingresantes reales
  trayectoria_postulante.csv cuantos insisten y con que resultado

Salida: data_normalizada/gold/
"""
import csv, os, re, statistics, unicodedata
from collections import defaultdict, Counter

RAIZ = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(RAIZ, "data_normalizada", "postulaciones.csv")
SALIDA = os.path.join(RAIZ, "data_normalizada", "gold")

# Debajo de este numero de postulaciones una tasa es ruido, no señal.
MINIMO_PARA_TASA = 15

# Una tasa de ingreso solo significa algo si el documento publico tambien a los
# rechazados. UCSM dejo de hacerlo: en 2026 solo el 9.6% de las filas son
# NO INGRESO y en 2027 ninguna. Calcular la tasa ahi daria 100% de admision en
# Medicina Humana, que es falso. El flag deja que el tablero los excluya en vez
# de mostrar una cifra sin sentido.
MINIMO_RECHAZADOS = 25.0


def fiabilidad(filas):
    """Porcentaje de rechazados del grupo y si la tasa es interpretable."""
    con = [f for f in filas if f["ingreso"]]
    if not con:
        return 0.0, "no"
    rech = sum(1 for f in con if f["ingreso"] == "0") / len(con) * 100
    return round(rech, 1), "si" if rech >= MINIMO_RECHAZADOS else "no"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def escribir(nombre, campos, filas):
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, nombre), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    print(f"  {nombre:<30} {len(filas):>6} filas")


def cargar():
    return list(csv.DictReader(open(FUENTE, encoding="utf-8")))


def por_carrera(datos):
    """Una fila por carrera y ciclo: volumen, tasa y corte."""
    g = defaultdict(list)
    for x in datos:
        if x["ingreso"]:
            g[(x["ciclo"], x["carrera"])].append(x)
    fuera = []
    for (ciclo, carrera), filas in sorted(g.items()):
        adm = sum(1 for f in filas if f["ingreso"] == "1")
        cortes = [num(f["nota_minima"]) for f in filas if num(f["nota_minima"])]
        puntajes = [num(f["total"]) for f in filas if num(f["total"])]
        pct_rech, fiable = fiabilidad(filas)
        fuera.append(dict(
            ciclo=ciclo, carrera=carrera,
            postulaciones=len(filas), ingresantes=adm,
            pct_rechazados=pct_rech, denominador_fiable=fiable,
            tasa_ingreso=round(adm / len(filas) * 100, 1)
            if len(filas) >= MINIMO_PARA_TASA and fiable == "si" else "",
            nota_corte=round(min(cortes), 4) if cortes else "",
            puntaje_min=round(min(puntajes), 2) if puntajes else "",
            puntaje_max=round(max(puntajes), 2) if puntajes else "",
            puntaje_mediana=round(statistics.median(puntajes), 2) if puntajes else ""))
    return fuera


def por_modalidad(datos):
    """La pregunta del postulante real: por que via entro mas gente."""
    g = defaultdict(list)
    for x in datos:
        if x["ingreso"]:
            g[(x["ciclo"], x["carrera"], x["modalidad"])].append(x)
    fuera = []
    for (ciclo, carrera, modalidad), filas in sorted(g.items()):
        adm = sum(1 for f in filas if f["ingreso"] == "1")
        puntajes = [num(f["total"]) for f in filas if num(f["total"])]
        admitidos = [num(f["total"]) for f in filas
                     if f["ingreso"] == "1" and num(f["total"])]
        pct_rech, fiable = fiabilidad(filas)
        fuera.append(dict(
            ciclo=ciclo, carrera=carrera, modalidad=modalidad,
            postulaciones=len(filas), ingresantes=adm,
            denominador_fiable=fiable,
            tasa_ingreso=round(adm / len(filas) * 100, 1)
            if len(filas) >= MINIMO_PARA_TASA and fiable == "si" else "",
            puntaje_min_admitido=round(min(admitidos), 2) if admitidos else "",
            puntaje_mediana=round(statistics.median(puntajes), 2) if puntajes else ""))
    return fuera


def distribucion(datos):
    """Histograma de puntajes por carrera y ciclo, separando resultado.

    El intervalo de 10 puntos es suficiente para ver la forma sin exponer
    posiciones individuales.
    """
    g = Counter()
    for x in datos:
        t = num(x["total"])
        if t is None or not x["ingreso"]:
            continue
        tramo = int(t // 10) * 10
        g[(x["ciclo"], x["carrera"], tramo,
           "ingresante" if x["ingreso"] == "1" else "no_ingresante")] += 1
    return [dict(ciclo=c, carrera=ca, tramo_desde=t, tramo_hasta=t + 10,
                 resultado=r, postulantes=n)
            for (c, ca, t, r), n in sorted(g.items())]


def cercanos_al_corte(datos):
    """Cuantos quedaron a menos de un punto. Le importa a un postulante real."""
    g = defaultdict(lambda: [0, 0])
    for x in datos:
        t, corte = num(x["total"]), num(x["nota_minima"])
        if t is None or corte is None or x["ingreso"] != "0":
            continue
        g[(x["ciclo"], x["carrera"])][0] += 1
        if corte - t <= 1.0:
            g[(x["ciclo"], x["carrera"])][1] += 1
    return [dict(ciclo=c, carrera=ca, no_ingresantes=tot, a_menos_de_un_punto=cerca,
                 porcentaje=round(cerca / tot * 100, 1) if tot else 0)
            for (c, ca), (tot, cerca) in sorted(g.items()) if tot]


def trayectoria(datos):
    """Cuantas veces postula una misma persona y como le va.

    Solo tiene sentido de 2021 a 2024: UCSM dejo de publicar el codigo del
    postulante en 2026, asi que despues no hay con que enlazar.
    """
    intentos = defaultdict(list)
    for x in datos:
        if x["postulante"] and x["ingreso"]:
            intentos[x["postulante"]].append(x)
    g = Counter()
    for persona, filas in intentos.items():
        n = len(filas)
        entro = any(f["ingreso"] == "1" for f in filas)
        g[(min(n, 5), entro)] += 1
    return [dict(postulaciones=n if n < 5 else "5 o mas",
                 ingreso_alguna_vez="si" if e else "no", personas=c)
            for (n, e), c in sorted(g.items())]


def ocupacion(datos):
    """Plazas ofertadas contra ingresantes reales, por carrera y ciclo.

    Es la metrica de gestion del conjunto: dice que carreras no llenan sus
    cupos, que es una decision de oferta academica y no un dato descriptivo.

    PROVISIONAL, no publicar en el tablero todavia. Dos cosas por resolver:

    Primero, el INGRESO de precatolica significa aprobar la seleccion del
    Centro Preuniversitario, no ocupar una plaza de la carrera. Sumarlo con los
    ordinarios cuenta dos veces la misma vacante y por eso Contabilidad 2025 da
    302% de ocupacion, que es imposible.

    Segundo, del cuadro solo se extrae la seccion presencial; la de estudios a
    distancia usa otra tabla que el extractor todavia no lee.

    Hasta cerrar ambas, la columna ocupacion sirve para ordenar carreras entre
    si, no como porcentaje absoluto.

    Solo hay cuadro de vacantes parseable de 2024 en adelante; antes el
    documento usa otro formato de tabla.
    """
    ruta = os.path.join(RAIZ, "data", "vacantes.csv")
    if not os.path.exists(ruta):
        return []
    # El cuadro de vacantes escribe 'Ingeniería Mecatrónica' y los resultados
    # 'INGENIERIA MECATRONICA'. Sin quitar tildes el cruce falla y la carrera
    # aparece con 0% de ocupacion, que es un artefacto y no un hallazgo.
    def clave(s):
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"[^A-Z0-9]", "", s.upper())

    vac = {}
    for v in csv.DictReader(open(ruta, encoding="utf-8")):
        vac[(v["ciclo"], clave(v["carrera"]))] = (int(v["total"] or 0), v["carrera"])

    ing = Counter()
    for x in datos:
        if x["ingreso"] == "1":
            ing[(x["ciclo"], clave(x["carrera"]))] += 1

    fuera = []
    for (ciclo, k), (plazas, etiqueta) in sorted(vac.items()):
        if not plazas:
            continue
        entraron = ing.get((ciclo, k), 0)
        fuera.append(dict(
            ciclo=ciclo, carrera=etiqueta, vacantes=plazas, ingresantes=entraron,
            ocupacion=round(entraron / plazas * 100, 1),
            plazas_libres=max(0, plazas - entraron),
            cruzo="si" if entraron else "no",
            estado="provisional"))
    return fuera


def main():
    datos = cargar()
    print(f"{len(datos):,} postulaciones normalizadas\n")
    escribir("admision_por_carrera.csv",
             ["ciclo", "carrera", "postulaciones", "ingresantes", "tasa_ingreso",
              "denominador_fiable", "pct_rechazados", "nota_corte",
              "puntaje_min", "puntaje_max", "puntaje_mediana"],
             por_carrera(datos))
    escribir("comparador_modalidad.csv",
             ["ciclo", "carrera", "modalidad", "postulaciones", "ingresantes",
              "tasa_ingreso", "denominador_fiable", "puntaje_min_admitido",
              "puntaje_mediana"],
             por_modalidad(datos))
    escribir("distribucion_puntajes.csv",
             ["ciclo", "carrera", "tramo_desde", "tramo_hasta", "resultado",
              "postulantes"], distribucion(datos))
    escribir("cercanos_al_corte.csv",
             ["ciclo", "carrera", "no_ingresantes", "a_menos_de_un_punto",
              "porcentaje"], cercanos_al_corte(datos))
    escribir("ocupacion_vacantes.csv",
             ["ciclo", "carrera", "vacantes", "ingresantes", "ocupacion",
              "plazas_libres", "cruzo", "estado"], ocupacion(datos))
    escribir("trayectoria_postulante.csv",
             ["postulaciones", "ingreso_alguna_vez", "personas"],
             trayectoria(datos))
    print(f"\nsalida: data_normalizada/gold/")


if __name__ == "__main__":
    main()
