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
