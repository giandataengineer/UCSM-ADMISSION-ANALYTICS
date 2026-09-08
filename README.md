# Admisión UCSM en Datos

Extracción y análisis de los resultados de admisión de la Universidad Católica de
Santa María, publicados como PDFs por la Dirección de Admisión.

Estado: **corpus construido y auditado**. Falta el parser de tablas.

## Estructura

```
ExtraccionPDF/
  1_DescubrimientoDescarga.py    descubre por 3 vías, descarga con throttle
  2_AuditoriaCorpus.py           cuenta qué hay realmente dentro de cada PDF
  3_CatalogoCarreras.py          qué carreras se convocaron en cada ciclo
  4_Vacantes.py                  cuadro de vacantes por carrera y modalidad
  5_DocumentosBase.py            reglamentos, temarios, cronogramas y vacantes por año
  6_RescateHistorico.py          archivos fuera de convención de nombre
  7_RequisitosIngresantes.py     instructivos por proceso
  8_ExtraccionTablas.py          reconstrucción de filas por coordenadas
  9_NormalizacionDatos.py        [pendiente] esquema único + seudonimización
  10_AnalisisExploratorio.ipynb  [pendiente]
  data/
    manifest.csv                 223 filas: una por PDF de resultados descubierto
    auditoria.csv                151 filas: contenido real de cada PDF
    carreras_por_ciclo.csv       47 carreras × 9 ciclos
    vacantes.csv                 vacantes 2027 por carrera y modalidad
    documentos_base.csv          30 documentos normativos indexados
    raw/<ciclo>/                 151 PDFs de resultados por ciclo de admisión
    documentos_base/<año>/       vacantes, reglamento, temario, cronograma
    requisitos/<ciclo>/          instructivos de ingresantes por proceso
  data_extraida/                 [vacío] salida del parser
  data_normalizada/              [vacío] listo para el warehouse
docs/INVENTARIO.md               tabla detallada de los 151 PDFs
docs/ADR-001-paralelismo.md      por qué no se usa PySpark
docs/ADR-002-ventana-temporal.md por qué el corpus arranca en 2021
```

## Reproducir

```bash
pip install -r requirements.txt
python ExtraccionPDF/1_DescubrimientoDescarga.py   # ~5 min, 47 MB
python ExtraccionPDF/2_AuditoriaCorpus.py
python ExtraccionPDF/3_CatalogoCarreras.py
python ExtraccionPDF/5_DocumentosBase.py           # 22.9 MB de normativa
python ExtraccionPDF/4_Vacantes.py
```

Los PDFs no están versionados. Se reconstruyen con el primer script.

## El corpus

151 PDFs de resultados y 30 documentos normativos, 61.1 MB, ciclos de admisión 2021 a 2027.

El **ciclo** es el año de ingreso declarado dentro del PDF, no el año en que se
rindió el examen: `EG2023I.pdf` dice *PRIMER EXAMEN ORDINARIO 2023* pero está
fechado el 29/08/2022. Un ciclo de admisión reúne entre 12 y 16 procesos
repartidos entre el año anterior y el año de inicio de clases.

### Tres vías de descubrimiento

Ninguna sola alcanza:

| Vía | Aporte | Por qué hace falta |
|---|---|---|
| Wayback CDX | 190 | Cubre lo histórico. Desactualizado en 2026-2027. |
| Sondeo de nombres | +16 | Rellena nombres predecibles. Se agota rápido. |
| Página web con navegador | +16 | Única que ve los nombres nuevos. |

En 2026 UCSM cambió la convención: de `EG2026I.pdf` pasaron a
`RESULT_ORDINARIO_2027.pdf`, `Resultados_2026_IIIORDINARIO.pdf`,
`Resul_PrecaIII.pdf`. Esos nombres no se adivinan, y el WAF del sitio devuelve
403 a cualquier cliente que no sea un navegador real.

## Lo que limita el análisis

Estos límites son de la fuente, no del procesamiento. Están aquí porque
determinan qué preguntas tienen respuesta y cuáles no.

**Dos familias de PDF.** 108 archivos salen del generador del sistema de
admisión, que usa fuentes subset con ToUnicode, y 43 de Excel o Word con object
streams. Se leen distinto, así que el parser reconoce el esquema por sus
rótulos en vez de asumirlo.

**Ocho esquemas distintos.** El más completo es
`Condición | Código | Nombre | Nota 01 | Nota 02 | Ord. | Total`, en 53
archivos. El más pobre es `Condición | Nombre | Ord. | Total`, en 26. Otros
54 no exponen un encabezado uniforme y se resuelven por coordenadas.

**El `Código` desaparece progresivamente.** Está en el 97% de las filas de 2021
y en el 100% de 2023 y 2024, cae al 81% en 2025, al 11% en 2026 y a cero en
2027. Seguir a la misma persona entre procesos, que es lo que habilita el
análisis de cohortes, solo es viable **hasta 2025**.

### Por qué la serie empieza en 2021

Porque antes la UCSM no publicaba estos resultados en la web. No es una
decisión de alcance: es donde empieza la fuente.

Se verificó con seis métodos independientes, entre ellos el índice CDX del
Internet Archive sobre el dominio completo, el índice de Common Crawl y el
rastreo de las convenciones de nombre que la universidad fue usando. Ninguno
devuelve resultados de exámenes generales anteriores al ciclo 2021. Lo que sí
existe de antes son reglamentos y temarios, que no son resultados.

Los 91 PDFs previos a 2021 que se habían descargado en la exploración inicial
se eliminaron por eso. El detalle está en `docs/ADR-002-ventana-temporal.md`.

### Desde 2026 solo se publica a quien ingresa

Hasta 2025 los PDFs listaban a todos los postulantes con su condición, así que
se podía calcular la tasa de admisión real. A partir de 2026 la universidad
cambió de criterio y publica únicamente a los admitidos.

| Ciclo | Ingresantes | No ingresantes | Tasa calculable |
|---|---|---|---|
| 2021 | 3 033 | 4 333 | sí |
| 2022 | 5 117 | 4 865 | sí |
| 2023 | 4 832 | 7 590 | sí |
| 2024 | 5 741 | 7 149 | sí |
| 2025 | 4 977 | 4 472 | sí |
| **2026** | **4 715** | **498** | **no** |
| **2027** | **1 697** | **0** | **no** |

De los 22 PDFs de 2026 apenas 4 traen rechazados, y ninguno de los 6 de 2027.
No faltan archivos: están los 28 y cubren los nueve tipos de proceso. Lo que
falta es el dato, porque el documento dejó de traerlo.

La consecuencia es concreta. **De 2026 en adelante se puede decir cuántos
entraron y con qué puntaje, pero no qué tan difícil fue entrar**, porque no se
conoce el número de postulantes. Los agregados marcan esos ciclos con
`denominador_fiable = 0` para que ningún tablero los grafique como si la
exigencia hubiera bajado.

### Cobertura por ciclo

| Ciclo | Ordinarios | Precatólica | Distancia | Extraordinarios | Total |
|---|---|---|---|---|---|
| 2021 | 3 | 4 | — | 5 | 21 |
| 2022 | 4 | 7 | — | 5 | 28 |
| 2023 | 3 | 6 | 3 | 5 | 25 |
| 2024 | 3 | 3 | 3 | 4 | 27 |
| 2025 | 3 | 5 | 4 | 1 | 22 |
| 2026 | 5 | 2 | 3 | 1 | 22 |
| 2027 | 2 | 1 | — | 1 | 6 |

Estudios a Distancia no aparece en 2021 ni 2022 porque la modalidad se creó en
2023. 2027 es el ciclo en curso: se completa conforme UCSM publique.

**Por qué desde 2021 y no desde 2016.** La UCSM no publicó los exámenes
generales antes de ese ciclo. Verificado con seis métodos independientes; el
detalle está en `docs/ADR-002-ventana-temporal.md`.

## Procesamiento

Once etapas, todas reproducibles. Los PDFs no se versionan: se reconstruyen.

| Etapa | Script | Salida |
|---|---|---|
| Descubrir y descargar | `1_DescubrimientoDescarga.py` | 151 PDFs de resultados |
| Auditar el corpus | `2_AuditoriaCorpus.py` | qué trae cada PDF |
| Catálogo de carreras | `3_CatalogoCarreras.py` | 47 carreras × 7 ciclos |
| Cuadro de vacantes | `4_Vacantes.py` | plazas por carrera y modalidad |
| Base normativa | `5_DocumentosBase.py` | reglamentos, temarios, cronogramas |
| Rescate histórico | `6_RescateHistorico.py` | archivos sin convención de nombre |
| Instructivos | `7_RequisitosIngresantes.py` | 22 documentos por proceso |
| **Extracción de tablas** | `8_ExtraccionTablas.py` | **66 069 filas** por coordenadas, bloque a bloque |
| Normalización (Silver) | `9_NormalizacionDatos.py` | 65 715 filas, 47 carreras, seudonimizadas |
| Agregados (Gold) | `10_Agregados.py` | 6 CSV para Tableau |
| Reconciliación | `11_Validacion.py` | 10 pruebas en DuckDB |
| Auditoría integral | `12_Auditoria.py` | cadena, pérdidas, privacidad |

### Verificación

Tres suites, 20 pruebas, todas en verde. Ninguna se ajustó para pasar: cada vez
que una falló, se corrigió el parser o se documentó por qué la fuente es así.

`11_Validacion.py` contrasta cada fila contra las redundancias que el propio
PDF publica. Si el parser asignara mal una columna, la aritmética dejaría de
cerrar sola. Dos pruebas van más allá y **abren el PDF de origen**: cuando el
orden de mérito salta un número, se comprueba si el ordinal tampoco está en el
documento. Los nueve casos resultaron ser omisiones de la fuente, que retira
gente de una lista ya ordenada sin renumerar.

`13_PruebasCalidad.py` mira las capas derivadas: integridad referencial, que la
fecha del examen caiga en la ventana de su ciclo, que Gold sume lo mismo que
Silver, que el seudónimo no colisione y que reejecutar produzca el mismo
archivo byte a byte.

`12_Auditoria.py` revisa el conjunto: que cada etapa conserve lo que recibió,
que no salga ningún dato personal en lo versionado, y **que todo PDF sin filas
tenga una explicación verificada**. Los 15 que no producen datos son 9 listas
de aptitud previas al examen, 5 instructivos y 1 duplicado; la auditoría los
clasifica leyendo el propio documento y falla si aparece uno sin explicar.

Esa última prueba fue la que más valió. Reportar "35 PDFs sin filas" mezclaba
documentos que nunca iban a tener filas con tablas que sí había que arreglar.
Al separarlos quedaron a la vista 12 PDFs de resultados de 2021 a 2023 que no
se estaban leyendo, y se recuperaron 1 009 filas.

## Decisiones de arquitectura

Registradas en `docs/`, con la medición que las sostiene.

**ADR-003 · Hallazgos de la validación.** Cuatro errores de modelo que la
reconciliación destapó: `Nota Mínima` no es la nota de corte sino el mínimo
institucional, faltaban las dimensiones de sede y grupo (aparecieron ocho
sedes), el corte no se puede calcular mezclando modalidades porque cada una usa
su escala, y en Medicina aprobar el examen da `TEST + ENTREVISTA` y no
`INGRESO`.

**ADR-001 · Paralelismo.** La etapa de extracción usa `ProcessPoolExecutor` con
8 procesos: 40.8 s en serial contra 9.3 s en paralelo sobre los 221 PDFs.
PySpark queda descartado porque arrancar la JVM tarda más que el trabajo
completo, y porque la eficiencia cae a 55% en 8 procesos, señal de que el
cuello de botella es ancho de banda de memoria local y no cómputo distribuible.
El umbral que revertiría la decisión está escrito en el ADR. Reproducible con
`python ExtraccionPDF/bench_paralelismo.py`.

## Datos personales

Los PDFs traen nombre completo y, hasta 2025, código de documento. Que UCSM los
publique no habilita a republicarlos consolidados.

- Los nombres se descartan en la ingesta.
- El código se reemplaza por `HMAC-SHA256(código, sal)` truncado, que conserva
  la trazabilidad entre procesos sin exponer el documento. La sal va en `.env`.
- `data_extraida/` está en `.gitignore`.
- Solo se publican agregados por carrera, modalidad y ciclo.

## Base normativa

30 documentos oficiales de 2021 a 2027, en
`data/documentos_base/<año>/`:

| Documento | Cobertura | Para qué sirve |
|---|---|---|
| `vacantes.pdf` | 2021-2027, completo | Plazas por carrera y modalidad. Es el denominador. |
| `temario.pdf` | 2021-2027, completo | Qué se evalúa. Explica saltos en las notas. |
| `reglamento.pdf` | 2021, 2022, 2024, 2026, 2027 | Reglas del proceso. Los PDFs citan sus artículos. |
| `cronograma.pdf` | 2022-2027 | Fechas oficiales de cada proceso. |

El cuadro de vacantes reparte las plazas entre cinco vías de ingreso. Para 2027:

| Modalidad | Vacantes |
|---|---|
| Exámenes ordinarios | 2 654 |
| Centro preuniversitario (CEPRE I-II-III) | 1 434 |
| Concurso extraordinario | 1 201 |
| Vacantes PRONABEC | 188 |
| Traslado interno | 90 |
| **Total** | **5 567** |

Cruzar esto contra los ingresantes reales de cada proceso da la tasa de
ocupación de plazas por carrera y modalidad.

## Catálogo de carreras

47 carreras distintas entre 2021 y 2027. La oferta no es fija: **Ingeniería en
Inteligencia Artificial** e **Ingeniería Biomédica** aparecen recién en el ciclo
2026; **Turismo y Hotelería** dejó de convocarse después de 2021. Una serie
temporal por carrera tiene que distinguir "no se convocó" de "nadie postuló", y
para eso está `carreras_por_ciclo.csv`.

## Fuente

Dirección de Admisión, Universidad Católica de Santa María — ucsm.edu.pe
Enumeración histórica vía Internet Archive Wayback CDX API.
Este análisis no es institucional ni está avalado por la UCSM.
