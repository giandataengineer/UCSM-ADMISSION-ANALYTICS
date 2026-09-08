#!/usr/bin/env python3
"""
Reconstruye las tablas de resultados a partir de la geometria de la pagina.

Un PDF no contiene tablas: contiene caracteres con coordenadas. La fila existe
solo porque varios textos comparten altura, y la columna porque comparten
posicion horizontal. Este modulo recompone ambas cosas.

El metodo, en orden:

  1. Agrupar caracteres por coordenada Y  -> lineas
  2. Partir cada linea en palabras por separacion horizontal
  3. Localizar la linea de encabezado, la que trae 'Ord.' y 'Nombre'
  4. Tomar la posicion X de cada encabezado como ancla de columna
  5. Asignar cada palabra de las filas siguientes a su ancla mas cercana

El paso 4 es el que hace que funcione con los siete esquemas distintos: no se
asume que columnas hay ni en que orden, se leen del propio encabezado. Cuando
UCSM publique el octavo esquema, el parser lo detecta en vez de romperse.

Salida: data_extraida/<ciclo>/<archivo>.csv  +  data_extraida/_resumen.csv
"""
import csv, os, re, sys, unicodedata
from concurrent.futures import ProcessPoolExecutor

import pdfplumber

RAIZ = os.path.dirname(os.path.abspath(__file__))
CRUDO = os.path.join(RAIZ, "data", "raw")
SALIDA = os.path.join(RAIZ, "data_extraida")

# 8 procesos: medido en bench_paralelismo.py, ver ADR-001
PROCESOS = 8

# Tolerancia vertical para considerar que dos caracteres estan en la misma fila.
# Los PDFs de admision usan interlineado de ~13pt, asi que 2.5 separa filas sin
# partir una sola por el redondeo del renderizador.
TOL_FILA = 2.5

# Separacion horizontal minima para cortar dos palabras. Menor que el espacio
# entre columnas y mayor que el espacio entre palabras de un nombre.
CORTE_PALABRA = 2.2
# Margen para buscar el hueco real alrededor del borde de una columna.
CERCA_DEL_BORDE = 8

# Cada tipo de proceso usa su propio vocabulario para el mismo concepto:
# los ordinarios dicen INGRESO, los de seleccion previa SELECCIONADO, y las
# listas de aptos APTO. El normalizador los unifica despues.
# El orden importa: los terminos compuestos van antes que los simples, porque
# la deteccion es por contencion y 'NO INGRESO' contiene 'INGRESO'.
CONDICIONES = [
    "INGR NO BENEF", "NO SELECCIONADO", "NO INGRESO", "NO APTO",
    "TEST + ENTREVISTA", "SELECCIONADO", "NIVELACION", "OBSERVADO",
    "RECHAZADO", "RETIRADO", "INGRESO", "APTO", "NSP", "NC",
]


def condicion_de(texto):
    """Extrae la condicion reconocida de dentro del texto de la celda.

    No basta comparar por igualdad: la celda llega con arrastre de columnas
    vecinas, como 'MEDICINA HUMANA INGRESO' cuando la escuela se derrama, o
    '84.6500 APTO' cuando lo hace el puntaje. Buscar el termino dentro del
    texto recupera esas filas en vez de descartarlas.

    Devuelve cadena vacia si no hay ninguno, que es distinto de no tener
    columna de condicion.
    """
    t = (texto or "").upper()
    for c in CONDICIONES:
        if c in t:
            return c
    return ""

# Encabezado publicado -> nombre de campo. UCSM cambio la etiqueta del examen
# varias veces sin cambiar su significado.
CAMPOS = {
    "Ord.": "orden", "Orden": "orden",
    "Código": "codigo", "Codigo": "codigo",
    "Nombre": "nombre",
    "Nota 01": "nota_01", "Nota 1": "nota_01", "Exam 1": "nota_01",
    "Nota 02": "nota_02", "Nota 2": "nota_02", "Exam 2": "nota_02",
    "Nota": "total",
    # Precatolica 2025 agrega un componente sobre los dos habituales. Sin
    # declararlo, su columna se descartaba del encabezado y las siguientes se
    # corrian una posicion.
    "Adic": "nota_adicional", "Adicional": "nota_adicional",
    "Total": "total", "TOTAL": "total", "Puntaje": "total",
    "Condición": "condicion", "Condicion": "condicion",
    "RESULTADO": "condicion", "Resultado": "condicion",
    # Familia Excel/Word: la carrera va como columna, no como titulo de bloque
    "Escuela": "escuela", "ESCUELA PROFESIONAL": "escuela",
    "N°": "orden", "Nº": "orden",
    "DMI": "codigo", "DNI": "codigo",
    "APELLIDOS Y NOMBRES": "nombre",
    # Los documentos del area de salud y los de convenio rotulan en mayusculas.
    # Sin declararlos no se reconocia su encabezado y 12 PDFs de resultados
    # entre 2021 y 2023 no producian ni una fila.
    "NOMBRE": "nombre", "NOMBRES": "nombre",
    "CONDICIÓN": "condicion", "CONDICION": "condicion",
    "PUNTAJE FINAL": "total", "PUNTAJE": "total",
    "MODALIDAD": "modalidad", "INSTITUCIÓN EDUCATIVA": "institucion",
    "Opc": "opcion", "Opción": "opcion",
    # Los documentos de aptos parten el encabezado en varias lineas y usan
    # rotulos largos propios.
    "ORDEN DE MERITO": "orden", "ORDEN DE MÉRITO": "orden",
    "PROMEDIO": "total", "PROMEDIO NOTAS SEGÚN": "total",
    "EQUIVALENCIA DEL PROMEDIO": "equivalencia",
}

# La postulacion NO entra aca: es un valor legitimo del grupo, no ruido.
RUIDO = {
    "Universidad Católica de Santa María", "Dirección de Admisión",
    "Fecha:", "Pág.:",
}

# Un documento repite la misma carrera muchas veces, una por sede y grupo, y
# cada bloque reinicia el orden de merito desde 1. Sin estas dos dimensiones el
# grano queda mal definido: precatolica2021-I trae MEDICINA HUMANA en 16
# bloques distintos y todos con un orden 6, que parecen duplicados y no lo son.
#
# Lo que va tras el guion en la linea del proceso separa bloques, pero no
# siempre es lo mismo: en precatolica es la sede ('- AREQUIPA', '- ILO') y en
# los extraordinarios la submodalidad ('- DEPORTISTAS DESTACADOS',
# '- GRADUADO O PROFESIONAL UNIVERSITARIO'). Se guarda tal cual bajo un nombre
# que no promete de mas, porque para el grano ambos cumplen la misma funcion.
#
# Sin limite de largo: acotarlo a 24 caracteres dejaba fuera
# 'GRADUADO O PROFESIONAL UNIVERSITARIO' y sus bloques se mezclaban con los de
# deportistas, dando 39 filas donde el documento declaraba 24.
# Se excluyen los numerales romanos: 'PRECATOLICA 2026-III' termina en '- III'
# y sin este filtro el numero de proceso se guardaba como si fuera una ciudad.
ROMANOS = {"I", "II", "III", "IV", "V"}
SEDE = re.compile(r"-\s*([A-ZÑÁÉÍÓÚ][A-ZÑÁÉÍÓÚ ]{2,})\s*$")
LINEA_PROCESO = re.compile(r"EXAMEN|PRECATOLICA|CONCURSO|ADMISION|EXTRAORD", re.I)


def normalizar(s):
    """Quita tildes y espacios repetidos. Para comparar, no para guardar."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def lineas_de(pagina):
    """Agrupa los caracteres de la pagina en lineas y cada linea en palabras.

    Devuelve [(y, [(texto, x0, x1), ...]), ...] ordenado de arriba hacia abajo.
    """
    filas = []
    for c in sorted(pagina.chars, key=lambda c: (c["top"], c["x0"])):
        if filas and abs(c["top"] - filas[-1][0]) <= TOL_FILA:
            filas[-1][1].append(c)
        else:
            filas.append((c["top"], [c]))

    fuera = []
    for y, chars in filas:
        chars.sort(key=lambda c: c["x0"])
        palabras, actual = [], [chars[0]]
        for previo, siguiente in zip(chars, chars[1:]):
            if siguiente["x0"] - previo["x1"] > CORTE_PALABRA:
                palabras.append(actual)
                actual = [siguiente]
            else:
                actual.append(siguiente)
        palabras.append(actual)
        # Se conservan los caracteres de cada palabra: hacen falta para poder
        # partirla despues si resulta que cruza el borde de una columna.
        fuera.append((y, [("".join(c["text"] for c in w).strip(),
                           w[0]["x0"], w[-1]["x1"], w) for w in palabras if
                          "".join(c["text"] for c in w).strip()]))
    return fuera


def encabezados(lineas):
    """Todos los encabezados de la pagina, como [(indice, anclas), ...].

    Una pagina no tiene una sola tabla. Los procesos con pocos admitidos por
    carrera apilan varios bloques cortos en la misma hoja, cada uno con su
    titulo y su encabezado: la pagina 78 de Extraordinario 2022-I trae seis.
    Quedarse con el primero hacia que las 14 filas de esa pagina se guardaran
    todas como INGENIERIA CIVIL, que era la carrera del primer bloque.

    Se reconoce por su contenido, no por rotulos fijos: debe traer el nombre de
    la persona, su resultado o puntaje, y al menos tres columnas reconocibles.

    Se probo unir las lineas contiguas para leer encabezados partidos en varias
    alturas, y salio peor: con las vecinas incluidas hay lineas que no son
    encabezado y alcanzan el umbral, y el reconocimiento cayo de 116 a 62
    archivos. Los encabezados multilinea se cubren declarando sus rotulos.
    Los rotulos ajenos a CAMPOS se ignoran, asi un esquema nuevo se parsea
    igual en las columnas que si conoce en vez de fallar entero.
    """
    salida = []
    for i, (_, palabras) in enumerate(lineas):
        anclas, vistos = [], set()
        for texto, x0, x1, _ in palabras:
            campo = CAMPOS.get(texto)
            if campo and campo not in vistos:
                anclas.append((campo, x0, x1))
                vistos.add(campo)
        # Un encabezado necesita identificar a la persona y su resultado. Con
        # menos que eso la linea es un titulo o una nota al pie que coincidio.
        if "nombre" in vistos and len(anclas) >= 3 and (
                "total" in vistos or "condicion" in vistos):
            salida.append((i, anclas))
    return salida


def parte_un_numero(chars, i):
    """Si cortar en i dejaria un puntaje partido en dos.

    En Extraordinario 2025-I los tres componentes se imprimen pegados y sin
    hueco. Cortar por el borde de columna producia nota_01 = '93' y nota_02 =
    '.492000 60.745200' cuando el valor real era 93.492000.
    """
    return (chars[i - 1]["text"].isdigit()
            and (chars[i]["text"].isdigit() or chars[i]["text"] == "."))


def partir_en_columnas(palabras, anclas):
    """Parte las palabras que cruzan el inicio de una columna.

    Agrupar caracteres por hueco horizontal no distingue un espacio ancho del
    borde entre dos celdas. En Beca Esperanza 2025 un nombre largo queda a
    menos de CORTE_PALABRA de la carrera que le sigue y los dos textos salen
    como una sola palabra, con lo que la carrera se pierde entera.

    El inicio de la columna da el punto de corte exacto. Solo se parte por los
    bordes que se piden: hacerlo por todos destruye nombres legitimos en los
    documentos donde el rotulo del encabezado cae dentro de la columna vecina,
    y la extraccion baja de 65 060 filas a 46 297.
    """
    bordes = [x0 for _, x0, _ in anclas]
    fuera = []
    for texto, px0, px1, chars in palabras:
        cruza = [b for b in bordes if px0 < b < px1]
        if not cruza or not chars:
            fuera.append((texto, px0, px1))
            continue
        # El corte no va en la x del borde sino en el hueco entre caracteres
        # mas cercano a el: dos celdas contiguas siempre dejan alguna separacion,
        # solo que menor que CORTE_PALABRA. Cortar en la x exacta se comia la
        # primera letra del campo siguiente.
        indices = set()
        for borde in cruza:
            candidatos = [(chars[i + 1]["x0"] - chars[i]["x1"], i + 1)
                          for i in range(len(chars) - 1)
                          if abs(chars[i + 1]["x0"] - borde) <= CERCA_DEL_BORDE
                          and not parte_un_numero(chars, i + 1)]
            # Sin un corte admisible se deja la palabra entera: un campo vacio
            # dice que no se sabe, un numero cortado afirma algo falso.
            if candidatos:
                indices.add(max(candidatos)[1])
        piezas, previo = [], 0
        for i in sorted(indices):
            if i > previo:
                piezas.append(chars[previo:i])
            previo = i
        piezas.append(chars[previo:])
        for w in piezas:
            t = "".join(c["text"] for c in w).strip()
            if t:
                fuera.append((t, w[0]["x0"], w[-1]["x1"]))
    return fuera


def asignar(palabras, anclas):
    """Reparte las palabras de una fila entre las columnas del encabezado.

    No se puede usar solo la X de inicio del rotulo: unos documentos alinean el
    encabezado a la izquierda de su columna y otros lo centran. En los de salud,
    'APELLIDOS Y NOMBRES' empieza en x=277 mientras sus datos empiezan en 176.

    Por eso se decide en dos pasos. Primero por solapamiento: la palabra va a la
    columna cuyo rotulo cubre mas de su ancho horizontal, que resuelve los
    encabezados centrados y los anchos. Si no toca ninguno, cae en el de centro
    mas cercano, que resuelve las columnas numericas alineadas a la derecha.

    La asignacion se fuerza monotona de izquierda a derecha: una palabra nunca
    puede caer en una columna anterior a la de la palabra que la precede. Eso
    evita que un nombre largo invada la columna siguiente y luego vuelva atras.
    """
    fila = repartir(palabras, anclas)
    # Una columna vacia cuando alguna palabra cubre su borde significa que dos
    # celdas se leyeron como una sola palabra. Se reintenta partiendo solo por
    # ese borde, que es donde consta que hay un campo perdido.
    huecos = [a for a in anclas if not fila[a[0]]]
    if huecos:
        partidas = partir_en_columnas(palabras, huecos)
        if len(partidas) > len(palabras):
            fila = repartir(partidas, anclas)
    return fila


def repartir(palabras, anclas):
    fila = {campo: [] for campo, _, _ in anclas}
    centros = [(x0 + x1) / 2 for _, x0, x1 in anclas]
    minimo = 0
    for palabra in palabras:
        texto, px0, px1 = palabra[0], palabra[1], palabra[2]
        mejor, mejor_solape = None, 0
        for i in range(minimo, len(anclas)):
            _, hx0, hx1 = anclas[i]
            solape = min(px1, hx1) - max(px0, hx0)
            if solape > mejor_solape:
                mejor, mejor_solape = i, solape
        if mejor is None:
            centro = (px0 + px1) / 2
            mejor = min(range(minimo, len(anclas)),
                        key=lambda i: abs(centro - centros[i]))
        fila[anclas[mejor][0]].append(texto)
        minimo = mejor
    return {k: " ".join(v).strip() for k, v in fila.items()}


def es_fila_datos(fila):
    """Una fila real identifica a una persona y le asigna un resultado.

    Hay tres formas validas, porque no todos los documentos publican las mismas
    columnas. Unos omiten el puntaje, otros la condicion, y varios no traen
    columna de orden de merito: exigir las tres descartaba 10 archivos enteros.

    Lo que no se negocia es que haya una persona identificable, sea por codigo
    o por un nombre de al menos dos palabras.
    """
    codigo = fila.get("codigo", "") or ""
    # Un codigo con letras es arrastre de la columna vecina, no un documento.
    # Aparece cuando una linea de encabezado partida se lee como fila.
    if codigo and not codigo.isdigit():
        return False
    persona = codigo.isdigit() or len((fila.get("nombre") or "").split()) >= 2
    if not persona:
        return False
    if condicion_de(fila.get("condicion", "")):
        return True
    if re.fullmatch(r"\d{1,4}\.\d+", fila.get("total", "") or ""):
        return True
    # Sin condicion ni puntaje, solo vale si el documento numera la fila: es la
    # unica señal de que pertenece a la tabla y no al pie de pagina.
    return fila.get("orden", "").isdigit()


def calibrar(lineas, idx, anclas):
    """Recalcula las anclas usando donde arrancan los datos, no el encabezado.

    El rotulo no siempre esta sobre su columna: en los documentos de salud
    'APELLIDOS Y NOMBRES' ocupa de x=277 a 361 mientras sus datos empiezan en
    176. Un nombre largo alcanza el rotulo y se asigna bien; uno corto termina
    antes de llegar y cae en la columna anterior. La misma tabla parseaba unas
    filas bien y otras mal segun el largo del apellido.

    Agrupar los inicios reales de las filas de datos da las columnas de verdad.
    Se conservan las etiquetas del encabezado en su orden, que es lo unico que
    el rotulo aporta con fiabilidad.
    """
    inicios = []
    for _, palabras in lineas[idx + 1:]:
        for _, x0, _, _ in palabras:
            inicios.append(x0)
    if len(inicios) < len(anclas) * 3:
        return anclas

    # Agrupa posiciones que difieren menos de 5pt: es el jitter del
    # renderizador, no una columna distinta.
    inicios.sort()
    grupos, actual = [], [inicios[0]]
    for x in inicios[1:]:
        if x - actual[-1] <= 5:
            actual.append(x)
        else:
            grupos.append(actual)
            actual = [x]
    grupos.append(actual)

    # Solo se calibra si la tabla tiene tantas columnas de datos como rotulos
    # reconocidos. Cuando trae mas, el encabezado esta incompleto y emparejar
    # por posicion asigna etiquetas equivocadas: en precatolica 2025 hay tres
    # componentes de nota y el rotulo solo declara dos, y forzar la calibracion
    # ponia el promedio bajo 'total' y rompia la aritmetica en 2 452 filas.
    poblados = [g for g in grupos if len(g) >= 3]
    if len(poblados) != len(anclas):
        return anclas
    columnas = sorted(sum(g) / len(g) for g in poblados)
    return [(campo, x, x + (anc[2] - anc[1]))
            for (campo, *_), x, anc in zip(anclas, columnas, anclas)]


def titulo_carrera(lineas):
    """La carrera es la ultima linea en mayusculas y sin digitos del tramo.

    Se busca hacia atras desde el encabezado: encima de el estan, en orden, el
    proceso, la modalidad y por ultimo el nombre de la carrera. Las filas de
    datos del bloque anterior no compiten porque llevan digitos.
    """
    for _, palabras in reversed(lineas):
        texto = " ".join(p[0] for p in palabras).strip()
        if texto in RUIDO or not texto:
            continue
        if texto == texto.upper() and len(texto) >= 5 and not re.search(r"\d", texto):
            return texto
    return None


def actualizar_proceso(tramo, estado):
    """Actualiza sede y grupo si el tramo trae una linea de proceso.

    Un mismo documento encadena subprocesos y el encabezado que los separa
    aparece donde toque, incluso a mitad de pagina: en la 78 de Extraordinario
    2022-I el convenio cambia de I a II entre dos bloques. Por eso sede y grupo
    son estado que corre a lo largo del PDF y no un atributo de la pagina; las
    primeras carreras de una hoja suelen pertenecer al proceso que arranco en
    la anterior.
    """
    for i, (_, palabras) in enumerate(tramo):
        texto = " ".join(p[0] for p in palabras).strip()
        if not LINEA_PROCESO.search(texto):
            continue
        m = SEDE.search(texto)
        estado["sede"] = (m.group(1).strip()
                          if m and m.group(1).strip() not in ROMANOS else "")
        # El grupo es la linea siguiente al proceso, si no es ya la carrera.
        estado["grupo"] = ""
        if i + 2 <= len(tramo) - 1:
            candidato = " ".join(p[0] for p in tramo[i + 1][1]).strip()
            if candidato and candidato not in RUIDO:
                estado["grupo"] = candidato


def procesar_pagina(pagina, estado):
    """Extrae las filas de cada bloque de la pagina con su propia carrera."""
    lineas = lineas_de(pagina)
    if not lineas:
        return []

    cabezas = encabezados(lineas)
    if not cabezas:
        return []

    filas = []
    for k, (idx, anclas) in enumerate(cabezas):
        fin = cabezas[k + 1][0] if k + 1 < len(cabezas) else len(lineas)
        desde = 0 if k == 0 else cabezas[k - 1][0]
        tramo = lineas[desde:idx]
        actualizar_proceso(tramo, estado)
        carrera = titulo_carrera(tramo)
        # La calibracion mira solo las filas de este bloque: los de mas abajo
        # pueden tener otro ancho de columna.
        anclas_bloque = calibrar(lineas[:fin], idx, anclas)

        bloque, corte = [], None
        for _, palabras in lineas[idx + 1:fin]:
            texto = " ".join(p[0] for p in palabras)
            if texto.startswith("Nota M"):
                m = re.search(r"(\d+\.\d+)", texto)
                if m:
                    corte = float(m.group(1))
                continue
            if re.match(r"^(NC|NSP)\s*:", texto) or texto.startswith("*"):
                continue
            fila = asignar(palabras, anclas_bloque)
            if es_fila_datos(fila):
                fila["condicion"] = condicion_de(fila.get("condicion", ""))
                bloque.append(fila)
        for f in bloque:
            f["carrera_bloque"] = carrera
            f["nota_minima"] = corte
            f["sede"] = estado["sede"]
            f["grupo"] = estado["grupo"]
        filas.extend(bloque)

    return filas


def procesar_pdf(ruta):
    """Recorre un PDF completo y devuelve (filas, incidencias)."""
    fuera, avisos = [], []
    nombre = os.path.basename(ruta)
    try:
        with pdfplumber.open(ruta) as pdf:
            estado = {"sede": "", "grupo": ""}
            for pagina in pdf.pages:
                filas = procesar_pagina(pagina, estado)
                if not filas:
                    continue
                if not any(f.get("escuela") or f.get("carrera_bloque")
                           for f in filas):
                    avisos.append(f"pag {pagina.page_number}: filas sin carrera")
                    continue
                for f in filas:
                    # En la familia Excel la carrera es una columna de la fila;
                    # en la del sistema de admision es el titulo de su bloque.
                    f.update(archivo=nombre,
                             carrera=(f.get("escuela")
                                      or f.pop("carrera_bloque", None)
                                      or "").strip(),
                             pagina=pagina.page_number)
                    f.pop("carrera_bloque", None)
                    fuera.append(f)
    except Exception as e:
        avisos.append(f"error de lectura: {type(e).__name__}: {e}")
    return nombre, fuera, avisos


CAMPOS_CSV = ["archivo", "pagina", "sede", "grupo", "carrera", "orden", "codigo",
              "nombre", "nota_adicional", "nota_01", "nota_02", "total",
              "condicion", "opcion", "nota_minima"]


def guardar(ciclo, nombre, filas):
    carpeta = os.path.join(SALIDA, ciclo)
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, nombre.replace(".pdf", ".csv"))
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_CSV, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    return destino


def main():
    objetivo = sys.argv[1] if len(sys.argv) > 1 else None
    tareas = []
    for ciclo in sorted(os.listdir(CRUDO)):
        carpeta = os.path.join(CRUDO, ciclo)
        if not os.path.isdir(carpeta):
            continue
        for archivo in sorted(os.listdir(carpeta)):
            if not archivo.lower().endswith(".pdf"):
                continue
            if objetivo and objetivo not in archivo:
                continue
            tareas.append((ciclo, os.path.join(carpeta, archivo)))

    print(f"{len(tareas)} PDFs a procesar con {PROCESOS} procesos\n")
    resumen = []
    with ProcessPoolExecutor(PROCESOS) as ex:
        for ciclo, (nombre, filas, avisos) in zip(
                [t[0] for t in tareas], ex.map(procesar_pdf, [t[1] for t in tareas])):
            if filas:
                guardar(ciclo, nombre, filas)
            carreras = len({f["carrera"] for f in filas})
            cortes = len({f["nota_minima"] for f in filas if f["nota_minima"]})
            resumen.append(dict(ciclo=ciclo, archivo=nombre, filas=len(filas),
                                carreras=carreras, cortes=cortes,
                                avisos=len(avisos)))
            marca = "  " if filas else "??"
            print(f" {marca} {ciclo}  {nombre[:40]:<42} {len(filas):>6} filas "
                  f"{carreras:>3} carreras")
            for a in avisos[:2]:
                print(f"      aviso: {a[:70]}")

    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "_resumen.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ciclo", "archivo", "filas", "carreras",
                                          "cortes", "avisos"])
        w.writeheader()
        w.writerows(resumen)

    total = sum(r["filas"] for r in resumen)
    vacios = sum(1 for r in resumen if r["filas"] == 0)
    print(f"\n{total:,} filas extraidas de {len(resumen) - vacios}/{len(resumen)} PDFs")
    print(f"salida: data_extraida/<ciclo>/")
    return resumen


if __name__ == "__main__":
    main()
