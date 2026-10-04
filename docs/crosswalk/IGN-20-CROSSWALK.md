# IGN-20 · Tabla de correspondencia MapBiomas Argentina → Scott & Burgan FBFM40

> **Estado: comparador vigente.** La generación del ráster está implementada. MapBiomas no
> sustituye a CCS-BAP en `modelo-v0`; se conserva como punto intermedio para la comparación final
> de mapas.
>
> Área de interés: Parque Nacional Los Alerces y entorno.
> −72,05 / −42,90 / −71,15 / −42,05 (EPSG:4326) · 948.092 ha · grilla EPSG:32719, 30 m.

---

## 1. Objeto y alcance

Asignar a cada clase de cobertura de **MapBiomas Argentina Colección 2** un modelo de combustible del sistema **Scott & Burgan FBFM40** (Gen. Tech. Rep. RMRS-GTR-153, 2005), de modo que el ráster `fbfm40.tif` que consume ELMFIRE represente la vegetación patagónica con
un criterio explícito, citable y reproducible.

**Lo que esta tabla es:** una asignación fundamentada, clase por clase, siguiendo el
procedimiento de selección publicado por los autores del sistema, contrastada contra
evidencia de comportamiento del fuego medida en la Patagonia andina.

**Lo que esta tabla no es:** una parametrización nueva del modelo de Rothermel. No se
modifican cargas, relaciones superficie-volumen, profundidades ni humedades de extinción de
los modelos FBFM40. Esa línea de trabajo está especificada en `docs/out-of-scope/ETAPA-C-MODELOS-PROPIOS.md` y
queda condicionada a disponer de mediciones de campo.

---



## 2. Por qué se cambia de insumo

El crosswalk vigente parte de ESA WorldCover v200, que dispone de **una única clase arbórea** para todo el Bosque Andino Patagónico. La consecuencia, medida sobre una corrida real (`docs/historico/SIMULATION_AUDIT.md` §1 y §2.1):


|                                 | WorldCover v200 (2021) | MapBiomas Col. 2 (2024)       |
| ------------------------------- | ---------------------- | ----------------------------- |
| Arbustal                        | **0,04 %**             | **25,86 %**                   |
| No combustible                  | 23,0 %                 | 24,23 %                       |
| Turberas                        | sin clase              | 0,06 % (clase propia)         |
| Mallines / herbáceas inundables | sin clase              | 5,07 %                        |
| Bosque cerrado vs abierto       | no distingue           | distingue                     |
| Sin dato sobre el AOI           | 0 % (global)           | 6,06 % (corta en la frontera) |


Un 0,04 % de arbustal es incompatible con la evidencia regional. Mermoz, Kitzberger y Veblen (2005) establecen que en los bosques y matorrales patagónicos **los matorrales presentan mayor ocurrencia y propagación de fuego que los bosques**; Godoy et al. (2022) reportan 15 % de arbustal y 23 % de bosque abierto de ñire para Esquel–Trevelin, inmediatamente al este del parque. El insumo global estaba suprimiendo el tipo de combustible que gobierna el régimen de fuego de la región.

**Resultado negativo que también corresponde registrar:** la sospecha de que la fracción no combustible (23 %) fuera un artefacto de sobreasignación de `bare/sparse` de WorldCover a 10 m **no se sostiene**. Dos productos independientes, con sensores y metodologías distintas, coinciden en ~24 %.

---



## 3. Método de asignación

Se aplica de forma explícita el procedimiento de selección de Scott & Burgan (2005, pp. 8-9), paso por paso, en lugar de una asignación por analogía de nombres.


| Paso  | Enunciado original                                                                                                                                                                                                | Cómo se instrumenta acá                                                                                                                                                                                                                                                                                                                                    |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | *"Determine the general fire-carrying fuel type […] Estimate which stratum of surface fuels is most likely to carry the fire"*                                                                                    | Se identifica el estrato portador para cada clase. Los autores advierten explícitamente que en un área forestada con dosel abierto puede ser el pasto y no la hojarasca quien propague.                                                                                                                                                                    |
| **2** | *"The dead fuel extinction moisture […] is generally associated with climate (humid versus dry)"*                                                                                                                 | Se elige la variante de humedad de extinción con **evidencia patagónica medida**, no con la etiqueta climática nominal del modelo (§4).                                                                                                                                                                                                                    |
| **3** | *"Note the general depth, compactness, and size of the fuel, and the relative amount of live vegetation"*                                                                                                         | Se contrasta la descripción fisonómica de la clase MapBiomas contra la profundidad de lecho y la proporción viva/muerta tabuladas por los autores.                                                                                                                                                                                                         |
| **4** | *"Do not restrict your selection by fuel model name or fuel type. After selecting a fuel model, view its predicted fire behavior to be sure the predicted behavior agrees with your expectation or observation."* | **Filtro de rechazo.** Se compara la clase adjetiva de tasa de propagación y longitud de llama publicada por los autores (escenario D2L2, viento a media llama 8 km/h, pendiente nula) contra el comportamiento observado en la región. Una asignación cuyo comportamiento predicho contradice la observación **se rechaza aunque la descripción encaje**. |
| **5** | —                                                                                                                                                                                                                 | Se registra la procedencia de la decisión: respaldo bibliográfico, o juicio del autor declarado como tal.                                                                                                                                                                                                                                                  |


Escala adjetiva de referencia (Scott & Burgan, Tabla 5): *muy baja* 0-2 ch/h · *baja* 2-5 · *moderada* 5-20 · *alta* 20-50 · *muy alta* 50-150 · *extrema* >150.

---



## 4. Marco de evidencia patagónica para la humedad de extinción

La humedad de extinción del combustible muerto (`mex`) es el parámetro con mayor respaldo local disponible, y el que más separa esta propuesta del baseline.

Los propios autores del sistema reconocen que es un parámetro de modelación asociado al clima *"though fire science research has yet to explain the mechanism for the association"* (Scott & Burgan 2005, p. 5). Esa admisión es la justificación formal para elegir la variante climática con datos regionales en lugar de heredar la etiqueta del modelo norteamericano.

**Bianchi & Defossé** (*Ignition probability of fine dead surface fuels of native Patagonian forests of Argentina*, Forest Systems) midieron el umbral de contenido de humedad por debajo del cual se produce ignición en combustibles finos muertos de bosque nativo patagónico:


| Sitio                             | Umbral de ignición |
| --------------------------------- | ------------------ |
| Ciprés (*Austrocedrus chilensis*) | **21,5 %**         |
| Ñire (*Nothofagus antarctica*)    | **25,0 %**         |


**Consecuencia directa sobre la tabla:** el baseline asigna sistemáticamente modelos de clima seco con `mex` de 15 a 20 % — TL3 (20 %), GR2 (15 %), SH5 (15 %) — es decir, **por debajo de los umbrales de ignición medidos en la región**. Un lecho de combustible que la medición muestra encendiéndose al 25 % de humedad está siendo modelado como incapaz de propagar por encima del 15-20 %. Toda la propuesta usa `mex ≥ 25 %` en las clases con vegetación, salvo justificación en contrario por clase.

Esto es un argumento cuantitativo y citable, no una analogía.

---



## 5. Tabla de correspondencia propuesta


| Cód. MapBiomas | Clase                            | % AOI   | → FBFM40    | Modelo                                        | `mex` | Dinámico |
| -------------- | -------------------------------- | ------- | ----------- | --------------------------------------------- | ----- | -------- |
| 3              | Bosques cerrados                 | 31,38 % | **165**     | TU5 · Timber-Shrub carga muy alta             | 25    | no       |
| 4              | Bosques abiertos                 | 0,00 %  | **163**     | TU3 · Timber-Grass-Shrub carga moderada       | 30    | sí       |
| 6              | Bosques inundables               | 0,06 %  | **162**     | TU2 · Timber-Shrub clima húmedo               | 30    | no       |
| 66             | Arbustales cerrados              | 0,00 %  | **149**     | SH9 · Shrub carga muy alta clima húmedo       | 40    | sí       |
| 77             | Arbustales abiertos              | 22,48 % | **144**     | SH4 · Timber-Shrub carga baja clima húmedo    | 30    | no       |
| 63             | Mosaicos de arbustos y herbáceas | 3,39 %  | **123**     | GS3 · Grass-Shrub carga moderada clima húmedo | 40    | sí       |
| 12             | Herbáceas                        | 2,63 %  | **103**     | GR3 · Grass muy grueso clima húmedo           | 30    | sí       |
| 11             | Herbáceas inundables (mallines)  | 5,07 %  | **105**     | GR5 · Grass carga baja clima húmedo           | 40    | sí       |
| 73             | Turberas                         | 0,06 %  | **99**      | NB9 — **fuera del alcance del modelo** (§7.1) | —     | no       |
| 9              | Silvicultura                     | 1,22 %  | **188**     | TL8 · Long-Needle Litter                      | 35    | no       |
| 15             | Pasturas                         | 0,00 %  | **102**     | GR2 · Grass carga baja                        | 15    | sí       |
| 18 / 19 / 36   | Agricultura y cultivos           | 0,00 %  | **101**     | GR1 · Grass ralo                              | 15    | sí       |
| 21             | Mosaico de usos                  | 3,42 %  | **101**     | GR1 · Grass ralo                              | 15    | sí       |
| 24             | Áreas urbanas                    | 0,23 %  | **91**      | NB1 · Urbano                                  | —     | no       |
| 25             | Otras áreas no vegetadas         | 18,09 % | **99**      | NB9 · Suelo desnudo                           | —     | no       |
| 33             | Ríos, lagunas, lagos             | 3,36 %  | **98**      | NB8 · Agua                                    | —     | no       |
| 34             | Hielo y nieve permanente         | 2,55 %  | **92**      | NB2 · Nieve/hielo                             | —     | no       |
| 27             | No observado                     | 1,52 %  | **99**      | NB9 — declarado (§7.4)                        | —     | no       |
| 0              | Sin dato (lado chileno)          | 4,54 %  | *pendiente* | Decisión abierta (§7.5)                       | —     | —        |


Los porcentajes provienen de `scripts/probe_mapbiomas.py` sobre la ventana del AOI, Colección 2, año 2024.

---



## 6. Fichas de asignación



### 6.1 · Clase 3 — Bosques cerrados → **165 (TU5)** · 31,38 % del AOI

**Composición en el AOI.** Coihue (*Nothofagus dombeyi*, perennifolio), lenga (*N. pumilio*, caducifolio), ciprés de la cordillera (*Austrocedrus chilensis*, conífera) y alerce (*Fitzroya cupressoides*, conífera), en bosques puros y mixtos de dosel cerrado.

**Paso 1 · Estrato portador.** No es la hojarasca. Los bosques de *Nothofagus* y *Austrocedrus* de la Patagonia andina presentan un sotobosque leñoso denso —caña colihue (*Chusquea culeou*), *Berberis*, *Maytenus*, *Schinus*— y material muerto en pie. El estrato portador es **hojarasca con sotobosque arbustivo**, lo que sitúa la clase en la familia Timber-Understory (TU), no en Timber Litter (TL).

**Paso 2 · Humedad de extinción.** Umbral de ignición medido de 21,5 % en ciprés (§4). TU5 tiene `mex = 25 %`, el valor de la familia TU más cercano por encima del umbral medido.

**Paso 3 · Estructura.** TU5 es el modelo de mayor carga de la familia: 4,0 t/ac de 1 h, 4,0 de 10 h, 3,0 de 100 h y 3,0 de leñoso vivo — **14,0 t/ac totales**, carga fina 7,0 t/ac. Descripción de los autores: *"heavy forest litter with a shrub or small tree understory"*. Corresponde a un bosque maduro con sotobosque desarrollado y acumulación de material grueso, que es lo que hay.

**Paso 4 · Contraste de comportamiento.** TU5: propagación *moderada*, longitud de llama *moderada*. Consistente con un régimen de fuego de superficie en bosque cerrado. **Se rechaza TL3 (183)**, la asignación del baseline: carga fina de 0,50 t/ac, profundidad de lecho 0,3 pies, sin componente vivo, `mex` 20 %, y comportamiento publicado de propagación *muy baja* y llama *baja*. Es un modelo de hojarasca de conífera pura sin sotobosque — describe un fuelbed que no es el de Los Alerces, y su comportamiento contradice la ocurrencia de incendios de superficie extensos en la región.

**Procedencia.** Bibliográfica en cuanto al estrato portador y a `mex`. La elección de TU5 frente a TU2 es juicio fundamentado del autor sobre la carga.

**Limitación declarada.** MapBiomas agrupa en una sola clase el bosque caducifolio de lenga, el perennifolio de coihue y el conífero de ciprés y alerce, cuyos lechos de hojarasca son físicamente distintos. **Esta es la principal pérdida de información respecto de CCS-BAP**, que sí discrimina especie, y la razón por la que la Etapa B mantiene CCS-BAP como objetivo.

---



### 6.2 · Clase 77 — Arbustales abiertos → **144 (SH4)** · 22,48 % del AOI

> **Es la asignación más incierta de la tabla y la segunda en superficie. Requiere revisión
> específica del director y se evalúa por sensibilidad (§8).**

**Composición.** Matorral patagónico: ñire arbustivo (*N. antarctica*), laura (*Schinus patagonicus*), radal (*Lomatia hirsuta*), *Berberis*, *Discaria*.

**Paso 1 · Estrato portador.** Arbustivo. La clase MapBiomas 63 existe por separado para el mosaico de arbustos y herbáceas, de modo que la clase 77 es **dominada por arbustos con claros**, no una co-dominancia arbusto-pasto. Eso ubica la asignación en la familia SH y no en GS.

**Paso 2 · Humedad de extinción.** Umbral medido de 25,0 % en ñire (§4). SH4 tiene `mex = 30 %`, clima subhúmedo a húmedo. **Se descarta SH5 (145), la asignación del baseline**, por `mex = 15 %`: modela el matorral patagónico como incapaz de propagar por encima del 15 % de humedad, cuando la medición regional muestra ignición al 25 %.

**Paso 3 · Estructura.** SH4: carga fina 3,4 t/ac, profundidad de lecho 3,0 pies (~0,9 m), 0,11708 lb/ft² de leñoso vivo, sin componente herbáceo. Compatible con matorral abierto de porte medio.

**Paso 4 · Contraste de comportamiento.** SH4: propagación *alta*, llama *moderada*. Consistente con Mermoz et al. (2005), que documentan que los matorrales patagónicos propagan más que los bosques. **Se rechaza SH3 (143)** pese a que su `mex` de 40 % y su profundidad de 2-3 pies encajan bien en los pasos 2 y 3: su comportamiento publicado es propagación *baja* y llama *baja*, lo que contradice directamente la observación regional. Es un caso donde el paso 4 anula a los pasos 2 y 3, exactamente como los autores prescriben.

**Procedencia.** `mex` con respaldo bibliográfico. La elección de SH4 sobre GS3 y SH3 es **juicio del autor**, y es el punto más débil de la tabla: no existe un modelo FBFM40 construido sobre un matorral de *Nothofagus*.

---



### 6.3 · Clase 63 — Mosaicos de arbustos y herbáceas → **123 (GS3)** · 3,39 % del AOI

**Paso 1.** Co-dominancia arbusto-herbácea; ambos componentes gobiernan el comportamiento. Familia Grass-Shrub por definición de la clase de origen.

**Paso 2.** GS3, `mex = 40 %`, clima subhúmedo a húmedo. Por encima del umbral medido.

**Paso 3.** Carga fina 3,0 t/ac, profundidad 1,8 pies, con carga herbácea viva (0,06657) y leñosa viva (0,05739) equilibradas. *"Moderate grass/shrub load, average grass/shrub depth less than 2 feet."*

**Paso 4.** Propagación *alta*, llama *moderada*. Coherente con un ecotono que arde con facilidad.

**Modelo dinámico.** GS3 transfiere carga herbácea viva a muerta en función de la humedad del combustible herbáceo vivo. Verificado que ELMFIRE 2025.0212 implementa la transferencia dinámica (columna `dynamic` en la tabla de combustibles, precómputo por humedad herbácea).

**Si el modelo se usara en un procesador no dinámico, no propagaría** (Scott & Burgan, p. 4).

---



### 6.4 · Clase 12 — Herbáceas → **103 (GR3)** · 2,63 % del AOI

**Paso 1.** Pastizal. En el AOI se trata de pastizal de altura andino, no de estepa árida: el gradiente árido está al este del dominio.

**Paso 2.** GR3, `mex = 30 %`, clima subhúmedo a húmedo. **Se descarta GR2 (102)**, la asignación del baseline, por `mex = 15 %` y etiqueta de clima seco.

**Paso 3.** *"Very coarse grass, average depth about 2 feet"*, carga fina 1,6 t/ac. El coirón (*Festuca*, *Stipa*) es un pasto amacollado grueso; la descripción de GR3 es el ajuste fisonómico correcto dentro de la familia.

**Paso 4.** Propagación *alta*, llama *moderada*.

---



### 6.5 · Clase 11 — Herbáceas inundables (mallines) → **105 (GR5)** · 5,07 % del AOI

**Paso 1.** Pastizal higrófilo sobre suelo estacionalmente saturado. Los mallines son
formaciones de alta productividad que permanecen verdes hasta avanzado el verano.

**Paso 2.** GR5, `mex = 40 %` — el valor más alto de la familia GR. Es la manera correcta de
codificar "sólo propaga cuando está curado" dentro del formalismo de Rothermel.

**Paso 3.** Carga fina 2,9 t/ac, profundidad 1,5 pies, carga herbácea viva alta (0,11478).

**Paso 4.** Propagación *muy alta*, llama *alta* **cuando está curado**. El modelo es
dinámico: con humedad del combustible herbáceo vivo alta, la carga permanece viva y el
comportamiento cae drásticamente. Es exactamente la fenología de un mallín, y depende de
`LH_MOISTURE_CONTENT` (§7.3).

---



### 6.6 · Clase 73 — Turberas → **99 (NB9)** · declarado fuera de alcance · 0,06 %

**No se asigna un modelo de superficie porque el fenómeno no es de superficie.**

Scott & Burgan (2005, p. 3) delimitan el alcance del conjunto de manera explícita: los
modelos representan *"surface fire behavior at the flaming front only, not residual
combustion that takes place after the flaming front has passed"*, y advierten que sus
parámetros *"should not be used as fuelbed characteristics for fuel consumption models"*.

Una turbera arde por **combustión latente subterránea**, un proceso que el modelo de Rothermel
no representa en absoluto. Asignarle un modelo de superficie produciría un número sin
sustento físico. Asignarle NB9 lo declara explícitamente fuera del alcance del modelo.

**Esto subestima el fuego en turberas.** Es una limitación aceptada y declarada, no un
resultado. En este AOI afecta al 0,06 % de la superficie, de modo que es inmaterial para la
validación; en un dominio con turberas extensas —Tierra del Fuego— invalidaría el enfoque.

---



### 6.7 · Clases arbóreas restantes

**Clase 4 — Bosques abiertos → 163 (TU3).** Con dosel abierto, el estrato portador se
desplaza al pasto y al arbusto del sotobosque; es precisamente la advertencia del paso 1 de
Scott & Burgan. TU3: *"moderate forest litter with grass and shrub components"*, `mex = 30 %`,
dinámico, propagación *alta* y llama *moderada*. Ausente del AOI actual (0,00 %), se define
por completitud de la leyenda.

**Clase 6 — Bosques inundables → 162 (TU2).** Bosque sobre suelo saturado. TU2:
*"moderate litter load with shrub component"*, `mex = 30 %`, propagación *moderada*, llama
*baja*. 0,06 % del AOI.

**Clase 9 — Silvicultura → 188 (TL8).** Las plantaciones patagónicas son mayoritariamente de
*Pinus ponderosa* y *P. contorta*, coníferas de acícula larga. TL8 es literalmente
*"Long-Needle Litter"*, `mex = 35 %`, propagación *moderada*, llama *baja*. 1,22 % del AOI.
**Reserva:** en plantaciones jóvenes y densas, con combustible de escalera y pasto entre
líneas, TU5 sería mejor descriptor. MapBiomas no informa edad del rodal. Declarado.

---



### 6.8 · Clases antrópicas y no combustibles

**21 Mosaico de usos y 18/19/36 Agricultura → 101 (GR1).** *"Grass is short, patchy, and
possibly heavily grazed"*, carga fina 0,40 t/ac. **Deliberadamente no se asigna NB3
(agrícola no combustible)**: los propios autores advierten que *"there are many agricultural
areas that are not kept in a nonburnable condition"* (p. 22). Declarar no combustible algo
que arde es el error peligroso; el error inverso es conservador.

**15 Pasturas → 102 (GR2).** Pastura implantada, carga mayor y lecho más continuo que GR1.

**24 Áreas urbanas → 91 (NB1)** · **25 Otras áreas no vegetadas → 99 (NB9)** ·
**33 Ríos, lagunas y lagos → 98 (NB8)** · **34 Hielo y nieve permanente → 92 (NB2)**.

> **Corrección respecto del baseline.** El crosswalk de WorldCover mapeaba nieve y hielo a
> **93 (NB3, "Agricultural")**, que es semánticamente incorrecto: NB2 es la clase de nieve y
> hielo del sistema. Con la tabla de combustibles propia (`app/elmfire/fuel_models.csv`), que
> incorpora las filas NB ausentes de la tabla por defecto de ELMFIRE, el código 92 ya está
> definido y la asignación correcta es posible. Sin efecto sobre el comportamiento del fuego
> —ambas son no combustibles— pero sí sobre la corrección de la leyenda y del mapa publicado.

---



## 7. Limitaciones

Enunciadas como requisito de aceptación de IGN-20.

### 7.1 · Alcance del modelo de Rothermel

Se representa únicamente el **frente de llama superficial**. Quedan fuera la combustión
latente y el consumo residual, lo que hace inaplicable el enfoque a turberas (§6.6). El
comportamiento de fuego de copa se resuelve por separado, a partir de `cc`, `ch`, `cbh` y
`cbd`, y no depende de esta tabla.

### 7.2 · Supuesto de homogeneidad y continuidad

Los modelos FBFM40 heredan de Rothermel (1972) el supuesto de un lecho de combustible
**homogéneo y continuo** (Scott & Burgan, p. 3). El mosaico bosque–matorral–pastizal del
ecotono patagónico lo viola de manera estructural. La agregación por clase mayoritaria a 30 m
(`ETAPA-A-BASELINE.md` §A5) impone además una pérdida de continuidad: **corredores de
combustible más angostos que un píxel desaparecen**, y la continuidad gobierna la propagación.

### 7.3 · Humedad del combustible vivo

Seis de las asignaciones propuestas —TU3, SH9, GS3, GR3, GR5, GR1/GR2— son **modelos
dinámicos** o tienen carga viva. Con el baseline TL3 esto era irrelevante, porque TL3 no tiene
componente vivo. Con esta tabla, `LH_MOISTURE_CONTENT` y `LW_MOISTURE_CONTENT` pasan a ser
**drivers de primer orden**.

ELMFIRE acepta **un escalar global por cada uno** para todo el dominio; no existe un ráster de
humedad viva. Cualquier valor es una media espacial. La fuente para fijarlos es Bianchi &
Defossé (2015), que mide contenido de humedad del combustible vivo por especie en la Patagonia
andina, ponderada por área de clase y referida al **período de quema** (verano tardío), no a
la media anual. Especificado en `ETAPA-B-INSUMO-PATAGONICO.md` §B5.

### 7.4 · Calibración de origen y ausencia de precedente

FBFM40 se construyó a partir de series fotográficas de combustibles de Estados Unidos
(Scott & Burgan, p. 3). **Ninguna especie patagónica participó de su calibración.** No se
localizó ningún crosswalk publicado de vegetación patagónica a FBFM40; esta tabla es una
propuesta original y debe presentarse como tal.

Antecedente regional relevante: Chile **no adaptó** los modelos norteamericanos sino que
construyó los propios en el sistema **KITRAL** (Laboratorio de Incendios Forestales,
Universidad de Chile), con cartografía nacional de modelos de combustible para vegetación
chilena, incluidas formaciones de *Nothofagus*. Es el precedente que fundamenta la
`docs/out-of-scope/ETAPA-C-MODELOS-PROPIOS.md`.

### 7.5 · Cobertura del insumo y hueco fronterizo

MapBiomas Argentina termina en el límite internacional. **El 4,54 % del AOI —todo el tercio
oeste, hasta lon −71,72— queda sin dato**, más un 1,52 % de "no observado": **6,06 % sin clase
asignable**. CCS-BAP tendrá la misma limitación, por ser el inventario del BAP argentino.

No es cosmético: está sobre el borde oeste del dominio computacional, y un borde
artificialmente incombustible **frena el frente por construcción**, sesgando la validación.
Opciones a resolver antes de generar el ráster:

1. Rellenar con ESA WorldCover reclasificado (global, sin hueco, clases pobres).
2. Rellenar con el Catastro de Bosque Nativo de CONAF del lado chileno (leyenda propia,
  requiere un segundo crosswalk).
3. Declarar no combustible y acotar el alcance del claim.

**Decisión pendiente.** La opción 1 es la de menor esfuerzo y mantiene el dominio cerrado.

### 7.6 · Homogeneidad dentro de la clase

La correspondencia clase → modelo supone que todos los píxeles de una clase comparten
fuelbed. No se distingue estado sucesional, historia de fuego, carga de material muerto en
pie ni densidad de sotobosque. Un bosque de coihue maduro y uno regenerando tras incendio
reciben el mismo modelo.

### 7.7 · Desfase temporal

MapBiomas Colección 2 año 2024 contra el incendio de validación de febrero de 2026: **dos
años**. Mejor que los cinco del baseline (WorldCover 2021), pero no nulo. Corresponde
verificar con el histórico de FIRMS si hubo fuegos en el AOI entre 2024 y 2026 que hayan
modificado la cobertura.

---



## 8. Sensibilidades a evaluar

No sustituyen a la tabla; cuantifican cuánto depende el resultado de las decisiones más
discutibles.


| #   | Decisión                     | Alternativa                               | Motivo                                                                                     |
| --- | ---------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------ |
| S1  | Clase 77 → SH4               | GS3 (123) o SH3 (143)                     | Asignación más incierta, 22,48 % del AOI                                                   |
| S2  | Clase 3 → TU5                | TU2 (162), `mex` 30                       | El oeste del parque es valdiviano, más húmedo que la etiqueta "dry climate" de TU5         |
| S3  | `LH/LW_MOISTURE_CONTENT`     | Rango medido por Bianchi & Defossé (2015) | Si el resultado es muy sensible, un escalar global es insuficiente y corresponde un ráster |
| S4  | Relleno del hueco fronterizo | Las tres opciones de §7.5                 | Afecta el borde oeste del dominio                                                          |


---



## 9. Verificación automática

El criterio de aceptación de IGN-21 —*"todos los píxeles corresponden a un código FBFM40
válido"*— se implementa contra la tabla que **ELMFIRE realmente carga**, no contra el rango
numérico 90-204.

ELMFIRE 2025.0212 resuelve cualquier código ausente de su tabla de combustibles al modelo
**256 (NB)** —carga 0,0001, profundidad 0,01, no combustible— **sin error y sin registro**. Un
código huérfano convierte parte del parque en incombustible en silencio e invalida la corrida.

`fuels_builder.assert_codes_are_defined()` levanta excepción antes de escribir el ráster.
Cubierto por `tests/test_fuels_cache.py`.

---



## 10. Estado de aprobación


|                        |               |
| ---------------------- | ------------- |
| Propuesta elaborada    | 2026-09-06    |
| Revisión del director  | **pendiente** |
| Aprobación para IGN-21 | **pendiente** |


Puntos que requieren decisión explícita antes de implementar:

1. **Clase 77 → SH4** (§6.2) — la asignación más incierta, 22,48 % del AOI.
2. **Relleno del hueco fronterizo** (§7.5) — afecta el borde oeste del dominio.
3. **Turberas fuera de alcance** (§6.6) — inmaterial acá, invalidante en otros dominios.
4. **Ponderación de la humedad del combustible vivo** (§7.3).

---



## 11. Fuentes

**Sistema de modelos de combustible**

- Scott, J.H.; Burgan, R.E. (2005). *Standard Fire Behavior Fuel Models: A Comprehensive Set for Use with Rothermel's Surface Fire Spread Model.* Gen. Tech. Rep. RMRS-GTR-153. USDA Forest Service, Rocky Mountain Research Station. 72 p. (Alcance y supuestos p. 3 · parámetros constantes p. 2 · bloques de numeración p. 5 · procedimiento de selección pp. 8-9 · modelos dinámicos pp. 4, 6-7 · Tabla 7 p. 18 · clases NB pp. 19-24)
- Rothermel, R.C. (1972). *A mathematical model for predicting fire spread in wildland fuels.* Res. Pap. INT-115.

**Evidencia patagónica**

- Bianchi, L.O.; Defossé, G.E. *Ignition probability of fine dead surface fuels of native Patagonian forests of Argentina.* Forest Systems. [https://fs.revistas.csic.es/index.php/fs/article/view/4632](https://fs.revistas.csic.es/index.php/fs/article/view/4632)
- Bianchi, L.O.; Defossé, G.E. (2015). *Live fuel moisture content and leaf ignition of forest species in Andean Patagonia, Argentina.* Int. J. Wildland Fire 24(3):340.
- Mermoz, M.; Kitzberger, T.; Veblen, T.T. (2005). *Landscape influences on occurrence and spread of wildfires in Patagonian forests and shrublands.* Ecology 86(10).
- Godoy, M.M. et al. (2022). *Forty Years of Wildland Urban Interface Growth and Its Relation With Wildfires in Central-Western Chubut, Argentina.* Front. For. Glob. Change.
- Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. *Modelos de combustibles en el ecotono bosque-estepa de la Patagonia andina.* CIEFAP, Publicación Técnica N.º 37, Esquel, 2012. **(obtenida 2026-09-13; evaluada en** `docs/out-of-scope/ETAPA-C-MODELOS-PROPIOS.md` **§C0, todavía no incorporada a las fichas §6)**

**Insumo de cobertura**

- MapBiomas Argentina, Colección 2 (1985-2024), 30 m, Landsat. Leyenda: [https://argentina.mapbiomas.org/wp-content/uploads/sites/12/2025/09/Leyenda_Code.pdf](https://argentina.mapbiomas.org/wp-content/uploads/sites/12/2025/09/Leyenda_Code.pdf) Datos: `argentina_coverage_2024.tif`, COG público.
- CIEFAP, MAyDS (2016). *Actualización de la Clasificación de Tipos Forestales y Cobertura del Suelo de la Región Bosque Andino Patagónico.* **(objetivo de la Etapa B, en gestión)**

**Antecedente de modelos propios**

- Sistema KITRAL — Laboratorio de Incendios Forestales, Facultad de Ciencias Forestales y Conservación de la Naturaleza, Universidad de Chile.

**Interno**

- `docs/historico/SIMULATION_AUDIT.md` §1, §2.1 · `docs/resultados/IGN-26-VALIDACION.md` §12 · `ETAPA-A-BASELINE.md` · `ETAPA-B-INSUMO-PATAGONICO.md` · `docs/out-of-scope/ETAPA-C-MODELOS-PROPIOS.md` · `scripts/probe_mapbiomas.py`
- ELMFIRE 2025.0212, `build/source/elmfire_init.f90` — [https://github.com/lautenberger/elmfire](https://github.com/lautenberger/elmfire)
