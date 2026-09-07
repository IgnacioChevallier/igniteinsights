# Etapa C — Modelos de combustible patagónicos propios

> Estado: **condicionada**, fuera del camino crítico de la tesis
> Depende de: Etapa B completa **y** de conseguir parámetros medidos
> Bloqueada por: disponibilidad de CIEFAP Publicación Técnica N.º 37 (no está en nuestro poder)

## Objetivo

Dejar de mapear la vegetación patagónica a los 40 modelos de combustible estadounidenses y
**parametrizar el modelo de Rothermel directamente** con cargas, profundidades y humedades de
extinción medidas en Patagonia, cargando la tabla resultante en ELMFIRE.

Es el aporte más fuerte posible, y también el único que puede quedar sin respaldo si los datos
de campo no aparecen. Por eso está documentado pero **no es camino crítico**: la Etapa B se
sostiene sola.

## Precedente: no sería el primero

Chile hizo exactamente esto. El **sistema KITRAL**, desarrollado por el Laboratorio de
Incendios Forestales de la Facultad de Ciencias Forestales de la Universidad de Chile a
mediados de los años 90 bajo la dirección de Guillermo Julio, tiene su **propio conjunto de
modelos de combustible** para vegetación chilena — incluyendo formaciones de *Nothofagus* —
en lugar de importar los modelos norteamericanos. Su simulador se apoya en cartografía
nacional de modelos de combustible propia, y opera en coordinación con CONAF.

Es el argumento de autoridad más sólido disponible para justificar la decisión: **el país
vecino, con la misma vegetación y el mismo problema, concluyó que los modelos estadounidenses
no alcanzaban y construyó los propios.**

## Viabilidad técnica: es la parte barata

Verificado en el fuente de ELMFIRE 2025.0212 (`build/source/elmfire_init.f90`,
`build/source/elmfire_namelists.f90`):

- El namelist expone `FUEL_MODEL_FILE` en el grupo `&MISCELLANEOUS`, junto con
  `MISCELLANEOUS_INPUTS_DIRECTORY`.
- Si no se lo pasa (`'null'`), ELMFIRE **escribe** su tabla por defecto en `fuel_models.csv`.
  Si se lo pasa, lee la nuestra.
- La tabla admite índices **0–303**.
- Todo código presente en el raster y ausente de la tabla cae al modelo **256 (`NB`)**, no
  combustible, **en silencio**.

Si la Etapa A se hizo, ya emitimos nuestro propio `fuel_models.csv` y ya validamos que todo
código emitido existe en la tabla. **El cableado de esta etapa ya está hecho**: agregar
modelos propios es agregar filas.

**El trabajo real de esta etapa no es de software. Es conseguir los números.**

---

## C0 — Puerta de decisión: ¿existen los parámetros?

Referencia principal: **Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. —
*Modelos de combustibles en el ecotono bosque-estepa de la Patagonia andina: caracterización
de las asociaciones arbustivas de acuerdo a su respuesta al fuego*. CIEFAP, Publicación
Técnica N.º 37, Esquel, 45 pp.** Citada como Bianchi et al. (2012) por Godoy et al. (2022),
que además señalan que hacen falta más modelos porque los existentes cubren *"unos pocos tipos
de vegetación del ecotono bosque-estepa en Chubut"*.

Estado: **no está en nuestro poder.** Obtenerla es el primer paso.

Vías: biblioteca de CIEFAP (info@ciefap.org.ar), el portal de publicaciones técnicas de
CIEFAP, o el director por vía institucional.

### Parámetros que ELMFIRE exige por modelo

Una fila del CSV, en este orden y sin encabezado:

```
num, shortname, dynamic, w0_1h, w0_10h, w0_100h, w0_liveherb, w0_livewoody,
     sav_1h, sav_liveherb, sav_livewoody, depth_ft, mex_dead_pct, hoc_btu_lb
```

| Parámetro | Unidad | Cómo se obtiene |
|---|---|---|
| Carga 1 h / 10 h / 100 h | lb/ft² (`t/ac × 0,0459137`) | Inventario de combustible muerto caído, método de intercepción planar (Brown 1974) |
| Carga herbácea viva / leñosa viva | lb/ft² | Parcelas de corte y pesado en seco |
| SAV 1 h / herbácea viva / leñosa viva | 1/ft | Medición de partículas, o asignación por analogía con especies de morfología similar |
| Profundidad del lecho | ft | Medición directa en campo |
| Humedad de extinción | % | **Aquí sí hay dato patagónico medido** (ver abajo) |
| Calor de combustión | BTU/lb | Bomba calorimétrica; 8000 es el valor estándar de todo el set SB40 |

Constantes internas de ELMFIRE, no configurables por fila: SAV 10 h = 109 1/ft,
SAV 100 h = 30 1/ft, densidad de partícula = 32 lb/ft³, contenido mineral total = 0,055,
contenido mineral efectivo = 0,01. Coinciden con los valores fijos que declaran Scott &
Burgan (2005, p. 2) para todo el conjunto.

### Criterio de decisión

- **Si PT-37 tiene cargas por clase de tamaño, profundidad y las asociaciones cubren las
  clases dominantes del AOI** → la etapa es ejecutable. Adelante.
- **Si sólo tiene caracterización cualitativa o parcial** → se puede construir un subconjunto
  de modelos propios para las clases cubiertas y mantener SB40 para el resto, declarando la
  mezcla. Es aceptable si se documenta.
- **Si no hay cargas medidas utilizables** → **la etapa no se ejecuta.** Estimar cargas sin
  respaldo para después presentarlas como aporte es peor que no hacerlo: es exactamente el
  tipo de decisión que se cae en una defensa. En ese caso pasa a *trabajo futuro*, con el
  diseño ya documentado acá y el requerimiento de campo especificado, que también es un
  entregable legítimo.

**Esta puerta se atraviesa antes de escribir una sola línea de código.**

---

## C1 — Definir el conjunto de modelos

1. Partir de las clases dominantes por área del mapa de la Etapa B, no de la leyenda completa.
   Un modelo propio para una clase que ocupa el 0,5 % del AOI no cambia nada y cuesta lo mismo.
2. Agrupar clases que compartan estructura de lecho de combustible. Scott & Burgan agruparon
   ~60 complejos de combustible y luego **eliminaron modelos cuyo comportamiento predicho
   resultaba indistinguible** de otros (p. 3-4). Mismo criterio: dos modelos que producen la
   misma tasa de propagación y longitud de llama son un modelo.
3. Asignar números **dentro de los bloques que Scott & Burgan reservan para modelos custom**
   (2005, p. 5, Tabla 1), para que el código conserve su semántica de tipo de combustible:

   | Tipo | Bloque disponible para custom |
   |---|---|
   | NB | 90, 96-97 |
   | GR | 100, 113-119 |
   | GS | 120, 131-139 |
   | SH | 140, 153-159 |
   | TU | 160, 171-179 |
   | TL | 180, 193-199 |
   | SB | 200, 211-219 |
   | (sin tipo) | 14-89, 220-256 |

   ELMFIRE admite hasta 303, pero **mantenerse en 1-256 preserva la convención de 8 bits** que
   Scott & Burgan adoptaron deliberadamente para aplicaciones cartográficas, y mantiene el
   raster interoperable con herramientas estándar. Salir de ese rango sin necesidad es deuda
   gratuita.

4. Nombre corto de hasta la longitud que acepta el CSV, mnemotécnico y trazable a la clase de
   origen.

---

## C2 — Parametrizar

1. Volcar los valores medidos a las unidades de ELMFIRE. **Verificar la conversión con un
   caso conocido**: TL3 son 0,50 t/ac de carga 1 h y en la tabla de ELMFIRE figura como
   `0.02296`; el factor es `0,0459137`.
2. Humedad de extinción: usar los umbrales de ignición medidos por Bianchi & Defossé —
   **21,5 % para ciprés y 25,0 % para ñire** — en lugar de heredar el valor de un modelo
   estadounidense. Es el parámetro con respaldo local más directo y el que Scott & Burgan
   (2005, p. 5) reconocen como asociado al clima *"aunque la investigación aún no ha explicado
   el mecanismo de la asociación"*. Esa admisión de los propios autores es la justificación
   textual para recalibrarlo con datos regionales.
3. Fijar el flag `dynamic` según haya o no carga herbácea viva. Scott & Burgan (p. 4): usar un
   modelo dinámico en un procesador no dinámico hace que **no propague**. ELMFIRE sí lo
   implementa; el riesgo es equivocarse al escribir la fila.
4. Documentar cada parámetro con su procedencia: medido, derivado, o asumido por analogía. La
   proporción de parámetros asumidos es un resultado en sí mismo y define el alcance de lo que
   se puede afirmar.

---

## C3 — Cargar en ELMFIRE

Con la Etapa A hecha, esto es agregar filas al CSV versionado y las entradas correspondientes
al crosswalk. Nada más. La validación de A3 verifica automáticamente que no queden códigos
huérfanos.

Verificación adicional específica de esta etapa: comprobar que ELMFIRE **no sobrescribe**
nuestro archivo. `WRITE_FUEL_MODEL_TABLE` sólo escribe cuando `FUEL_MODEL_FILE` vale `'null'`,
pero conviene confirmarlo en corrida real antes de confiar en el resultado.

---

## C4 — Validar

Mismo protocolo que B6, agregando el mapa con modelos propios como punto adicional de
comparación: IoU sobre el anillo de crecimiento, estratificado, sin tocar `ADJ`.

Comparación de interés para la tesis: `IoU(SB40 con crosswalk fundamentado)` contra
`IoU(modelos propios)`. Si los modelos propios **no** mejoran sobre el crosswalk fundamentado,
eso responde una pregunta valiosa — dice que la ganancia estaba en el insumo de cobertura y no
en la parametrización, lo que orienta el esfuerzo futuro y es publicable.

---

## Criterio de abandono

Esta etapa se abandona sin culpa, y se reporta como trabajo futuro con el diseño ya
especificado, si se cumple cualquiera de estas condiciones:

1. PT-37 no se consigue, o no contiene cargas por clase de tamaño.
2. Las asociaciones cubiertas por la bibliografía no coinciden con las clases dominantes del
   AOI de Los Alerces (PT-37 es del **ecotono bosque-estepa**, y Los Alerces es
   mayoritariamente bosque húmedo — es un riesgo real de solape insuficiente).
3. El calendario de la tesis no permite cerrar la Etapa B con validación.

Abandonarla no debilita la tesis: el núcleo del aporte es el crosswalk fundamentado y su
demostración cuantitativa. Esta etapa es techo, no piso.

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| PT-37 caracteriza el **ecotono bosque-estepa**, no bosque húmedo | Evaluar el solape en C0 antes de comprometerse; puede cubrir sólo el borde este del AOI |
| Faltan SAV, que rara vez se miden | Asignar por analogía con modelos SB40 de morfología comparable y **declararlo** |
| Parámetros estimados presentados como medidos | Columna de procedencia obligatoria por parámetro |
| Los modelos propios no mejoran el resultado | Es un resultado válido y publicable, no un fracaso |
| Rothermel sigue siendo el modelo subyacente | Parametrizar mejor no arregla los supuestos de homogeneidad y continuidad; declararlo |

## Decisiones registradas

| Decisión | Elegida | Motivo |
|---|---|---|
| Prioridad | Extensión condicionada, no camino crítico | PT-37 no está disponible hoy |
| Numeración | Bloques custom de Scott & Burgan dentro de 1-256 | Preserva semántica de tipo y compatibilidad de 8 bits |
| Sin datos medidos | No ejecutar | Estimar y presentarlo como aporte no resiste una defensa |
| Cableado en ELMFIRE | Ya resuelto en Etapa A | Emitir tabla propia desde el arranque lo deja listo |

## Fuentes

- ELMFIRE 2025.0212, `build/source/elmfire_init.f90` y `build/source/elmfire_namelists.f90` —
  <https://github.com/lautenberger/elmfire>
- Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. *Modelos de combustibles en el
  ecotono bosque-estepa de la Patagonia andina.* CIEFAP, Publicación Técnica N.º 37, Esquel.
  **(pendiente de obtener)**
- Bianchi, L.O.; Defossé, G.E. *Ignition probability of fine dead surface fuels of native
  Patagonian forests of Argentina.* Forest Systems. —
  <https://fs.revistas.csic.es/index.php/fs/article/view/4632>
- Scott, J.H.; Burgan, R.E. (2005). RMRS-GTR-153. (Parámetros constantes: p. 2; bloques de
  numeración custom: p. 5, Tabla 1; criterio de eliminación de modelos redundantes: pp. 3-4;
  modelos dinámicos: p. 4)
- Brown, J.K. (1974). *Handbook for inventorying downed woody material.* GTR INT-16.
- Sistema KITRAL — Laboratorio de Incendios Forestales, Facultad de Ciencias Forestales y
  Conservación de la Naturaleza, Universidad de Chile.
- Godoy, M.M. et al. (2022). Frontiers in Forests and Global Change. —
  <https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2022.850543/full>
