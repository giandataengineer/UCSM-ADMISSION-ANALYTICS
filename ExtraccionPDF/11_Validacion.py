#!/usr/bin/env python3
"""
Reconciliacion de lo extraido contra lo que dicen los PDFs.

No comprueba que el codigo corra: comprueba que el resultado sea fiel al
documento. Cada prueba usa una redundancia que el propio PDF publica, asi que
si el parser asigno mal una columna la aritmetica deja de cerrar sola.

  aritmetica   nota_01 + nota_02 = total, con NC y NSP como componente ausente
  minimo       nadie con INGRESO queda por debajo del minimo institucional
  secuencia    el orden de merito va de 1 a N dentro de carrera y postulacion
  unicidad     nadie repetido en el mismo archivo, carrera y postulacion
  minimo unico la nota minima institucional es una sola por documento
  cobertura    cada bloque extrae tantas filas como declara su orden

Nota sobre 'Nota Minima': no es el corte de la carrera sino el puntaje minimo
para calificar, y el documento publica el mismo valor para todas. En EG2023I es
45.647 en las 27 carreras. El corte real de una carrera es el puntaje del
ultimo admitido, y se calcula en la capa Gold.

Una prueba que falla no se corrige bajando el umbral: se corrige el parser o se
documenta por que la fuente es asi.

Uso: python ExtraccionPDF/11_Validacion.py
"""
import csv, glob, os, re, sys
from collections import Counter

import duckdb

RAIZ = os.path.dirname(os.path.abspath(__file__))
EXTRAIDA = os.path.join(RAIZ, "data_extraida")
ALMACEN = os.path.join(RAIZ, "ucsm.duckdb")

# Tolerancia de coma flotante. Los puntajes traen cinco decimales, asi que
# cualquier diferencia real es mucho mayor que esto.
EPS = 0.001


def construir(con):
    """Carga los CSV extraidos y tipa las columnas numericas."""
    patron = os.path.join(EXTRAIDA, "*", "*.csv").replace("\\", "/")
    con.execute(f"""
        CREATE OR REPLACE TABLE crudo AS
        SELECT * FROM read_csv_auto('{patron}', union_by_name = true,
                                    header = true, all_varchar = true)
    """)
    con.execute("""
        CREATE OR REPLACE TABLE filas AS
        SELECT
            archivo, carrera,
            CAST(pagina AS INTEGER)                       AS pagina,
            TRY_CAST(orden  AS INTEGER)                   AS orden,
            codigo, condicion, sede, grupo,
            TRY_CAST(nota_adicional AS DOUBLE)            AS nota_adicional,
            TRY_CAST(nota_01 AS DOUBLE)                   AS nota_01,
            TRY_CAST(nota_02 AS DOUBLE)                   AS nota_02,
            TRY_CAST(total   AS DOUBLE)                   AS total,
            TRY_CAST(nota_minima AS DOUBLE)               AS nota_minima
        FROM crudo
        WHERE carrera IS NOT NULL AND carrera <> ''
    """)
    # El orden de merito no siempre se reinicia por carrera. Hay dos familias:
    # cuando la carrera es el titulo del bloque, el orden va de 1 a N dentro de
    # cada carrera; cuando la carrera es una columna de la fila, el orden es
    # correlativo de todo el documento.
    #
    # Distinguirlas no es cosmetico: comparar un orden global contra un conteo
    # por carrera hacia aparecer 14 545 filas perdidas que no existen.
    #
    # El discriminante es si todos los bloques arrancan en 1. Cuando la carrera
    # titula el bloque, cada uno reinicia la numeracion; cuando es una columna,
    # solo el bloque que contiene al primer puesto empieza en 1 y el resto cae
    # donde le toque. La separacion es tajante en el corpus: 97 archivos con
    # todos los bloques en 1 y 9 con a lo sumo la mitad.
    #
    # Se probaron antes dos reglas peores. Comparar orden_max contra filas * 0.9
    # dejaba a EComplementario2024 (bloques de 5 y 45) justo en el umbral, y
    # exigir que el ordinal no se repitiera fallaba por uno en
    # Beca_Esperanza_2025, que es global y trae un 1 duplicado.
    con.execute("""
        CREATE OR REPLACE TABLE grano AS
        WITH bloque AS (
            SELECT archivo, sede, grupo, carrera, min(orden) AS primero
            FROM filas WHERE orden IS NOT NULL GROUP BY 1, 2, 3, 4
        )
        SELECT archivo,
               CASE WHEN count(*) FILTER (WHERE primero = 1) = count(*)
                    THEN 'por_carrera' ELSE 'global' END AS tipo
        FROM bloque GROUP BY archivo
    """)
    return con.execute("SELECT count(*) FROM filas").fetchone()[0]


RAW = os.path.join(RAIZ, "data", "raw")

# Ordinal al inicio de linea seguido de un apellido: la forma de una fila.
FILA_PDF = re.compile(r"^(\d{1,4})\s+[A-ZÑÁÉÍÓÚ]")


def _texto(archivo, _cache={}):
    if archivo not in _cache:
        rutas = glob.glob(os.path.join(RAW, "*", archivo))
        if not rutas:
            _cache[archivo] = None
        else:
            import pdfplumber
            with pdfplumber.open(rutas[0]) as pdf:
                _cache[archivo] = "\n".join(
                    (pag.extract_text() or "") for pag in pdf.pages)
    return _cache[archivo]


def _bloques(texto, carrera):
    """Los conjuntos de ordinales publicados bajo cada aparicion de la carrera."""
    lineas = texto.split("\n")
    salida = []
    for i, l in enumerate(lineas):
        if l.strip() != carrera:
            continue
        ordinales = set()
        for sig in lineas[i + 1:]:
            m = FILA_PDF.match(sig.strip())
            if m:
                ordinales.add(int(m.group(1)))
            elif ordinales:
                break
        salida.append(ordinales)
    return salida


def huecos_de_fuente(con):
    """Ordinales que faltan porque el PDF no los publica, no porque se perdieran.

    Solo tiene sentido en documentos donde la numeracion reinicia por carrera.
    Donde es correlativa de todo el archivo, los ordinales de una carrera son un
    subconjunto disperso del rango y los saltos no significan nada.

    UCSM retira gente de una lista ya ordenada sin renumerar el resto, asi que
    hay bloques que van 1,2,3,4,6. Suponer lo contrario hacia fallar la prueba
    de secuencia sobre una extraccion que era fiel.

    En vez de excluir esos casos a mano, cada hueco se contrasta contra el texto
    del PDF: si el ordinal tampoco esta ahi, la fuente lo omite y la extraccion
    es correcta. Si esta en el PDF y no en la salida, es una perdida real y la
    prueba debe seguir fallando.
    """
    faltantes = con.execute("""
        WITH t AS (SELECT f.archivo, f.sede, f.grupo, f.carrera, max(f.orden) AS m
                   FROM filas f JOIN grano g USING (archivo)
                   WHERE f.orden IS NOT NULL AND g.tipo = 'por_carrera'
                   GROUP BY 1, 2, 3, 4),
        esperado AS (SELECT archivo, sede, grupo, carrera, generate_series AS o
                     FROM t, generate_series(1, t.m))
        SELECT e.archivo, e.sede, e.grupo, e.carrera, e.o
        FROM esperado e
        LEFT JOIN filas f ON f.archivo = e.archivo
             AND f.sede IS NOT DISTINCT FROM e.sede
             AND f.grupo IS NOT DISTINCT FROM e.grupo
             AND f.carrera = e.carrera AND f.orden = e.o
        WHERE f.orden IS NULL
    """).fetchall()

    de_fuente, sin_verificar = set(), []
    for archivo, sede, grupo, carrera, orden in faltantes:
        texto = _texto(archivo)
        if texto is None:
            sin_verificar.append((archivo, carrera, orden))
            continue
        # Un mismo nombre de carrera aparece una vez por subproceso, asi que hay
        # que quedarse con el bloque de texto que corresponde. Se identifica por
        # su ordinal maximo, que es lo que la base declara para ese bloque.
        bloques = _bloques(texto, carrera)
        declarado = con.execute("""
            SELECT max(orden) FROM filas
            WHERE archivo = ? AND sede IS NOT DISTINCT FROM ?
              AND grupo IS NOT DISTINCT FROM ? AND carrera = ?
        """, [archivo, sede, grupo, carrera]).fetchone()[0]
        publicados = next((b for b in bloques if b and max(b) == declarado), None)
        if publicados is None:
            sin_verificar.append((archivo, carrera, orden))
            continue
        if orden not in publicados:
            de_fuente.add((archivo, sede, grupo, carrera, orden))
        else:
            sin_verificar.append((archivo, carrera, orden))
    return de_fuente, sin_verificar


# Cada prueba devuelve las filas que la incumplen. Vacio es aprobado.
PRUEBAS = [
    # Precatolica 2025 publica tres componentes en vez de dos, asi que la suma
    # incluye el adicional cuando existe.
    ("aritmetica: los componentes suman el total", """
        SELECT archivo, carrera, orden, nota_adicional, nota_01, nota_02, total
        FROM filas
        WHERE nota_01 IS NOT NULL AND nota_02 IS NOT NULL AND total IS NOT NULL
          AND abs(coalesce(nota_adicional, 0) + nota_01 + nota_02 - total) > {eps}
    """),

    # Solo se afirma en documentos que publican los dos componentes. Precatolica
    # 2026 y 2027 publican unicamente 'Exam 2' y el total, y ese total acumula
    # periodos previos que el documento no muestra: ahi la suma no es
    # verificable, que es distinto de estar mal.
    ("aritmetica: con un componente ausente, total = componente presente", """
        WITH esquema AS (
            SELECT archivo FROM filas
            GROUP BY archivo
            HAVING count(nota_01) > 0 AND count(nota_02) > 0
        )
        SELECT f.archivo, f.carrera, f.orden, f.nota_01, f.nota_02, f.total
        FROM filas f JOIN esquema e USING (archivo)
        WHERE f.total IS NOT NULL AND f.nota_adicional IS NULL
          AND ((f.nota_01 IS NULL) <> (f.nota_02 IS NULL))
          AND abs(coalesce(f.nota_01, f.nota_02) - f.total) > {eps}
    """),

    ("minimo: ningun INGRESO por debajo del minimo institucional", """
        SELECT archivo, carrera, orden, total, nota_minima
        FROM filas
        WHERE condicion = 'INGRESO' AND nota_minima IS NOT NULL
          AND total IS NOT NULL AND total < nota_minima - {eps}
    """),



    ("secuencia: el orden de merito arranca en 1", """
        SELECT archivo, carrera, min(orden) AS primer_orden
        FROM filas WHERE orden IS NOT NULL AND grupo IS NOT NULL
        GROUP BY archivo, sede, grupo, carrera HAVING min(orden) <> 1
    """),

    ("unicidad: nadie repetido en el mismo archivo y carrera", """
        SELECT archivo, sede, grupo, carrera, orden, count(*) AS veces
        FROM filas WHERE orden IS NOT NULL AND grupo IS NOT NULL
        GROUP BY archivo, sede, grupo, carrera, orden HAVING count(*) > 1
    """),

    # Un archivo puede cubrir varios subprocesos, cada uno con su minimo.
    # Extraordinario2025I trae dos y no publica sede ni grupo con que
    # separarlos, asi que se excluye: es un limite de la fuente, no un error.
    ("minimo unico: un solo minimo por documento, sede y grupo", """
        SELECT archivo, sede, grupo, count(DISTINCT nota_minima) AS distintos
        FROM filas
        WHERE nota_minima IS NOT NULL AND archivo <> 'Extraordinario2025I.pdf'
        GROUP BY archivo, sede, grupo HAVING count(DISTINCT nota_minima) > 1
    """),

    ("dominio: puntaje total dentro de rango plausible", """
        SELECT archivo, carrera, orden, total
        FROM filas WHERE total IS NOT NULL AND (total < 0 OR total > 2000)
    """),

    ("dominio: codigo de documento con forma valida", """
        SELECT archivo, carrera, orden, codigo
        FROM filas
        WHERE codigo IS NOT NULL AND codigo <> ''
          AND NOT regexp_matches(codigo, '^[0-9]+$')
          AND length(codigo) NOT BETWEEN 6 AND 12
    """),
]


def main():
    con = duckdb.connect(ALMACEN)
    total = construir(con)
    print(f"almacen: ucsm.duckdb")
    print(f"filas cargadas: {total:,}\n")

    fallidas, detalle = 0, []
    for nombre, sql in PRUEBAS:
        malas = con.execute(sql.format(eps=EPS)).fetchall()
        if malas:
            fallidas += 1
            print(f"  FALLA  {nombre}")
            print(f"         {len(malas)} filas incumplen")
            for fila in malas[:3]:
                print(f"           {fila}")
            detalle.append((nombre, len(malas), malas[:20]))
        else:
            print(f"  ok     {nombre}")

    # Los ordinales que el propio PDF omite se descuentan antes de comparar:
    # de otro modo un retiro sin renumerar se contabiliza como fila perdida.
    de_fuente, sin_verificar = huecos_de_fuente(con)
    if sin_verificar:
        fallidas += 1
        print(f"\n  FALLA  secuencia: {len(sin_verificar)} ordinales estan en el PDF "
              f"pero no en la salida")
        for x in sin_verificar[:5]:
            print(f"           {x[0]} · {x[1]}: falta el orden {x[2]}")
    else:
        print(f"\n  ok     secuencia: los {len(de_fuente)} huecos de numeracion "
              f"tambien faltan en el PDF de origen")

    # El ambito de la comparacion depende de la familia del documento: donde la
    # numeracion es correlativa de todo el archivo hay que contar el archivo
    # entero, y donde se reinicia por carrera hay que contar cada bloque.
    omitidos = Counter((a, s_, g, c) for a, s_, g, c, _ in de_fuente)
    hueco = []

    for archivo, sede, grupo, declaradas, extraidas in con.execute("""
        SELECT f.archivo, f.sede, f.grupo, max(f.orden), count(*)
        FROM filas f JOIN grano g USING (archivo)
        WHERE f.orden IS NOT NULL AND g.tipo = 'global'
        GROUP BY 1, 2, 3
    """).fetchall():
        if declaradas != extraidas:
            hueco.append((archivo, sede, grupo, "(documento)", declaradas, extraidas))

    for archivo, sede, grupo, carrera, declaradas, extraidas in con.execute("""
        SELECT f.archivo, f.sede, f.grupo, f.carrera, max(f.orden), count(*)
        FROM filas f JOIN grano g USING (archivo)
        WHERE f.orden IS NOT NULL AND g.tipo = 'por_carrera'
        GROUP BY 1, 2, 3, 4
    """).fetchall():
        if declaradas - omitidos.get((archivo, sede, grupo, carrera), 0) != extraidas:
            hueco.append((archivo, sede, grupo, carrera, declaradas, extraidas))

    if hueco:
        fallidas += 1
        print(f"  FALLA  cobertura: {len(hueco)} bloques donde el maximo orden "
              f"no coincide con las filas extraidas")
        for h in hueco[:5]:
            print(f"           {h[0]} · {h[1]}/{h[2]} · {h[3]}: declara {h[4]}, extrae {h[5]}")
    else:
        print(f"  ok     cobertura: cada bloque extrae tantas filas como declara "
              f"su orden de merito")

    ruta = os.path.join(RAIZ, "data_extraida", "_validacion.csv")
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prueba", "filas_que_incumplen"])
        for nombre, sql in PRUEBAS:
            n = len(con.execute(sql.format(eps=EPS)).fetchall())
            w.writerow([nombre, n])
        w.writerow(["secuencia: ordinales del PDF ausentes en la salida", len(sin_verificar)])
        w.writerow(["cobertura: orden maximo = filas extraidas", len(hueco)])

    print(f"\n{len(PRUEBAS) + 2 - fallidas}/{len(PRUEBAS) + 2} pruebas aprobadas")
    print(f"informe: data_extraida/_validacion.csv")
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main())
