# Plan: documento de correspondencia CCS-BAP y Anexo D

Estado al 2026-11-09: el documento se pasó de LaTeX a Typst, en `crosswalk/main.typ`. Las imágenes
ya están en `crosswalk/images/`, sólo las ocho que se usan. El resto del plan sigue sin ejecutar: no
se aplicaron las correcciones de contenido y no se modificó el Google Doc ni el código.

## Objetivo

1. Terminar `crosswalk/main.typ` como documento autónomo y alineado con `modelo-v0`.

   Sólo muestra qué clase va a qué modelo FBFM40 y con qué procedimiento. No muestra resultados.
2. Reducir el Anexo D del informe a las fichas de lenga y ciprés, con enlace al documento completo.
3. Publicar el PDF con un enlace estable que se pueda citar desde el informe.

Se asume que «estas dos especies» son lenga y ciprés de la cordillera, las dos fichas que hoy
tiene el Anexo D.5.

## 1. Referencia: qué usa modelo-v0

La referencia es el código fijado en la instantánea (`codigo_sha` f710c4b) con la receta
`lw-100-001`. Las tablas `CCSBAP_TO_FBFM40` (28 pares), `CCSBAP_N3_OVERRIDES` (10) y
`CCSBAP_SOBRE_LIMITE_BOSQUE` (1) son idénticas en f710c4b y en el árbol actual.

| # | `main.typ` dice | modelo-v0 usa | Dónde impacta |
|---|---|---|---|
| 1 | `OT Herb-Subarb` → 103 GR3, `mex` 30 | 102 GR2, `mex` 15 | §4, §5.8 |
| 2 | Sin regla de altura | `Ley_N3 = Estepa` sobre 1.300 m → 99 NB9 | §4, §5.8, §8 |
| 3 | `Rem Dist Rec` → 123 GS3 | 143 SH3, `mex` 40 (rebrote leñoso de 6-15 años) | §2 (fila A2), §4, §5.7, §7, §11 |
| 4 | Sólo se usa la capa 2017, y la 2013 queda como referencia | Último mapa anterior al incendio: 2013 en Cholila 2015, Alerces 2015 y Alerces 2016, y 2017 en los otros ocho | §1, §7, §11 |
| 5 | `mex ≥ 25 %` para toda la vegetación nativa | La estepa nativa queda en GR2, `mex` 15 | §2 |
| 6 | Los fundamentos hablan de un incendio de 2026 («once años», «nueve años») | Once casos entre 2015 y 2026 | §5.7, §7, §11 |
| 7 | `LW` = 110 % | `LW` = 100 % | Sale con §6. Es parámetro de la receta, no de la correspondencia |
| 8 | «Tres clases de nivel 2» explican las excepciones | Las diez excepciones están en cinco clases: las tres citadas más `OFL Arbu Na` (Caña) y `OFL Cg` (Cg Juv-Tur) | §3 |

El punto 5 pide reescribir el criterio. Los umbrales de ignición se midieron en ciprés y ñire, así
que `mex ≥ 25 %` debe acotarse a las formaciones leñosas. `docs/crosswalk.md:16-17` tiene la misma
frase y se corrige igual.

`FUEL_BY_BURN_AGE` (LYQ-3, GR1 y SH3 por edad de quema) es posterior a modelo-v0 y no entra en la
tabla. Se menciona en una oración de alcance, porque la aplicación sí la usa.

## 2. Qué queda y qué sale de `main.typ`

Los números de sección son los actuales. Al sacar §6, las siguientes se renumeran solas, porque las
referencias usan etiquetas (`@sec:7`).

| Sección | Acción |
|---|---|
| Introducción | Queda. Quitar «comparaciones con el comportamiento observado y simulado». Decir que las fichas cubren las clases principales, y que las menores sólo figuran en la tabla |
| §1 El insumo, §1.1 | Quedan, corrigiendo el punto 4 |
| §1.2 «Por qué este insumo es el aporte» | Sale la tabla comparativa. Queda una oración sobre por qué se eligió CCS-BAP |
| §2 Método | Queda, corrigiendo los puntos 3 y 5 |
| §3 Clave | Queda, corrigiendo el punto 8. Quitar la referencia a S4 |
| §4 Tabla | Queda, corrigiendo los puntos 1 a 3. El `% AOI` describe el insumo y no es un resultado |
| §5 Fichas | Quedan. Reescribir §5.7 y §5.8. Quitar menciones a baseline, IGN-20, Etapa C y S1-S3 |
| §6 Resultado, §6.1, §6.3 | Salen completas |
| §6.2 Quema experimental | Sale como sección. Ver la decisión A |
| §7.1 Limitaciones | Quedan, sin Etapa C y corrigiendo los puntos 4 y 6 |
| §7.2 Sensibilidades a evaluar | Sale. S3 ya no aplica y el resto es trabajo futuro |
| §8 Verificación | Quedan los controles de código y el cotejo de la tabla. Salen el cuadro de evidencia de resultados y los comandos |
| §9 Glosario | Queda, sin FLI |
| §10 Fuentes | Quedan las citadas. Agregar las que respaldan SH3 (Tiribelli, Blackhall), con la cita corregida según `INCONSISTENCIAS.md` §2.1 |
| §11 Supuestos | Queda, corrigiendo los puntos 3, 4 y 6 |

Limpieza necesaria antes de publicar:

- Reemplazar el enlace firmado de Notion de §2. Expira y expone identificadores de la cuenta.
- Quitar las rutas locales que el lector no puede abrir, como `RESULTADOS.md`,
`ETAPA-B-INSUMO-PATAGONICO.md` e `IGN-20B-CROSSWALK-CCSBAP.md`.
- Limpiar los comentarios del `.typ` que nombran `IGN-20B` y `main.tex`, porque la fuente va a un
repo público.
- Actualizar la fecha del encabezado (28 de septiembre) y agregar versión y commit de referencia.
- Confirmar en Wikimedia Commons la licencia exacta de las dos fotos de ñire. Hoy dice «licencia
abierta indicada en las páginas de origen». Páginas:
[formación](https://commons.wikimedia.org/wiki/File:Nothofagus_antarctica_en_Reserva_Nacional_Coyhaique.JPG)
y [rama](https://commons.wikimedia.org/wiki/File:Nothofagus_antarctica_-_rama_con_brotes.JPG).

## 3. Anexo D reducido

| Parte | Acción |
|---|---|
| D.1 Principio | Se condensa en un párrafo y agrega el enlace al documento completo |
| D.2 Tabla 32 | Queda, con las correcciones de abajo |
| D.3 Dosel y Tabla 33 | Queda. El documento completo no cubre dosel, y §3.2 del informe cita esta tabla |
| D.4 Incertidumbre | Se queda el planteo de hipótesis auditable. Salen los resultados, que ya están en el cuerpo |
| D.5 Fichas | Quedan lenga y ciprés, reescritas con el texto corregido de `main.typ` |

Errores actuales contra modelo-v0:

- **Tabla 34, lenga:** dice «Familia TU cuando existe bosque con sotobosque». `TF Le` es siempre
TL6, como dice la propia Tabla 33.
- **Tabla 35, ciprés:** dice que la variante «depende de la continuidad del sotobosque». `TF Ci` es
TU5 y `OFL Ci` es SH4, sin otra variante.
- **Tabla 32, bosque:** «Bosque nativo con sotobosque → TU» no representa a la lenga. Agregar una
fila para TL6.
- **Tablas 32 y 34, altura:** la regla de 1.300 m se aplica sólo a la clase `Estepa`, no a toda la
alta montaña.
- **Tabla 32, pérdida de bosque:** mezcla dos reglas. `Rem Dist Rec` va a SH3. La pérdida de Hansen
previa al incendio anula el dosel y, en modelo-v0, no cambia el combustible.

También hay que actualizar la cita de la Tabla 28 (Anexo A), que apunta a
`docs/crosswalk/DECISIONES-MODELO-V0.md`, una ruta que ya no existe. Los cambios en el Doc siguen el
flujo de `informe-gdoc`: propuesta old/new, aprobación y aplicación.

## 4. Publicación

**Recomendación: PDF en Drive, como propusiste.** Alcanza para la entrega y es lo más simple. Con
estas condiciones:

- Subirlo desde la cuenta dueña del informe (nachochevallier@gmail.com), con acceso de lector para
cualquiera con el enlace.
- Actualizarlo siempre con «Administrar versiones», que conserva el enlace. Subir un archivo nuevo
lo rompe.
- Probar el enlace en una ventana de incógnito.
- Imprimir la URL visible en el Anexo D, porque el informe puede leerse en papel.
- Citarlo en APA como documento técnico propio, con versión y fecha, y sumarlo a la Tabla 28.

El `.typ` queda en el repo como fuente. Se versionan `crosswalk/main.typ` y `crosswalk/images/`
(3,1 MB). `crosswalk/main.pdf` se genera y se publica en Drive, así que va al `.gitignore`.

No se automatiza la coincidencia entre la tabla y el código: modelo-v0 está congelado y esta tabla
sólo cambia con un modelo-v1. El control es un cotejo manual al cerrar el documento.

## 5. Orden de trabajo

1. Resolver las decisiones abiertas.
2. Editar `main.typ`, primero las correcciones de la sección 1 y después los recortes de la 2.
3. Corregir la frase de `mex` en `docs/crosswalk.md`.
4. Cotejar las tablas §4 contra los 28 pares, las 10 excepciones y la regla de altura.
5. Compilar con `typst compile crosswalk/main.typ`. Una referencia `@sec:` rota corta la
   compilación, así que los recortes quedan controlados. Buscar en el `.typ` «baseline», «IGN-20»,
   «harness», «Etapa C» y «Dice».
6. Revisión tuya y, si corresponde, del director. Es el aporte de la tesis.
7. Subir a Drive y probar el enlace.
8. Proponer los cambios del Anexo D con el enlace definitivo y aplicarlos una vez aprobados.

## 6. Decisiones abiertas

**A. ¿Queda el contraste con la quema experimental de la PT-37?** Propuesta: sí, resumido en
Método y en la ficha de SH8, sin la tabla de §6.2. Es el paso 4 del procedimiento y mide los modelos
contra una quema real, no el desempeño de modelo-v0. Sin él se pierde el sesgo declarado de SH8. SH3
no fue parte de ese ensayo, y hay que decirlo.

**B. ¿Cómo se declara que GR2, NB9 sobre 1.300 m y SH3 se revisaron durante la calibración?**
Propuesta: una oración de procedencia en esas fichas, sin cifras, que remita al informe. Omitirlo
presentaría como puramente bibliográficas decisiones que también usaron resultados.

**C. ¿Hace falta un DOI?** Propuesta: no para la entrega. Si después se quiere citar como propuesta
original fuera de la tesis, se deposita el PDF en Zenodo. Es difícil de deshacer, por lo que
conviene hacerlo con la versión aprobada por el director.
