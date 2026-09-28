# Calibración de ELMFIRE con CCS-BAP sobre los incendios de mask-dataset-gen

> Rama `feat/calibracion-ccsbap`. Combustible fijo: CCS-BAP con `"anio": "anterior_al_fuego"`.
> Método: `IGN-26-VALIDACION.md` §Benchmark. Hallazgos previos: `RESULTADOS.md` §8.
> Todo lo de este documento es reproducible con `scripts/benchmark.py` y los casos y recetas de
> `benchmarks/`.

## 1. Estado actual

*(se reescribe en cada loop — última: loop 0, 2026-09-28)*

- **Fase:** 0 cerrada para los incendios 2021+ salvo Las Golondrinas (falta extender el AOI al
  norte). Protocolo común `calibracion` (§3.1) empaquetándose para seis incendios.
- **Mejor receta:** todavía no hay sobre el conjunto de calibración. Punto de partida:
  `humedad-m6-001` (Dice medio 0,478 en Alerces 2023 + Epuyén 2025, `RESULTADOS.md` §8).
- **Corriendo:** `data/benchmark/cola_emp1.sh` (protocolo `cadena-horizonte`, sirve sobre todo
  para bajar y cachear el GFS), `cola_emp2.sh` (protocolo `calibracion`) y `cola_run2.sh`
  (`base-001` y `humedad-m6-001` sobre `calibracion`, de a uno). Logs en
  `data/benchmark/log_{emp1,emp2,run2}.txt`.
- **Hipótesis abiertas:** H1 (el −6 compensa viento, no T/HR), H2 (la copa no puede iniciarse:
  CBH de plantaciones), H3 (m1 con criterio: Fosberg y corrección por altura). Ver §4.
- **Próximo paso:** con `base-001` en los cuatro incendios de calibración 2021+, contestar las
  cinco preguntas del loop por incendio, y probar `modelo_humedad: fosberg` / `altura` contra
  el −6 uniforme.

## 2. Supuestos

Decisiones tomadas sin poder consultar, con su justificación.

1. **Cicatriz truncada al horizonte** (`referencias.cicatriz.hasta_horizonte`). La cadena corre
   4–5 días, pero varios incendios siguieron semanas: Alerces 2024 estuvo activo 27 días; El
   Turbio creció diez días seguidos. Puntuar 5 días contra la cicatriz de 3 meses castiga al
   modelo por tiempo que no simuló. La referencia pasa a ser la cicatriz ∩ un píxel VIIRS
   (375 m) alrededor de cada detección SP hasta el fin de la última ventana. El resto de la
   cicatriz va a la **exclusión**: ardió después o no se vio, y no cuenta ni como acierto ni
   como error. En Alerces 2023, que terminó en tres días, la truncación deja 1.057 de 1.059 ha y
   reproduce exactamente los números viejos (0,484 / 0,528). Contra: las celdas de la cicatriz
   entre dos pasadas sin detección quedan excluidas, y un modelo que sobre-propaga *hacia lo
   que ardió después* no se penaliza. Es el sesgo correcto para un modelo sin supresión.
2. **Horizonte** = mientras FIRMS siga sumando área, con tope de 5 días. Se juzga con el área
   FIRMS acumulada día a día del diagnóstico. Cuando el incendio se funde con otro evento
   antes del tope, se corta antes (Patriada, §3).
3. **Incendios por rayo latentes** (El Turbio, Puerto Café): la cadena arranca en la primera
   pasada VIIRS con fuego, no en la tormenta. En Puerto Café, que ardió ~500 ha durante 27 días
   antes de explotar, el caso es la fase explosiva: semilla = FIRMS SP observado hasta el 5-ene
   20 UTC (nuevo tipo de semilla `firms`).
4. **Hora de ignición en punto.** El clima horario arranca en punto, así que una ignición a las
   22:30 se toma a las 22:00. Media hora de más frente a días de simulación.
5. **Varias igniciones** (Las Golondrinas: dos focos a 30–40 min): semilla de tipo `puntos`, a
   la misma hora.
6. **`.env` no es accesible desde esta sesión** (permisos). La extensión del AOI se hace en
   `app/config.py` y, al ejecutar, con variables de entorno `AOI_*`, que `pydantic-settings`
   antepone a `.env`. Hay que replicarla en `.env` a mano.
7. **Tolerancia de "detección en la cicatriz"** = 375 m (un píxel VIIRS I en el nadir). Con
   medio píxel, detecciones pegadas al borde contaban como "afuera".
8. **Fosberg en el hemisferio sur:** mes + 6 (enero usa la tabla de mayo-julio) y ladera norte ↔
   fila "sur" de la tabla. Hora solar local = UTC + lon/15. Sombra = dosel ≥ 50 % (no hay
   nubosidad: se supone cielo despejado, lo esperable en días de propagación). De noche, fuera
   del rango de las tablas (08–20 h), se usa la corrección sombreada de la última franja.
   Altura relativa a la "estación" = DEM menos terreno del GFS (el GFS es la estación).
9. **"Detecciones nuevas" = detecciones que agregan área.** VIIRS sigue viendo píxeles dentro de
   lo ya quemado días después de que el frente se detiene. El horizonte se corta cuando el área
   FIRMS acumulada deja de crecer, no cuando dejan de aparecer píxeles. Por eso Alerces 2023
   pasa a 72 h: la cicatriz alcanzada por detecciones queda fija desde las ~54 h, y `cadena-96h`
   corría 96 h.
10. **Las Golondrinas se puntúa contra la cicatriz completa.** VIIRS casi no vio ese incendio:
    6 píxeles a las 19:49 UTC y 1 en la pasada nocturna, para ~10.000 ha. Ardió entre dos
    pasadas y bajo el humo de otro incendio activo desde el 7-mar al este, que la máscara
    excluye. La truncación por detecciones dejaría 853 ha. Las crónicas ("605 viviendas en un
    par de horas") y la ausencia de detecciones posteriores ubican el crecimiento en la primera
    noche. Con un satélite ciego, manda la cronología documentada.
11. **La preparación extendida** (`scripts/preparar_benchmark.py` →
    `data/elmfire/inputs/benchmark-2026-09-28`) sólo la usan los casos nuevos. Los ya
    empaquetados conservan su grilla, así que no hace falta re-empaquetarlos.

## 3. Casos

### 3.1 Protocolo común `calibracion`

Para todos los incendios con GFS (2021+):

- ignición puntual (o semilla observada, §2.3) a la hora documentada;
- ventanas de 24 h encadenadas con semilla `prediccion`;
- clima de análisis GFS encadenados, con humedad de retardo (120 h de historia) y el clima crudo
  (T, HR y terreno del GFS a 0,25°) para las humedades con criterio;
- cicatriz `event-filter-*` truncada al horizonte, con `cambio_no_confirmado` y
  `otro_incendio_probable` excluidos.

El diagnóstico de cada incendio está en `benchmarks/diagnosticos/<incendio>.json` y sale de
`benchmark.py diagnosticar <caso>`. Reporta:

- las detecciones VIIRS SP del período, clasificadas en cicatriz, exclusión, sin observación o
  afuera, con los grupos de las de afuera;
- el área FIRMS acumulada por día;
- la máscara contra la superficie oficial, la cobertura válida y si las fechas pre/post
  encierran la actividad;
- la ignición contra la cicatriz y el DEM, con la celda interior sugerida.

### 3.2 Validez por incendio

| Incendio | Det. en cicatriz (≤5 km) | Máscara / oficial | Fechas | Ignición | Horizonte | Veredicto |
|---|---|---|---|---|---|---|
| los-alerces-2023 | 90 % | 1.059 / 1.160 ha | ✓ | parte SNMF, 124 m adentro, 801 m | 96 h (termina el día 3) | **válido** |
| epuyen-2025 | 96 % | 2.999 / 3.530 ha | ✓ | junto al lago (ya corregida), 348 m | 96 h (80 % del área FIRMS) | **válido** |
| los-alerces-2024 | 98 % | 6.009 / 5.971 ha | ✓ | corregida al Arroyo Centinela, 721 m | 120 h (tope; ~50 %) | **válido** |
| el-turbio-2025 | 94 % | 1.974 / 3.000 ha | ✓ | 1ª pasada VIIRS, 95 m adentro, 554 m | 120 h (tope; ~50 %) | **válido**; máscara chica (sotobosque bajo el umbral dNBR) |
| puerto-patriada-2026 | 96 % | 24.457 / 14.770 ha | post = fin de FIRMS* | corregida a la localidad, 343 m | 96 h (antes de la fusión del 10-ene) | **válido con horizonte acotado** |
| puerto-cafe-2025 | 97 % | 38.188 / 31.000 ha | ✓ | fase explosiva desde lo observado | 96 h desde el 5-ene 20 UTC | **válido como fase explosiva** |
| las-golondrinas-2021 | — | 8.988 (en grilla) / 12.901 ha | ✓ | 2 focos documentados, fuera de la grilla | 48 h (82 % en la 1ª noche) | **pendiente: AOI al norte** |
| epuyen-2019 | 99 % | 1.545 / 1.553 ha | ✓ | 90 m afuera, 517 m | — | pendiente: clima pre-GFS |
| los-alerces-2015 | 93 % | 1.190 / 1.500 ha | ✓ | 300 m adentro | — | pendiente: clima y CCS-BAP 2013 |
| los-alerces-2016 | 99 % | 1.837 / 1.700 ha | ✓ | 270 m adentro | — | pendiente: clima y CCS-BAP 2013 |
| desemboque-2015 | 96 % | **560 / 2.307 ha** | ✓ | 240 m adentro | — | **dudoso**: la máscara es un cuarto de lo oficial |
| currumahuida-2015 | 91 % | 4.242 / 3.151 ha | ✓ | centroide MODIS, **6,9 km** de las 1as detecciones | — | pendiente: ignición |
| cerro-plataforma-2015 | 88 % | 6.265 / 7.371 ha | 1ª detección 14 días después del "inicio" | centroide MODIS sobre NB, 297 m afuera | — | pendiente: ¿parte del complejo Cholila? |
| cholila-2015 | 97 % | 26.680 / 28.960 ha | ✓ | sobre agua, 350 m afuera, **15 km** de las 1as detecciones | — | pendiente: ignición |

\* La ventana post de Patriada empieza el 1-feb, justo cuando dejan de aparecer detecciones:
encierra el período, pero sin margen.

**Lo que dicen las detecciones de afuera.** En todos los incendios 2021+ el 90–98 % de las
detecciones a menos de 5 km cae en la cicatriz. Los grupos de afuera quedan a 375–450 m del borde:
son el píxel VIIRS desbordando la cicatriz, no otros incendios. La excepción son los grupos de
Patriada al este (−71,25), del 10-ene. Por eso el horizonte se corta antes.

**Partición (fijada antes del primer barrido; los incendios pendientes quedan asignados de
antemano):**

| Calibración | Prueba |
|---|---|
| los-alerces-2023 (1.000 ha, 2023) | el-turbio-2025 (2.000 ha, rayo, 2025) |
| epuyen-2025 (3.000 ha, 2025) | puerto-cafe-2025 (fase explosiva, 38.000 ha, 2026) |
| los-alerces-2024 (6.000 ha, 2024) | epuyen-2019 |
| puerto-patriada-2026 (grande, 2026) | los-alerces-2015 |
| las-golondrinas-2021 (viento extremo, 2021) | cerro-plataforma-2015 |
| los-alerces-2016, currumahuida-2015, cholila-2015, desemboque-2015 | |

## 4. Bitácora de loops

### Loop 0 — antes de barrer nada: ¿qué le falta al modelo?

**H1. El −6 no compensa un sesgo de T/HR del GFS.** Contra las estaciones de Meteostat, en la
tarde del día 1 de Epuyén (15-ene-2025):

| 18 UTC | T | HR | Viento 10 m | m1 Nelson |
|---|---|---|---|---|
| Estación El Bolsón (337 m, 25 km al norte) | 23,7 °C | 35 % | 35 km/h (ráfaga del registro) | 6,7 % |
| GFS en la ignición (terreno ~1.000 m) | 17,5 °C | 38 % | 19 km/h | 7,5 % |
| ERA5 (Open-Meteo) | 19,8 °C | 63 % | 13 km/h | — |

- El GFS es 4–6 °C más frío, pero con una HR parecida: m1 difiere en **menos de un punto**.
- Esquel (789 m) marcó 18,9 °C / 34 % y Bariloche 19,5 °C / 35 %: no fue un día extremo en la
  estación de montaña.
- ERA5 es más húmedo que el GFS, no más seco.
- Para llegar a m1 ≈ 1 % (lo que hace el −6) haría falta HR < 5 %.

**El −6 no corrige el clima: compensa otra cosa.** La diferencia grande está en el
**viento**: la estación marca 18–35 km/h y el GFS 19 km/h en el pico.

**H2. El fuego de copas no puede iniciarse en la cicatriz de Epuyén.** ELMFIRE 2025.0212
(`elmfire_spread_rate.f90`, `CROWN_SPREAD_RATE`) inicia la copa cuando la intensidad superficial
supera (0,01·CBH·(460+26·FMC))^1,5, con FMC = 90 % por defecto. Dentro de la cicatriz:

| Modelo | ha | CC | CH | CBH | CBD | I crítica |
|---|---|---|---|---|---|---|
| SH4 | 1.314 | 0 % | — | — | — | (sin dosel) |
| TL8 pino | 280 | 81 % | 25 m | 10,5 m | 0,06 | ~5.000 kW/m |
| TU5 | 397 | 57 % | 21 m | 7,4 m | 0,04 | ~3.300 kW/m |

- Una hojarasca TL8 no pasa de ~100–300 kW/m, así que la copa es imposible por construcción.
  Eso explica que `CROWN_FIRE_MODEL` 0 y 1 den un TOA idéntico byte a byte.
- El dosel sale de Hansen + ETH (`canopy_builder`, infraestructura que no se fundamenta en la
  tesis). Una plantación de pino sin podar tiene CBH de 2–4 m, no 10 m.
- **Queda como hallazgo, no como perilla:** tocar el dosel no está entre los parámetros sin
  criterio que este trabajo calibra.

**H3. El m1 sin criterio: dos reemplazos del delta uniforme** (`app/validation/humedad.py`,
tests en `tests/test_validation_humedad.py`):

- `modelo_humedad: altura`: T llevada al DEM con −6,5 °C/km conservando el punto de rocío.
  Nelson para m1/m10/m100.
- `modelo_humedad: fosberg`: tablas de Rothermel/Fosberg transcritas de BehavePlus
  (`firelab/behave`, `fineDeadFuelMoistureTool.cpp`, verificadas celda por celda contra el
  fuente). Corrigen m1 por hora, sombra (CC ≥ 50 %), orientación, pendiente y altura respecto
  del terreno del GFS. Sólo m1.

Por H1 espero que ninguna de las dos alcance el −6. Si no llegan, eso confirma que la
velocidad que falta no es de humedad, y la próxima hipótesis es el viento (factor por incendio
contra la estación) y la carga viva del SH4.

### Loop 1 — `base-001` y la humedad con criterio sobre Alerces 2023 y Epuyén 2025

`benchmark.py analizar <caso> <receta>` responde las preguntas del loop. Da:

- la curva de área predicha contra la cicatriz ya alcanzada por detecciones, cada 6 h;
- dónde caen aciertos, falsos positivos y no predichos, por grupo de combustible, altura,
  pendiente, distancia y rumbo desde la ignición;
- el viento del GFS en la ignición y el rumbo del frente observado cada día.

**1. ¿Sobre o sub-propaga, y cuándo?** Sub-propaga, y sobre todo el día 1.

| Incendio | Observado (ha) | `base-001` (ha) | `humedad-m6-001` (ha) |
|---|---|---|---|
| Alerces 2023 | 485 a las 24 h; 1.055 a las 54 h, y ahí se detiene (combate) | 116 a las 24 h; crece parejo hasta 697 a las 72 h | 256 a las 24 h |
| Epuyén 2025 | **1.120 en las primeras 6 h**; 1.730 a las 18 h | 18 a las 24 h | **26 a las 24 h** |

En Epuyén, el −6 alcanza el área final porque crece durante 3–4 días, no porque reproduzca la
corrida del día 1.

**2. ¿Dónde?** En las dos cicatrices, lo no predicho está al SE/S y lejos de la ignición:

- Alerces 2023: 2,9 km y más alto que la ignición (900 m contra 801 m).
- Epuyén 2025: 4,3 km.

Los falsos positivos van al N/NE (Alerces) y al SO, ladera arriba (Epuyén: 1.011 ha con el −6,
a 619 m de mediana contra 348 m de la ignición).

**Rumbo del frente observado** (cuartil más lejano de las detecciones de cada día, desde la
ignición) contra hacia dónde empuja el viento medio del GFS:

| Incendio | Día 1 | Día 2 | Día 3 | Día 4 |
|---|---|---|---|---|
| Alerces 2023 | 169° vs 97° (+72°) | 171° vs 92° (+79°) | 123° vs 84° (+39°) | — |
| Epuyén 2025 | 143° vs 100° (+44°) | 154° vs 91° (+63°) | 193° vs 89° (+103°) | 162° vs 96° (+66°) |

El frente real va 40–100° más al sur que el empuje del GFS, siempre en el mismo sentido. Es la
firma del **encauzamiento por los valles**, que un GFS de 0,25° no resuelve. La estación de El
Bolsón marcó 320° (NO) a 35 km/h a las 18 UTC del día 1, cuando el GFS daba 270° (O).

**3. ¿Por qué?** Hipótesis, en orden:

- H4, **dirección del viento** (explica la forma);
- H5, **velocidad**, que ninguna humedad realista alcanza: el día 1 de Epuyén (5 km en 6 h)
  necesita viento de ráfaga y pavesas;
- supresión, en Alerces después de las 54 h.

**H1 y H3 quedan confirmadas con datos:**

- *Estaciones contra GFS* (Meteostat; tardes 15–22 UTC de los días de fuego). El m1 de Nelson
  con el GFS es igual o más seco que con la estación:

  | Estación | m1 estación | m1 GFS |
  |---|---|---|
  | El Bolsón (Epuyén) | 6,4 % | 5,8 % |
  | Esquel (Alerces) | 5,9 % | 5,5 % |
  | Futaleufú | 6,6 % | 9,1 % |

  El sesgo grande del GFS está en el **viento de valle**: Futaleufú marca 30 km/h de media contra
  10 del GFS, con ráfagas de 83 contra 15. En El Bolsón, la ráfaga máxima es 35 contra 16.
- *Fosberg contra Nelson* en Alerces 2023 (`fosberg-001`, ventana 0): mediana 7,0 contra 6,8 %
  en el pico de la tarde y 9,0 contra 7,6 % a las 16 UTC. Las tablas no secan. El Dice queda
  igual: 0,423 contra 0,425.
- **Conclusión:** el m1 realista en las tardes de fuego es 5–7 %. El −6 (m1 ≈ 1 %) no tiene
  soporte en estaciones ni en Fosberg: es una **perilla de velocidad disfrazada de humedad**,
  que en PENDING_PARAMETERS le corresponde a ADJ (§1.3).

**ERA5 contra estaciones** (para los incendios anteriores al archivo GFS):

- ERA5 en su celda es más frío y más húmedo: m1 8,1 % contra 6,4 % en El Bolsón.
- La corrección de Open-Meteo por altura baja sólo la T y deja la HR: 8,2 %.
- Con la T llevada al DEM y el **punto de rocío conservado** (`modelo_humedad: altura`), la HR
  baja a ~32 % y m1 ≈ 6,5 %, igual que la estación. Lo mismo en Esquel y Futaleufú.
- Para el GFS, la misma corrección secaría de más: ya coincide crudo.
- **Protocolo comparable entre fuentes: GFS crudo ↔ ERA5 + `altura`.**

**4. ¿Tiene sentido el test?**

- Alerces 2023: el horizonte pasó a 72 h (§2.9).
- Las Golondrinas: la referencia pasó a la cicatriz completa (§2.10).
- Epuyén 2025 sigue en 96 h con la cicatriz truncada (2.317 de 2.999 ha), porque siguió
  creciendo en pulsos hasta el 22-ene.

**5. Experimentos:**

- `rotacion-060-001` (diagnóstico de H4: wd + 60°, el desvío medio) en los dos incendios.
- Después, la velocidad con la perilla que le corresponde: ADJ por grupo de combustible,
  contra el factor que pide cada incendio.

## 5. Resultados

*(pendiente del primer barrido sobre `calibracion`)*

## 6. Parámetros

*(se completa a medida que haya veredicto)*

## 7. Para corregir afuera

### 7.1 Igniciones de mask-dataset-gen

| Incendio | Coordenada de mask-dataset-gen | Problema | Propuesta (con fuentes en el caso) |
|---|---|---|---|
| epuyen-2025 | -42,2921 / -71,4447 | 1.400 m, en la montaña, 490 m fuera de la cicatriz | -42,21516 / -71,4299 (junto al lago, 348 m) |
| los-alerces-2024 | -42,8036 / -71,5939 | 1.015 m, a media ladera, 1 km del Arroyo Centinela documentado y 1,3 km de las 1as detecciones | -42,80381 / -71,61425 (721 m, junto al arroyo y a la 1ª pasada) |
| puerto-patriada-2026 | -42,148083 / -71,534694 | 150 m fuera de la cicatriz | -42,14589 / -71,53471 |
| el-turbio-2025 | -42,2959 / -71,9356 | 60 m fuera de la cicatriz | -42,29621 / -71,93738 |
| las-golondrinas-2021 | -42,084 / -71,371 | centroide MODIS a 1.393 m, 7,9 km de las 1as detecciones; los focos documentados son dos | Las Golondrinas (-42,015 / -71,533) y Cerro Radal (-42,033 / -71,566), 15 h ART del 9-mar |
| cholila-2015 | -42,45 / -71,7333 | sobre agua (NB8), 350 m fuera, 15 km de las 1as detecciones | pendiente |
| cerro-plataforma-2015 | -42,294 / -71,869 | centroide MODIS sobre NB, 297 m fuera | pendiente |
| currumahuida-2015 | -42,185 / -71,553 | centroide MODIS, 6,9 km de las 1as detecciones | pendiente |

### 7.2 Crosswalk y dosel (para el director)

- Epuyén: la plantación de pino (Forest → **TL8**) de la ignición es hojarasca lenta, y con el CBH
  derivado (10,5 m) nunca pasa a copa (§4 H2). Hallazgo del crosswalk más dosel, no de un
  parámetro.

### 7.3 Límites que ningún parámetro resuelve

- **Clima de superficie:** el GFS de 0,25° es 4–6 °C más frío que la estación de valle y
  subestima el viento de la tarde (§4 H1).
