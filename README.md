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
  6_ExtraccionTablas.py          [pendiente] reconstrucción de filas por coordenadas
  7_NormalizacionDatos.py        [pendiente] esquema único + seudonimización
  8_AnalisisExploratorio.ipynb   [pendiente]
  data/
    manifest.csv                 223 filas: una por PDF de resultados descubierto
    auditoria.csv                221 filas: contenido real de cada PDF
    carreras_por_ciclo.csv       47 carreras × 9 ciclos
    vacantes.csv                 vacantes 2027 por carrera y modalidad
    documentos_base.csv          38 documentos normativos indexados
    raw/<ciclo>/                 221 PDFs de resultados por año de ingreso
    documentos_base/<año>/       vacantes, reglamento, temario, cronograma
  data_extraida/                 [vacío] salida del parser
  data_normalizada/              [vacío] listo para el warehouse
docs/INVENTARIO.md               tabla detallada de los 221 PDFs de resultados
```

## Reproducir

```bash
pip install -r requirements.txt
python ExtraccionPDF/1_DescubrimientoDescarga.py   # ~5 min, 47 MB
python ExtraccionPDF/2_AuditoriaCorpus.py
python ExtraccionPDF/3_CatalogoCarreras.py
python ExtraccionPDF/5_DocumentosBase.py           # 22 MB de normativa
python ExtraccionPDF/4_Vacantes.py
```

Los PDFs no están versionados. Se reconstruyen con el primer script.

## El corpus

220 PDFs, 47 MB, 5 501 páginas, ciclos de admisión 2016 a 2027.

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

**Dos familias de PDF.** 98 archivos vienen de Excel/Word con object streams;
88 del generador del sistema de admisión, que usa fuentes subset con ToUnicode.
Son dos parsers distintos y el más laborioso cubre la mayoría del corpus.

**Siete esquemas distintos.** El más completo es
`Condición | Código | Nombre | Nota 01 | Nota 02 | Ord. | Total` (52 archivos).
El más pobre es `Condición | Nombre | Ord. | Total` (26 archivos). El
normalizador tiene que detectar el esquema leyendo los encabezados, nunca
asumirlo.

**El esquema rico empieza en 2019.** Los 34 archivos de 2016 a 2018 son todos
de Office, sin `Código` ni notas desagregadas.

**El `Código` desaparece en 2026.** Presente en 12 de 12 PDFs legibles de 2021,
en 12 de 17 de 2025, en 1 de 19 de 2026 y en ninguno de 2027. El análisis de
cohortes, que es seguir a la misma persona entre procesos, solo es viable
**2021-2024**.

**66 PDFs traen el denominador.** Es decir, listan `NO INGRESO` además de
`INGRESO`, lo que permite calcular tasas de admisión reales y no solo contar
ganadores. Concentrados en 2022-2025.

### Cobertura por ciclo

| Ciclo | PDFs | DEVEXP | Office | Con denominador |
|---|---|---|---|---|
| 2016-2018 | 34 | 0 | 34 | 0 |
| 2019 | 23 | 5 | 18 | 3 |
| 2020 | 13 | 4 | 9 | 3 |
| 2021 | 21 | 15 | 6 | 9 |
| 2022 | 28 | 16 | 12 | 9 |
| 2023 | 25 | 15 | 10 | 12 |
| 2024 | 26 | 19 | 5 | 15 |
| 2025 | 22 | 17 | 4 | 11 |
| 2026 | 22 | 19 | 3 | 4 |
| 2027 | 6 | 6 | 0 | 0 |

2027 es el ciclo en curso: se completa conforme UCSM publique.

## Decisiones de arquitectura

Registradas en `docs/`, con la medición que las sostiene.

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

38 documentos oficiales, 22 MB, uno por año de 2016 a 2027, en
`data/documentos_base/<año>/`:

| Documento | Cobertura | Para qué sirve |
|---|---|---|
| `vacantes.pdf` | 2016-2027, completo | Plazas por carrera y modalidad. Es el denominador. |
| `temario.pdf` | 2016-2027, completo | Qué se evalúa. Explica saltos en las notas. |
| `reglamento.pdf` | 2016-2021 y 2027 | Reglas del proceso. Los PDFs citan sus artículos. |
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

47 carreras distintas entre 2019 y 2027. La oferta no es fija: **Ingeniería en
Inteligencia Artificial** e **Ingeniería Biomédica** aparecen recién en el ciclo
2026; **Turismo y Hotelería** dejó de convocarse después de 2021. Una serie
temporal por carrera tiene que distinguir "no se convocó" de "nadie postuló", y
para eso está `carreras_por_ciclo.csv`.

## Fuente

Dirección de Admisión, Universidad Católica de Santa María — ucsm.edu.pe
Enumeración histórica vía Internet Archive Wayback CDX API.
Este análisis no es institucional ni está avalado por la UCSM.
