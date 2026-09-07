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
import csv, glob, os, sys

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
    con.execute("""
        CREATE OR REPLACE TABLE grano AS
        WITH por_archivo AS (
            SELECT archivo,
                   count(*)                       AS filas,
                   max(orden)                     AS orden_max,
                   count(DISTINCT carrera)        AS carreras
            FROM filas WHERE orden IS NOT NULL GROUP BY archivo
        )
        SELECT archivo,
               CASE WHEN carreras > 1 AND orden_max >= filas * 0.9
                    THEN 'global' ELSE 'por_carrera' END AS tipo
        FROM por_archivo
    """)
    return con.execute("SELECT count(*) FROM filas").fetchone()[0]


# Cada prueba devuelve las filas que la incumplen. Vacio es aprobado.
PRUEBAS = [
    ("aritmetica: nota_01 + nota_02 = total", """
        SELECT archivo, carrera, orden, nota_01, nota_02, total
        FROM filas
        WHERE nota_01 IS NOT NULL AND nota_02 IS NOT NULL AND total IS NOT NULL
          AND abs(nota_01 + nota_02 - total) > {eps}
    """),

    ("aritmetica: con un componente ausente, total = componente presente", """
        SELECT archivo, carrera, orden, nota_01, nota_02, total
        FROM filas
        WHERE total IS NOT NULL
          AND ((nota_01 IS NULL) <> (nota_02 IS NULL))
          AND abs(coalesce(nota_01, nota_02) - total) > {eps}
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

    ("secuencia: sin huecos entre 1 y el maximo", """
        SELECT archivo, sede, grupo, carrera,
               count(DISTINCT orden) AS distintos, max(orden) AS maximo
        FROM filas WHERE orden IS NOT NULL AND grupo IS NOT NULL
        GROUP BY archivo, sede, grupo, carrera
        HAVING count(DISTINCT orden) <> max(orden)
    """),

    ("unicidad: nadie repetido en el mismo archivo y carrera", """
        SELECT archivo, sede, grupo, carrera, orden, count(*) AS veces
        FROM filas WHERE orden IS NOT NULL AND grupo IS NOT NULL
        GROUP BY archivo, sede, grupo, carrera, orden HAVING count(*) > 1
    """),

    ("minimo unico: un solo minimo institucional por documento", """
        SELECT archivo, count(DISTINCT nota_minima) AS distintos
        FROM filas WHERE nota_minima IS NOT NULL
        GROUP BY archivo HAVING count(DISTINCT nota_minima) > 1
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

    # Contraste contra el conteo declarado por el propio documento: el maximo
    # orden de merito de cada carrera dice cuantas filas deberia haber.
    hueco = con.execute("""
        SELECT f.archivo, f.sede, f.grupo,
               CASE WHEN g.tipo = 'global' THEN '(documento)' ELSE f.carrera END AS ambito,
               max(f.orden) AS declaradas, count(*) AS extraidas
        FROM filas f JOIN grano g USING (archivo)
        WHERE f.orden IS NOT NULL
        GROUP BY 1, 2, 3, 4
        HAVING max(f.orden) <> count(*)
    """).fetchall()
    if hueco:
        fallidas += 1
        print(f"\n  FALLA  cobertura: {len(hueco)} bloques donde el maximo orden "
              f"no coincide con las filas extraidas")
        for h in hueco[:5]:
            print(f"           {h[0]} · {h[1]}/{h[2]} · {h[3]}: declara {h[4]}, extrae {h[5]}")
    else:
        print(f"\n  ok     cobertura: cada bloque extrae tantas filas como declara "
              f"su orden de merito")

    ruta = os.path.join(RAIZ, "data_extraida", "_validacion.csv")
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["prueba", "filas_que_incumplen"])
        for nombre, sql in PRUEBAS:
            n = len(con.execute(sql.format(eps=EPS)).fetchall())
            w.writerow([nombre, n])
        w.writerow(["cobertura: orden maximo = filas extraidas", len(hueco)])

    print(f"\n{len(PRUEBAS) + 1 - fallidas}/{len(PRUEBAS) + 1} pruebas aprobadas")
    print(f"informe: data_extraida/_validacion.csv")
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(main())
