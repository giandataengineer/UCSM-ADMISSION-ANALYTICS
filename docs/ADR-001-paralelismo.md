# ADR-001 · Paralelismo de la etapa de extracción

**Fecha:** 7 de setiembre de 2026
**Estado:** aceptada
**Contexto:** elección de tecnología para procesar 221 PDFs en la etapa Bronze → Silver

## Decisión

`concurrent.futures.ProcessPoolExecutor` con 8 procesos. **PySpark queda descartado.**

## Por qué

La etapa reconstruye filas a partir de la posición de cada carácter en la página.
Es trabajo intensivo en CPU sobre archivos independientes, no un problema de
volumen de datos.

Medición sobre el corpus real, máquina de 10 núcleos, pdfplumber 0.11.8,
extracción char-level de 221 PDFs (47.9 MB, 5 577 páginas):

| Configuración | Tiempo del corpus | Aceleración | Eficiencia |
|---|---|---|---|
| serial | 40.8 s | 1.00x | 100% |
| 2 procesos | 22.2 s | 1.84x | 92% |
| 4 procesos | 13.6 s | 3.00x | 75% |
| 8 procesos | **9.3 s** | 4.39x | 55% |
| 10 procesos | 9.4 s | 4.35x | 43% |

Reproducible con `python ExtraccionPDF/bench_paralelismo.py`.

Dos lecturas de esos números:

La etapa completa tarda **9.3 segundos**. Levantar una `SparkSession` toma entre
5 y 10 segundos antes de tocar el primer byte. Spark pasaría más tiempo
arrancando la JVM que el que dura el trabajo, y encima habría que serializar
Python a JVM y de vuelta.

La eficiencia cae a 55% en 8 procesos y no mejora en 10. La etapa satura ancho
de banda de memoria, no cómputo. Repartir eso entre nodos no lo arregla: agrega
red a un cuello de botella que es local.

## Cuándo revisar esta decisión

Spark entra si ocurre alguna de estas, y ninguna ocurre hoy:

- El conjunto de trabajo deja de entrar en la RAM de una máquina. Silver pesa
  ~18 MB; el umbral está en cientos de gigabytes.
- El trabajo pasa a durar horas y hace falta tolerancia a fallos por tarea.
- Los datos se mudan a un lakehouse ya gestionado con Spark.
- Aparecen joins o agregaciones que exceden la memoria de un nodo. Los actuales
  los resuelve DuckDB sin esfuerzo.

## Consecuencias

Se acepta que el repositorio no contenga PySpark. Si se necesita esa señal en un
portafolio, la salida es un proyecto aparte donde el volumen lo justifique, no
forzarla aquí: un `SparkSession.builder` sobre 47 MB comunica lo contrario de lo
que se busca.

## Referencias

- Reis, J. y Housley, M. *Fundamentals of Data Engineering*. O'Reilly, 2022.
  Elección de tecnología como trade-offs reversibles.
- Kleppmann, M. *Designing Data-Intensive Applications*. O'Reilly, 2017.
  Caracterizar la carga antes de elegir el sistema.
