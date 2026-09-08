# ADR-007 · Un PDF sin filas necesita una razón verificada

Estado: aceptado · 2026-09-07

## Contexto

La auditoría reportaba «35 de 151 PDFs no producen filas» como un aviso único.
El número era grande, sonaba a límite conocido de la fuente y llevaba semanas
sin mirarse de cerca.

Al abrirlos uno por uno, los 35 eran tres cosas distintas. Diecinueve listas de
aptitud, que dicen quién puede rendir el examen y no son resultados. Cuatro
instructivos. Y doce tablas de resultados reales que el parser no estaba
leyendo: los del área de ciencias de la salud de 2021 a 2023, las precatólicas
de esa misma área y los convenios de 2022 y 2023.

La causa era trivial. Esos documentos rotulan sus columnas en mayúsculas
(`NOMBRE`, `CONDICIÓN`, `PUNTAJE FINAL`) y el diccionario de rótulos solo
declaraba las formas capitalizadas. Sin `nombre` entre las anclas, la línea no
se reconocía como encabezado y el archivo entero salía vacío.

## Decisión

Se declaran las variantes en mayúsculas, y la auditoría deja de contar PDFs sin
filas para pasar a **clasificar cada uno por su motivo**, leído del propio
documento. Si aparece uno que no encaja en ningún motivo conocido, la auditoría
falla en vez de avisar.

Un aviso agregado esconde; una falla por caso obliga a mirar.

## Consecuencias

De 116 a 136 PDFs con datos, y 1 009 filas recuperadas.

Los 15 restantes quedan clasificados: nueve listas de aptitud, cinco
instructivos y `TercioSuperior2022final.pdf`, que se comprobó redundante porque
sus 145 personas ya están en `TercioSuperior2022.pdf`, que además publica los
226 no ingresantes que el «final» omite.

El aprendizaje es sobre la forma del control, no sobre los rótulos. La cifra
agregada llevaba tiempo visible sin que nadie la cuestionara, precisamente
porque parecía explicada.
