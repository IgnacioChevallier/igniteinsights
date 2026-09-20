# Etapa B — Insumo patagónico y crosswalk fundamentado

> Estado: **B0 ejecutado** (2026-09-06, MapBiomas promovido) · **B1 cerrado** (2026-09-13,
> CIEFAP dio acceso) · **B2 propuesto** en `IGN-20B-CROSSWALK-CCSBAP.md` · **B3/B4
> implementados** y cableados al pipeline (`settings.fuels_source`, por defecto `ccsbap`) ·
> **B5 parcial**: falta el valor medido, hecho el barrido de sensibilidad ·
> pendiente B6 (validación contra el perímetro observado)
> Issues: **IGN-20** (tabla) → **IGN-21** (raster) → IGN-22 / IGN-26
> Depende de: Etapa A completa · Es **el núcleo del aporte de tesis**

## Objetivo

Reemplazar el insumo de cobertura por uno que discrimine **a nivel de especie y de estructura** en el Bosque Andino Patagónico, y construir sobre él una tabla de correspondencia a FBFM40 **justificada clase por clase** con literatura patagónica, con el criterio de asignación explícito y auditable.

Luego demostrar cuantitativamente, con el harness B de validación, que el mapa resultante predice mejor que el baseline de la Etapa A.

## Por qué el insumo es el techo, no el crosswalk

ESA WorldCover tiene **una sola clase arbórea** para todo el bosque andino-patagónico. Lenga caducifolia, ciprés conífero, coihue perennifolio y alerce caen todos en `10 → Tree cover`. Ninguna asignación FBFM40, por buena que sea, recupera información que el raster nunca tuvo.

Evidencia medida sobre el AOI (`docs/historico/SIMULATION_AUDIT.md` §1, §2.1):


| Observado                            | Interpretación                                                                             |
| ------------------------------------ | ------------------------------------------------------------------------------------------ |
| 59,7 % del AOI en TL3                | Una clase arbórea → un modelo de combustible                                               |
| **0,04 % de arbustal**               | El sensor óptico a nadir ve la copa; el matorral bajo dosel se clasifica como *tree cover* |
| 23 % no combustible (NB3 + NB8)      | `bare/sparse` sobreasignado a 10 m en terreno rocoso o ralo                                |
| Intensidad de línea mediana 4,6 kW/m | Consecuencia directa de TL3 + 89 % de cobertura de copa                                    |


El 0,04 % de arbustal es el hallazgo central. Mermoz et al. (2005) establecen que en Patagonia **los matorrales arden y se propagan mucho más que los bosques**: el mapa está borrando el tipo de combustible que gobierna el régimen de fuego regional. Godoy et al. (2022), sobre Esquel–Trevelin (contiguo a Los Alerces), reportan **15 % de arbustal y 23 % de bosque abierto de ñire** usando la cartografía de CIEFAP/MAyDS.

Dato adicional que expone el origen del problema: la tabla vigente mapea `95 Mangroves → 183 TL3`. No hay manglares en Patagonia. Es un artefacto de haber adoptado una leyenda global sin adaptarla, y sirve como ilustración del argumento en la tesis.

---



## B0 — Sonda de MapBiomas (decisión con datos, sin construir infraestructura)

MapBiomas Argentina Colección 2 (Landsat 30 m, 1985–2024, equipo Patagonia propio) es de acceso libre, a diferencia de CCS-BAP. Sirve como puente mientras se gestiona el acceso.

Decisión: **sonda antes que módulo.** Montar MapBiomas como fuente productiva (cliente, servicio, tipo de asset, migración, tests, endpoint) es trabajo real que queda muerto si CCS-BAP llega pronto. La pregunta que MapBiomas responde es barata: *¿separa el arbustal mejor que WorldCover en este AOI?*

Pasos:

1. Descargar el recorte del AOI (plataforma MapBiomas o asset de Google Earth Engine), mediante un script de una sola pasada, versionado y reproducible.
2. Tabular la distribución de clases por área sobre el AOI.
3. Comparar contra la distribución de WorldCover en las tres dimensiones que importan: **fracción de arbustal**, separación de estepa, y fracción declarada no combustible.
4. Criterio de decisión, fijado **antes** de mirar el resultado: si la fracción de arbustal se mantiene en el mismo orden que WorldCover (~0 %), MapBiomas no aporta y se descarta, dejando registrado el resultado negativo. Si se acerca al orden de magnitud reportado por Godoy et al. (~15 %), se promueve a **tercer punto de comparación** de la tesis.
5. Registrar el resultado, sea cual sea. Un resultado negativo documentado también es material de tesis: acota qué familia de productos globales sirve para esto.



### Resultado (2026-09-06) — criterio cumplido, MapBiomas se promueve

Sonda: `scripts/probe_mapbiomas.py`. Lectura por ventana del COG público sobre el AOI, sin descargar los 650 MB del país entero.


| Fuente  | Colección 2, año 2024 (`argentina_coverage_2024.tif`), 30 m, EPSG:4326, int32                                                                                                |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ventana | 3.340 × 3.154 px = 948.092 ha                                                                                                                                                |
| Leyenda | [https://argentina.mapbiomas.org/wp-content/uploads/sites/12/2025/09/Leyenda_Code.pdf](https://argentina.mapbiomas.org/wp-content/uploads/sites/12/2025/09/Leyenda_Code.pdf) |



| Métrica                                             | MapBiomas   | WorldCover   |
| --------------------------------------------------- | ----------- | ------------ |
| **Arbustal** (66 cerrado + 77 abierto + 63 mosaico) | **25,86 %** | **0,04 %**   |
| No combustible (24 + 25 + 33 + 34)                  | 24,23 %     | 23,0 %       |
| Turberas (73)                                       | 0,06 %      | sin clase    |
| **Sin clase** (0 nodata + 27 no observado)          | **6,06 %**  | 0 % (global) |


**El criterio se cumple con holgura.** El arbustal pasa de 0,04 % a 25,86 % — supera incluso el ~15 % que Godoy et al. (2022) reportan para Esquel-Trevelin, lo cual es consistente: su recorte es más ecotonal y el nuestro incluye más ladera andina. MapBiomas **se promueve a tercer punto de comparación** de la tesis.

Además trae clases que el plan necesitaba y WorldCover no tiene:

- **Arbustal cerrado (66) separado de abierto (77)** — distinción estructural, no sólo fisonómica.
- **Turberas como clase propia (73)**, que es exactamente lo que §B2 pide declarar fuera del alcance de Rothermel. Ahora es identificable en vez de estar disuelta en otra clase.
- **Herbáceas inundables (11), 5,07 %** — los mallines, que WorldCover colapsaba.
- **Bosques cerrados (3) vs abiertos (4)** — la misma distinción TF/OFL que aporta CCS-BAP.
- Año **2024** contra 2021 de WorldCover: dos años más cerca del incendio de feb-2026.



### Dos hallazgos que no esperaba

**1. El 23 % no combustible NO es un artefacto de WorldCover.** El audit (§2.1) se preguntaba si `bare/sparse` estaba sobreasignado a 10 m. Dos productos independientes, con sensores y metodologías distintas, coinciden en ~24 %. La hipótesis de sobreasignación **no se sostiene**: el AOI tiene efectivamente esa proporción de roca, agua, hielo y suelo desnudo. Es un resultado negativo útil y va documentado como tal.

**2. MapBiomas corta en la frontera internacional.** El 4,54 % con código 0 está íntegramente en el tercio oeste del AOI, hasta lon −71,72: es el lado chileno. Sumado al 1,52 % de "no observado", **el 6,06 % del AOI queda sin clase asignable**. WorldCover, siendo global, no tiene ese hueco.

Esto afecta también a CCS-BAP, que es el inventario del BAP **argentino** y tendrá el mismo límite. Decisión pendiente para §B4: rellenar la franja chilena con un producto global (WorldCover como respaldo), con el Catastro de CONAF del lado chileno, o declararla no combustible y acotar el alcance. **No es cosmético**: está en el borde oeste del dominio, y
un borde artificialmente incombustible frena el frente por construcción.

---



## B1 — Obtener CCS-BAP

**Clasificación de Tipos Forestales y Cobertura del Suelo de la Región Bosque Andino Patagónico** (CIEFAP, MAyDS y provincias, 2016). Es el producto de referencia regional.

Características verificadas del producto (informe final CCS-BAP):


|                     |                                                                                                                   |
| ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Imágenes            | Mosaicos SPOT 5 (multiespectral 10 m, pancromático 2,5–5 m) + Landsat TM/ETM+/OLI de **verano e invierno**        |
| Escala              | Presentación 1:50.000, trabajo 1:25.000                                                                           |
| Unidad mínima       | **1 ha** (el producto anterior, PINBN BAP, era 1:250.000 y 15 ha)                                                 |
| Exactitud global    | **87 % nivel 2**, 95 % nivel 1                                                                                    |
| Método              | Análisis de imágenes basado en objetos (fase 1, automática) + interpretación visual con control de campo (fase 2) |
| Proyección original | POSGAR94 Faja 1                                                                                                   |


Lo que lo hace apto para combustibles, y no sólo para inventario forestal:

- **Discrimina especie**: lenga, ñire, coihue, ciprés, guindo, alerce, araucaria, roblepellín, raulí, radal, maitén, ciprés de las guaitecas, mirtáceas, y mixto.
- **Separa Tierras Forestales de Otras Formaciones Leñosas** por altura y cobertura. Es una distinción **estructural**, exactamente la variable que separa un modelo de hojarasca de uno de sotobosque.
- **Separa matorral de arbustal** (adoptando Loguercio et al. 2006), y agrega chacay.
- Usa **Landsat de invierno para separar perennifolio de caducifolio** — que es justamente
la variable que decide entre hojarasca latifoliada y de conífera en la familia TL.
- Clases no leñosas explícitas: estepa, mallines, turberas, eriales, hielo-nieve, agua.

Superficies en Chubut al nivel 2 (TF + OFL): lenga 301.325 + 125.098 ha; ñire 166.648 +
123.081; coihue 88.552; mixto 34.299.

### Dónde está y cómo pedirlo

CIEFAP publica un GeoNode en [https://mapas.ciefap.org.ar](https://mapas.ciefap.org.ar). La capa está catalogada:

```
dataset 247 · geonode:cobertura_bap_chubut · "Cobertura del Suelo del Chubut_ 2016"
abstract : CIEFAP, MAyDS, 2016. Actualización de la Clasificación de Tipos Forestales
           y Cobertura del Suelo de la Región Bosque Andino Patagónico. Informe Final.
CRS      : EPSG:4326 · geometría MultiPolygon
extent   : lon -72,188 … -70,406 · lat -46,001 … -41,999   → contiene nuestro AOI
atributos: ley_n1, ley_n2, ley_n3, provincia, apn, categoria, area_ha
```

Los tres niveles de leyenda vienen como campos separados (`ley_n1/2/3`), lo que permite
elegir el nivel de detalle del crosswalk sin reprocesar. El campo `apn` marca los
polígonos bajo jurisdicción de Parques Nacionales.

**Resuelto el 2026-09-13: CIEFAP entregó los datos.** Cinco provincias (Chubut, Río Negro,
Neuquén, Santa Cruz, Tierra del Fuego) en dos épocas, **2013 y 2017**, como shapefile de
nivel 3 en POSGAR94 Faja 1. Se usa `CH_2017`; la época 2013 sirve de control temporal y
reveló el incendio de Cholila de 2015 (+37.581 ha de "remanente de disturbio reciente" dentro
del AOI). Caracterización completa en `IGN-20B-CROSSWALK-CCSBAP.md` §1.

Estado de acceso previo, que quedó registrado: la descarga directa (`/download/247`) responde
**403** y el WFS anónimo no expone la capa.

Contactos:

- GeoNode / consultas cartográficas: **[geonodeciefap@gmail.com](mailto:geonodeciefap@gmail.com)**
- General CIEFAP: **[info@ciefap.org.ar](mailto:info@ciefap.org.ar)** · Ruta 259 km 16,24, Esquel (9200), Chubut

Pedido concreto: cuenta de acceso al GeoNode, o el shapefile de `geonode:cobertura_bap_chubut`.
Otras provincias disponibles: 245 (Tierra del Fuego), 246 (Neuquén), 248 (Río Negro),
249 (Santa Cruz), 200 (regional). Conviene mencionar en el pedido que es para una tesis de
grado y ofrecer la cita correspondiente.

Vía alternativa si el GeoNode no responde: Subsecretaría de Bosques y Parques de Chubut y
APN Delegación Regional Patagonia Norte participaron de la fase 2 de la clasificación y
tienen el dato.

---



## B2 — Construir la tabla de correspondencia (IGN-20)

Es el entregable que el director tiene que aprobar y el corazón de la fundamentación.

### Método de asignación

Para **cada clase** de la leyenda se registra una ficha con estos campos, en este orden.
Los pasos 1 a 4 son literalmente el procedimiento de selección de Scott & Burgan (2005,
pp. 8-9), aplicado de forma explícita en vez de por intuición:

1. **Descripción fisonómica** de la clase, tomada de la leyenda de origen (no inventada).
2. **Tipo de combustible portador del fuego**: pastizal, pastizal-arbustal, arbustal,
  hojarasca bajo dosel, o bosque con sotobosque. Scott & Burgan, paso 1: *"Estimate which
   stratum of surface fuels is most likely to carry the fire"* — y su advertencia de que un
   área forestada con dosel abierto puede propagar por pasto y no por hojarasca.
3. **Régimen climático de referencia → humedad de extinción**. Scott & Burgan, paso 2. Acá
  entra la evidencia patagónica: Bianchi & Defossé midieron umbrales de ignición de
   combustibles finos muertos de **21,5 % en ciprés y 25,0 % en ñire**. Los modelos SB40 de
   clima seco usan extinción de 15–20 %; esos umbrales medidos respaldan preferir las
   variantes de **clima subhúmedo/húmedo (30–40 %)**. Es un argumento cuantitativo, no una
   analogía.
4. **Profundidad, compacidad, tamaño del combustible y proporción de vegetación viva**.
  Scott & Burgan, paso 3.
5. **Contraste de comportamiento esperado**. Scott & Burgan, paso 4: *"Do not restrict your
  selection by fuel model name or fuel type. After selecting a fuel model, view its
   predicted fire behavior to be sure the predicted behavior agrees with your expectation or
   observation."* Se calcula la tasa de propagación y longitud de llama del modelo candidato
   bajo el escenario D2L2 y se contrasta con comportamiento observado en incendios
   patagónicos. **Una asignación que no pasa este paso se rechaza aunque el nombre encaje.**
6. **Cita** de respaldo, o declaración explícita de que es un juicio del autor sin respaldo
  bibliográfico. Esta última categoría debe ser visible, no disimulada.



### Criterios ecológicos por familia de clases

Guía de partida, a completar con el paso 5 antes de fijarla:

- **Bosques caducifolios de lenga y ñire** — hojarasca latifoliada, no de conífera. La
familia TL de latifoliadas (TL2/TL6/TL9) es el punto de partida natural, no TL3 que es
hojarasca de conífera. Cuando hay sotobosque, la familia TU desplaza a TL.
- **Ciprés de la cordillera (*Austrocedrus chilensis*)** — conífera con sotobosque arbustivo
característico. TU5 (*heavy forest litter with a shrub or small tree understory*) es el
candidato descriptivo, con la salvedad de que su extinción es 25 % y su clima de referencia
es seco.
- **Coihue y alerce** — perennifolios de ambiente húmedo a muy húmedo. Extinción alta.
- **Ñire bajo / OFL** — CCS-BAP documenta que ñire arbóreo y arbustivo **no son separables
por sensores ópticos** y los agrupa como *Ñire Bajo*. Fisonómicamente es matorral: familia
SH o TU, no TL.
- **Matorral y arbustal** — familia SH. La elección entre variantes de clima seco (15 %) y
húmedo (30–40 %) se decide con el paso 3.
- **Estepa** — familia GR, clima árido a semiárido, extinción baja.
- **Mallines** — pastizal húmedo. Estacionalmente puede no propagar.
- **Turberas** — **caso especial que debe declararse como limitación, no forzarse.** Scott &
Burgan (2005, p. 3) son explícitos: el set modela *"surface fire behavior at the flaming
front only, not residual combustion"*. Una turbera arde por combustión latente subterránea,
fenómeno que Rothermel no representa. Asignarle un modelo de superficie es incorrecto;
corresponde declararlo fuera del alcance del modelo.
- **Eriales, hielo-nieve, agua, urbano** — familia NB. Con CCS-BAP, *eriales* es una clase
propia, lo que permite revisar el 23 % no combustible del baseline en vez de heredarlo.



### Trampa verificada: modelos dinámicos

Scott & Burgan (2005, p. 4) advierten que **todos** los modelos con componente herbáceo vivo
son dinámicos, y que usarlos en un procesador no dinámico hace que *"los modelos de pastizal
predigan nula o muy escasa propagación bajo cualquier condición de viento o humedad"*.

Verificado en el fuente: **ELMFIRE sí implementa la transferencia dinámica de carga** — el
CSV de combustibles tiene una columna `dynamic` (`.TRUE.`/`.FALSE.`) y la tabla se precomputa
en función de la humedad herbácea viva. Al escribir nuestra propia tabla en la Etapa A hay que
**preservar el flag** de cada modelo. Si se copia mal, todos los modelos GR y GS dejan de
propagar sin dar error.

### Limitaciones a documentar (criterio de aceptación de IGN-20)

1. FBFM40 fue calibrado con series fotográficas de combustibles de EE.UU. Ninguna especie
  patagónica participó de su construcción.
2. El modelo de Rothermel supone un lecho de combustible **homogéneo y continuo**
  (Scott & Burgan p. 3); los mosaicos bosque-matorral-estepa del ecotono lo violan.
3. Sólo se representa el frente de llama superficial. Combustión latente y consumo residual
  quedan fuera (relevante para turberas).
4. La agregación a 30 m por clase mayoritaria pierde corredores de combustible más angostos
  que un píxel, y la continuidad del combustible gobierna la propagación.
5. La correspondencia de un tipo forestal a un modelo de combustible supone homogeneidad
  dentro de la clase: no distingue estado sucesional, historia de fuego, ni carga de
   material muerto en pie.
6. No existe crosswalk publicado de especies patagónicas a FBFM40. Esta tabla es una
  propuesta original y debe presentarse como tal.

---



## B3 — Fuentes de cobertura coexistentes

Decisión: **coexisten, seleccionables por configuración.** Un solo camino de reclasificación
con el crosswalk parametrizado por fuente, y la fuente activa elegida por config.

Motivo: el aporte de tesis es comparativo. Hay que poder regenerar el `fbfm40.tif` de
cualquiera de las fuentes para la tabla de IoU sin volver a un commit anterior.

Restricción de diseño: **sin abstracciones especulativas.** Un diccionario de crosswalk por
fuente y un parámetro de configuración. Nada de interfaces de proveedor, registros de
fuentes ni fábricas — hay como mucho tres fuentes y no van a crecer.

Pasos:

1. Renombrar `worldcover_to_fbfm40()` a un nombre neutral respecto de la fuente, conservando
  la firma. Es la función que ya sabe reproyectar, agregar por moda y escribir Int16.
2. Un diccionario de crosswalk por fuente, cada uno con su procedencia y versión.
3. Parámetro de configuración para la fuente activa, que **entra en la clave de caché** de
  A1 — cambiar de fuente debe invalidar el `fbfm40.tif`.
4. `app/api/v1/fuels.py` y `frontend/components/fuels-panel.tsx` muestran hoy
  `worldcover_classes` como procedencia de cada modelo. Generalizar el campo para que
   nombre la fuente activa.
5. Actualizar `tests/test_fuels_overlay.py`, que hoy verifica etiquetas de WorldCover.

---



## B4 — Rasterizar CCS-BAP

CCS-BAP es **vectorial**; WorldCover y MapBiomas son ráster. Es un camino de ingesta distinto.

Pasos:

1. Ingerir la capa vectorial recortada al AOI, registrada como asset con su propio tipo.
2. Elegir el **nivel de leyenda** (`ley_n1`, `ley_n2` o `ley_n3`) y justificar la elección.
  El nivel 2 tiene 87 % de exactitud reportada; el nivel 3 es más detallado pero el informe
   no reporta exactitud propia para él y advierte errores de omisión en las clases menores.
   **Recomendación: nivel 2, con el nivel 3 evaluado como sensibilidad.**
3. Rasterizar a la grilla de referencia (EPSG:32719, 30 m) por **clase mayoritaria** —
  fracción de área de cada clase dentro de cada píxel, gana la mayor. Es la misma regla
   fijada en A5, para que la comparación IoU no mida diferencias de remuestreo.
4. Reproyectar de EPSG:4326 a EPSG:32719 **antes** de calcular áreas, no después: en
  coordenadas geográficas el área de un polígono no es proporcional a su área en grados.
5. Definir el tratamiento de huecos: CCS-BAP filtró polígonos menores a 1 ha absorbiéndolos
  en el vecino, así que no debería haber vacíos dentro de su extensión, pero hay que
   verificarlo y decidir qué pasa en los píxeles sin polígono.
6. Aplicar el crosswalk de B2 y escribir Int16 con la validación de códigos de A3.

**Implementado** en `fuels_builder.ccsbap_to_fbfm40()`: rasteriza a 10 m (3×3 subceldas por
píxel de 30 m) y toma la clase mayoritaria, misma regla que A5. Cobertura medida del AOI:
95,45 %; el hueco se rellena con WorldCover (IGN-20 §7.5, opción 1), idéntico para todas las
fuentes para que la comparación no mida la regla de relleno.

---



## B5 — Fijar la humedad de combustible vivo

> **Cerrado el 2026-09-16.** `LH = 30 %`, `LW = 110 %`, contra el 60 % sin criterio anterior.

Al aparecer modelos con carga viva (SH, GS, TU), `LH_MOISTURE_CONTENT` y
`LW_MOISTURE_CONTENT` dejan de ser inocuos. Cuantificado en `IGN-20B` §6.3: el escalar mueve
el área quemada en un factor 2,5 sobre un rango plausible.

### Lo que mide la fuente

Bianchi & Defossé (2015), *Live fuel moisture content and leaf ignition of forest species in
Andean Patagonia*, IJWF 24(3):340. Muestreo cada 10 a 15 días **durante la temporada de
fuego** (mediados de noviembre a principios de abril), cinco temporadas para ñire y ciprés.
Hojas tomadas a 2 m de altura —la porción del dosel donde un fuego de superficie puede pasar
a copas— y **de la cara norte**, la más expuesta al sol y por lo tanto la de menor humedad.

| Nivel | Especies | LFMC en temporada de fuego |
|---|---|---|
| Bajo | Caña colihue (*Chusquea culeou*) | nunca supera **110 %** |
| Medio | Ñire, ciprés, laura, radal | **110 – 220 %** |
| Alto | Álamo (exótico) | 220 – 300 % |

### Los valores adoptados

**`LW_MOISTURE_CONTENT = 110 %`** — el extremo seco de la banda medida. Es la condición más
propensa al fuego dentro de lo observado, y es además donde cae la caña colihue, que es el
sotobosque de los bosques de coihue. La alternativa —el punto medio, 165 %— daría un fuego
sistemáticamente menor; se elige el extremo seco y **se declara la banda completa** como
incertidumbre, ya cuantificada por el barrido.

**`LH_MOISTURE_CONTENT = 30 %`** — el paper no mide herbáceas. 30 % representa el pasto
completamente curado del verano tardío, que es el umbral de transferencia dinámica de
Scott & Burgan. **Es una convención de modelado declarada, no un dato.**

### Limitaciones declaradas

1. **Lenga, coihue y alerce no fueron medidos.** Heredan el valor del ñire por analogía. Son
   el 26 % del AOI, así que no es menor.
2. **Es un escalar global.** ELMFIRE no acepta un ráster de humedad viva, así que un único
   número representa desde el mallín hasta la estepa. El barrido de §6.3 muestra que esta
   simplificación es cara y que **corresponde evaluar un ráster** como trabajo futuro.
3. **El valor anterior, 60 %, quedaba por debajo de todo lo medido** en la región. Toda
   corrida previa a esta fecha sobreestimaba el fuego por ese motivo.

## B6 — Comparación y cierre

1. Generar `fbfm40.tif` para cada fuente disponible con crosswalk fundamentado.
2. Correr ELMFIRE sobre el mismo incendio, mismos inputs, misma meteorología, **sin tocar
  ADJ** — variando únicamente el mapa de combustible.
3. Calcular IoU con el harness B, puntuando **sólo el anillo de crecimiento**, estratificado
  por `pct_quemado`.
4. Reportar además las métricas descriptivas por mapa: distribución de códigos por área,
  fracción no combustible, intensidad de línea mediana.
5. Conclusión falsable: el mapa patagónico mejora, empata o empeora respecto del baseline.
  **Las tres son resultado publicable.** Un empate diría que ELMFIRE es insensible al detalle
   del combustible en este régimen, lo que sería un hallazgo fuerte por sí mismo.

---



## Riesgos


| Riesgo                                                              | Mitigación                                                                                                                                                               |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| CCS-BAP no llega a tiempo                                           | MapBiomas como puente (B0); si tampoco sirve, la tesis se sostiene sobre la crítica cuantificada del baseline y el crosswalk propuesto queda como propuesta metodológica |
| El nivel 3 de la leyenda tiene errores de omisión en clases menores | Usar nivel 2 como principal, nivel 3 como análisis de sensibilidad                                                                                                       |
| Copiar mal el flag `dynamic` mata la propagación en pastizales      | Test que verifica el flag contra la tabla de referencia de ELMFIRE                                                                                                       |
| El crosswalk queda sin respaldo bibliográfico en algunas clases     | Marcarlo explícitamente como juicio del autor; es honesto y anticipa la pregunta del jurado                                                                              |
| CCS-BAP es de 2016 y el incendio de 2026                            | Declarar el desfase temporal; verificar con el histórico de FIRMS si hubo fuegos en el AOI en el intervalo que hayan cambiado la cobertura                               |




## Decisiones registradas


| Decisión          | Elegida                                      | Motivo                                                         |
| ----------------- | -------------------------------------------- | -------------------------------------------------------------- |
| Núcleo del aporte | Crosswalk fundamentado + marco comparativo   | No depende de conseguir mediciones de campo                    |
| MapBiomas         | Sonda antes que módulo                       | Responde la pregunta sin construir infraestructura descartable |
| Fuentes           | Coexisten por configuración                  | El aporte es comparativo y hay que poder regenerar cualquiera  |
| Nivel de leyenda  | Nivel 2 principal, nivel 3 como sensibilidad | Es el nivel con exactitud reportada (87 %)                     |
| Turberas          | Declarar fuera de alcance                    | Rothermel no modela combustión latente                         |
| ADJ               | No se toca en esta etapa                     | Absorbería el error del combustible y anularía el resultado    |




## Fuentes

- CIEFAP, MAyDS (2016). *Actualización de la Clasificación de Tipos Forestales y Cobertura del
Suelo de la Región Bosque Andino Patagónico. Informe Final.* —
[https://www.argentina.gob.ar/sites/default/files/2025/07/informe_final_ccs_bap_20160712.pdf](https://www.argentina.gob.ar/sites/default/files/2025/07/informe_final_ccs_bap_20160712.pdf)
- Capa: `geonode:cobertura_bap_chubut`, dataset 247 — [https://mapas.ciefap.org.ar/catalogue/#/dataset/247](https://mapas.ciefap.org.ar/catalogue/#/dataset/247)
- Scott, J.H.; Burgan, R.E. (2005). *Standard Fire Behavior Fuel Models: A Comprehensive Set for
Use with Rothermel's Surface Fire Spread Model.* RMRS-GTR-153. (Selección: pp. 8-9;
alcance y supuestos: p. 3; modelos dinámicos: pp. 4, 6-7)
- Mermoz, M.; Kitzberger, T.; Veblen, T.T. (2005). *Landscape influences on occurrence and spread
of wildfires in Patagonian forests and shrublands.* Ecology 86(10). —
[https://esajournals.onlinelibrary.wiley.com/doi/abs/10.1890/04-1850](https://esajournals.onlinelibrary.wiley.com/doi/abs/10.1890/04-1850)
- Godoy, M.M. et al. (2022). *Forty Years of Wildland Urban Interface Growth and Its Relation
With Wildfires in Central-Western Chubut, Argentina.* Frontiers in Forests and Global Change. —
[https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2022.850543/full](https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2022.850543/full)
- Bianchi, L.O.; Defossé, G.E. *Ignition probability of fine dead surface fuels of native
Patagonian forests of Argentina.* Forest Systems. —
[https://fs.revistas.csic.es/index.php/fs/article/view/4632](https://fs.revistas.csic.es/index.php/fs/article/view/4632)
- Bianchi, L.O.; Defossé, G.E. (2015). *Live fuel moisture content and leaf ignition of forest
species in Andean Patagonia, Argentina.* IJWF 24(3):340. —
[https://connectsci.au/wf/article-abstract/24/3/340/21003/Live-fuel-moisture-content-and-leaf-ignition-of](https://connectsci.au/wf/article-abstract/24/3/340/21003/Live-fuel-moisture-content-and-leaf-ignition-of)
- Loguercio, G. et al. (2006), citado por CCS-BAP para la separación matorral / arbustal.
- MapBiomas Argentina, Colección 2 — [https://argentina.mapbiomas.org/](https://argentina.mapbiomas.org/)
- `docs/historico/SIMULATION_AUDIT.md` §1, §2.1 · `IGN-26-VALIDACION.md` §12.3, §12.4

