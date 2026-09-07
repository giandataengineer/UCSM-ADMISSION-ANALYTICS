# ADR-004 · El cambio de escala de 2024

**Fecha:** 7 de setiembre de 2026
**Estado:** aceptada
**Contexto:** la prueba de distribución detectó saltos imposibles entre ciclos

## El hallazgo

La mediana del examen ordinario, sobre 34 carreras:

| Ciclo | Mediana | n |
|---|---|---|
| 2021 | 77.1 | 4 493 |
| 2022 | 76.8 | 6 205 |
| 2023 | 76.6 | 6 002 |
| **2024** | **152.7** | 5 561 |
| 2025 | 153.1 | 3 625 |
| 2026 | 128.6 | 1 914 |
| 2027 | 126.7 | 887 |

**26 de las 34 carreras saltan exactamente en la misma transición**, 2023 a
2024, y ninguna en otra. Un cambio real de exigencia no se sincroniza así entre
carreras independientes: la UCSM cambió la escala de calificación.

## La consecuencia

Un puntaje de 2023 y uno de 2024 **no son comparables**. Una serie de nota de
corte de siete ciclos se parte por la mitad, y quien la lea sin saberlo va a
concluir que la exigencia se duplicó.

## Decisión

Se publican dos campos junto al puntaje:

- **`escala`** marca el régimen, `anterior` hasta 2023 y `nueva` desde 2024.
- **`percentil`** es la posición relativa del puntaje dentro de su propio
  proceso y carrera. Es invariante a la escala: su mediana se mantiene entre
  47.9 y 49.4 en los siete ciclos, mientras la del puntaje bruto se duplica.

El tablero usa puntaje bruto dentro de un régimen y percentil cuando cruza la
frontera de 2024.

## Cómo se encontró

No se buscaba. La prueba `distribucion: sin saltos de mediana entre ciclos
consecutivos` marca cuando la mediana de una carrera se multiplica por más de
1.8 o cae por debajo de 0.55 de un ciclo al siguiente. Saltó con 26 casos y
todos en la misma transición, que es lo que convirtió una anomalía sospechosa
en un hecho institucional.

Es el argumento para tener pruebas de distribución y no solo de integridad
referencial: un dato puede ser perfectamente consistente consigo mismo y aun
así no significar lo que uno cree.
