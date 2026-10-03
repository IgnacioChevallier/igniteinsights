# IGN-20B · Tabla de correspondencia CCS-BAP → Scott & Burgan FBFM40

> **Estado: propuesta original, pendiente de revisión y aprobación del director.** Entregable final de IGN-20 para revisión: CCS-BAP es el insumo principal; MapBiomas queda como comparación intermedia y ESA WorldCover como baseline. El issue nació como «tabla de correspondencia ESA WorldCover → FBFM40»; este documento conserva ese objetivo comparativo con el nuevo insumo patagónico.
>
> La tabla completa está en §4, su fundamento en §5 y sus limitaciones y sensibilidades en §7. Las referencias a otros archivos identifican procedencia; el argumento necesario para decidir está incluido acá.
>
> **Actualización del 2026-09-30 (auditoría física, `AUDITORIA-FISICA.md`).** Las simulaciones de
> §6.1–§6.3 tenían dos errores de interfaz con ELMFIRE, ya corregidos: el clima quedaba fijo en su
> primera hora durante toda la corrida y el frente avanzaba a la mitad de la velocidad calculada.
> §6.1, §6.2 y §6.3 están re-medidos con la interfaz corregida, con las cifras anteriores al lado.
> **La tabla de correspondencia (§4) no cambia.** Cambian una conclusión del paso 4 (el sesgo del
> arbustal es la mitad de grande) y el valor de humedad viva adoptado (100 %). Además se agregan la
> interacción del ñire bajo y la lenga achaparrada con el dosel (§5.4) y dos limitaciones del
> dosel (§7). Las decisiones abiertas están resumidas en `DECISIONES-DIRECTOR.md`.
>
> Área de interés: Parque Nacional Los Alerces y entorno. −72,05 / −42,90 / −71,15 / −42,05 (EPSG:4326) · 699.000 ha · grilla EPSG:32719, 30 m.

---

## 1. El insumo

**Clasificación de Tipos Forestales y Cobertura del Suelo de la Región Bosque Andino Patagónico** (CIEFAP, MAyDS y provincias). Acceso otorgado por CIEFAP el 2026-09-13.


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


También se recibieron Río Negro, Neuquén, Santa Cruz y Tierra del Fuego, y la **época 2013** de cada una. Ninguna es necesaria para este AOI; la de 2013 se usa como control temporal.

### 1.1 Por qué 2017 y no 2013

Comparando ambas épocas dentro del AOI aparece un cambio que ningún producto global registra:


| Clase                           | 2013       | 2017          | Δ           |
| ------------------------------- | ---------- | ------------- | ----------- |
| Remanente de disturbio reciente | 155 ha     | **37.736 ha** | **+37.581** |
| Lenga                           | 143.012 ha | 135.275 ha    | −7.737      |
| Ñire                            | 75.704 ha  | 68.308 ha     | −7.395      |
| Mixto de ñire                   | 27.683 ha  | 20.727 ha     | −6.956      |
| Coihue                          | 53.723 ha  | 46.919 ha     | −6.804      |


Las pérdidas por especie suman lo que gana "remanente de disturbio reciente". Por fecha y magnitud corresponde al incendio de Cholila de 2015. **El 5,4 % del AOI es superficie quemada**, un estado de combustible propio que hay que representar (§5, clase `Rem Dist Rec`).

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

Se aplica el procedimiento de selección de Scott & Burgan (2005, pp. 8-9), conservado de `IGN-20-CROSSWALK.md` §3:

1. Identificar el **estrato portador del fuego**: pasto, arbusto, hojarasca o combinación con sotobosque.
2. Seleccionar la **humedad de extinción** con evidencia regional, sin heredar la etiqueta climática del modelo.
3. Contrastar **profundidad, compacidad, tamaño, carga y proporción viva/muerta** del lecho.
4. Usar el **comportamiento predicho como filtro de rechazo**, contrastándolo con lo observado; §6.2 explicita la falla compartida de los candidatos de arbustal y por qué se mantienen con ese sesgo declarado.

Cada ficha identifica el respaldo bibliográfico o el juicio del autor. No se modifican los parámetros de los modelos FBFM40: construir modelos propios es trabajo futuro (Etapa C), fuera de este entregable.

Se mantiene el marco de humedad de extinción de Bianchi & Defossé (*Ignition probability of fine dead surface fuels of native Patagonian forests of Argentina*, fuentes, §10): los umbrales de ignición medidos en combustibles finos muertos patagónicos (**21,5 % en ciprés, 25,0 % en ñire**) descartan las variantes de clima seco con `mex` de 15 a 20 %. Toda clase con vegetación nativa usa `mex ≥ 25 %`.

**Novedad respecto de IGN-20:** cuatro clases de arbustal tienen ahora **carga medida en la Patagonia** (CIEFAP Publicación Técnica N.º 37, Bianchi et al. 2012), que se usa para elegir dentro de la familia. Conversión: `t/ha métrica × 0,0204816 = lb/ft²`.


| Modelo PT-37                     | Carga fina medida | Equivalente   | Modelo elegido | Carga 1 h del modelo |
| -------------------------------- | ----------------- | ------------- | -------------- | -------------------- |
| A1 · ñire maduro arbustivo       | 5,91 t/ha         | 0,1210 lb/ft² | SH8            | 0,09412              |
| A2 · ñire post-fuego             | 0,82 t/ha         | 0,0168 lb/ft² | GS3            | 0,01377              |
| A3 · matorral maqui-radal-ciprés | 1,68 t/ha         | 0,0344 lb/ft² | SH4            | 0,03903              |
| A4 · arbustal bajo               | 5,66 t/ha         | 0,1159 lb/ft² | GS3 / SH8      | —                    |




## 3. La clave del crosswalk

`(Ley_N1, Ley_N2)`**, no** `Ley_N2` **sola.** La leyenda repite el código de especie entre
niveles: `Le` existe como `TF Le` (bosque de lenga) y como `OFL Le` (lenga achaparrada). Esa diferencia es estructural y es exactamente la que separa un modelo de hojarasca de uno de matorral. Usar `Ley_N2` sin `Ley_N1` fusionaría ambos.

Se elige el nivel 2 como principal porque es el nivel con exactitud reportada (87 %); el
nivel 3 queda como análisis de sensibilidad (§7, S4).

**Excepciones por nivel 3.** Tres clases de nivel 2 agrupan cosas que arden de manera
distinta, y ahí el nivel 2 no alcanza:

- `OT Humedales` contiene mallín, otros humedales y **turbera**.
- `OT Exot-Artif` contiene forestación de coníferas, arboledas, pasturas, cultivos e
**infraestructura**.
- `OT Herb-Subarb` contiene estepa graminosa, **estepa arbustiva** y pradera.

Sin excepciones, la turbera heredaría el modelo del mallín y una plantación de pino heredaría el de un cultivo. Las diez excepciones están en §4.

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


Las clases de nivel 3 que son **mezclas de especies** (`Le-Co`, `Co-Ci`, `Ñi Baj-Le`, …) heredan el modelo de su nivel 2, es decir el de la especie dominante, que es la que da nombre a la clase. Regla declarada, no caso por caso.

---



## 5. Fichas de asignación



### 5.1 · TF Le — Bosque de lenga → **186 (TL6)** · 10,64 % del AOI

**Paso 1 · Estrato portador.** Hojarasca. La lenga (*Nothofagus pumilio*) es caducifolia y produce un lecho de hojas pequeñas; el sotobosque es pobre en los rodales densos de altura. Es el caso en que la familia TL corresponde y TU no.

**Paso 2 · Humedad de extinción.** TL6 tiene `mex = 25 %`, que iguala el umbral de ignición medido en ñire (25,0 %) y supera el de ciprés. Se descarta **TL3 (183)**, la asignación del baseline, por dos razones: `mex = 20 %` y, sobre todo, porque es hojarasca de **conífera de acícula larga**, un lecho físicamente distinto del de una latifoliada caducifolia.

**Paso 3 · Estructura.** TL6: 1 h 0,11019 lb/ft², lecho 0,3 pies, sin componente vivo.
Es hojarasca latifoliada de carga moderada.

**Paso 4 · Contraste.** TL6 propaga *moderado* con llama *baja*, coherente con un fuego de superficie bajo dosel cerrado. El fuego de copas en lenga no se resuelve acá sino con `cc`/`ch`/`cbh`/`cbd`.

**Procedencia.** El estrato portador y el tipo de hojarasca son bibliográficos; la elección
de TL6 sobre TL2 y TU2 es juicio fundamentado del autor. **Sensibilidad S1.**

### 5.2 · TF Co, TF Ci y TF Mx — Coihue, ciprés y mixtos → **165 (TU5)** · 12,33 % del AOI

Coihue (*N. dombeyi*, perennifolio) y ciprés (*Austrocedrus chilensis*, conífera) comparten
una característica que decide el modelo: **sotobosque leñoso denso**, de caña colihue
(*Chusquea culeou*), *Berberis* y *Maytenus*. El estrato portador es hojarasca **con**
sotobosque, o sea familia TU.

TU5 es el modelo de mayor carga de la familia (1 h 0,18365, 10 h 0,18365, 100 h 0,13774,
leñoso vivo 0,13774, `mex` 25) y su descripción —*"heavy forest litter with a shrub or small
tree understory"*— es literalmente la estructura descrita. Es la misma elección que IGN-20
§6.1 hizo para "bosques cerrados", acá restringida a las especies que efectivamente la
justifican en vez de aplicarse a todo el bosque.

**TF Mx — mixtos (3,03 %).** Son rodales donde ninguna especie domina, así que no aplica la
regla general de mezclas del §4: ahí la clase hereda de la especie dominante, y acá no hay
dominante que heredar. Se les asigna TU5 porque las especies que entran en la mezcla son las
mismas de esta ficha más lenga, y ninguna de ellas cambia el estrato portador: el sotobosque
leñoso de caña sigue presente y el fuego sigue corriendo por hojarasca **con** sotobosque.
**Es la asignación con menos respaldo específico de las tres de esta ficha**, porque la
composición exacta de cada rodal mixto no se verificó clase por clase.

**Limitación.** Coihue (muy húmedo, oeste) y ciprés (más seco, este) reciben el mismo modelo
pese a tener regímenes de humedad distintos. CCS-BAP los separa y nuestra parametrización no.
Los mixtos agravan esto: un rodal de lenga y coihue recibe el modelo del coihue puro.

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

**Paso 4 · Contraste con comportamiento observado.** Ejecutado (§6.2), re-corrido con la
interfaz corregida (`AUDITORIA-FISICA.md` §7.4). SH8 reproduce la longitud de llama
observada —3,5 m contra los 3 a 4 m medidos— pero **subestima la propagación**: 739 m/h con
viento sostenido y 1.785 m/h bajo ráfaga, contra 4.800 m/h observados (2,7–6,5× por debajo;
antes de la corrección se leía 437 y 900 m/h, 5–11×). SH4 y GS3 con ráfaga llegan al
51–60 % de lo observado con la llama medida, así que el "ningún modelo de arbustal
reproduce las dos variables a la vez" de la versión anterior ya no vale tal cual. La
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

**Interacción con el dosel (2026-09-30).** SH8 es un modelo de matorral con el lecho expuesto
al viento. Pero dentro de las cicatrices del benchmark, las capas de dosel (cobertura de Hansen
2000, altura de ETH 2020) asignan a esta clase cobertura de bosque cerrado: mediana 78–91 %, a
13–18 m. ELMFIRE combina las dos cosas y le aplica la reducción de viento de un bosque (factor
~0,08 en vez del 0,46 de un matorral abierto). En Alerces 2024, dos tercios del matorral quemado
es ñire bajo, y el 92 % tiene cobertura de Hansen de 50 % o más. Vale lo mismo para la lenga
achaparrada (§5.5) y parte del arbustal nativo (§5.6). Hay que decidir si la clase es combustible
arbustivo expuesto (sin dosel) o sotobosque bajo dosel (familia TU): `DECISIONES-DIRECTOR.md` §1.

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

**Evidencia del benchmark (2026-09-30).** En El Turbio 2025 el incendio volvió a quemar el
remanente de la cicatriz de 2015: ardió lento (latente, diez días hasta 2.000 ha, combatido), y el
modelo lo recorre como GS3 con cinco veces el área observada (82 % de la cicatriz es GS3). Además,
Hansen 2000 todavía ve bosque cerrado en el 83 % de esa cicatriz. La asignación describe un
disturbio de dos años mejor que uno de diez (`DECISIONES-DIRECTOR.md` §4).

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


| Tipo de combustible        | WorldCover 2021 | MapBiomas 2024 | **CCS-BAP 2017** |
| -------------------------- | --------------- | -------------- | ---------------- |
| NB · no combustible        | 19,21 %         | 26,39 %        | 20,99 %          |
| GR · pastizal              | 34,70 %         | 12,49 %        | 18,22 %          |
| GS · pastizal-arbustal     | 0,00 %          | 3,34 %         | **5,11 %**       |
| SH · arbustal              | **3,75 %**      | 22,11 %        | **23,25 %**      |
| TU · bosque con sotobosque | 0,00 %          | 31,00 %        | 16,41 %          |
| TL · hojarasca de bosque   | 42,34 %         | 4,68 %         | 16,02 %          |


**Trazabilidad del porcentaje de arbustal.** La consigna de revisión indica 23,21 %, pero tanto la tabla de la versión consultada de `IGN-20B-CROSSWALK-CCSBAP.md` §6 como `RESULTADOS.md` §2 reportan **23,25 %**. Se conserva este último para que tabla y lectura coincidan; 23,21 % no se presenta como una medición verificada. El control reproducible es `report()` de `scripts/build_fuel_maps.py`, que suma todos los códigos de la familia SH sobre el total de celdas del ráster. No se recalcularon los rásters en esta revisión documental.

Lecturas:

1. **El arbustal pasa de 3,75 % a 23,25 %**, y con el pastizal-arbustal de 3,75 % a 28,36 %.
  Es el hallazgo central de la Etapa B, ahora sobre un insumo que discrimina especie.
2. **El bosque deja de ser un solo modelo.** Donde el baseline pone el 42,34 % del AOI en TL3
  —un único modelo, y además de hojarasca de conífera— y MapBiomas el 30,91 % en TU5, CCS-BAP
   reparte entre TU5 (12,21 %), TL6 (10,51 %) y TU3 (4,17 %) según especie y estructura.
3. **MapBiomas declara más superficie no combustible que CCS-BAP** (26,39 % contra 20,99 %),
  pese a ser siete años posterior (épocas 2024 y 2017). La diferencia está sobre todo en nieve y hielo y merece
   revisión antes de la comparación final.

> Los porcentajes por modelo se miden sobre los rásters efectivamente construidos
> (`data/static/fuel_maps/fbfm40_<fuente>.tif`, grilla 2.563 × 3.222). El TL3 (3,16 %) y el GR2 (0,77 %)
> que aparecen dentro del mapa de CCS-BAP no salen de la leyenda de CIEFAP: son el relleno
> fronterizo tomado de WorldCover (§7, limitación 2).



### 6.1 · Comparación con ELMFIRE (2026-09-16, con humedad viva fundamentada)

Tres corridas de 12 h sobre el **mismo incendio**: misma ignición, misma meteorología, misma
topografía, mismo `ADJ`. Lo único que cambia es `fbfm40.tif`. Se puntúa **sólo el anillo de
crecimiento**, nunca la unión con la semilla (`IGN-26-VALIDACION.md` §12.1).

Semilla FIRMS: 8.095 ha, verificada idéntica en las tres corridas. Humedad del combustible
vivo: `LH` 30 %, `LW` 110 %. **No son dos valores medidos:** Bianchi & Defossé (2015) respaldan la elección de `LW`; `LH` es una convención de pasto curado. El fundamento completo está en §6.3.


| Mapa             | Anillo a 12 h | vs baseline | FLI mediana    | FLI p90 |
| ---------------- | ------------- | ----------- | -------------- | ------- |
| WorldCover 2021  | 2.342 ha      | —           | 96,1 kW/m      | 333     |
| MapBiomas 2024   | 5.849 ha      | +150 %      | 311,1 kW/m     | 1.267   |
| **CCS-BAP 2017** | **7.576 ha**  | **+223 %**  | **317,0 kW/m** | 1.309   |


Acuerdo entre mapas sobre el anillo:


| Par                     | IoU       | Sólo el primero | Sólo el segundo |
| ----------------------- | --------- | --------------- | --------------- |
| WorldCover vs MapBiomas | 0,245     | 728 ha          | 4.235 ha        |
| WorldCover vs CCS-BAP   | 0,269     | 243 ha          | 5.476 ha        |
| MapBiomas vs CCS-BAP    | **0,599** | 822 ha          | 2.550 ha        |


> **Corrida anterior, con** `LH`**/**`LW` **en 60 %:** 1.989 / 9.328 / 10.537 ha, con IoU de 0,179 /
> 0,179 / 0,629. Al pasar a la humedad fundamentada, el fuego de los dos mapas patagónicos se reduce
> cerca de un tercio y el del baseline **sube** —el pasto curado hace arder más el GR2—, así
> que la diferencia entre mapas se achica de un factor 5,3 a uno de 3,2. **La conclusión no
> cambia; la magnitud sí.** Es exactamente el motivo por el que el escalar tenía que fijarse
> con evidencia y convenciones explícitas antes de citar cualquier número.

Qué combustible quemó cada corrida, dentro del anillo:

- **WorldCover:** GR2 62 %, TL3 38 %. El fuego avanza por el pastizal porque TL3 casi no
propaga: es la consecuencia directa del hallazgo del audit.
- **MapBiomas:** TU5 70 %, SH4 19 %, GR5 9 %.
- **CCS-BAP:** SH8 29 %, TU5 17 %, TL6 17 %, SH4 12 %, GR3 11 %, TU3 10 %. **El arbustal lleva
el fuego**, que es lo que Mermoz et al. (2005) documentan para la Patagonia.

**Qué demuestra y qué no.** Demuestra que el resultado de ELMFIRE es **fuertemente sensible al
mapa de combustible**: 7.576 ha contra 2.342 ha de anillo y 317,0 contra 96,1 kW/m de intensidad mediana (tabla de esta sección), con el
resto de los insumos congelados. Un empate habría sido un hallazgo en contra de toda la Etapa B.
Por sí sola **no demuestra que CCS-BAP prediga mejor**: eso exige puntuar contra el perímetro
observado, que es el harness B. Que los dos insumos patagónicos coincidan entre sí (IoU 0,599)
y difieran igual del baseline (0,245 y 0,269) es consistente con que el baseline sea el
atípico, pero no lo prueba.

**Y el harness B ya corrió** (2026-09-19, `RESULTADOS.md` §4). Contra la cicatriz de
Sentinel-2 —dNBR entre una ventana pre y una post, umbral 0,30, independiente de FIRMS, que es
lo que construyó la semilla— para el mismo incendio y un horizonte de 12 h, **con una preparación distinta de la comparación preliminar anterior**:

- Caso del 1-2 de febrero de 2026; semilla de **17.747 ha**, no las 8.095 ha de la corrida preliminar.
- Referencia: **196 máscaras a 20 m**, ventana pre de noviembre-diciembre de 2023 y post de febrero-marzo de 2026. Cubren **46,2 % del dominio** y contienen **76.178 ha** de cicatriz observada, antes de excluir la semilla.
- Se puntúa sólo dentro de la cobertura observada y fuera de la semilla; las máscaras se llevan por moda a la grilla de la corrida. IoU es acierto dividido por la unión de predicho y observado; recall es la fracción de lo observado alcanzada; precisión es la fracción de lo predicho que coincide con lo observado.
- `RESULTADOS.md` §3 registra el anclaje temporal corregido (`SIMULATION_TSTART` de **6.360 s**) para estos resultados. El anclaje en cero de la comparación preliminar no se traslada al harness B.

Fuente de configuración y cifras: `RESULTADOS.md` §3-4; cálculo: `scripts/score_against_observed.py`.

| Mapa             | IoU       | Recall    | Precisión | Acierto      |
| ---------------- | --------- | --------- | --------- | ------------ |
| WorldCover 2021  | 0,036     | 0,043     | 0,182     | 2.827 ha     |
| MapBiomas 2024   | 0,045     | 0,048     | **0,412** | 3.175 ha     |
| **CCS-BAP 2017** | **0,067** | **0,082** | 0,267     | **5.362 ha** |

CCS-BAP casi duplica el IoU del baseline. En el estrato de **once tiles con 70-100 % de superficie quemada**, la diferencia se agranda a **0,101 contra 0,047**; MapBiomas obtiene **0,051** (`RESULTADOS.md` §4). El porcentaje quemado define el estrato: por sí solo no demuestra que todos esos tiles contengan el borde real del fuego.

**Lo que ese número no dice.** Los valores absolutos son bajos y no miden la calidad del
modelo: la referencia es la cicatriz final de semanas y la corrida es de 12 h, así que el
recall está acotado por construcción y las ~62.000 ha "no predichas" son sobre todo tiempo de
simulación que no existió. **Lo comparable es el orden entre mapas, no la magnitud.**

**Salvedades y alcance de las dos comparaciones:**

1. **La comparación preliminar del 2026-09-16 corre sobre la grilla reducida** (1.414 × 1.526); los mapas de §6 corresponden al AOI definitivo. Sus áreas, intensidades y acuerdos entre mapas no deben mezclarse con las métricas del harness B, que usa otra preparación y otra semilla.
2. **Humedad viva fundamentada, con incertidumbre:** `LW` toma el extremo seco de las mediciones de Bianchi & Defossé (2015); `LH` es una convención. La transferencia entre especies y el uso de escalares globales siguen siendo limitaciones (§6.3).
3. **Validación contra lo observado: ejecutada, con alcance parcial.** El harness B se
  ejecutó y su resultado está arriba. Sigue pendiente puntuar sobre una corrida que abarque
   el incendio completo y no 12 h, que es lo que hoy acota el recall por construcción.
4. `SIMULATION_TSTART` **quedó en 0 en las corridas preliminares** porque su preparación precede al arreglo del anclaje. El harness B reportado usa el anclaje corregido indicado arriba.
5. **Mayor IoU no implica mejor desempeño en toda métrica:** MapBiomas tiene mayor precisión en el harness B. La referencia también arrastra el intervalo amplio entre imágenes pre y post; no aísla por sí sola el crecimiento de esas 12 h.
6. **No hay validación general del sistema:** es un solo incendio, sin calibración de `ADJ` ni supresión representada. `RESULTADOS.md` §5-7 registra sobrepropagación frente a FIRMS en el harness A y ventaja de MapBiomas en IoU y precisión agregadas. Eso no elimina la subestimación de ROS del ensayo de arbustal (§6.2): son escalas, referencias y experimentos distintos. No corresponde declarar un ganador universal.



**Re-medición con la interfaz corregida (2026-09-30).** Las mismas corridas, sobre los mismos
insumos (misma semilla, los mismos tres mapas), con los errores de interfaz corregidos
(`scripts/corregir_preparacion_legado.py`; `AUDITORIA-FISICA.md`, loop J):

| Mapa | Anillo a 12 h (antes → corregido) | FLI mediana (antes → corregido) |
| --- | --- | --- |
| WorldCover 2021 | 2.342 → **3.892 ha** | 96,1 → 32,1 kW/m |
| MapBiomas 2024 | 5.849 → **7.268 ha** | 311,1 → 261,5 kW/m |
| CCS-BAP 2017 | 7.576 → **9.262 ha** | 317,0 → 234,8 kW/m |

- IoU entre mapas: WorldCover–MapBiomas 0,302, WorldCover–CCS-BAP 0,344, MapBiomas–CCS-BAP
  0,574. Lo que quema CCS-BAP casi no cambia (SH8 30 %, TL6 18 %, TU5 17 %).
- **El orden se sostiene** y la diferencia con el baseline se achica de 3,2× a 2,4×. Las
  intensidades bajan, no suben: la corrida vieja mantenía las 12 h en la primera hora, la más
  seca y ventosa.
- **Harness B.** La referencia de arriba (las 196 máscaras con la ventana pre de nov–dic 2023) ya
  no existe en `mask-dataset-gen`. Contra `puerto-patriada-2026/runs/baseline-002` (mismo
  algoritmo y celdas, ventana pre nov 2025–ene 2026), las corridas corregidas dan IoU **0,010 /
  0,035 / 0,046** (WorldCover / MapBiomas / CCS-BAP; en el estrato 70–100 %: 0,010 / 0,034 /
  0,056). **El orden de IoU se sostiene** y MapBiomas sigue con la mejor precisión (0,443). Los
  valores bajan porque el anillo corregido es la mitad: la corrida atraviesa la noche.
- La comparación sobre un benchmark de 11 incendios, con la interfaz corregida, está en
  `COMPARACION-MAPAS-V5.md`.

### 6.2 · Paso 4 contra la quema experimental de la PT-37 (2026-09-16)

Scott & Burgan cierran su procedimiento con un filtro de rechazo: elegido un modelo, hay que mirar su comportamiento predicho y descartarlo si contradice lo observado. Hasta acá ese paso se aplicó con la escala adjetiva publicada, que está medida en un escenario de referencia (D2L2) que no es el nuestro. La PT-37 §3.3-3.4 da algo mejor: una **quema experimental con meteorología medida**, en el mismo ecotono y sobre el modelo A4.

**Condiciones reproducidas** (Cerro Jones, 14-09-2011, 16:00), terreno plano, ignición puntual, 1 h de simulación: `m1` 8,0 % —de FFMC 92,7 por la conversión de Van Wagner—, `LW` 82 % medido en espino negro, `LH` 30 % por pasto 100 % curado, viento sostenido de 24 km/h y ráfagas de
51 km/h. **Observado:** el frente recorrió 40 m en 30 s, o sea 4.800 m/h y llama de 3 a 4 m. Esos 80 m/min son el pico bajo ráfaga y no un promedio horario, así que cada candidato se corre en las dos condiciones y el resultado se lee como horquilla. Longitud de llama por Byram (1959), `L = 0,0775 · I^0,46`.


**Actualizado el 2026-09-30.** La corrida del 2026-09-16 tenía el frente a la mitad de la
velocidad calculada (el campo de ignición del playground, `AUDITORIA-FISICA.md` hallazgo 2).
La longitud de llama sale de la intensidad que calcula ELMFIRE y casi no cambia. Re-corrido con
la interfaz corregida (entre paréntesis, la cifra anterior):

| Modelo              | ROS sostenido          | Llama | ROS ráfaga               | Llama  | Veredicto                                   |
| ------------------- | ---------------------- | ----- | ------------------------ | ------ | ------------------------------------------- |
| **SH8** (148)       | 739 m/h (437)          | 3,5 m | 1.785 m/h (900)          | 5,6 m  | llama sí, propagación no (2,7–6,5× abajo)    |
| SH4 (144)           | 888 m/h (522)          | 2,2 m | 2.445 m/h (1.201)        | 3,7 m  | llama sí; con ráfaga, 51 % de lo observado  |
| GS3 (123)           | 1.098 m/h (627)        | 2,8 m | 2.896 m/h (1.394)        | 4,5 m  | llama sí; con ráfaga, 60 % de lo observado  |
| SH9 (149)           | 1.966 m/h (1.034)      | 7,9 m | 4.875 m/h (2.321)        | 11,8 m | propagación sí, llama muy por encima        |
| SH5 (145) · control | 2.118 m/h (1.091)      | 5,1 m | 5.085 m/h (2.529)        | 7,4 m  | propagación sí, llama por encima            |


Reproducir: `uv run python scripts/paso4_quema_a4.py`.

Lecturas:

1. **Ningún modelo de arbustal de SB40 reproduce del todo propagación y llama a la vez, pero SH4
  y GS3 se acercan con ráfaga.** SH8 clava la llama —3,5 m contra 3 a 4 m medidos— y queda
   entre 2,7 y 6,5 veces por debajo en propagación (antes de la corrección: 5 a 11). SH4 y GS3,
   con ráfaga, llegan al 51–60 % de la propagación observada con la llama medida. Los dos que
   alcanzan la propagación observada lo hacen con llamas de 7 a 12 m, dos a tres veces lo medido.
2. **SH9 queda descartado por segunda vez**, ahora por comportamiento y no sólo por carga
  (§5.4): su llama duplica largamente lo observado en las dos condiciones.
3. **SH5, la familia del baseline, sigue rechazado.** Propaga más, pero con llama de 4,9 a
  8,0 m y `mex` de 15 %, incompatible con los umbrales de ignición medidos (§2).
4. SH4 y GS3 caen en el mismo régimen que SH8, lo que es coherente: las tres asignaciones se
  eligieron por carga fina medida y las tres heredan el mismo sesgo.

**Qué se hace con esto.** El paso 4 rechaza un modelo cuando su comportamiento contradice lo observado *y existe una alternativa mejor*. Acá todas las alternativas fallan en el mismo eje, así que **el resultado no invalida ninguna asignación**: muestra que el techo dejó de ser el insumo y pasó a ser el sistema de modelos. Las asignaciones se mantienen **con el sesgo declarado: subestiman la velocidad de propagación en arbustal** — con la interfaz corregida, un sesgo de la mitad del que se estimó el 2026-09-16. Es el argumento directo a
favor de la `ETAPA-C` y de la sensibilidad S5.

**Salvedades.** Es **una sola quema, un solo sitio, 2011**. La comparación corre con los parámetros propios de SB40, no con las cargas de la PT-37 —eso es S5—, sobre terreno plano y con ignición puntual, sin la continuidad de combustible que la quema tenía medida.

### 6.3 · Sensibilidad a la humedad del combustible vivo (2026-09-16)

Barrido uniforme de `LH_MOISTURE_CONTENT` y `LW_MOISTURE_CONTENT` sobre el mapa de CCS-BAP,
12 h, con todo lo demás congelado. Se puntúa sólo el anillo de crecimiento.


| LH/LW | Anillo a 12 h (antes → corregido) | vs 60 % (corregido) | FLI mediana (antes → corregido) |
| ----- | --------------------------------- | ------------------- | ------------------------------- |
| 30 %  | 11.293 → 14.120 ha                | +7 %                | 512,0 → 391 kW/m                |
| 60 %  | 10.537 → 13.241 ha                | —                   | 484,9 → 367 kW/m                |
| 90 %  | 7.472 → 8.930 ha                  | −33 %               | 327,5 → 245 kW/m                |
| 120 % | 4.513 → 5.575 ha                  | −58 %               | 220,5 → 154 kW/m                |

*Re-medida el 2026-09-30 con la interfaz corregida (`AUDITORIA-FISICA.md`, loop J).*


Reproducir: `uv run python scripts/sweep_live_moisture.py`.

**Factor 2,53 en superficie entre 30 % y 120 %** (2,50 antes de la corrección), y 2,54 en intensidad mediana. Con el baseline el escalar era inocuo, porque TL3 no tiene carga viva; con CCS-BAP los modelos SH, GS y TU son mayoría y el escalar **pasa a ser driver de primer orden**. Ésa es la razón por la que tenía que fijarse con evidencia y convenciones explícitas antes de citar cualquier número: la fila de 60 % reproduce exactamente la corrida vieja de §6.1 (10.537 ha), la que quedó superada.

**Fundamento de los valores adoptados** (Bianchi & Defossé, 2015; desarrollo en `ETAPA-B-INSUMO-PATAGONICO.md` §B5). En temporada de fuego, el contenido de humedad foliar vivo medido es de **110–220 %** para ñire, ciprés, laura y radal; la caña colihue no supera **110 %**. Se adoptó **`LW = 110 %`**, el extremo seco de la banda, como condición más propensa al fuego dentro de esa evidencia. **Actualización del 2026-09-30:** la calibración contra siete incendios, con la interfaz corregida, elige **100 %** (intervalo sin sobre-propagación: 97–110 %). Es coherente con la misma fuente: Bianchi & Defossé ubican en 110 % el umbral por debajo del cual ocurren los grandes incendios, así que el día de un gran incendio está por debajo. No es un promedio ni una medición del día simulado; la banda completa queda como incertidumbre. Lenga, coihue y alerce no fueron medidos y heredan ese valor por analogía.

**`LH = 30 %` no sale de una medición de herbáceas de ese artículo.** Representa pasto completamente curado, según el umbral de transferencia dinámica de Scott & Burgan (2005, pp. 4, 6-7). Es una convención de modelado declarada.

**Los valores adoptados no son uniformes** —`LH` 30 % y `LW` 110 %—, así que la tabla acota pero no predice: la combinación adoptada da 7.576 ha (§6.1), entre las filas de 60 % y 90 %, que es donde tiene que caer.

**Limitación.** Un escalar global es lo que hay. Un ráster de humedad viva por clase y
fenología sería la mejora, y no está en alcance.



## 7. Limitaciones y sensibilidades



### Limitaciones

1. **Desfase temporal: 2017 contra un incendio de febrero de 2026, nueve años.** Es el precio
  de la discriminación por especie. Mitigación: contrastar con el histórico de FIRMS los
   fuegos del intervalo; MapBiomas 2024 queda como control de dos años de desfase.
2. **Hueco fronterizo del 4,55 % en el recorte vectorial**, relleno con WorldCover; en la grilla definitiva ocupa el 5,38 % (§6). Se aplica la misma regla de relleno, pero la máscara de huecos difiere entre productos: no se puede afirmar que no sesgue la comparación. El borde oeste se apoya en el baseline y la mejora allí queda limitada por ese insumo.
3. **SB40 no distingue lo que CCS-BAP sí distingue** (§5.5): ñire bajo y lenga achaparrada
  comparten modelo, y coihue y ciprés también. El techo ahora es el sistema de modelos, no el
   insumo. Es el argumento de la Etapa C.
4. **Homogeneidad dentro de la clase**: no se distingue estado sucesional, historia de fuego ni
  carga de material muerto en pie, salvo por la clase de disturbio reciente.
5. **Agregación a 30 m por clase mayoritaria**: se pierden corredores de combustible más
  angostos que un píxel, y la continuidad gobierna la propagación.
6. **La PT-37 sólo cubre arbustales**, no bosque. Las clases de bosque siguen sin carga medida.
7. **FBFM40 se calibró con series fotográficas de combustibles de los Estados Unidos.** Ninguna
  especie patagónica participó de su construcción. Los cuarenta modelos son un conjunto
   estándar pensado para otro continente, y ésta es la limitación de fondo de todo el
   ejercicio: la tabla elige el modelo menos malo, no el correcto.
8. **El modelo de Rothermel supone un lecho de combustible homogéneo y continuo**
  (Scott & Burgan 2005, p. 3). Los mosaicos de bosque, matorral y estepa del ecotono violan
   ese supuesto, y la continuidad del combustible es justamente lo que gobierna la
   propagación. Las quemas de la PT-37 lo muestran: el fuego cruza entre parches por el
   estrato herbáceo de los entreparches, que es geometría que el formalismo no representa.
9. **No existe crosswalk publicado de especies patagónicas a FBFM40.** No hay precedente
  contra el cual contrastar esta tabla ni calibración de origen que heredar: es una
   **propuesta original** y debe presentarse y evaluarse como tal. Es también la razón por la
   que cada asignación lleva ficha con su procedencia (§5) y por la que el §7 declara
   sensibilidades en vez de dar la tabla por cerrada.
10. **El dosel viene de otras fuentes y puede contradecir al combustible** (2026-09-30). La
   cobertura (Hansen) es del año 2000 y la altura (ETH) de 2020: 15 a 26 años antes de los
   incendios del benchmark en el primer caso. Donde CCS-BAP ve matorral (ñire bajo, lenga
   achaparrada, parte del arbustal nativo), el dosel suele ver bosque cerrado, y ELMFIRE le quita
   el viento al matorral (§5.4). Donde hubo fuegos después de 2000, ve un bosque que ya no está
   (§5.7).
11. **La altura de base de copa es derivada, no medida** (2026-09-30). Se calcula como 0,20–0,50
   de la altura del dosel (5 a 10 m en la región), y con esos valores el fuego de copas casi
   nunca se enciende. Con una base de copa baja sí se enciende, y es el insumo que más mueve el
   resultado del benchmark (`AUDITORIA-FISICA.md`, loop F; `DECISIONES-DIRECTOR.md` §2).



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




**Control documental de esta versión.** Se cotejó la tabla de §4 contra los **28 pares** de
`CCSBAP_TO_FBFM40` y las **10 excepciones** de `CCSBAP_N3_OVERRIDES` en
`app/elmfire/builder/fuels_builder.py`: coincidencia completa. En la fila agrupada de OFL,
cada código se verificó por separado. La excepción por `Ley_N3` tiene prioridad sobre
`(Ley_N1, Ley_N2)`, tal como implementa `ccsbap_fuel_code()`. No se modificó el código.
La tabla (§4), las fichas (§5) y la tabla de sensibilidades (§7) se conservaron íntegramente.

**Procedencia de los números.** Los porcentajes de §4-5 corresponden al recorte vectorial;
los de §6 al ráster final, con agregación y relleno. No son el mismo denominador: por eso,
por ejemplo, TF Le ocupa 10,64 % en la tabla y TL6 10,51 % en el ráster.

| Evidencia incluida | Fuente o cálculo que la reproduce |
| --- | --- |
| AOI, conteos de polígonos, superficies, épocas y porcentajes por clase (§1, §3-5) | Inventario del recorte de `cob_2017_N3_aok_CH` y comparación con la capa de época 2013, documentados en `IGN-20B-CROSSWALK-CCSBAP.md` §1, §3-5; especificaciones y exactitud: informe CIEFAP/MAyDS |
| Códigos, familias y parámetros de los modelos (§2-5) | Diccionarios de `fuels_builder.py`; Scott & Burgan (2005), Tabla 7; tabla cargada por ELMFIRE: `app/elmfire/fuel_models.csv` |
| Cargas, humedades y comportamiento observado (§2, §5, §6.2-6.3) | PT-37, Tabla 2 y §3.3-3.4; Bianchi & Defossé; Cóbar-Carranza et al.; procedencia puntual declarada en cada ficha |
| Distribución de combustible y huecos sobre la grilla (§6) | `scripts/build_fuel_maps.py`, función `report()`, y registro de `_fill_gaps()` en `fuels_builder.py`; cifras de la fuente base §6 y `RESULTADOS.md` §2 |
| Anillo, FLI, acuerdo entre mapas y composición del anillo preliminar (§6.1) | `scripts/run_three_maps.py` y `scripts/compare_fuel_map_runs.py`; resultados históricos de la fuente base §6.1 |
| Harness B, configuración y métricas globales y estratificadas (§6.1) | `RESULTADOS.md` §3-4; `scripts/score_against_observed.py` |
| Ensayo de arbustal y barrido de humedad (§6.2-6.3) | `scripts/paso4_quema_a4.py` y `scripts/sweep_live_moisture.py`; resultados históricos de la fuente base |
| Fechas de elaboración y ejecución (§9) | Registro de estado de la fuente base §9 y corte de `RESULTADOS.md` |

**Reproducción.** Los scripts requieren las capas, preparaciones, salidas de ELMFIRE y
máscaras originales. Esta revisión verifica documentación y correspondencias; no vuelve a
ejecutar simulaciones ni certifica mediciones nuevas. Una preparación nueva no reproduce
necesariamente las cifras históricas de la grilla reducida.

```bash
# Distribución por familia y por modelo sobre la grilla definitiva
uv run python scripts/build_fuel_maps.py

# Puntuar las salidas existentes del harness B; requiere máscaras y metadata originales
for fuente in worldcover mapbiomas ccsbap; do
  uv run python scripts/score_against_observed.py \
    --run "cmp_aoi_${fuente}" --caso feb2026_12h --mapa "${fuente}"
done

# Contraste con la quema y sensibilidad de humedad
uv run python scripts/paso4_quema_a4.py
uv run python scripts/sweep_live_moisture.py
```

Los identificadores `cmp_aoi_<fuente>` siguen la convención de `run_three_maps.py` y el
caso documentado en `RESULTADOS.md` §8; no sustituyen el archivo de la preparación usada.
Las métricas del harness B se escriben en `data/validation/harness_b/feb2026_12h/`.


## 9. Estado de aprobación


|                                        |                                     |
| -------------------------------------- | ----------------------------------- |
| Propuesta elaborada                    | 2026-09-15                          |
| Comparación de los tres mapas (§6.1)   | 2026-09-16                          |
| Paso 4 sobre la quema de la PT-37      | **hecho** 2026-09-16 (§6.2)         |
| Sensibilidad de la humedad viva (§6.3) | 2026-09-16                          |
| Validación contra lo observado         | **ejecutada, alcance parcial** · 2026-09-19 (§6.1, harness B) |
| Re-medición con la interfaz corregida  | 2026-09-30 (§6.1-§6.3; `AUDITORIA-FISICA.md`) |
| Comparación sobre el benchmark de 11 incendios | en curso (`COMPARACION-MAPAS-V5.md`) |
| Revisión del director                  | **pendiente**                       |


Puntos que requieren decisión explícita:

1. **OFL Le → SH8** (§5.5): 8,71 % del AOI por analogía, sin carga medida.
2. **TF Le → TL6** (§5.1): 10,64 % del AOI, la clase de bosque más extensa, elegida sin dato de sotobosque.
3. **Rem Dist Rec → GS3** (§5.7): 5,40 % del AOI, once años de regeneración supuestos.
4. **Época 2017 frente al desfase de nueve años** (§7, limitación 1).

**Lo que el paso 4 agregó a la decisión.** No cambia ninguno de los cuatro puntos en
discusión, pero sí cambia lo que se les puede pedir: ningún modelo de arbustal de SB40
reproduce del todo a la vez propagación y llama observadas (§6.2), así que las asignaciones de
arbustal —SH8, SH4 y GS3— se aprueban **con el sesgo declarado de subestimar la propagación**
(con la interfaz corregida, la mitad del estimado originalmente: SH8 2,7–6,5× por debajo, SH4 y
GS3 al 51–60 % con ráfaga).

**Puntos agregados el 2026-09-30** (detalle en `DECISIONES-DIRECTOR.md`):

5. **Ñire bajo, lenga achaparrada y arbustal nativo con dosel de bosque** (§5.4): ¿sin dosel, o
   sotobosque bajo dosel (familia TU)?
6. **La altura de base de copa derivada** (§7, limitación 11).
7. **`LW` en 100 %** (§6.3), el valor calibrado. Levantar
ese techo es `ETAPA-C`, no este crosswalk.

## 10. Fuentes

- CIEFAP, MAyDS (2016). *Actualización de la Clasificación de Tipos Forestales y Cobertura del
Suelo de la Región Bosque Andino Patagónico. Informe Final.* Capa `cob_2017_N3_aok_CH`,
provista por CIEFAP el 2026-09-13.
- Bianchi, L.O.; Dentoni, M.C.; Muñoz, M.M.; Defossé, G.E. (2012). *Modelos de combustibles en
el ecotono bosque-estepa de la Patagonia andina.* CIEFAP, Publicación Técnica N.º 37.
ISSN 1514-2264. (Tabla 2: cargas por clase de tamaño · §3.1: descripción de los modelos ·
§3.3-3.4: quema experimental)
- Scott, J.H.; Burgan, R.E. (2005). *Standard Fire Behavior Fuel Models: A Comprehensive Set for Use with Rothermel's Surface Fire Spread Model.* RMRS-GTR-153. (Procedimiento de selección pp. 8-9 · alcance
p. 3 · modelos dinámicos p. 4 · parámetros Tabla 7)
- Bianchi, L.O.; Defossé, G.E. *Ignition probability of fine dead surface fuels of native
Patagonian forests of Argentina.* Forest Systems. (Umbrales de ignición: 21,5 % en ciprés y
25,0 % en ñire · §2)
- Bianchi, L.O.; Defossé, G.E. (2015). *Live fuel moisture content and leaf ignition of forest
species in Andean Patagonia, Argentina.* International Journal of Wildland Fire 24(3):340.
(Respalda la elección de `LW` 110 %; **no mide herbáceas ni respalda `LH` 30 % como dato**. Esa convención se fundamenta con Scott & Burgan, como se explica en §6.3.)
- Mermoz, M.; Kitzberger, T.; Veblen, T.T. (2005). *Landscape influences on occurrence and spread of wildfires in Patagonian forests and shrublands.* Ecology 86(10).
- Cóbar-Carranza, A.J.; García, R.A.; Pauchard, A.; Peña, E. (2014). *Effect of Pinus contorta
invasion on forest fuel properties and its potential implications on the fire regime of
Araucaria araucana and Nothofagus antarctica forests.* Biological Invasions. (Carga de leña
fina en rodales de ñire; inflamabilidad comparada de nativas y pino exótico, relevante para
la clase de forestación exótica.)
- Interno: `IGN-20-CROSSWALK.md` · `ETAPA-B-INSUMO-PATAGONICO.md` ·
`docs/out-of-scope/ETAPA-C-MODELOS-PROPIOS.md` §C0 · `app/elmfire/builder/fuels_builder.py` ·
`scripts/build_fuel_maps.py`
- Resultados: `RESULTADOS.md` §2-4, §5-7 (alcance y sesgos); `scripts/score_against_observed.py`.
- Criterios de aceptación: `ETAPA-B-INSUMO-PATAGONICO.md` §B2; `IGN-20-CROSSWALK.md` §7.2 y §7.4; [issue IGN-20](https://linear.app/ignite-insights/issue/IGN-20).

**Versiones consultadas del repositorio** (`main`, lectura del 2026-09-20; identificadores de blob de Git):

- [IGN-20B-CROSSWALK-CCSBAP.md](https://github.com/IgnacioChevallier/igniteinsights/blob/main/IGN-20B-CROSSWALK-CCSBAP.md): `8e9452f06f00dcdb84102a22b62935b2caa37031`.
- [RESULTADOS.md](https://github.com/IgnacioChevallier/igniteinsights/blob/main/RESULTADOS.md): `0641aebfa9f0f7af95400e0489fcab54f76d2f19`.
- [ETAPA-B-INSUMO-PATAGONICO.md](https://github.com/IgnacioChevallier/igniteinsights/blob/main/ETAPA-B-INSUMO-PATAGONICO.md): `b27a09b015479c718d8b150d327e03582cc1ad9f`.
- [IGN-20-CROSSWALK.md](https://github.com/IgnacioChevallier/igniteinsights/blob/main/IGN-20-CROSSWALK.md): `a032b80bad96c176bf27d8a2d10f8668ecaaa64e`.
- [app/elmfire/builder/fuels_builder.py](https://github.com/IgnacioChevallier/igniteinsights/blob/main/app/elmfire/builder/fuels_builder.py): `dc881ab51502da2ad6ae0428b48af5dc12a14b78`.

---

**Decisiones que requieren firma del director** — pendientes; aprobar el documento no elimina los sesgos declarados:

1. **OFL Le → SH8:** analogía estructural sin carga medida; **8,71 % del AOI** (§4 y §5.5).
2. **TF Le → TL6:** sin dato de sotobosque; **10,64 % del AOI** (§4 y §5.1).
3. **Rem Dist Rec → GS3:** **once años de regeneración supuestos**; **5,40 % del AOI** (§4 y §5.7).
4. **Época 2017 frente al desfase de nueve años:** aceptar el insumo para el incendio de 2026 con la incertidumbre temporal declarada (§1 y §7).

Firma del director: ____________________ · Fecha: ____________________
