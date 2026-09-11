# Diccionario de datos

Capa Gold: los seis archivos que consume el tablero. Una fila por combinacion,
sin ningun dato personal. Generado desde los propios CSV.


## `admision_por_carrera.csv`

244 filas · 14 columnas

| Columna | Valores distintos | Ejemplo | Significado |
|---|---|---|---|
| `ciclo` | 7 | `2021` | Ano de ingreso declarado dentro del PDF, no el ano del examen |
| `carrera` | 47 | `ADMINISTRACION DE EMP…` | Nombre canonico de la escuela profesional, mayusculas sin tilde |
| `postulaciones` | 180 | `269` | Filas de postulacion en el ciclo. No es personas: alguien puede postular varias veces |
| `ingresantes` | 162 | `174` | Postulaciones cuya condicion, leida segun la clase del documento, significa admitido |
| `tasa_ingreso` | 87 | `64.7` | ingresantes / postulaciones, en porcentaje. Vacio si el denominador no es fiable |
| `denominador_fiable` | 2 | `si` | si cuando el acta publica tambien a los no admitidos. no desde 2026 |
| `pct_rechazados` | 158 | `35.3` | Porcentaje de filas con resultado de no admision |
| `nota_corte_ordinario` | 176 | `50.71` | Puntaje del ultimo admitido por examen ordinario. Solo esa modalidad: cada via usa su escala |
| `percentil_corte` | 41 | `0.0` | Posicion relativa del corte dentro de la distribucion del ciclo |
| `escala` | 2 | `anterior` | anterior hasta 2023, nueva desde 2024. Los puntajes no son comparables entre ambas |
| `minimo_institucional` | 17 | `42.605558` | Puntaje minimo para figurar en el acta. No es la nota de corte |
| `puntaje_min` | 180 | `46.88` | Puntaje mas bajo observado entre todos los postulantes del ciclo |
| `puntaje_max` | 210 | `268.04` | Puntaje mas alto observado |
| `puntaje_mediana` | 225 | `75.33` | Mediana de los puntajes del ciclo |

## `cercanos_al_corte.csv`

137 filas · 5 columnas

| Columna | Valores distintos | Ejemplo | Significado |
|---|---|---|---|
| `ciclo` | 5 | `2021` | Ano de ingreso declarado dentro del PDF, no el ano del examen |
| `carrera` | 32 | `ADMINISTRACION DE EMP…` | Nombre canonico de la escuela profesional, mayusculas sin tilde |
| `no_ingresantes` | 82 | `69` | Postulaciones no admitidas con puntaje publicado |
| `a_menos_de_un_punto` | 77 | `68` | No admitidos cuyo puntaje queda a menos de un punto de la nota de corte |
| `porcentaje` | 81 | `98.6` | a_menos_de_un_punto sobre no_ingresantes, en porcentaje |

## `comparador_modalidad.csv`

1170 filas · 9 columnas

| Columna | Valores distintos | Ejemplo | Significado |
|---|---|---|---|
| `ciclo` | 7 | `2021` | Ano de ingreso declarado dentro del PDF, no el ano del examen |
| `carrera` | 47 | `ADMINISTRACION DE EMP…` | Nombre canonico de la escuela profesional, mayusculas sin tilde |
| `modalidad` | 10 | `beca` | Via de ingreso: ordinario, precatolica, distancia, beca, entre otras |
| `postulaciones` | 207 | `37` | Filas de postulacion en el ciclo. No es personas: alguien puede postular varias veces |
| `ingresantes` | 157 | `8` | Postulaciones cuya condicion, leida segun la clase del documento, significa admitido |
| `tasa_ingreso` | 145 | `21.6` | ingresantes / postulaciones, en porcentaje. Vacio si el denominador no es fiable |
| `denominador_fiable` | 2 | `si` | si cuando el acta publica tambien a los no admitidos. no desde 2026 |
| `nota_corte` | 927 | `77.53` | Puntaje del ultimo admitido en esa modalidad |
| `puntaje_mediana` | 978 | `67.57` | Mediana de los puntajes del ciclo |

## `distribucion_puntajes.csv`

4961 filas · 6 columnas

| Columna | Valores distintos | Ejemplo | Significado |
|---|---|---|---|
| `ciclo` | 7 | `2021` | Ano de ingreso declarado dentro del PDF, no el ano del examen |
| `carrera` | 47 | `ADMINISTRACION DE EMP…` | Nombre canonico de la escuela profesional, mayusculas sin tilde |
| `tramo_desde` | 30 | `0` | Limite inferior del tramo de 10 puntos |
| `tramo_hasta` | 30 | `10` | Limite superior del tramo |
| `resultado` | 2 | `no_ingresante` | ingresante o no_ingresante |
| `postulantes` | 136 | `1` | Cuantas postulaciones caen en ese tramo |

## `ocupacion_vacantes.csv`

108 filas · 8 columnas

| Columna | Valores distintos | Ejemplo | Significado |
|---|---|---|---|
| `ciclo` | 4 | `2024` | Ano de ingreso declarado dentro del PDF, no el ano del examen |
| `carrera` | 35 | `Administracion de Emp…` | Nombre canonico de la escuela profesional, mayusculas sin tilde |
| `vacantes` | 57 | `210` | Plazas convocadas segun el cuadro oficial del ciclo |
| `ingresantes` | 87 | `216` | Postulaciones cuya condicion, leida segun la clase del documento, significa admitido |
| `ocupacion` | 89 | `102.9` | ingresantes / vacantes, en porcentaje. Puede superar 100 cuando la fuente difiere |
| `plazas_libres` | 52 | `0` | vacantes menos ingresantes, con piso en cero |
| `cruzo` | 2 | `si` | si cuando el nombre de la carrera pudo cruzarse entre el cuadro de vacantes y las actas |
| `estado` | 1 | `provisional` | provisional: la cifra mezcla la seleccion del centro preuniversitario con la admision ordinaria |

## `trayectoria_postulante.csv`

10 filas · 3 columnas

| Columna | Valores distintos | Ejemplo | Significado |
|---|---|---|---|
| `postulaciones` | 5 | `1` | Filas de postulacion en el ciclo. No es personas: alguien puede postular varias veces |
| `ingreso_alguna_vez` | 2 | `no` | si cuando la persona fue admitida en al menos uno de sus intentos |
| `personas` | 10 | `8645` | Cuantos seudonimos distintos caen en esa combinacion |
