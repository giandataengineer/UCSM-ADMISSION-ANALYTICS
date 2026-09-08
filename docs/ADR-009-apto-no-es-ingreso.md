# ADR-009 · «Apto» no es «ingresó»

Estado: aceptado · 2026-09-07

## Contexto

La UCSM publica dos clases de documento que se parecen mucho. Uno lista quién
puede rendir el examen; el otro, quién ingresó. Los dos usan la palabra `APTO`.

En un acta de resultados `APTO` se opone a `NO INGRESO` y significa admitido.
En una lista previa se opone a `NO APTO` y solo significa que la persona reúne
los requisitos para presentarse.

El normalizador traducía las dos con el mismo diccionario, así que **414
personas que solo habían sido declaradas aptas para dar el examen aparecían
como ingresantes**. No es un error de extracción: cada fila era fiel a su PDF.
Es un error de modelo, del tipo que ninguna prueba de integridad detecta porque
todos los números cierran.

## Decisión

El significado depende del documento, así que la traducción también. Hay dos
diccionarios y la clase del documento decide cuál se aplica. Las filas de una
lista de aptitud reciben `apto_para_rendir` o `no_apto` y su campo `ingreso`
queda vacío, que es distinto de cero: nunca hubo un resultado de admisión que
registrar.

La clase se determina en dos pasos, y hacen falta los dos. El vocabulario de
condiciones del propio documento basta cuando publica esa columna. Cuando no la
publica, que es el caso de varias listas de no aptos, vale lo que el documento
declara en su portada, que el parser registra al leerlo.

Se descartó decidirlo por el nombre del archivo: hay listas de aptitud que no
se llaman «Aptos» y actas que sí.

## Consecuencias

28 documentos y 2 048 filas quedan fuera del conteo de admisiones sin salir del
conjunto de datos.

Las tres suites tuvieron que aprender la misma distinción. La reconciliación
exigía a esos documentos un orden de mérito que no tienen, y la auditoría
contaba como pérdida las filas que se descartan porque su columna de carrera
trae el rótulo del encabezado. Separadas por clase, la tasa de descarte real
sobre actas de resultados es de 0.04%.
