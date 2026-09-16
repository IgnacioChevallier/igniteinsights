# IGN-20B · Tabla de correspondencia CCS-BAP → Scott & Burgan FBFM40

> **Estado: propuesta, pendiente de revisión y aprobación del director.**
> Insumo principal de la Etapa B. Convive con `IGN-20-CROSSWALK.md` (MapBiomas), que pasa a
> ser punto intermedio de comparación, y con el baseline de WorldCover (`ETAPA-A §A7`).
>
> Área de interés: Parque Nacional Los Alerces y entorno.
> −72,05 / −42,90 / −71,15 / −42,05 (EPSG:4326) · 699.000 ha · grilla EPSG:32719, 30 m.

---

## 1. El insumo

**Clasificación de Tipos Forestales y Cobertura del Suelo de la Región Bosque Andino
Patagónico** (CIEFAP, MAyDS y provincias). Acceso otorgado por CIEFAP el 2026-09-13.


|                   |                                                                          |
| ----------------- | ------------------------------------------------------------------------ |
| Capa usada        | `cob_2017_N3_aok_CH` — Chubut, **época 2017**, nivel 3                   |
| Formato           | Shapefile, **POSGAR94 Faja 1** (EPSG:22181), geometría Polygon Z         |
| Polígonos         | 67.285 en Chubut · 20.277 tocan el AOI                                   |
| Atributos         | `Ley_N1`, `Ley_N2`, `Ley_N3`, `Provincia`, `APN`, `Categoria`, `Area_Ha` |
| Leyenda           | 3 niveles · 28 pares (N1,N2) · **92 clases de nivel 3**                  |
| Unidad mínima     | 1 ha · exactitud global reportada 87 % en nivel 2                        |
| Cobertura del AOI | **95,45 %** (667.229 ha). El 4,55 % restante es el lado chileno          |
| Topología         | Sin solapes (suma de polígonos = unión) y sin clases nulas, verificado   |


También se recibieron Río Negro, Neuquén, Santa Cruz y Tierra del Fuego, y la **época 2013**
de cada una. Ninguna es necesaria para este AOI; la de 2013 se usa como control temporal.

### 1.1 Por qué 2017 y no 2013

Comparando ambas épocas dentro del AOI aparece un cambio que ningún producto global registra:


| Clase                           | 2013       | 2017          | Δ           |
| ------------------------------- | ---------- | ------------- | ----------- |
| Remanente de disturbio reciente | 155 ha     | **37.736 ha** | **+37.581** |
| Lenga                           | 143.012 ha | 135.275 ha    | −7.737      |
| Ñire                            | 75.704 ha  | 68.308 ha     | −7.395      |
| Mixto de ñire                   | 27.683 ha  | 20.727 ha     | −6.956      |
| Coihue                          | 53.723 ha  | 46.919 ha     | −6.804      |


Las pérdidas por especie suman lo que gana "remanente de disturbio reciente". Por fecha y
magnitud corresponde al incendio de Cholila de 2015. **El 5,4 % del AOI es superficie
quemada**, un estado de combustible propio que hay que representar (§5, clase `Rem Dist Rec`).

### 1.2 Por qué este insumo es el aporte


|                                  | WorldCover 2021 | MapBiomas 2024 | **CCS-BAP 2017**                |
| -------------------------------- | --------------- | -------------- | ------------------------------- |
| Clases arbóreas                  | 1               | 3              | **10 por especie + mixtos**     |
| Distingue bosque de matorral     | no              | sí             | **sí, y por especie**           |
| Distingue TF de OFL (estructura) | no              | parcial        | **sí, es el eje de la leyenda** |
| Superficie quemada reciente      | no              | no             | **sí**                          |
| Turberas                         | no              | sí             | sí                              |
| Cobertura del AOI                | 100 %           | 93,94 %        | 95,45 %                         |


---



## 2. Método

Idéntico al de `IGN-20-CROSSWALK.md` §3: el procedimiento de selección de Scott & Burgan
(2005, pp. 8-9) aplicado paso por paso, con el paso 4 como **filtro de rechazo**. No se
modifican los parámetros de los modelos FBFM40; eso es `ETAPA-C-MODELOS-PROPIOS.md`.

Se mantiene el marco de humedad de extinción de IGN-20 §4: los umbrales de ignición medidos
por Bianchi & Defossé en combustibles finos muertos patagónicos (**21,5 % en ciprés, 25,0 %
en ñire**) descartan las variantes de clima seco con `mex` de 15 a 20 %. Toda clase con
vegetación nativa usa `mex ≥ 25 %`.

**Novedad respecto de IGN-20:** cuatro clases de arbustal tienen ahora **carga medida en la
Patagonia** (CIEFAP Publicación Técnica N.º 37, Bianchi et al. 2012), que se usa para elegir
dentro de la familia. Conversión: `t/ha métrica × 0,0204816 = lb/ft²`.


| Modelo PT-37                     | Carga fina medida | Equivalente   | Modelo elegido | Carga 1 h del modelo |
| -------------------------------- | ----------------- | ------------- | -------------- | -------------------- |
| A1 · ñire maduro arbustivo       | 5,91 t/ha         | 0,1210 lb/ft² | SH8            | 0,09412              |
| A2 · ñire post-fuego             | 0,82 t/ha         | 0,0168 lb/ft² | GS3            | 0,01377              |
| A3 · matorral maqui-radal-ciprés | 1,68 t/ha         | 0,0344 lb/ft² | SH4            | 0,03903              |
| A4 · arbustal bajo               | 5,66 t/ha         | 0,1159 lb/ft² | GS3 / SH8      | —                    |




## 3. La clave del crosswalk

`(Ley_N1, Ley_N2)`**, no** `Ley_N2` **sola.** La leyenda repite el código de especie entre
niveles: `Le` existe como `TF Le` (bosque de lenga) y como `OFL Le` (lenga achaparrada). Esa
diferencia es estructural y es exactamente la que separa un modelo de hojarasca de uno de
matorral. Usar `Ley_N2` sin `Ley_N1` fusionaría ambos.

Se elige el nivel 2 como principal porque es el nivel con exactitud reportada (87 %); el
nivel 3 queda como análisis de sensibilidad (§7, S4).

**Excepciones por nivel 3.** Tres clases de nivel 2 agrupan cosas que arden de manera
distinta, y ahí el nivel 2 no alcanza:

- `OT Humedales` contiene mallín, otros humedales y **turbera**.
- `OT Exot-Artif` contiene forestación de coníferas, arboledas, pasturas, cultivos e
**infraestructura**.
- `OT Herb-Subarb` contiene estepa graminosa, **estepa arbustiva** y pradera.

Sin excepciones, la turbera heredaría el modelo del mallín y una plantación de pino heredaría
el de un cultivo. Las diez excepciones están en §5.

---



## 4. Tabla de correspondencia

`%` es superficie dentro del AOI de la tesis, sobre el recorte de la capa 2017.

### Tierras Forestales (TF) — bosque


| N2  | Especie                 | % AOI | → FBFM40 | Modelo                                 | `mex` |
| --- | ----------------------- | ----- | -------- | -------------------------------------- | ----- |
| Le  | Lenga                   | 10,64 | **186**  | TL6 · hojarasca latifoliada moderada   | 25    |
| Co  | Coihue                  | 6,70  | **165**  | TU5 · hojarasca alta con sotobosque    | 25    |
| Ñi  | Ñire                    | 4,32  | **163**  | TU3 · hojarasca con pasto y arbustos   | 30    |
| Mx  | Mixtos                  | 3,03  | **165**  | TU5                                    | 25    |
| Ci  | Ciprés de la cordillera | 2,60  | **165**  | TU5                                    | 25    |
| Ma  | Maitén                  | 0,07  | **182**  | TL2 · hojarasca latifoliada carga baja | 25    |
| Rd  | Radal                   | 0,07  | **182**  | TL2                                    | 25    |
| Al  | Alerce                  | 0,04  | **185**  | TL5 · hojarasca de conífera carga alta | 25    |
| Mr  | Mirtáceas               | 0,04  | **182**  | TL2                                    | 25    |
| Cg  | Ciprés de las guaitecas | 0,00  | **185**  | TL5                                    | 25    |




### Otras Formaciones Leñosas (OFL) — matorral y bosque achaparrado


| N2                     | Descripción                       | % AOI | → FBFM40 | Modelo                                 | `mex` |
| ---------------------- | --------------------------------- | ----- | -------- | -------------------------------------- | ----- |
| Le                     | Lenga achaparrada, baja, marginal | 8,71  | **148**  | SH8 · arbustal carga alta clima húmedo | 40    |
| Arbu Na                | Arbustal nativo                   | 6,59  | **144**  | SH4 · arbustal carga baja clima húmedo | 30    |
| Ñi                     | Ñire bajo                         | 5,45  | **148**  | SH8                                    | 40    |
| MMx                    | Matorral mixto                    | 2,97  | **144**  | SH4                                    | 30    |
| Ci                     | Ciprés abierto y juvenil          | 0,06  | **144**  | SH4                                    | 30    |
| Co, Ch, Rd, Mr, Ma, Cg | Juveniles y arbustos menores      | 0,02  | **144**  | SH4                                    | 30    |




### Otras Tierras (OT)


| N2           | % AOI | → FBFM40 | Modelo                           | `mex` |
| ------------ | ----- | -------- | -------------------------------- | ----- |
| Herb-Subarb  | 15,02 | **103**  | GR3 · pastizal grueso húmedo     | 30    |
| Erial        | 11,76 | **99**   | NB9 · estéril                    | —     |
| Rem Dist Rec | 5,40  | **123**  | GS3 · pastizal-arbustal húmedo   | 40    |
| Hie-Nie      | 3,86  | **92**   | NB2 · nieve y hielo              | —     |
| Agua         | 3,84  | **98**   | NB8 · agua                       | —     |
| Exot-Artif   | 2,50  | **101**  | GR1 · pastizal ralo              | 15    |
| Humedales    | 1,76  | **105**  | GR5 · pastizal húmedo carga baja | 40    |




### Excepciones por nivel 3


| Ley_N3     | → FBFM40    | Motivo                                                    |
| ---------- | ----------- | --------------------------------------------------------- |
| Turbera    | **99** NB9  | Combustión latente, fuera del alcance de Rothermel (§6.3) |
| Cg Juv-Tur | **99** NB9  | Ciprés de las guaitecas sobre turbera, ídem               |
| Caña       | **149** SH9 | Caña colihue: carga muy alta, lecho profundo              |
| Estepa Arb | **123** GS3 | Estepa arbustiva — PT-37 modelos A4 y A5                  |
| Pradera    | **105** GR5 | Pastizal húmedo de mayor productividad que la estepa      |
| Forest     | **188** TL8 | Forestación de coníferas exóticas, acícula larga          |
| Arles Ex   | **182** TL2 | Arboledas exóticas latifoliadas                           |
| Arbu Ex    | **144** SH4 | Arbustal exótico                                          |
| Pastura    | **102** GR2 | Pastura implantada                                        |
| Infraest   | **91** NB1  | Infraestructura                                           |


Las clases de nivel 3 que son **mezclas de especies** (`Le-Co`, `Co-Ci`, `Ñi Baj-Le`, …)
heredan el modelo de su nivel 2, es decir el de la especie dominante, que es la que da nombre
a la clase. Regla declarada, no caso por caso.

---



## 5. Fichas de asignación



### 5.1 · TF Le — Bosque de lenga → **186 (TL6)** · 10,64 % del AOI

**Paso 1 · Estrato portador.** Hojarasca. La lenga (*Nothofagus pumilio*) es caducifolia y
produce un lecho de hojas pequeñas; el sotobosque es pobre en los rodales densos de altura.
Es el caso en que la familia TL corresponde y TU no.

**Paso 2 · Humedad de extinción.** TL6 tiene `mex = 25 %`, que iguala el umbral de ignición
medido en ñire (25,0 %) y supera el de ciprés. Se descarta **TL3 (183)**, la asignación del
baseline, por dos razones: `mex = 20 %` y, sobre todo, porque es hojarasca de **conífera de
acícula larga**, un lecho físicamente distinto del de una latifoliada caducifolia.

**Paso 3 · Estructura.** TL6: 1 h 0,11019 lb/ft², lecho 0,3 pies, sin componente vivo.
Es hojarasca latifoliada de carga moderada.

**Paso 4 · Contraste.** TL6 propaga *moderado* con llama *baja*, coherente con un fuego de
superficie bajo dosel cerrado. El fuego de copas en lenga no se resuelve acá sino con
`cc`/`ch`/`cbh`/`cbd`.

**Procedencia.** El estrato portador y el tipo de hojarasca son bibliográficos; la elección
de TL6 sobre TL2 y TU2 es juicio fundamentado del autor. **Sensibilidad S1.**

### 5.2 · TF Co y TF Ci — Coihue y ciprés → **165 (TU5)** · 9,30 % del AOI

Coihue (*N. dombeyi*, perennifolio) y ciprés (*Austrocedrus chilensis*, conífera) comparten
una característica que decide el modelo: **sotobosque leñoso denso**, de caña colihue
(*Chusquea culeou*), *Berberis* y *Maytenus*. El estrato portador es hojarasca **con**
sotobosque, o sea familia TU.

TU5 es el modelo de mayor carga de la familia (1 h 0,18365, 10 h 0,18365, 100 h 0,13774,
leñoso vivo 0,13774, `mex` 25) y su descripción —*"heavy forest litter with a shrub or small
tree understory"*— es literalmente la estructura descrita. Es la misma elección que IGN-20
§6.1 hizo para "bosques cerrados", acá restringida a las especies que efectivamente la
justifican en vez de aplicarse a todo el bosque.

**Limitación.** Coihue (muy húmedo, oeste) y ciprés (más seco, este) reciben el mismo modelo
pese a tener regímenes de humedad distintos. CCS-BAP los separa y nuestra parametrización no.

### 5.3 · TF Ñi — Bosque de ñire → **163 (TU3)** · 4,32 % del AOI

El ñire (*N. antarctica*) forma bosques abiertos con estrato herbáceo continuo, históricamente
pastoreados, en el ecotono. Es el caso que Scott & Burgan advierten en el paso 1: con dosel
abierto **el pasto puede llevar el fuego, no la hojarasca**.

TU3: *"moderate forest litter with grass and shrub components"*, `mex = 30 %`, **dinámico**,
propagación *alta*. La PT-37 lo respalda de manera indirecta: sus modelos de ñire (A1 y A2)
describen la propagación por el estrato herbáceo de los entreparches.

### 5.4 · OFL Ñi — Ñire bajo → **148 (SH8)** · 5,45 % del AOI

**Es la asignación con mejor respaldo de toda la tabla**, y la única con carga medida en la
misma formación.

**Paso 1.** Arbustivo. CCS-BAP documenta que el ñire arbóreo y el arbustivo no son separables
por sensores ópticos y los agrupa como *Ñire Bajo*; fisonómicamente es matorral.

**Paso 2.** SH8, `mex = 40 %`, clima húmedo. Muy por encima del umbral medido de 25,0 % en
ñire, que es la especie de esta clase.

**Paso 3.** PT-37 modelo A1 —ñire maduro arbustivo, dosel continuo, laura, radal y caña
colihue— mide **5,91 t/ha de combustible fino muerto = 0,1210 lb/ft²**, con 27,5 % de muerto
aéreo en copa y altura media de 4,83 m. La carga 1 h de SH8 es 0,09412 lb/ft², la más cercana
entre los modelos de arbustal de clima húmedo. **Se descarta SH9 (149)** por carga 1 h de
0,20661, casi el doble de lo medido, y **SH5 (145)**, la familia del baseline, por `mex = 15 %`.

**Paso 4 · Contraste con comportamiento observado.** Ejecutado (§6.2). SH8 reproduce la
longitud de llama observada —3,1 m contra los 3 a 4 m medidos— pero **subestima la
propagación**: 437 m/h con viento sostenido y 900 m/h bajo ráfaga, contra 4.800 m/h
observados. Ningún modelo de arbustal de SB40 reproduce las dos variables a la vez. La
asignación se mantiene, porque es la que ajusta la llama y la carga fina medida, **y se
declara que subestima la velocidad de propagación**.

**Segunda fuente, independiente.** Cóbar-Carranza et al. (2014) miden en rodales de
*N. antarctica* de la Reserva Malalcahuello (Chile, ~38°S, 2.580 árboles/ha, 3,6 m de altura
media —o sea ñire bajo—) **1.930 ± 307 kg/ha de leña fina caída de menos de 0,6 cm**. No es
directamente comparable con la PT-37, porque ese trabajo separa la hojarasca de la leña fina
y la PT-37 las agrupa, pero cae en el mismo orden y refuerza que la clase no es de carga alta.
Traslado a declarar: es otra latitud y un bosque subalpino con araucaria, ausente del AOI.

**Procedencia.** Carga: medida (PT-37, Tabla 2), corroborada por una segunda fuente. `mex`:
bibliográfico. Elección final del modelo: juicio del autor sobre carga, sujeto al paso 4.

### 5.5 · OFL Le — Lenga achaparrada → **148 (SH8)** · 8,71 % del AOI

Lenga de porte achaparrado en el límite altitudinal: densa, baja, con mucho material muerto en
pie. No hay carga medida para esta formación; se le asigna el mismo modelo que al ñire bajo
por analogía estructural, ambas son formaciones densas de *Nothofagus* caducifolio de porte
arbustivo.

**Esto es una pérdida declarada.** CCS-BAP separa lenga achaparrada de ñire bajo y **nuestra
parametrización no puede**: no existe un modelo FBFM40 construido sobre ninguna de las dos, y
sólo una tiene carga medida. Es un argumento directo a favor de la `ETAPA-C`. **Sensibilidad S2.**

### 5.6 · OFL Arbu Na y MMx — Arbustal nativo y matorral mixto → **144 (SH4)** · 9,56 %

PT-37 modelo A3: matorral de maqui, radal, ciprés y laura, altura media 3,42 m, cobertura
54 %, **1,68 t/ha de combustible fino = 0,0344 lb/ft²**. La carga 1 h de SH4 es 0,03903, la
coincidencia más ajustada de la tabla.

SH4: lecho de 3 pies, leñoso vivo 0,11708, `mex = 30 %`, propagación *alta*, llama *moderada*.
Coherente con Mermoz et al. (2005): los matorrales patagónicos propagan más que los bosques.

Es la misma elección que IGN-20 §6.2 tomó para el arbustal de MapBiomas, que allí era la
asignación más incierta de la tabla. **Con CCS-BAP y la PT-37 deja de serlo**: ahora hay una
clase de origen que es efectivamente matorral y una carga medida que la respalda.

### 5.7 · OT Rem Dist Rec — Remanente de disturbio reciente → **123 (GS3)** · 5,40 %

Superficie quemada en 2015, mapeada en 2017, simulada en 2026: **once años de regeneración**.
El análogo medido es el modelo A2 de la PT-37, regeneración coetánea de ñire post-fuego con
entreparches amplios y estrato herbáceo de gramíneas, donde *"el fuego propaga rápidamente por
el estrato herbáceo en los entreparches y por las copas de los arbustos en los parches"* y
*"los incendios generalmente son de alta intensidad"*.

A2 mide 0,82 t/ha de fino = **0,0168 lb/ft²**; GS3 tiene 1 h de 0,01377. GS3 es dinámico,
`mex = 40 %`, lecho de 1,8 pies, con carga herbácea y leñosa viva equilibradas.

**Alternativa evaluada y descartada como principal:** SB2 (202), de la familia
*slash-blowdown*, que representaría el material muerto en pie inmediatamente después del
fuego. Se descarta porque describe el estado a los dos años, no a los once. **Sensibilidad S3.**

### 5.8 · OT Herb-Subarb — Estepa → **103 (GR3)** · 15,02 %, con excepción

`Estepa` (graminosa, coirón de *Festuca* y *Stipa*) → GR3, *"very coarse grass"*, `mex = 30 %`.
Misma elección y mismo motivo que IGN-20 §6.4.

`Estepa Arb` (estepa arbustiva) → **GS3**, por los modelos A4 y A5 de la PT-37: arbustal bajo
con gramíneas, donde *"con vientos moderados o fuertes el largo de llama supera la distancia
entre parches"*. Es co-dominancia arbusto-pasto, familia GS por definición.

`Pradera` → GR5, pastizal húmedo de mayor productividad.

### 5.9 · OT Erial → **99 (NB9)** · 11,76 %

Erial es clase propia en CCS-BAP: suelo desnudo, roca, pedregal. Que exista como clase permite
**revisar** la fracción no combustible en vez de heredarla de un producto global. El resultado
es que los tres insumos coinciden en el orden de magnitud, lo que refuerza que no es un
artefacto (IGN-20 §2).

### 5.10 · OT Humedales — Mallín y turbera

`Mallin` y `Otros Hum` → GR5 (`mex = 40 %`, dinámico, carga herbácea viva alta): pastizal
higrófilo que sólo propaga cuando está curado, que es la manera correcta de codificar esa
fenología dentro del formalismo de Rothermel.

`Turbera` → **NB9, declarado fuera de alcance.** Scott & Burgan (2005, p. 3) delimitan el
conjunto al *"surface fire behavior at the flaming front only, not residual combustion"*. Una
turbera arde por combustión latente subterránea. Asignarle un modelo de superficie daría un
número sin sustento físico. **Subestima el fuego en turberas y se declara.**

---



## 6. Resultado de la construcción

Los tres mapas generados sobre la misma grilla (`scripts/build_fuel_maps.py`), con la misma
regla de agregación y el mismo relleno de huecos, sobre el **AOI definitivo**
(2.563 × 3.222 = 8,3 M celdas, tras re-ingestar el DEM el 2026-09-16). El relleno del hueco
fronterizo toma el 6,90 % de la grilla en MapBiomas y el 5,38 % en CCS-BAP:


| Tipo de combustible | WorldCover 2021 | MapBiomas 2024 | **CCS-BAP 2017** |
| --- | --- | --- | --- |
| NB · no combustible | 19,21 % | 26,39 % | 20,99 % |
| GR · pastizal | 34,70 % | 12,49 % | 18,22 % |
| GS · pastizal-arbustal | 0,00 % | 3,34 % | **5,11 %** |
| SH · arbustal | **3,75 %** | 22,11 % | **23,25 %** |
| TU · bosque con sotobosque | 0,00 % | 31,00 % | 16,41 % |
| TL · hojarasca de bosque | 42,34 % | 4,68 % | 16,02 % |


Lecturas:

1. **El arbustal pasa de 0,04 % a 20,13 %.** Es el hallazgo central de la Etapa B, ahora sobre
  un insumo que discrimina especie.
2. **El bosque deja de ser un solo modelo.** Donde el baseline pone 59,93 % de TL3 y MapBiomas
  53,40 % de TU5, CCS-BAP reparte entre TU5 (21,09 %), TL6 (19,23 %) y TU3 (5,20 %) según
   especie y estructura.
3. **MapBiomas declara más superficie no combustible que CCS-BAP** (29,83 % contra 25,65 %),
  pese a ser nueve años posterior. La diferencia está sobre todo en nieve y hielo y merece
   revisión antes de la comparación final.



### 6.1 · Comparación con ELMFIRE (2026-09-16, con humedad viva medida)

Tres corridas de 12 h sobre el **mismo incendio**: misma ignición, misma meteorología, misma
topografía, mismo `ADJ`. Lo único que cambia es `fbfm40.tif`. Se puntúa **sólo el anillo de
crecimiento**, nunca la unión con la semilla (`IGN-26-VALIDACION.md` §12.1).

Semilla FIRMS: 8.095 ha, verificada idéntica en las tres corridas. Humedad del combustible
vivo en los valores medidos de `ETAPA-B` §B5: `LH` 30 %, `LW` 110 %.


| Mapa | Anillo a 12 h | vs baseline | FLI mediana | FLI p90 |
| --- | --- | --- | --- | --- |
| WorldCover 2021 | 2.342 ha | — | 96,1 kW/m | 333 |
| MapBiomas 2024 | 5.849 ha | +150 % | 311,1 kW/m | 1.267 |
| **CCS-BAP 2017** | **7.576 ha** | **+223 %** | **317,0 kW/m** | 1.309 |


Acuerdo entre mapas sobre el anillo:


| Par | IoU | Sólo el primero | Sólo el segundo |
| --- | --- | --- | --- |
| WorldCover vs MapBiomas | 0,245 | 728 ha | 4.235 ha |
| WorldCover vs CCS-BAP | 0,269 | 243 ha | 5.476 ha |
| MapBiomas vs CCS-BAP | **0,599** | 822 ha | 2.550 ha |

> **Corrida anterior, con `LH`/`LW` en 60 %:** 1.989 / 9.328 / 10.537 ha, con IoU de 0,179 /
> 0,179 / 0,629. Al pasar a la humedad medida, el fuego de los dos mapas patagónicos se reduce
> cerca de un tercio y el del baseline **sube** —el pasto curado hace arder más el GR2—, así
> que la diferencia entre mapas se achica de un factor 5,3 a uno de 3,2. **La conclusión no
> cambia; la magnitud sí.** Es exactamente el motivo por el que el escalar tenía que fijarse
> con una medición antes de citar cualquier número.


Qué combustible quemó cada corrida, dentro del anillo:

- **WorldCover:** GR2 62 %, TL3 38 %. El fuego avanza por el pastizal porque TL3 casi no
propaga: es la consecuencia directa del hallazgo del audit.
- **MapBiomas:** TU5 70 %, SH4 19 %, GR5 9 %.
- **CCS-BAP:** SH8 29 %, TU5 17 %, TL6 17 %, SH4 12 %, GR3 11 %, TU3 10 %. **El arbustal lleva
el fuego**, que es lo que Mermoz et al. (2005) documentan para la Patagonia.

**Qué demuestra y qué no.** Demuestra que el resultado de ELMFIRE es **fuertemente sensible al
mapa de combustible**: un factor 5 en superficie y un factor 7 en intensidad mediana, con el
resto de los insumos congelados. Un empate habría sido un hallazgo en contra de toda la Etapa B.
**No demuestra que CCS-BAP prediga mejor**: eso requiere puntuar contra el perímetro observado
(§B6, harness B). Que los dos insumos patagónicos coincidan entre sí (IoU 0,599) y difieran
igual del baseline (0,245 y 0,269) es consistente con que el baseline sea el atípico, pero no
lo prueba.

**Salvedades de esta corrida:**

1. **Corre sobre la grilla reducida** (1414 × 1526), aunque el DEM ya se re-ingestó y los mapas
   de §6 están sobre el AOI definitivo. Llevar ELMFIRE al AOI completo exige regenerar también
   meteorología, `phi` y dosel, o sea una preparación entera. **Pendiente.**
2. ~~Humedad del combustible vivo sin criterio~~ → **resuelto**: valores medidos de Bianchi &
   Defossé (2015), fundamentados en `ETAPA-B` §B5 y cuantificados en §6.3.
3. **Sin validación contra lo observado.** Las tres corridas se comparan entre sí. El harness
   ya existe y se ejecutó (`IGN-26-VALIDACION.md`), pero puntuar de verdad exige una corrida
   que abarque el incendio completo y no 12 h.
4. **`SIMULATION_TSTART` quedó en 0 en estas corridas**, porque el directorio de preparación es
   anterior al arreglo del anclaje. Una preparación nueva las mueve.

---



## 7. Limitaciones y sensibilidades



### Limitaciones

1. **Desfase temporal: 2017 contra un incendio de febrero de 2026, nueve años.** Es el precio
  de la discriminación por especie. Mitigación: contrastar con el histórico de FIRMS los
   fuegos del intervalo; MapBiomas 2024 queda como control de dos años de desfase.
2. **Hueco fronterizo del 4,55 %**, relleno con WorldCover (IGN-20 §7.5, opción 1). El relleno
  es idéntico para los tres mapas, así que no sesga la comparación, pero el borde oeste del
   dominio se apoya en el insumo pobre.
3. **SB40 no distingue lo que CCS-BAP sí distingue** (§5.5): ñire bajo y lenga achaparrada
  comparten modelo, y coihue y ciprés también. El techo ahora es el sistema de modelos, no el
   insumo. Es el argumento de la Etapa C.
4. **Homogeneidad dentro de la clase**: no se distingue estado sucesional, historia de fuego ni
  carga de material muerto en pie, salvo por la clase de disturbio reciente.
5. **Agregación a 30 m por clase mayoritaria**: se pierden corredores de combustible más
  angostos que un píxel, y la continuidad gobierna la propagación.
6. **La PT-37 sólo cubre arbustales**, no bosque. Las clases de bosque siguen sin carga medida.



### Sensibilidades a evaluar


| #   | Decisión           | Alternativa                              | Motivo                                          |
| --- | ------------------ | ---------------------------------------- | ----------------------------------------------- |
| S1  | TF Le → TL6        | TU2 (162) o TL2 (182)                    | 10,64 % del AOI, sin sotobosque medido          |
| S2  | OFL Le → SH8       | SH3 (143), carga menor                   | 8,71 % del AOI, sin carga medida                |
| S3  | Rem Dist Rec → GS3 | SB2 (202)                                | 5,40 %, depende de cuánto pesa el muerto en pie |
| S4  | Clave (N1,N2)      | Nivel 3 completo, 92 clases              | El nivel 3 no tiene exactitud reportada propia  |
| S5  | Cargas de SB40     | Sustituir `w0_1h` por el medido en PT-37 | Es la rama parcial de la Etapa C §C0            |


---



## 8. Verificación

- `ccsbap_fuel_code()` **levanta excepción** ante una clase de leyenda sin modelo asignado. Un
`KeyError` silencioso mandaría una clase real a no combustible sin que nadie lo note.
- `assert_codes_are_defined()` verifica, antes de escribir el ráster, que todo código exista en
la tabla que ELMFIRE realmente carga. ELMFIRE resuelve cualquier código ausente al modelo
256 (NB, no combustible) **sin error y sin registro**.
- Las 92 clases de nivel 3 de Chubut resuelven a un modelo; verificado al construir el ráster.



## 9. Estado de aprobación


|                                   |               |
| --------------------------------- | ------------- |
| Propuesta elaborada               | 2026-09-15    |
| Paso 4 sobre la quema de la PT-37 | **pendiente** |
| Revisión del director             | **pendiente** |


Puntos que requieren decisión explícita:

1. **OFL Le → SH8** (§5.5): 8,71 % del AOI por analogía, sin carga medida.
2. **TF Le → TL6** (§5.1): la clase de bosque más extensa, elegida sin dato de sotobosque.
3. **Rem Dist Rec → GS3** (§5.7): 5,40 % del AOI, once años de regeneración supuestos.
4. **Época 2017 frente al desfase de nueve años** (§7.1).



## 10. Fuentes

- CIEFAP, MAyDS (2016). *Actualización de la Clasificación de Tipos Forestales y Cobertura del
Suelo de la Región Bosque Andino Patagónico. Informe Final.* Capa `cob_2017_N3_aok_CH`,
provista por CIEFAP el 2026-09-13.
- Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. (2012). *Modelos de combustibles en
el ecotono bosque-estepa de la Patagonia andina.* CIEFAP, Publicación Técnica N.º 37.
ISSN 1514-2264. (Tabla 2: cargas por clase de tamaño · §3.1: descripción de los modelos ·
§3.3-3.4: quema experimental)
- Scott, J.H.; Burgan, R.E. (2005). RMRS-GTR-153. (Procedimiento de selección pp. 8-9 · alcance
p. 3 · modelos dinámicos p. 4 · parámetros Tabla 7)
- Bianchi, L.O.; Defossé, G.E. *Ignition probability of fine dead surface fuels of native
Patagonian forests of Argentina.* Forest Systems.
- Mermoz, M.; Kitzberger, T.; Veblen, T.T. (2005). Ecology 86(10).
- Cóbar-Carranza, A.J.; García, R.A.; Pauchard, A.; Peña, E. (2014). *Effect of Pinus contorta
  invasion on forest fuel properties and its potential implications on the fire regime of
  Araucaria araucana and Nothofagus antarctica forests.* Biological Invasions. (Carga de leña
  fina en rodales de ñire; inflamabilidad comparada de nativas y pino exótico, relevante para
  la clase de forestación exótica.)
- Interno: `IGN-20-CROSSWALK.md` · `ETAPA-B-INSUMO-PATAGONICO.md` ·
`ETAPA-C-MODELOS-PROPIOS.md` §C0 · `app/elmfire/builder/fuels_builder.py` ·
`scripts/build_fuel_maps.py`

