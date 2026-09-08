#!/usr/bin/env python3
"""
Capa Silver: unifica los siete esquemas en uno y aplica seudonimizacion.

Cuatro conciliaciones, cada una obligada por un cambio real de la fuente:

  Carrera    El nombre viene truncado cuando la celda es angosta
             ('ADMINISTRACION Y NEGOCIOS INTERNACI') y a veces con sufijo de
             version del plan ('CONTABILIDAD (V6)'). Se resuelve contra el
             catalogo de formas largas.

  Condicion  Cada proceso usa su vocabulario para lo mismo: los ordinarios
             dicen INGRESO, los de seleccion previa SELECCIONADO. Sin unificar,
             la tasa de admision de precatolica sale en cero.

  Modalidad  Tercio Superior se llamo Rendimiento Superior desde 2024 sin
             cambiar de sitio en el calendario. Sin unificar, la serie muestra
             una modalidad que muere en 2023 y otra que nace en 2024.

  Identidad  El nombre se descarta y el codigo se reemplaza por un HMAC. Eso
             conserva la trazabilidad de una misma persona entre procesos, que
             es lo que habilita el analisis de cohortes, sin exponer a nadie.

Salida: data_normalizada/postulaciones.csv
"""
import csv, difflib, glob, hashlib, hmac, os, re, unicodedata
from collections import Counter

RAIZ = os.path.dirname(os.path.abspath(__file__))
ENTRADA = os.path.join(RAIZ, "data_extraida")
SALIDA = os.path.join(RAIZ, "data_normalizada")

# La sal vive fuera del repo. Sin ella el seudonimo no se puede revertir ni
# recomputar, que es justamente lo que se busca.
SAL = os.environ.get("UCSM_SAL", "").encode() or b"desarrollo-cambiar-en-produccion"

# Texto que el parser toma por carrera y no lo es: rotulos de encabezado que
# quedan a la altura de la celda, y nombres de modalidad.
NO_ES_CARRERA = re.compile(
    r"RESULTADO|POSTULANTES|AREA DE CIENCIAS|ESCUELA PROFESIONAL|APELLIDOS|"
    r"TRASLADO|PRIMEROS PUESTOS|GRADUADO|NOMBRES|CONVENIO|DEPORTISTAS|^$")

# Abreviaturas que aparecen cuando la celda es angosta.
ABREVIATURAS = [
    (r"^ING\.\s+", "INGENIERIA "),
    (r"^ADM\.\s+", "ADMINISTRACION "),
    (r"^EDUC\.\s+", "EDUCACION "),
    (r"^TEC\.\s+", "TECNOLOGIA "),
    (r"^MED\.\s+", "MEDICINA "),
    (r"^ARQ\.\s+", "ARQUITECTURA "),
]

# 'APTO' significa dos cosas distintas segun el documento, asi que se traduce
# con dos diccionarios y no con uno. Ver listas_de_aptitud().
APTITUD = {"APTO": "apto_para_rendir", "NO APTO": "no_apto",
           "OBSERVADO": "observado", "RECHAZADO": "rechazado"}

CONDICION = {
    "INGRESO": "ingreso", "SELECCIONADO": "ingreso", "APTO": "ingreso",
    "NO INGRESO": "no_ingreso", "NO SELECCIONADO": "no_ingreso",
    "NO APTO": "no_ingreso",
    "NSP": "no_se_presento", "NC": "no_corresponde",
    "NIVELACION": "nivelacion", "TEST + ENTREVISTA": "test_entrevista",
    "OBSERVADO": "observado", "RETIRADO": "retirado",
}

# UCSM cambio la escala de calificacion en el ciclo 2024: la mediana del examen
# ordinario pasa de 76.6 a 152.7 y 26 de 34 carreras saltan en esa misma
# transicion. No es un error de extraccion, es un cambio institucional.
#
# La consecuencia practica es que un puntaje de 2023 y uno de 2024 no se pueden
# comparar. Por eso se publica ademas el percentil dentro del propio proceso y
# carrera, que es invariante a la escala y permite series de siete ciclos.
CICLO_CAMBIO_ESCALA = "2024"

MODALIDAD = {
    "tercio_superior": "rendimiento_superior",   # renombrada en 2024
    "lista_aptos": "lista_aptos",
}


def limpiar(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"\(V\s*\d*\)?", "", s)          # sufijo de version del plan
    # En 2023CCI-I el puntaje se imprime a continuacion de la carrera y sin
    # separador de celda, asi que llega pegado al nombre.
    s = re.sub(r"\s+\d+[.,]\d+\s*$", "", s)
    s = re.sub(r"\s+", " ", s.upper()).strip()
    for patron, expansion in ABREVIATURAS:
        s = re.sub(patron, expansion, s)
    return s


def texto_corrupto(s):
    """Detecta cadenas donde dos lineas del PDF quedaron superpuestas.

    Al solaparse producen secuencias sin vocales o con consonantes imposibles
    en español, como 'RETHRAABSLIALDITOA'. Descartar la fila es preferible a
    guardar una carrera que no existe.
    """
    for palabra in s.split():
        if len(palabra) >= 12 and not re.search(r"[AEIOU]{1}[^AEIOU]{1}[AEIOU]", palabra):
            return True
        if re.search(r"[BCDFGHJKLMNPQRSTVWXYZ]{5}", palabra):
            return True
    return False


def catalogo_oficial():
    """Las carreras que UCSM convoco, leidas del propio corpus de encabezados.

    Es la referencia contra la que se resuelven truncados y variantes. Usar una
    lista autoritativa en vez del propio texto extraido evita dos errores que
    aparecieron al hacerlo al reves: 'MEDICINA HUMANA' resolviendose hacia
    'MEDICINA HUMANA TRASLADO INTERNO II', que era contaminacion de modalidad, y
    cadenas corruptas por lineas superpuestas quedandose como carreras validas.
    """
    ruta = os.path.join(RAIZ, "data", "carreras_por_ciclo.csv")
    if not os.path.exists(ruta):
        return []
    return sorted({limpiar(f["carrera"]) for f in csv.DictReader(
        open(ruta, encoding="utf-8")) if f.get("carrera")}, key=len, reverse=True)


def catalogo_carreras(filas):
    """Mapea cada forma observada a su carrera del catalogo.

    La fuente corta el nombre al ancho de la celda, asi que un truncado es
    prefijo de su forma completa. Se busca en el catalogo, no entre las formas
    observadas, y solo se acepta cuando hay una unica coincidencia.
    """
    oficiales = catalogo_oficial()
    cuenta = Counter(f["carrera_limpia"] for f in filas if f["carrera_limpia"])

    mapa = {}
    for forma in cuenta:
        if not forma or NO_ES_CARRERA.search(forma) or len(forma) < 5:
            continue
        if forma in oficiales:
            mapa[forma] = forma
            continue
        candidatas = [o for o in oficiales if o.startswith(forma)]
        if len(candidatas) == 1:
            mapa[forma] = candidatas[0]
            continue
        # La fuente trae erratas propias: 'INGENIERIA BIIOTECNOLOGICA' con dos
        # ies, 'INGENIERIA BIOTECNOLOGIA' sin la ca. No son truncados, asi que
        # el prefijo no las resuelve. Se acepta la carrera del catalogo mas
        # parecida solo con un umbral alto, que a esta distancia solo alcanza
        # una errata de un par de letras y nunca otra carrera.
        cerca = difflib.get_close_matches(forma, oficiales, n=1, cutoff=0.92)
        mapa[forma] = cerca[0] if cerca else forma
    return mapa


def listas_de_aptitud(crudas):
    """Documentos que dicen quien puede rendir el examen, no quien ingreso.

    En un acta de resultados 'APTO' se opone a 'NO INGRESO' y quiere decir
    admitido. En una lista previa se opone a 'NO APTO' y solo dice que la
    persona reune los requisitos para presentarse. Es la misma palabra sobre
    dos hechos distintos, y tratarlos igual sumaba 414 admisiones inexistentes.

    La distincion sale del vocabulario que usa cada documento y no del nombre
    del archivo: hay listas de aptitud que no se llaman 'Aptos' y actas que si.
    """
    vocabulario = {}
    for x in crudas:
        vocabulario.setdefault(x["archivo"], set()).add(
            limpiar(x.get("condicion", "")))
    por_vocabulario = {
        archivo for archivo, v in vocabulario.items()
        if "NO APTO" in v
        or ("APTO" in v and not {"INGRESO", "NO INGRESO", "SELECCIONADO"} & v)}

    # El vocabulario no alcanza cuando el documento no publica columna de
    # condicion, que es el caso de las listas de no aptos. Para esos vale lo
    # que el propio PDF declara en su portada, que el parser ya registro.
    ruta = os.path.join(ENTRADA, "_resumen.csv")
    por_portada = set()
    if os.path.exists(ruta):
        por_portada = {r["archivo"] for r in csv.DictReader(open(ruta, encoding="utf-8"))
                       if r.get("clase") == "lista_aptitud"}
    return por_vocabulario | por_portada


def seudonimo(codigo):
    if not codigo or not codigo.isdigit():
        return ""
    return hmac.new(SAL, codigo.encode(), hashlib.sha256).hexdigest()[:16]


CAMPOS = ["ciclo", "archivo", "proceso", "modalidad", "fecha_examen", "carrera",
          "postulante", "orden_merito", "nota_01", "nota_02", "total",
          "percentil", "escala", "condicion", "ingreso", "nota_minima"]


def agregar_percentil(filas):
    """Anade la posicion relativa del puntaje dentro de su proceso y carrera.

    Se calcula sobre el grupo mas chico que comparte examen y escala, que es
    la combinacion de archivo y carrera. Un percentil 90 significa lo mismo en
    2021 que en 2027, cosa que el puntaje bruto no cumple.
    """
    grupos = {}
    for f in filas:
        t = f["total"]
        try:
            valor = float(t)
        except (TypeError, ValueError):
            continue
        grupos.setdefault((f["archivo"], f["carrera"]), []).append(valor)
    for clave in grupos:
        grupos[clave].sort()

    for f in filas:
        try:
            valor = float(f["total"])
        except (TypeError, ValueError):
            f["percentil"] = ""
            continue
        orden = grupos[(f["archivo"], f["carrera"])]
        if len(orden) < 5:
            f["percentil"] = ""
            continue
        debajo = sum(1 for v in orden if v < valor)
        f["percentil"] = round(debajo / len(orden) * 100, 1)
    return filas


def main():
    manifiesto = {r["archivo"]: r for r in csv.DictReader(
        open(os.path.join(RAIZ, "data", "manifest.csv"), encoding="utf-8"))}

    crudas = []
    for ruta in sorted(glob.glob(os.path.join(ENTRADA, "*", "*.csv"))):
        ciclo = os.path.basename(os.path.dirname(ruta))
        for x in csv.DictReader(open(ruta, encoding="utf-8")):
            x["ciclo"] = ciclo
            x["carrera_limpia"] = limpiar(x.get("carrera", ""))
            crudas.append(x)

    aptitud = listas_de_aptitud(crudas)
    mapa = catalogo_carreras(crudas)
    oficiales = set(catalogo_oficial())
    resueltas = set(mapa.values()) & oficiales

    filas, descartadas = [], Counter()
    for x in crudas:
        carrera = mapa.get(x["carrera_limpia"], x["carrera_limpia"])
        # Fuera del catalogo y sin resolver: es ruido de extraccion, no una
        # carrera que UCSM haya convocado.
        if carrera and carrera not in oficiales and carrera not in resueltas:
            descartadas[x["archivo"]] += 1
            continue
        if not carrera or NO_ES_CARRERA.search(carrera) or texto_corrupto(carrera):
            descartadas[x["archivo"]] += 1
            continue
        m = manifiesto.get(x["archivo"], {})
        es_aptitud = x["archivo"] in aptitud
        tabla = APTITUD if es_aptitud else CONDICION
        cond = tabla.get(limpiar(x.get("condicion", "")), "")
        modalidad = "lista_aptos" if es_aptitud else m.get("tipo", "")
        filas.append(dict(
            ciclo=x["ciclo"], archivo=x["archivo"],
            proceso=m.get("proceso", ""),
            modalidad=MODALIDAD.get(modalidad, modalidad),
            fecha_examen=m.get("fecha_examen", ""),
            carrera=carrera,
            postulante=seudonimo(x.get("codigo", "")),
            orden_merito=x.get("orden", ""),
            nota_01=x.get("nota_01", ""), nota_02=x.get("nota_02", ""),
            total=x.get("total", ""),
            escala=("nueva" if x["ciclo"] >= CICLO_CAMBIO_ESCALA else "anterior"),
            percentil="",
            condicion=cond,
            # Campo derivado: 1 si entro, 0 si no, vacio si el documento no
            # publica condicion. Separar el vacio del cero evita contar como
            # rechazado a quien nunca tuvo esa columna.
            ingreso={"ingreso": "1", "no_ingreso": "0"}.get(cond, ""),
            nota_minima=x.get("nota_minima", "")))

    filas = agregar_percentil(filas)

    os.makedirs(SALIDA, exist_ok=True)
    destino = os.path.join(SALIDA, "postulaciones.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)

    resueltos = sum(1 for k, v in mapa.items() if k != v)
    print(f"filas normalizadas : {len(filas):,}")
    print(f"descartadas        : {sum(descartadas.values())} "
          f"(sin carrera reconocible)")
    print(f"carreras canonicas : {len({f['carrera'] for f in filas})}")
    print(f"truncados resueltos: {resueltos}")
    print(f"con seudonimo      : {sum(1 for f in filas if f['postulante']):,}")
    print(f"listas de aptitud  : {len(aptitud)} documentos, "
          f"{sum(1 for f in filas if f['modalidad'] == 'lista_aptos'):,} filas "
          f"(no cuentan como admision)")
    # Se registra por archivo para que la auditoria pueda separar lo que se
    # cae de un acta de resultados, que es una perdida, de lo que se cae de una
    # lista de aptitud, cuya columna de carrera trae texto del encabezado.
    with open(os.path.join(SALIDA, "_descartes.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "descartadas"])
        w.writerows(sorted(descartadas.items()))

    print(f"\nsalida: data_normalizada/postulaciones.csv")
    return filas


if __name__ == "__main__":
    main()
