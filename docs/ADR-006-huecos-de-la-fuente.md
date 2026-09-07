# ADR-006 · Los huecos de numeración se contrastan contra el PDF

Estado: aceptado · 2026-09-07

## Contexto

Dos pruebas de reconciliación asumían que el orden de mérito de un bloque va de
1 a N sin saltos. Fallaban en siete filas y la lectura natural era pérdida de
datos.

No lo era. UCSM retira gente de una lista ya ordenada sin renumerar el resto,
así que hay bloques que van 1, 2, 3, 4, 6. El PDF de precatólica 2026-I lo hace
en cuatro carreras y el de precatólica 2026-III en tres seguidas.

La suposición estaba en la prueba, no en los datos.

## Decisión

Cada hueco detectado se contrasta contra el texto del PDF de origen. Si el
ordinal tampoco está ahí, la fuente lo omite y la extracción es fiel. Si está en
el PDF y no en la salida, es pérdida real y la prueba sigue fallando.

La alternativa era excluir esos casos a mano. Se descartó porque una excepción
escrita a mano deja de verse cuando aparece un documento nuevo, y porque
convierte una prueba en una lista de perdones.

Verificar contra el PDF cuesta abrir unos pocos archivos y a cambio la prueba
pasa a afirmar algo cierto: no que la numeración sea continua, sino que la
salida dice lo mismo que la fuente.

## Detalle que costó dos intentos

Un mismo nombre de carrera aparece una vez por subproceso, así que buscarlo en
el texto devuelve varios bloques. Unirlos daba falsos negativos: el ordinal 5
que falta en PSICOLOGÍA de un subproceso existe en el de otro. El bloque
correcto se identifica por su ordinal máximo, que es lo que la base declara.

## Resultado

Nueve huecos verificados como propios de la fuente y dos pérdidas reales que la
versión anterior de la prueba escondía entre el ruido.
