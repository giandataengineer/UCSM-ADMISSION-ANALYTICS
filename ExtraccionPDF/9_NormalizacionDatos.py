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
import csv, glob, hashlib, hmac, os, re, unicodedata
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
    r"^TRASLADO|^PRIMEROS PUESTOS|^GRADUADO|NOMBRES|^$")

# Abreviaturas que aparecen cuando la celda es angosta.
ABREVIATURAS = [
    (r"^ING\.\s+", "INGENIERIA "),
    (r"^ADM\.\s+", "ADMINISTRACION "),
    (r"^EDUC\.\s+", "EDUCACION "),
    (r"^TEC\.\s+", "TECNOLOGIA "),
]

CONDICION = {
    "INGRESO": "ingreso", "SELECCIONADO": "ingreso", "APTO": "ingreso",
    "NO INGRESO": "no_ingreso", "NO SELECCIONADO": "no_ingreso",
    "NO APTO": "no_ingreso",
    "NSP": "no_se_presento", "NC": "no_corresponde",
    "NIVELACION": "nivelacion", "TEST + ENTREVISTA": "test_entrevista",
    "OBSERVADO": "observado", "RETIRADO": "retirado",
}

MODALIDAD = {
    "tercio_superior": "rendimiento_superior",   # renombrada en 2024
    "lista_aptos": "lista_aptos",
}


def limpiar(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"\(V\s*\d*\)?", "", s)          # sufijo de version del plan
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


def catalogo_carreras(filas):
    """Construye la lista canonica y el mapa de truncados.

    Un nombre truncado es prefijo de su forma completa: la fuente corta la
    cadena al ancho de la celda, no la abrevia. Asi que basta buscar, entre las
    formas largas, la unica que empieza igual.
    """
    cuenta = Counter(f["carrera_limpia"] for f in filas if f["carrera_limpia"])
    formas = [c for c in cuenta if not NO_ES_CARRERA.search(c) and len(c) >= 5]
    largas = sorted(formas, key=len, reverse=True)

    mapa = {}
    for forma in formas:
        candidatas = [L for L in largas if L != forma and L.startswith(forma)]
        # Solo se resuelve si hay una unica forma larga compatible: con dos, el
        # truncamiento es ambiguo y se deja como esta en vez de adivinar.
        mapa[forma] = candidatas[0] if len(candidatas) == 1 else forma
    return mapa


def seudonimo(codigo):
    if not codigo or not codigo.isdigit():
        return ""
    return hmac.new(SAL, codigo.encode(), hashlib.sha256).hexdigest()[:16]


CAMPOS = ["ciclo", "archivo", "proceso", "modalidad", "fecha_examen", "carrera",
          "postulante", "orden_merito", "nota_01", "nota_02", "total",
          "condicion", "ingreso", "nota_minima"]


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

    mapa = catalogo_carreras(crudas)

    filas, descartadas = [], 0
    for x in crudas:
        carrera = mapa.get(x["carrera_limpia"], x["carrera_limpia"])
        if not carrera or NO_ES_CARRERA.search(carrera) or texto_corrupto(carrera):
            descartadas += 1
            continue
        m = manifiesto.get(x["archivo"], {})
        cond = CONDICION.get(limpiar(x.get("condicion", "")), "")
        modalidad = m.get("tipo", "")
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
            condicion=cond,
            # Campo derivado: 1 si entro, 0 si no, vacio si el documento no
            # publica condicion. Separar el vacio del cero evita contar como
            # rechazado a quien nunca tuvo esa columna.
            ingreso={"ingreso": "1", "no_ingreso": "0"}.get(cond, ""),
            nota_minima=x.get("nota_minima", "")))

    os.makedirs(SALIDA, exist_ok=True)
    destino = os.path.join(SALIDA, "postulaciones.csv")
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)

    resueltos = sum(1 for k, v in mapa.items() if k != v)
    print(f"filas normalizadas : {len(filas):,}")
    print(f"descartadas        : {descartadas} (titulos leidos como carrera)")
    print(f"carreras canonicas : {len({f['carrera'] for f in filas})}")
    print(f"truncados resueltos: {resueltos}")
    print(f"con seudonimo      : {sum(1 for f in filas if f['postulante']):,}")
    print(f"\nsalida: data_normalizada/postulaciones.csv")
    return filas


if __name__ == "__main__":
    main()
