# Etapa C — Modelos de combustible patagónicos propios

> Estado: **condicionada**, fuera del camino crítico de la tesis
> Depende de: Etapa B completa **y** de conseguir parámetros medidos
> Puerta C0: **evaluada el 2026-09-13** con la PT-37 en mano → rama *parcial* (ver C0). No
> alcanza para modelos propios completos; habilita un ajuste acotado de SB40 en arbustales.

## Objetivo

Dejar de mapear la vegetación patagónica a los 40 modelos de combustible estadounidenses y
**parametrizar el modelo de Rothermel directamente** con cargas, profundidades y humedades de extinción medidas en Patagonia, cargando la tabla resultante en ELMFIRE.

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

Es el argumento de autoridad más sólido disponible para justificar la decisión: **el país vecino, con la misma vegetación y el mismo problema, concluyó que los modelos estadounidenses no alcanzaban y construyó los propios.**

## Viabilidad técnica: es la parte barata

Verificado en el fuente de ELMFIRE 2025.0212 (`build/source/elmfire_init.f90`,
`build/source/elmfire_namelists.f90`):

- El namelist expone `FUEL_MODEL_FILE` en el grupo `&MISCELLANEOUS`, junto con
`MISCELLANEOUS_INPUTS_DIRECTORY`.
- Si no se lo pasa (`'null'`), ELMFIRE **escribe** su tabla por defecto en `fuel_models.csv`.
Si se lo pasa, lee la nuestra.
- La tabla admite índices **0–303**.
- Todo código presente en el raster y ausente de la tabla cae al modelo **256 (**`NB`**)**, no
combustible, **en silencio**.

Si la Etapa A se hizo, ya emitimos nuestro propio `fuel_models.csv` y ya validamos que todo
código emitido existe en la tabla. **El cableado de esta etapa ya está hecho**: agregar
modelos propios es agregar filas.

**El trabajo real de esta etapa no es de software. Es conseguir los números.**

---



## C0 — Puerta de decisión: ¿existen los parámetros?

Referencia principal: **Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. — *Modelos de combustibles en el ecotono bosque-estepa de la Patagonia andina: caracterización de las asociaciones arbustivas de acuerdo a su respuesta al fuego*. CIEFAP, Publicación Técnica N.º 37, Esquel, 45 pp.** Citada como Bianchi et al. (2012) por Godoy et al. (2022), que además señalan que hacen falta más modelos porque los existentes cubren *"unos pocos tipos de vegetación del ecotono bosque-estepa en Chubut"*.

Estado: **obtenida** (2026-09-13). Conversión a texto en `docs/referencias/Publ_tec_37_Modelos_combustibles.pdf.md`. Publicada en 2012, ISSN 1514-2264, PICTO Forestal 36890.

### Evaluación de la PT-37 contra la puerta

**Qué es.** Seis modelos de combustible de **arbustal** (A1–A6) del ecotono bosque-estepa de Río Negro, Chubut y Santa Cruz, definidos con criterio del **sistema canadiense (CFFDRS)**, no de Rothermel. Los propios autores aclaran que los modelos de comportamiento quedan fuera del alcance (§2, §4) y que la validación con quemas está pendiente salvo en A4.


| Modelo | Asociación (§3.1)                                                          | Clase de destino probable               |
| ------ | -------------------------------------------------------------------------- | --------------------------------------- |
| A1     | Ñire maduro arbustivo, dosel continuo, laura, radal, caña colihue          | CCS-BAP *Ñire bajo* · MapBiomas 77/66   |
| A2     | Regeneración de ñire post-fuego, entreparches amplios con gramíneas        | CCS-BAP *Ñire bajo* · MapBiomas 63      |
| A3     | Maqui, radal, ciprés, laura; a veces bajo ciprés aislado                   | CCS-BAP matorral mixto · MapBiomas 77   |
| A4     | Arbustal bajo (<1 m): espino negro, palo piche, calafate, coirón           | CCS-BAP estepa arbustiva · MapBiomas 63 |
| A5     | Subarbustivo (neneo, leña de piedra) con coirón; se comporta como pastizal | CCS-BAP estepa · MapBiomas 12           |
| A6     | Duraznillo (Santa Cruz)                                                    | **No aplica** al AOI                    |


**Qué mide (Tabla 2).** Altura, cobertura, distancia entre parches, % de muerto aéreo, mantillo
y **carga muerta en contacto con el suelo** en tres clases: fino < 0,6 cm, medio 0,6–5 cm,
grueso > 5 cm (parcelas de 1 m², secado en estufa, n = 10 parcelas por asociación).

**Contra la fila que exige ELMFIRE:**


| Parámetro                     | PT-37                      | Veredicto                                                                            |
| ----------------------------- | -------------------------- | ------------------------------------------------------------------------------------ |
| `w0_1h`                       | Fino < 0,6 cm              | ✅ Límite casi idéntico al de 1 h (0,635 cm)                                          |
| `w0_10h`, `w0_100h`           | Medio 0,6–5 cm, **sumado** | ⚠️ No separable en la Tabla 2                                                        |
| `w0_liveherb`, `w0_livewoody` | —                          | ❌ No se midió carga viva ni biomasa aérea                                            |
| `sav_*` (×3)                  | —                          | ❌                                                                                    |
| `depth_ft`                    | Sólo altura del arbusto    | ⚠️ No es profundidad de lecho: A1 mide 4,8 m, fuera del rango de cualquier modelo SH |
| `mex_dead_pct`                | —                          | ❌ (hay dato local en Bianchi & Defossé, fuente distinta)                             |
| `hoc_btu_lb`                  | —                          | ❌ (8000 estándar)                                                                    |


En arbustales el portador principal es la **carga viva leñosa**, justamente lo que falta. Una
fila A1–A5 tendría medido `w0_1h`, la suma 10 h + 100 h y, por otra fuente, `mex`: **8 de 11
parámetros quedarían asumidos por analogía.**

**Cobertura del AOI.** Ningún modelo de bosque (lenga, coihue, ciprés, alerce), que es la
clase dominante (31 % del AOI en MapBiomas). Las áreas de estudio de Chubut (Esquel–Trevelin)
y Río Negro (El Bolsón–El Foyel) quedan inmediatamente al sur y al norte del AOI, sin
superponerse; el traslado es por estructura de vegetación vía la clase de cobertura, no por
ubicación, y se declara.

**Veredicto: rama *parcial*.** No se construyen modelos propios completos. Lo defendible es:

1. **SB40 ajustado** en las clases de arbustal: mantener el modelo elegido en IGN-20 y
  sustituir **sólo** `w0_1h` por la carga fina medida, declarando el resto como heredado.
   Se evalúa como sensibilidad frente al SB40 sin ajustar, no como reemplazo.
2. El uso principal de la PT-37 pasa a la **Etapa B** (IGN-20 §6.2–6.4 y §B5), como
  respaldo bibliográfico y como contraste de comportamiento.

**Datos crudos a pedir a CIEFAP** (junto con CCS-BAP): la planilla de campo (Anexo 2)
separa la carga media en **0,6–2,5 cm y 2,5–5 cm**, que coincide casi exacto con 10 h
(0,635–2,54 cm) y 100 h (2,54–7,62 cm). La separación existe en los datos por parcela aunque
la Tabla 2 la publique sumada.

**Búsqueda bibliográfica previa al pedido (2026-09-16): la separación no está publicada.**
No hace falta repetirla.

- **PT-37**: sin anexo digital ni depósito de datos (CONICET Digital, INFOR, SNMF, sitio de
CIEFAP).
- **Bianchi (2009)**, tesis de maestría (Lleida): trata humedad de combustibles, no carga.
- **Paritsis et al. (2018)**, mismo ecotono bosque-estepa: mide sólo combustible fino.
- **Cóbar-Carranza et al. (2014)**: el material caído lo agrupa en *"10–100 h (0,6–7,5 cm)"*,
el mismo hueco. El corte en 2,5 cm aparece sólo en la alometría de copa de *N. antarctica*
(Tabla 1, Fig. 7). Sirve como **precedente** de que el corte es relevante en ñire, no como
dato: la ecuación de 2,5–7,5 cm (exponentes 5,59 sobre DAP y −7 sobre H) no se puede
extrapolar fuera del rango calibrado de 1–20 cm de DAP.
- **Global Fuelbed Dataset** (Pettinari & Chuvieco 2016, PANGAEA 849808): tiene
`W_1h`…`W_1000h` por fuelbed y cubre el AOI, pero **se descarta**:
  1. Es circular: los fuelbeds de arbustal usan como especie de referencia *Vaccinium* spp.
    (FB 4130) y *Larrea tridentata* (FB 8130), y se construyeron con photo series de
     EE.UU., México y Brasil. Es la analogía de SB40 por otro camino.
  2. Los dos biomas que se cruzan en el AOI se contradicen: FB 4130 da 10 h 1,6 y 100 h
    3,0 Mg/ha (65 % en 100 h), mientras que FB 8130 da 10 h 0,9 y 100 h 0,0.
  3. La licencia es CC-BY-**NC**-SA 3.0. Choca con el mismo criterio que fija ELMFIRE en
    2025.0212.

**Supuesto adoptado mientras no responda CIEFAP: todo el "Medio" va a** `w0_10h`**, con**
`w0_100h = 0` **en A1–A6.** Tiene dos apoyos independientes:

- El corte en 2,5 cm está medido en ñire (Cóbar-Carranza).
- El único fuelbed global cuya magnitud coincide con lo medido en Patagonia es FB 8130, que
suma 0,9 Mg/ha contra un Medio de 0,37–1,12 t/ha en la lectura tentativa de la Tabla 2.
Asigna todo al 10 h. FB 4130 suma 4,6 Mg/ha, cuatro veces más.

**Sesgo declarado**: SAV 10 h = 109 1/ft y SAV 100 h = 30 1/ft son constantes internas. Si
parte del Medio es realmente 100 h, el supuesto **sobreestima** la propagación. La
dirección es conocida y la magnitud se acota con un barrido.

**Pedido a CIEFAP** (mail a L. O. Bianchi, `lbianchi@ciefap.org.ar`, redactado el
2026-09-16). Pide tres cosas:

1. Confirmar si la columna 2,5–5 cm del Anexo 2 se relevó por separado.
2. Si se relevó, las cargas por parcela y subparcela de 0,6–2,5 y 2,5–5 cm para A1–A6, o
  al menos la media y el desvío por modelo.
3. Si hay registro del diámetro dentro de "Grueso > 5 cm", que mezcla 100 h con 1000 h.

Si llega la planilla, cambian dos columnas del CSV de combustibles de las filas de arbustal
y se vuelve a correr.

### Dato de comportamiento: quema experimental en A4 (§3.3–3.4)

Único registro cuantitativo de comportamiento del fuego en arbustal patagónico que tenemos.
Sirve para el paso 4 de Scott & Burgan en IGN-20 (filtro de rechazo) corriendo Rothermel
sobre los candidatos con **estas condiciones**, no con el escenario D2L2.


|                          |                                                                                                |
| ------------------------ | ---------------------------------------------------------------------------------------------- |
| Fecha y lugar            | 14-09-2011, 16:00 · Cerro Jones, Trevelin (43°00'S, 71°25'W) · terreno plano                   |
| Parcela                  | 50 × 50 m · fino 2,8 t/ha · medio 0,4 t/ha · altura 1,6 m · cobertura 67 % · muerto aéreo 50 % |
| Meteorología en parcela  | 20,0 °C · HR 16 % · viento 24 km/h (ráfagas 51) · FFMC 92,7 · ISI 20,9                         |
| Humedad foliar           | Espino negro 82 % · maitén 155 %                                                               |
| Velocidad de propagación | ~80 m/min en régimen (40 m en 30 s) ≈ 240 ch/h, clase *extrema*                                |
| Largo de llama           | 3–4 m                                                                                          |


Limitaciones a declarar: una sola quema, parcela chica (el régimen se alcanzó a los 10 m),
altura de medición del viento no informada, y quema de fin de invierno (el pasto estaba 100 %
curado, pero no son condiciones de verano tardío).

### Trampas de lectura del `.md`

- **Unidades:** la PT-37 usa toneladas **métricas por hectárea**. Ver factor en la tabla de
parámetros más abajo; no confundir con el de t/ac.
- **Tabla 2 con columnas corridas:** en las filas de carga fina y gruesa la conversión perdió
una celda y los valores quedan desplazados. Lectura tentativa de carga fina: A1 5,91 · A2 0,82 ·
A3 1,68 · A4 5,66 · A5 2,9 · A6 1,73 t/ha; media: A1 0,86 · A2 1,03 · A3 1,03 · A4 1,12 ·
A5 0,37 · A6 0,62 t/ha. **Verificar contra el PDF antes de usar un solo número.**
- **Anexo 5 ilegible:** el texto de las leyendas de los mapas salió corrupto del OCR (p. ej.
A3 "0,5 m" contra 3,42 m de la Tabla 2). Citar §3.1 y la Tabla 2, nunca el Anexo 5.
- **Mantillo** no se suma a ninguna carga de Rothermel: es combustión latente, fuera de alcance.
- **Varianza alta:** A1 fino 5,91 ± 5,62 t/ha. Reportar el desvío junto a cualquier valor usado.



### Parámetros que ELMFIRE exige por modelo

Una fila del CSV, en este orden y sin encabezado:

```
num, shortname, dynamic, w0_1h, w0_10h, w0_100h, w0_liveherb, w0_livewoody,
     sav_1h, sav_liveherb, sav_livewoody, depth_ft, mex_dead_pct, hoc_btu_lb
```


| Parámetro                             | Unidad                                                  | Cómo se obtiene                                                                      |
| ------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Carga 1 h / 10 h / 100 h              | lb/ft² (`t/ac × 0,0459137`; `t/ha métrica × 0,0204816`) | Inventario de combustible muerto caído, método de intercepción planar (Brown 1974)   |
| Carga herbácea viva / leñosa viva     | lb/ft²                                                  | Parcelas de corte y pesado en seco                                                   |
| SAV 1 h / herbácea viva / leñosa viva | 1/ft                                                    | Medición de partículas, o asignación por analogía con especies de morfología similar |
| Profundidad del lecho                 | ft                                                      | Medición directa en campo                                                            |
| Humedad de extinción                  | %                                                       | **Aquí sí hay dato patagónico medido** (ver abajo)                                   |
| Calor de combustión                   | BTU/lb                                                  | Bomba calorimétrica; 8000 es el valor estándar de todo el set SB40                   |


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

  | Tipo       | Bloque disponible para custom |
  | ---------- | ----------------------------- |
  | NB         | 90, 96-97                     |
  | GR         | 100, 113-119                  |
  | GS         | 120, 131-139                  |
  | SH         | 140, 153-159                  |
  | TU         | 160, 171-179                  |
  | TL         | 180, 193-199                  |
  | SB         | 200, 211-219                  |
  | (sin tipo) | 14-89, 220-256                |

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
   `0.02296`; el factor es `0,0459137` para toneladas cortas por acre. **La PT-37 publica en
   t/ha métricas: el factor es** `0,0204816` (1 t/ha = 0,4461 t/ac). Aplicar el de t/ac a un
   dato en t/ha infla la carga ×2,24.
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

1. PT-37 no contiene cargas por clase de tamaño. *(Evaluado 2026-09-13: contiene carga muerta
  fina y media, no viva. Se cumple a medias → se abandona la versión completa y queda sólo el
   ajuste acotado de C0.)*
2. Las asociaciones cubiertas por la bibliografía no coinciden con las clases dominantes del
  AOI de Los Alerces (PT-37 es del **ecotono bosque-estepa**, y Los Alerces es
   mayoritariamente bosque húmedo — es un riesgo real de solape insuficiente).
3. El calendario de la tesis no permite cerrar la Etapa B con validación.

Abandonarla no debilita la tesis: el núcleo del aporte es el crosswalk fundamentado y su
demostración cuantitativa. Esta etapa es techo, no piso.

---



## Riesgos


| Riesgo                                                           | Mitigación                                                                                                |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| PT-37 caracteriza el **ecotono bosque-estepa**, no bosque húmedo | **Materializado:** sólo arbustales, ningún modelo de bosque. Se limita el ajuste a las clases de arbustal |
| La PT-37 no mide carga viva                                      | Heredar la carga viva de SB40 y declararlo; pedir los datos por parcela a CIEFAP                          |
| Faltan SAV, que rara vez se miden                                | Asignar por analogía con modelos SB40 de morfología comparable y **declararlo**                           |
| Parámetros estimados presentados como medidos                    | Columna de procedencia obligatoria por parámetro                                                          |
| Los modelos propios no mejoran el resultado                      | Es un resultado válido y publicable, no un fracaso                                                        |
| Rothermel sigue siendo el modelo subyacente                      | Parametrizar mejor no arregla los supuestos de homogeneidad y continuidad; declararlo                     |




## Decisiones registradas


| Decisión               | Elegida                                                                   | Motivo                                                   |
| ---------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------- |
| Prioridad              | Extensión condicionada, no camino crítico                                 | PT-37 no alcanza para modelos completos                  |
| Puerta C0 (2026-09-13) | Rama parcial: SB40 con `w0_1h` medido, sólo arbustales, como sensibilidad | 8 de 11 parámetros por fila serían asumidos              |
| Numeración             | Bloques custom de Scott & Burgan dentro de 1-256                          | Preserva semántica de tipo y compatibilidad de 8 bits    |
| Sin datos medidos      | No ejecutar                                                               | Estimar y presentarlo como aporte no resiste una defensa |
| Cableado en ELMFIRE    | Ya resuelto en Etapa A                                                    | Emitir tabla propia desde el arranque lo deja listo      |




## Fuentes

- ELMFIRE 2025.0212, `build/source/elmfire_init.f90` y `build/source/elmfire_namelists.f90` —
[https://github.com/lautenberger/elmfire](https://github.com/lautenberger/elmfire)
- Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. *Modelos de combustibles en el
ecotono bosque-estepa de la Patagonia andina: caracterización de las asociaciones arbustivas
de acuerdo a su respuesta al fuego.* CIEFAP, Publicación Técnica N.º 37, Esquel, 2012.
ISSN 1514-2264. **(obtenida;** `docs/referencias/Publ_tec_37_Modelos_combustibles.pdf.md`**)**
- Bianchi, L.O.; Defossé, G.E. *Ignition probability of fine dead surface fuels of native
Patagonian forests of Argentina.* Forest Systems. —
[https://fs.revistas.csic.es/index.php/fs/article/view/4632](https://fs.revistas.csic.es/index.php/fs/article/view/4632)
- Cóbar-Carranza, A.J. et al. (2014). *Effect of Pinus contorta invasion on forest fuel
properties and its potential implications on the fire regime of Araucaria araucana and
Nothofagus antarctica forests.* Biological Invasions 16:2273–2291. doi:10.1007/s10530-014-0663-8
**(**`docs/referencias/Cobar_Carranza_2014_BiolInv_fuel_properties.pdf`**)**
- Paritsis, J. et al. (2018). *Pine plantations and invasion alter fuel structure and potential
fire behavior in a Patagonian forest-steppe ecotone.* Forests 9(3):117. doi:10.3390/f9030117
- Pettinari, M.L.; Chuvieco, E. (2016). *Generation of a global fuel data set using the Fuel
Characteristic Classification System.* Biogeosciences 13:2061–2076. Datos:
doi:10.1594/PANGAEA.849808 (CC-BY-NC-SA 3.0). **Evaluado y descartado, ver §C0.**
- Scott, J.H.; Burgan, R.E. (2005). RMRS-GTR-153. (Parámetros constantes: p. 2; bloques de
numeración custom: p. 5, Tabla 1; criterio de eliminación de modelos redundantes: pp. 3-4;
modelos dinámicos: p. 4)
- Brown, J.K. (1974). *Handbook for inventorying downed woody material.* GTR INT-16.
- Sistema KITRAL — Laboratorio de Incendios Forestales, Facultad de Ciencias Forestales y
Conservación de la Naturaleza, Universidad de Chile.
- Godoy, M.M. et al. (2022). Frontiers in Forests and Global Change. —
[https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2022.850543/full](https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2022.850543/full)

