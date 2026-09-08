# ADR-008 · Un segundo método que no comparta código con el primero

Estado: aceptado · 2026-09-07

## Contexto

Las tres suites que había comprobaban que la salida fuera coherente consigo
misma y con las redundancias que el PDF publica. Es mucho, pero tiene un punto
ciego: todas leen los datos por el mismo camino. Si el parser interpreta mal
una página entera de forma consistente, la aritmética cierra igual y ninguna se
entera.

La pregunta que faltaba no era «¿es coherente?» sino «¿cuenta lo mismo que el
documento?».

## Decisión

`14_ContrasteIndependiente.py` cuenta las filas de cada página sin usar el
parser. Donde el parser reconstruye la tabla por coordenadas de carácter, esta
prueba toma el texto plano que entrega pdfplumber y lo mide con expresiones
regulares, que es la forma tosca y directa de hacerlo.

La comparación es por página, no por archivo. Dos errores que se compensan
entre páginas dan el mismo total y distinto detalle.

## Lo que encontró

Arrancó en 97.58% y cada punto que faltaba era un hallazgo:

- Tablas que continúan en la página siguiente sin repetir el encabezado. El
  parser exigía uno en cada página y descartaba el resto enteras. En
  `EG2022Isalud` eran tres de cuatro páginas. **Se recuperaron 5 523 filas.**
- `INGRESÓ` con tilde, que el vocabulario de condiciones no reconocía y dejaba
  una página entera fuera. Ahora se compara sin tildes.
- Nombres cortos que terminan antes de que empiece el rótulo de su columna y
  caían en la anterior. El desempate pasó a medir distancia al intervalo del
  rótulo en vez de entre centros.
- Una columna que producía dos grupos de calibración porque `INGRESO` y
  `NO INGRESO` arrancan siete puntos distintos, lo que anulaba la calibración
  del documento entero.

También corrigió a la propia prueba tres veces: la fuente trae su codificación
rota de varias formas (`MU?OZ` por una eñe, `ZU&NTILDE;IGA` sin convertir la
entidad HTML) y el contador no las reconocía. Cuando los dos métodos difieren,
el equivocado puede ser cualquiera de los dos.

## Resultado

**4 974 de 4 974 páginas de resultados coinciden.** Las listas de aptitud se
contrastan aparte y se reportan como aviso: no forman parte del conjunto
analítico y su maquetación cambia de un año a otro.
