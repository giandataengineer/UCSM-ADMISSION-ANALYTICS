# ADR-002 · Ventana temporal del corpus

**Fecha:** 7 de setiembre de 2026
**Estado:** aceptada
**Contexto:** qué ciclos de admisión entran al análisis

## Decisión

El corpus arranca en el **ciclo 2021**. Los PDFs de 2015 a 2020 se descartaron.

## Por qué

La UCSM no publicó los exámenes generales antes de 2021. No es un problema de
búsqueda: se verificó con seis métodos independientes.

| Método | Alcance |
|---|---|
| Wayback CDX sobre el dominio | 60 000 URLs, 5 041 PDFs |
| Sondeo de rutas en el sitio vivo | 936 combinaciones de nombre |
| Lectura del portal con navegador | índice actual completo |
| Common Crawl | 6 índices, 7 400 URLs |
| Índices históricos archivados | capturas de `/resultados-de-pregrado/` desde 2016 |
| Subdominios | `aulavirtual` y `admision` |

Lo que existe de 2015-2020 son 75 PDFs de modalidades especiales: traslados,
tercio superior, becas y convenios. Ninguno trae `Código`, `Nota 01` ni
`Nota 02`, y casi ninguno lista rechazados. Sin esos campos no se puede calcular
tasa de admisión, ni seguir a una persona entre procesos, ni descomponer el
puntaje. Sostienen conteos, no análisis.

El sistema que genera los PDFs con esquema completo aparece en 2019 y se
consolida en 2021. Desde ese ciclo la publicación es sistemática: los tres
exámenes ordinarios de cada año, más precatólica, extraordinarios, becas,
convenios y traslados.

## Cobertura resultante

| Ciclo | Ordinarios | Precatólica | Distancia | Extraordinarios | Total |
|---|---|---|---|---|---|
| 2021 | 3 | 4 | — | 5 | 21 |
| 2022 | 4 | 7 | — | 5 | 28 |
| 2023 | 3 | 6 | 3 | 5 | 25 |
| 2024 | 3 | 3 | 3 | 4 | 27 |
| 2025 | 3 | 5 | 4 | 1 | 22 |
| 2026 | 5 | 2 | 3 | 1 | 22 |
| 2027 | 2 | 1 | — | 1 | 6 |

151 PDFs de resultados y 30 documentos normativos, 61.1 MB.

Estudios a Distancia no aparece en 2021 ni 2022 porque la modalidad se creó
en 2023. 2027 es el ciclo en curso y se completa conforme la UCSM publique.

## Verificación de completitud del ciclo

Cada ciclo se contrastó contra la plantilla de procesos deducida de los propios
documentos y del cronograma oficial. Los exámenes de un ciclo se rinden en dos
años calendario: para el ciclo 2021, entre agosto de 2020 y agosto de 2021.

Ejemplo del ciclo 2021 completo, con las fechas que trae cada PDF por dentro:

| Fecha | Proceso |
|---|---|
| 18/08/2020 | Precatólica 2021-I |
| 22/08/2020 | Concurso de Admisión 2021 · Tercio Superior |
| 31/08/2020 | Primer Examen General 2021 |
| 13/12/2020 | Precatólica 2021-II |
| 21/12/2020 | Segundo Examen General 2021 |
| 11/02/2021 | Cobertura de Metas Segundo Examen |
| 20/02/2021 | Precatólica 2021-III |
| 22/02/2021 | Extraordinario 2021 I · Deportistas Destacados |
| 01/03/2021 | Tercer Examen General 2021 |
| 01/03/2021 | PRONABEC Beca-18 2021 |
| 08 y 24/08/2021 | Extraordinario 2021 II · Traslado Externo |

### Dos ausencias que no son huecos

**Estudios a Distancia no existe en 2021 ni 2022.** La modalidad se creó en el
ciclo 2023: el primer examen es del 13/11/2022. Antes de eso no hay nada que
falte.

**Tercio Superior y Rendimiento Superior son la misma modalidad renombrada.**
Ocupa el mismo lugar del calendario, fines de junio o inicios de julio del año
anterior, sin interrupción:

| Ciclo | Fecha | Nombre publicado |
|---|---|---|
| 2021 | 22/08/2020 | Concurso de Admisión · Tercio Superior |
| 2022 | 27/06/2021 | Concurso de Admisión · Tercio Superior |
| 2023 | 03/07/2022 | Concurso de Admisión · Tercio Superior |
| 2024 | 09/07/2023 | Examen Extraordinario I · Rendimiento Superior |
| 2025 | 14/07/2024 | Examen Extraordinario I · Rendimiento Superior |
| 2026 | 06/07/2025 | Examen Extraordinario I · Rendimiento Superior |
| 2027 | 06/07/2026 | Examen Extraordinario I · Rendimiento Superior |

La cobertura es 7 de 7 ciclos. El normalizador tiene que unificarlos bajo una
sola modalidad o la serie mostrará un corte en 2024 que no ocurrió.

### El único hueco real

**Precatólica 2026-II no está publicada.** El proceso sí ocurrió: el cronograma
oficial 2026 programa Centro Preuniversitario II con inscripciones del 4 de
agosto al 12 de setiembre de 2025 y clases desde el 15 de setiembre. Están
publicadas la I (03/08/2025, 51 páginas) y la III (08/02/2026, 55 páginas), pero
no la II.

**La prueba está en la propia página de la UCSM.** Cada proceso publica dos
enlaces, "Ingresantes" con los resultados e "Indicaciones" con el instructivo:

| Proceso | Ingresantes | Indicaciones |
|---|---|---|
| Precatólica 2026-I | `precatolica2026-I_final.pdf` | `REQ_2026_PRECA_I.pdf` |
| **Precatólica 2026-II** | **no existe** | `REQ_2026_PRECA_II.pdf` |
| Precatólica 2026-III | `Resul_PrecaIII.pdf` | `REQ_2026_PRECAIII.pdf` |
| Precatólica 2027-I | `Resultados_Final_Preca2027-I.pdf` | `INDICACIONES ... 2027-I.pdf` |

La sección existe y el instructivo está publicado, pero el PDF de resultados
nunca se subió. La sección está construida como pestaña, así que el enlace solo
aparece al abrirla: por eso una lectura plana del HTML no lo detecta.

También se verificó en Wayback, que entre noviembre de 2025 y setiembre de 2026
capturó un solo archivo de esa carpeta. Es un hueco de la fuente, no de la
búsqueda.

### Copia parcial recuperada

El documento circuló fuera del portal: una copia está subida a Studocu. La
versión obtenible desde ahí es una vista previa con **14 de las 50 páginas**
legibles; el resto viene rasterizado con desenfoque irreversible, así que no se
recupera por OCR ni por ningún otro medio.

Esa copia trae 117 ingresantes en 14 de las 27 carreras, fechada el 14/12/2025,
lo que concuerda con el instructivo que fija matrícula del 17 al 31 de diciembre.
Confirma que el proceso se realizó.

**Se decidió no incorporarla al corpus.** Un documento con 14 de 27 carreras
mete un denominador incompleto: la tasa de admisión que saldría de ahí sería
falsa, y una cifra falsa hace más daño que un proceso declarado como ausente.
Tampoco se simulan los datos faltantes, por la misma razón y porque serían
nombres y puntajes inventados de personas reales.

Búsqueda agotada también fuera del portal: Scribd, Issuu, SlideShare, Course
Hero y páginas de academias en Facebook. Scribd aloja Precatólica 2026-I, el
Tercer Ordinario 2026, EG2026II y el cuadro de vacantes, todos ya presentes en
el corpus desde la fuente oficial. Del 2026-II no hay copia completa en ningún
lado.

El proceso queda declarado como ausente. Si la Dirección de Admisión facilita la
copia oficial, se incorpora y la matriz cierra en 72 de 72.

## Consecuencias

El README declara siete ciclos, no diez. Prometer una década y entregar tres
años vacíos cuesta más credibilidad de la que gana el titular.

Los scripts 1, 5 y 6 filtran por `CICLO_MINIMO = "2021"`, así que una
reejecución no vuelve a traer lo descartado. Revertir la decisión es cambiar esa
constante.

## Nota sobre datos personales

Durante la búsqueda se encontró que `admision.ucsm.edu.pe` expone 749 documentos
personales de postulantes: fichas de inscripción, solicitudes y cartas de
compromiso firmadas, nombradas por UUID y archivadas por el Internet Archive en
enero de 2025.

No se descargaron ni se indexaron. No son resultados, no aportan al análisis, y
recolectarlos sería tratamiento de datos personales a escala sobre documentos
que quedaron accesibles por un error de configuración, no por publicación
deliberada.
