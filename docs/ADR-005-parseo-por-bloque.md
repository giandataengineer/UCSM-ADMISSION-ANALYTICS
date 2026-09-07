# ADR-005 · La unidad de parseo es el bloque, no la página

Estado: aceptado · 2026-09-07

## Contexto

El parser trataba cada página como una tabla: buscaba el primer encabezado,
tomaba la carrera que había encima y aplicaba esa carrera a todas las filas de
la hoja. La sede y el grupo se resolvían igual, una vez por página.

Los procesos con pocos admitidos por carrera no se imprimen así. Apilan varios
bloques cortos en la misma hoja, cada uno con su título de carrera y su propia
línea de encabezado. La página 78 de `Extraordinario20221.pdf` trae seis
bloques y hasta un cambio de subproceso a media hoja: las cuatro primeras
carreras pertenecen al Convenio I y la última al Convenio II.

Con el modelo por página, esas 14 filas se guardaron todas como
INGENIERÍA CIVIL, que era la carrera del primer bloque, y con la sede vacía.
Es la peor clase de error: no faltan filas, están mal atribuidas, y ninguna
prueba de conteo lo ve.

Lo detectó la reconciliación por otra vía. INGENIERÍA CIVIL declaraba orden
máximo 5 y tenía 14 filas, y ADMINISTRACIÓN DE EMPRESAS declaraba 2 con 9.

## Decisión

La unidad de parseo pasa a ser el bloque. `encabezados()` devuelve todos los
encabezados de la página y cada uno delimita un tramo con su propia carrera,
su propia calibración de columnas y su propia nota mínima.

La sede y el grupo dejan de ser atributos de la página y pasan a ser estado que
corre a lo largo del PDF, actualizado donde aparezca una línea de proceso. Un
subproceso que empieza a media hoja se respeta, y las primeras carreras de una
página heredan el proceso que arrancó en la anterior, que es lo que la fuente
quiere decir al no repetir el encabezado.

## Alcance

Tres páginas del corpus tienen más de un encabezado, en dos archivos
(`Extraordinario20221.pdf` y `Aptos2022CCI.pdf`). Es poco volumen y aun así
justifica el cambio: eran filas silenciosamente mal atribuidas, no filas
faltantes, y el modelo por página iba a repetir el error con cada documento
nuevo que use ese formato.

## Consecuencias

Los 11 bloques que no reconciliaban bajaron a 1, y ese último resultó ser otra
cosa: una palabra que cubría dos columnas. La reconciliación quedó en 10/10.

El cambio es una generalización estricta. En una página con un solo encabezado
el tramo abarca toda la hoja y el comportamiento es idéntico al anterior, que
es lo que confirmó la comparación del corpus completo: solo cambiaron los
archivos que se querían arreglar.
