# ADR-003 · Lo que la validación corrigió del modelo

**Fecha:** 7 de setiembre de 2026
**Estado:** aceptada
**Contexto:** reconciliación de lo extraído contra lo que publican los PDFs

## Decisión

Se construye una suite de reconciliación en DuckDB que contrasta cada fila
contra las redundancias que el propio documento publica. Corre con
`python ExtraccionPDF/11_Validacion.py` y falla si el resultado deja de ser
fiel a la fuente.

## Los cuatro errores que encontró

### 1. `Nota Mínima` no es la nota de corte

Se estaba usando como corte de carrera. No lo es: es el puntaje mínimo
institucional para calificar, y el documento publica **el mismo valor para
todas las carreras**. En `EG2023I.pdf` es 45.647 en las 27.

El corte real es el puntaje del último admitido. La prueba que lo destapó fue
"ningún NO INGRESO por encima de la nota mínima": daba 8 342 filas incumpliendo,
porque casi todo rechazado supera el mínimo institucional.

### 2. Faltaban dos dimensiones: sede y grupo

Un documento repite la misma carrera muchas veces y cada bloque reinicia el
orden de mérito desde 1. `precatolica2021-I.pdf` trae MEDICINA HUMANA en 16
bloques distintos, todos con un orden 6.

Lo que los separa es la **sede** y el **grupo de postulante**:

```
Pág. 19   PRECATOLICA 2021-I - AREQUIPA   PRIMERA POSTULACION
Pág. 40   PRECATOLICA 2021-I - AREQUIPA   EGRESADO SECUNDARIA
Pág. 52   PRECATOLICA 2021-I - ILO        PRIMERA POSTULACION
```

Aparecieron **ocho sedes**: Arequipa, Camaná, Characato, Ciudad de Dios, Ilo,
Juliaca, Puno y Tacna. Con el grano corregido los duplicados pasaron de 18 885
a cero.

### 3. El corte no se puede calcular mezclando modalidades

Cada modalidad califica en su propia escala. Al mezclarlas, Medicina 2022 daba
un corte de 23.0 cuando el mínimo institucional de ese año era 45.84.

El corte por carrera se calcula ahora solo sobre examen ordinario, y el corte
por modalidad vive en `comparador_modalidad.csv`, que es donde la cifra
significa algo. Para Medicina 2022: 100.54 por ordinario y 224.51 por
precatólica.

### 4. En Medicina, aprobar el examen no es ingresar

Medicina Humana tiene 1 080 postulantes por ordinario en 2021 y cero
`INGRESO`. No es un fallo de extracción: su condición es `TEST + ENTREVISTA`,
una etapa siguiente. Contar solo `INGRESO` subestima a esa carrera.

## Estado de las pruebas

Cinco de diez aprueban sobre las 64 077 filas. Las que no, y por qué:

| Prueba | Estado | Causa |
|---|---|---|
| aritmética `nota_01 + nota_02 = total` | aprueba | — |
| ningún INGRESO bajo el mínimo institucional | aprueba | — |
| orden de mérito arranca en 1 | aprueba | — |
| unicidad por sede, grupo, carrera y orden | aprueba | — |
| puntaje en rango plausible | aprueba | — |
| total = componente presente cuando falta uno | falla | Precatólica publica más componentes que los dos que trae el encabezado |
| sin huecos en el orden | falla | 185 bloques, concentrados en becas, distancia y extraordinario |
| un solo mínimo por documento | falla | `Extraordinario2025I.pdf` cubre dos subprocesos con mínimos distintos |
| código con forma válida | falla | 44 filas de `EG2023IIsalud.pdf` mezclan código y nombre |
| cobertura: orden máximo = filas extraídas | falla | mismos 185 bloques |

Las cinco que fallan están cuantificadas y acotadas a familias concretas de
archivo. Se dejan reportando en rojo a propósito: una suite ajustada para pasar
no sirve de nada.

## Consecuencias

El grano de la capa Silver es **archivo × sede × grupo × carrera × orden**.

Ninguna cifra del tablero sale de `nota_minima`. Los agregados publican
`nota_corte_ordinario` y `minimo_institucional` como campos separados, para que
no vuelvan a confundirse.
