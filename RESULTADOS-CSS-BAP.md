# Calibración de ELMFIRE con CCS-BAP sobre los incendios de mask-dataset-gen

> Rama `feat/calibracion-ccsbap`. Combustible fijo: CCS-BAP con `"anio": "anterior_al_fuego"`.
> Método: `IGN-26-VALIDACION.md` §Benchmark. Hallazgos previos: `RESULTADOS.md` §8.
> Todo lo de este documento es reproducible con `scripts/benchmark.py` y los casos y recetas de
> `benchmarks/`.

## 1. Estado actual

*(se reescribe en cada loop — última: loop 6d, 2026-09-28 21 h)*

- **Receta final: `lw100-adj115-001`** (LW 100 % + ADJ 1,15; CCS-BAP anterior al fuego;
  pendiente corregida).
  - Calibración (siete incendios): Dice medio 0,372 y mediana 0,411, contra 0,312 / 0,340 de
    base. Cero alarmas en los seis alcanzables.
  - Prueba (cuatro incendios, no usados para elegir): 0,212 contra 0,202 de base.
  - Tablas en §5; veredictos por parámetro en §6.
- **Lo que se entendió:**
  1. La orientación del terreno estaba invertida en todo el repo; corregirla es la mejora más
     grande.
  2. El m1 del GFS ya es el de las estaciones: el −6 no tiene soporte.
  3. La calibración mueve el reloj, no la forma.
  4. El día 1 explosivo (10–50× por debajo) no es de viento medio ni de humedad: faltan copa,
     pavesas y ráfagas.
  5. La velocidad que pide cada incendio varía ~5× según el régimen: la supresión manda en los
     combatidos cerca de poblados.
  6. La ignición (±500 m / ±2 h) pesa más que cualquier perilla.
- **Corriendo:** nada. El consumidor `data/benchmark/cola_run2.sh` sigue vivo, esperando líneas
  nuevas en `data/benchmark/trabajos.txt`.
- **Hipótesis abiertas:** la supresión (el módulo `&SUPPRESSION` de ELMFIRE no está expuesto) y
  la dirección del viento de superficie (sin corrección general con estas herramientas).
- **Próximo paso posible:** sensibilidad de la receta final a la ignición (como en el loop 5c,
  con ADJ 1,3), para confirmar que no es más frágil; revisar Forest → TL8 y Rem Dist Rec → GS3
  con el director (§7.2).

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
12. **Las Golondrinas es un caso límite del clima, no del modelo:** la restricción de alarmas
    de sesgo se evalúa sin él.
    - La estación de El Bolsón (337 m, a 5 km de los focos) muestra una tarde muy seca: 28 °C,
      19–22 % de HR y m1 ≈ 4 %, con viento del ONO de 10–12 km/h.
    - A las 00 UTC del 10-mar entra una **ráfaga del norte de 54 km/h de media horaria**, con un
      salto de temperatura (frente o corriente descendente). Es el momento de la explosión.
    - El GFS de 0,25° no tiene ese evento: 8,5 mph del ONO.
    - Ninguna receta pasa de sesgo 0,07: `base-001` quema 450 de 10.623 ha en 24 h.
    - Se sigue reportando en las tablas y cuenta en la media y la mediana.
13. **ERA5 es intercambiable con el GFS para este modelo.** En los mismos incendios da el mismo
    Dice: Alerces 2023, 0,424 contra 0,425; Epuyén 2025, 0,118 contra 0,128. Los incendios viejos
    se corren con ERA5 y la misma receta, pero se resumen aparte: `objetivo … era5`.
14. **Cambios ajenos en `app/` durante el loop 6.** Desde el 28-sep a la tarde hay cambios sin
    commitear que no son de esta calibración: `app/config.py`, `app/elmfire/runner/client.py`,
    el cliente FIRMS y `.env.example` (transferencia de archivos al runner para Railway). No se
    tocan ni se commitean desde esta rama. Los manifiestos de esas corridas registran
    `git.sucio = true`. El valor por defecto (`elmfire_runner_transfer_files = False`) deja el
    volumen compartido, así que la ejecución es la misma.
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
| epuyen-2019 | 99 % | 1.545 / 1.553 ha | ✓ | corregida 180 m adentro (La Rinconada, 29-ene 16:30 ART) | 120 h (tope; 80 % al día 4) | **válido con ERA5** (`calibracion-era5`) |
| los-alerces-2015 | 93 % | 1.190 / 1.500 ha | ✓ | 300 m adentro, 841 m; hora no publicada (13 ART) | 72 h (91 % al día 3) | **válido con ERA5**, CCS-BAP 2013 |
| los-alerces-2016 | 99 % | 1.837 / 1.700 ha | ✓ | 270 m adentro (Arroyo Cascada, 21-ene 14 ART) | 72 h (94 % al día 3) | **válido con ERA5**, CCS-BAP 2013 |
| desemboque-2015 | 96 % | **560 / 2.307 ha** | ✓ | 240 m adentro | — | **excluido**: la máscara es un cuarto de lo oficial (La Nueva, 3-feb-2015: 'siguen sin control'); la referencia no mide el incendio |
| currumahuida-2015 | 91 % | 4.242 / 3.151 ha | ✓ | centroide MODIS, **6,9 km** de las 1as detecciones | — | **excluido**: incendio de varias fases (empezó el 28-feb desde El Desemboque; reactivaciones en marzo; evacuación el 28-mar, Diario Río Negro / La Nueva). La ventana pre (15-feb a 22-mar) ya contiene la primera fase: la máscara ve sólo la reactivación, sin ignición definida |
| cerro-plataforma-2015 | 88 % | 6.265 / 7.371 ha | 1ª detección 14 días después del "inicio" | centroide MODIS sobre NB, 297 m afuera | — | **excluido**: rayo a comienzos de febrero en El Turbio (Tres Picos y Plataforma), 'controlado' el 20-feb (Página/12); FIRMS lo ve recién el 17-feb y la máscara crece a la par de Cholila, cuya ROI se superpone. Hora de inicio incierta en semanas y referencia probablemente mezclada |
| cholila-2015 | 97 % | 26.680 / 28.960 ha | ✓ | 1ª detección VIIRS (nacientes del Río Tigre, 1.234 m) | 120 h (tope; 39 %) | **válido con ERA5**, CCS-BAP 2013, cicatriz truncada |

\* La ventana post de Patriada empieza el 1-feb, justo cuando dejan de aparecer detecciones:
encierra el período, pero sin margen.

**CCS-BAP 2013** (`fbfm40_ccsbap2013.tif`, de `datasets/CH_2013_…/cob_2013_N3_aok_CH.shp`) se
rasteriza con el mismo crosswalk, la misma regla de mayoría a 10 m y el mismo relleno de
WorldCover que 2017, sobre la grilla extendida (`scripts/preparar_benchmark.py`).

- **Leyenda compatible:** sobre el AOI, las ternas (`Ley_N1`, `Ley_N2`, `Ley_N3`) de 2013 y 2017 son
  exactamente las mismas, todas con modelo asignado. No hay clases nuevas.
- **La diferencia es de contenido:** "Remanente de disturbio reciente" pasa de 170 ha en 2013 a
  39.715 ha en 2017. Son las cicatrices de 2015–2016, mapeadas a GS3. Con el mapa de 2017, un
  incendio de 2015 vería su propia cicatriz: la regla de fuga temporal lo impide, con razón.

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

### Loop 2 — velocidad con ADJ por grupo, dirección, y los incendios nuevos

**Resultados de las hipótesis del loop 1:**

- **H4 (dirección).** `rotacion-060-001` (wd + 60°) sube la forma de Alerces 2023 de 0,425 a
  0,456 y no mueve Epuyén (0,128 → 0,118). **Confirmada a medias:** la dirección pesa sólo
  cuando el modelo avanza a la velocidad correcta. En Epuyén no avanza, y lo poco que avanza lo
  gobierna la pendiente, con un GFS de 5–7 mph.
- **El desvío se repite en los incendios nuevos.** El frente observado va más al sur que el empuje
  del GFS en 5 de 6 incendios:

  | Incendio | Desvío por día |
  |---|---|
  | Alerces 2024 | +0°, +22°, +41°, +35°, +31° |
  | Patriada | −44° (día 1), después +26°, +32°, +16° |
  | Alerces 2016 | +85°, +103°, +90° |

  El rumbo de Cholila no sirve: su caja incluye las detecciones de Cerro Plataforma.
- **ERA5 contra GFS en los mismos incendios** (§2.13): intercambiables.

**H5b (ADJ por grupo).** Barrido sobre los dos incendios chicos:

| Receta | Alerces 2023 (71 % TU) | Epuyén 2025 (54 % SH) |
|---|---|---|
| base | 0,425 / sesgo 0,66 | 0,128 / 0,25 |
| SH ×1,5 | 0,446 / 0,90 | 0,165 / 0,32 |
| SH ×2 | 0,467 / 1,10 | 0,203 / 0,42 |
| SH ×2,5 | 0,481 / 1,29 | 0,241 / 0,58 |
| TU ×1,3 | 0,467 / 0,99 | 0,159 / 0,30 |
| −6 (referencia) | 0,465 / 1,21 | 0,462 / 1,39 |

- Alerces responde como se esperaba.
- **Epuyén apenas responde a SH, porque el fuego queda atrapado en la ignición.** Con SH ×2,5,
  en las primeras 24 h quema 18 ha, casi todo TU5 y TL8 (la plantación de pino donde empezó).
  En 1 km a la redonda hay TL2, TL8, TU5 y agua, y recién a las 36 h el fuego llega al SH4.
- El fuego real ardió en copa en la plantación desde el principio y cubrió 1.120 ha en 6 h.
  Con el CBH derivado (10,5 m) la copa es imposible (H2), y Forest → TL8 es hojarasca lenta.
  **Es el hallazgo del crosswalk (§7.2), cuantificado:** ninguna perilla de las permitidas
  reproduce el día 1 de Epuyén sin romper los demás incendios.
- **Por qué el −6 "funciona" en Epuyén.** Acelera sobre todo la hojarasca (TL8/TU5), la más
  sensible a m1, así que el fuego escapa de la plantación uno o dos días antes y llena el área
  a los 3–4 días, con 1.011 ha de falso positivo ladera arriba al SO. Es un **sustituto del fuego
  de copas que falta**, no una humedad.

**Alerces 2016 (ERA5), el tercero con el mismo patrón:**

- 1.213 ha observadas en 12 h, contra 28 ha de `base-001`.
- Lo no predicho trepa laderas de 30° al S/SO/O (974 m de mediana contra 602 m de la ignición).
- Los falsos positivos se extienden por el fondo plano del valle hacia el E (3°, 551 m), a
  favor del viento del GFS.

**Diagnóstico común** en Alerces 2023, Epuyén 2025 y Alerces 2016:

1. Explosión del día 1 no reproducida (encauzamiento, ráfagas, copa en plantaciones).
2. El modelo avanza a sotavento del GFS por el fondo del valle, y el fuego real corre al S,
   encauzado o ladera arriba.

La calibración de velocidad sólo mueve el reloj. La forma la limitan el viento de superficie y
el combustible de la ignición.

**Hallazgo mayor: la pendiente estaba invertida en todas las corridas.** El patrón de Alerces 2016
(lo no predicho sube las laderas; lo predicho de más se queda en el fondo del valle) llevó a
revisar la convención de la orientación:

- `raster_aligner._derive_slope_aspect` escribía en `asp.tif` la dirección **cuesta arriba**.
  Verificado sobre el DEM de Epuyén: avanzando 150 m en la dirección de `asp`, el terreno sube
  en el 96 % de las celdas con pendiente de más de 20°.
- ELMFIRE 2025.0212 empuja la propagación por pendiente hacia `ASP − 180°`
  (`elmfire_level_set.f90`: `SINASPM180(IASP) = SIN((IASP − 180)·π/180)`). Eso presupone la
  convención LANDFIRE: la dirección hacia la que mira la ladera, cuesta abajo.
- **Todas las corridas del repo empujaron el fuego ladera abajo:** las de este documento con
  protocolo sin `-v2`, las de `RESULTADOS.md` §4–§8 y las de los harness A y B.
- Corregido en la causa: `raster_aligner` pasa a `DERIVATION_VERSION = 3`, con tests de
  laderas sintéticas (`tests/test_topo_aspect.py`) y la trampa documentada en el skill de
  ELMFIRE.
- Preparaciones corregidas en directorios nuevos (`benchmark-aoi-asp3`,
  `benchmark-2026-09-28-asp3`) y protocolos **`calibracion-v2`** / **`calibracion-era5-v2`**.
  Los paquetes viejos quedan como registro. La receta `aspecto-corregido-001` (asp + 180° en la
  corrida) mide sobre los paquetes viejos cuánto cambia el resultado.

Todo lo anterior de esta bitácora (loops 0–2) es con la pendiente invertida. Las conclusiones
de clima (H1, H3, ERA5) no dependen de eso, porque comparan insumos, no corridas. Las de
velocidad y forma se rehacen sobre v2.

### Loop 3 — v2 (pendiente corregida) en los siete incendios de calibración

`benchmark.py objetivo calibracion gfs|era5`. Dice / sesgo al horizonte:

| Receta | Alerces 2023 | Epuyén 2025 | Alerces 2024 | Patriada 2026 | Golondrinas 2021 | Alerces 2016 (ERA5) | Cholila 2015 (ERA5) |
|---|---|---|---|---|---|---|---|
| base-001 | 0,457 / 0,95 | 0,160 / 0,44 ⚠ | 0,522 / 0,53 | 0,340 / 0,69 | 0,029 / 0,05 ⚠ | 0,433 / 0,99 | 0,244 / 0,44 ⚠ |
| adj-130-001 | 0,550 / 1,73 | 0,282 / 0,67 | 0,553 / 0,98 | … | 0,049 / 0,07 ⚠ | 0,400 / 1,72 | … |
| adj-160-001 | 0,520 / 2,71 ⚠ | 0,440 / 1,20 | 0,564 / 1,28 | 0,426 / 1,40 | 0,067 / 0,09 ⚠ | 0,374 / 3,05 ⚠ | 0,431 / 1,10 |
| adj-sh-200-001 | 0,470 / 1,60 | 0,273 / 0,75 | 0,550 / 1,00 | 0,473 / 1,18 | 0,040 / 0,06 ⚠ | 0,458 / 2,27 ⚠ | 0,290 / 0,68 |
| adj-tu-130-001 | 0,557 / 1,45 | 0,217 / 0,52 | 0,564 / 0,68 | — | 0,032 / 0,05 ⚠ | 0,405 / 1,32 | — |
| humedad-m6-001 | 0,517 / 1,77 | 0,471 / 2,08 ⚠ | 0,558 / 1,09 | 0,446 / 1,41 | 0,058 / 0,08 ⚠ | 0,410 / 2,98 ⚠ | 0,393 / 0,74 |

**1. ¿Sobre o sub-propaga, y cuándo?** `base-001` sub-propaga el día 1 en todos:

| Incendio | Observado | `base-001` | Factor |
|---|---|---|---|
| Alerces 2024 | 851 ha a las 24 h | 49 ha | 17× |
| Patriada | 1.600 ha a las 12 h | 30 ha | 50× |
| Alerces 2016 | 1.213 ha a las 12 h | 21 ha | ~60× |
| Epuyén 2025 | 1.120 ha a las 6 h | 1 ha | — |
| Cholila | clavado hasta las 30 h (364 contra 389 ha) | — | — |

Cholila explota entre las 36 y las 54 h (+4.600 ha) y el modelo no. **Al horizonte el sesgo va
de 0,44 a 0,99:** el modelo alcanza el área tarde, porque sigue creciendo cuando el real ya
estaba combatido.

**2. ¿Dónde?** Lo no predicho está al SE/E de la ignición en todos:

| Incendio | No predicho al SE/E | Detalle |
|---|---|---|
| Alerces 2024 | 1.323 de 1.612 ha | incluye 773 ha de TL6 (lenga) a 1.073 m |
| Patriada | 2.415 de 4.079 ha | 2.286 ha de TU |
| Cholila | 5.470 de 5.735 ha | — |

El frente observado va 20–100° más al sur que el empuje del GFS. Los falsos positivos quedan
al SO/O, ladera arriba en Patriada (1.172 ha de GS).

**3. ¿Por qué? Hipótesis descartadas en este loop:**

- **H5b (ADJ por grupo), descartada.** La velocidad que pide cada incendio no sigue a su
  composición:

  | Incendio | SH | Sesgo de base |
  |---|---|---|
  | Alerces 2016 | 52 % | 0,99 (no pide nada) |
  | Epuyén | 54 % | 0,44 |
  | Alerces 2023 | 24 % | 0,95 |
  | Cholila | 29 % | 0,44 |

  El factor depende del incendio (el clima de ese día, la ignición), no del grupo de
  combustible. Con siete incendios, ADJ por grupo no es identificable, y liberarlo sólo
  sobreajustaría.
- **H2 (copa por el CBH), descartada como explicación del día 1.** Con el CBH ×0,25
  (`cbh-025-001`, 2–3 m en las plantaciones), Epuyén pasa de 0,160 a 0,166 y Alerces 2023 de
  0,457 a 0,461. La copa sigue sin iniciarse: en TL8 la intensidad superficial no llega ni a los
  ~600 kW/m que pide un CBH de 2,6 m. El freno está en el modelo de superficie de la
  plantación (Forest → TL8), no en el dosel. Refuerza el hallazgo del crosswalk (§7.2).
- **Dirección.** `rotacion-060-001` sube la forma: Alerces 2023 de 0,457 a 0,483; Epuyén de
  0,160 a 0,183. Sigue abierta como H4, con el atlas de WindNinja (§ loop 4).

**Convergencia y rugosidad (PENDING §3 y §1.4):**

- Paso a la mitad: Alerces 2023 0,461/0,97 contra 0,457/0,95; Epuyén 0,162/0,44 contra
  0,160/0,44; Alerces 2016 0,436/1,00 contra 0,433/0,99. **Convergido en los tres.**
- `z0-dosel-001`: Alerces 2023 0,442/0,84; Epuyén 0,126/0,40. **Peor**, por el doble conteo con
  el WAF.

**4. ¿Tiene sentido el test?** Sí en los seis incendios alcanzables; Golondrinas sigue siendo
el caso límite (§2.12). Cholila con ERA5: la primera fase coincide hasta las 30 h, lo que
valida la ignición en la primera detección.

**5. Experimento:** buscar el **ADJ uniforme** que deja a los seis sin alarma. Interpolando
base/1,3/1,6, el intervalo factible es ~[1,1; 1,35]; se barren 1,1, 1,2, 1,3 y 1,4 en los siete.
En paralelo, el atlas de WindNinja (protocolos v3) para la dirección.

### Loop 4 — la dirección del viento con criterio

**H4a: viento ajustado al terreno con WindNinja (atlas), descartada.**

- WindNinja 3.12.2 (`tools/windninja`, sólo la CLI de conservación de masa, dominio público)
  corre una vez por dirección (16, a 90 m, velocidad unitaria), y la corrida interpola ese
  atlas con el viento del GFS de cada celda y hora (`app/validation/viento.py`, perilla
  `viento_atlas`, protocolos `-v3`).
- En Alerces 2023, la forma queda en 0,456 contra 0,457 y el sesgo pasa de 0,95 a 1,00.
  `base-001` en v3 reproduce exactamente a v2, lo que valida el protocolo.
- El solver desvía el flujo ±15° (percentiles 10–90) y cambia la velocidad entre 0,5 y 1,1
  (crestas contra reparos). **La conservación de masa no produce el encauzamiento de valle**
  que muestran los frentes (40–100°): ese flujo es dinámico y térmico. El solver de
  momento/OpenFOAM de WindNinja sí podría, pero cuesta horas por dirección y queda fuera de
  alcance.

**H4b: canalización por gradiente de presión (Whiteman y Doran 1993), descartada como regla
general.** Dentro de un valle, el viento sigue el eje hacia la baja presión (en el hemisferio
sur, a la derecha del viento de arriba). Prueba sin ELMFIRE: eje del valle en la ignición
(Hessiano del DEM suavizado a σ = 3 km), dirección canalizada contra rumbo observado del
frente:

- Mejora mucho los valles N–S de Los Alerces: Alerces 2023 pasa de −71/−80/−40° a
  −17/−20/+28°; Alerces 2016, de −85/−103/−90° a −23/−32/−37°.
- Empeora Alerces 2024 (de 0/−23° a +75/+54°), Patriada (de +44/−26° a +113/+47°) y
  Las Golondrinas (de +41° a +85°).
- Error absoluto medio: 55° contra 53° del GFS.

Un solo eje en la ignición no representa por dónde corre el fuego cuando sale del valle.

**Lo que sí es sistemático:** el desvío observado − GFS es positivo (el frente corre más al
sur) en 16 de 20 incendio-días, con media ~+43°. Es un **sesgo de dirección del GFS en la
región**, corregible empíricamente como ADJ corrige la velocidad. Se evalúa como
`rotacion_viento` calibrada con validación cruzada, declarada como corrección empírica del
insumo y no como física.

**Rotación empírica sobre ADJ 1,3, descartada: no mejora el objetivo.**

| Receta | Alerces 2023 | Epuyén | Alerces 2024 | Patriada | Media GFS |
|---|---|---|---|---|---|
| ADJ 1,3 | 0,550 | 0,282 | 0,553 | 0,386 | 0,364 |
| + 30° | 0,569 | 0,291 | 0,558 | 0,367 | 0,366 |
| + 45° | 0,570 | 0,279 | 0,560 | … | … |
| + 60° | 0,565 | 0,263 | 0,558 | … | … |

Gana donde el fuego corre al sur (los valles de Los Alerces) y pierde en Patriada, donde el
día 1 fue al NE. El sesgo medio existe, pero su efecto sobre el Dice se cancela entre
incendios.

**Veredicto de la dirección:** el error de dirección del viento de superficie es real y
sistemático, pero con las perillas disponibles no se corrige de forma general. El atlas de
WindNinja es la única corrección con física que ayuda, y sólo en terreno empinado (loop 5).

### Loop 5 — la receta: ADJ uniforme, y qué tan lejos transfiere

**El ADJ que pide cada incendio** para llegar a sesgo 1 (interpolado entre base, 1,1, 1,2, 1,3,
1,4 y 1,6):

| Incendio | ADJ para sesgo 1 |
|---|---|
| Alerces 2016 | 1,00 |
| Alerces 2023 | 1,02 |
| Alerces 2024 | 1,32 |
| Patriada | 1,32 |
| Epuyén | 1,50 |
| Cholila | 1,53 |

Media geométrica: 1,26. No se correlaciona con la hora de ignición, el viento máximo ni el m1
mínimo del día 1 según el GFS. La dispersión (±20 %) está en lo que el GFS no ve.

**ADJ uniforme, sin alarmas en los seis incendios alcanzables:**

| ADJ | Alarmas | Dice GFS (media / mediana) | Dice ERA5 |
|---|---|---|---|
| 1,0 (base) | 2 | 0,302 / 0,340 | 0,339 |
| 1,1 | 0 | 0,330 / 0,358 | 0,345 |
| 1,2 | 0 | 0,347 / 0,374 | 0,356 |
| **1,3** | **0** | **0,364 / 0,386** | **0,365** |
| 1,4 | 2 | 0,378 / 0,404 | 0,375 |
| 1,6 | 3 | 0,403 / 0,440 | 0,403 |

A partir de 1,4, Alerces 2023 y Alerces 2016 pasan de sesgo 2: llegan al área observada a las
~50 h y siguen quemando.

**Validación cruzada.**

- Con todas las recetas v2 (incluidas las que alarman), el Dice fuera de muestra es 0,396.
  Pero al sacar Alerces 2023 se elige ADJ 1,6, que en él da sesgo 2,71; al sacar Epuyén se
  elige el −6, que en él da 2,08.
- **Alerces 2023 (pide lento) y Epuyén (pide rápido) acotan la receta.** Ningún factor global
  cubre a todos con seguridad fuera de muestra: el intervalo seguro es angosto ([1,1; 1,3]).
- Con las recetas v3 se elige `adj-130-001` en los cinco pliegues (fuera de muestra: media
  0,364, mediana 0,386).

**Receta elegida: `adj-130-001`.** Es el ADJ de PENDING_PARAMETERS §1.3, uniforme, en 1,3,
calibrado contra seis incendios. Mejora +20 % sobre base con GFS (0,302 → 0,364) y +8 % con ERA5
(0,339 → 0,365), sin alarmas. Lo que no hace:

- Mejorar la forma: 0,346 contra 0,302 de base, porque al llegar al área a tiempo cubre algo
  más de lo observado.
- Reproducir el día 1: sigue 10–50 veces por debajo en las primeras 12–24 h.

### Loop 5b — la receta sobre los casos de prueba (no usados para elegir)

| Incendio (prueba) | Composición de la cicatriz | `base-001` | `adj-130-001` | `humedad-m6-001` |
|---|---|---|---|---|
| Alerces 2015 (ERA5) | SH 45 %, TU 31 %, TL 24 % | 0,195 / 0,40 ⚠ | **0,230 / 1,01** | 0,370 / 2,46 ⚠ |
| Puerto Café (fase explosiva, `v2s`) | TU 61 %, SH 23 %, TL 15 % | 0,126 / 0,23 ⚠ | **0,179 / 0,34 ⚠** | 0,188 / 0,37 ⚠ |
| El Turbio 2025 | **GS3 82 %** | 0,356 / 4,55 ⚠ | 0,241 / 7,25 ⚠ | 0,225 / 7,88 ⚠ |
| Epuyén 2019 (ERA5) | SH 66 %, TU 18 % | 0,129 / 13,7 ⚠ | 0,114 / 16,0 ⚠ | 0,103 / 18,5 ⚠ |

**La receta transfiere dentro del régimen en que se calibró y falla fuera de él.**

- **Alerces 2015 y Puerto Café** son grandes incendios de montaña, en zona intangible o de
  acceso difícil, como los de calibración. ADJ 1,3 los mejora: Alerces 2015 queda con sesgo
  1,01; Café, +42 % de Dice.
  - Café sigue muy corto: la explosión del 6-ene (1.319 ha en 12 h, 5.619 ha a las 36 h) no
    aparece, y lo no predicho está al E, a 18 km. Es el mismo patrón del día 1 de la
    calibración.
- **El Turbio y Epuyén 2019 sobre-propagan ya con `base-001`** (sesgo 4,5 y 13,7). Son el
  otro régimen:
  - **Epuyén 2019:** 17.044 ha de falso positivo en la estepa plana al este (GR/SH, 4°,
    699 m). El incendio real (1.980 ha) se combatió con más de 200 brigadistas y aviones
    junto a Epuyén y la Ruta 40. Desde las 36 h el modelo ya va 2× por encima (1.602 contra
    812 ha): no es el horizonte, es la supresión, que ELMFIRE no modela.
  - **El Turbio:** el 82 % de la cicatriz es GS3, el "Remanente de disturbio reciente" con que
    CCS-BAP 2017 marca la cicatriz del complejo de 2015. El incendio de 2025 re-quemó ese
    rebrote de 10 años. Ardió lento (latente, por rayo, diez días hasta 2.000 ha, combatido
    por más de 110 personas), y el modelo corre por el GS3: 628 ha el primer día contra 100.
    **Hallazgo del crosswalk:** Rem Dist Rec → GS3 (PT-37 A2) describe un disturbio de 2 años,
    no uno de 10; con un mapa de 2017, la asignación envejece.
- **Test corregido en Puerto Café.** Con la semilla `firms` de toda la caja, el caso sembraba
  otros incendios activos al NE, y el modelo los propagaba: 21.718 ha de falso positivo a
  44 km, Dice 0,044. La semilla observada ahora toma sólo detecciones a menos de 1 km de la
  cicatriz objetivo (`radio_cicatriz_m`, protocolo `v2s`).

**Media en prueba:** `base-001` 0,202, `adj-130-001` 0,191. Mejora en 2 de 4 y empeora en 2 de 4.
El factor de velocidad que pide un incendio va de ~0,3 (El Turbio, Epuyén 2019) a ~1,5
(Epuyén 2025, Cholila): un rango de ~5×, mucho más ancho que el que vio la calibración
(1,0–1,5).

### Loop 5c — sensibilidad a la ignición (±500 m, ±2 h), con `adj-130-001`

| Incendio | Documentada | N 500 m | S 500 m | E 500 m | O 500 m | −2 h | +2 h |
|---|---|---|---|---|---|---|---|
| Alerces 2023 | 0,550 / 1,73 | 0,450 / 1,79 | 0,605 / 1,64 | 0,515 / 1,91 | 0,479 / 1,59 | 0,490 / **2,92** | 0,542 / 1,63 |
| Epuyén 2025 | 0,282 / 0,67 | 0,089 / 0,33 | 0,454 / 0,93 | **0,077 / 0,07** | 0,283 / 0,66 | 0,195 / 0,52 | 0,495 / 1,61 |
| Alerces 2016 | 0,400 / 1,72 | 0,371 / 1,79 | 0,460 / 2,05 | 0,274 / 2,19 | 0,515 / 1,24 | 0,455 / 0,77 | 0,376 / 1,89 |

- **La incertidumbre de la ignición pesa más que la calibración.**
  - Desplazar 500 m o 2 h mueve el Dice ±0,1–0,2 y el sesgo hasta 4×. En Epuyén el Dice va
    de 0,08 a 0,50.
  - Pasar de ADJ 1,0 a 1,3 mueve +0,06 de media.
  - Con seis incendios, la mejora de la receta es consistente en tendencia (+20 %), pero del
    orden de la incertidumbre de un solo caso.
- **Epuyén es el extremo, por lo heterogéneo del lugar:**
  - 500 m al E cae junto al lago, entre TL2 y agua, y el fuego casi no sale (sesgo 0,07).
  - 500 m al S cae sobre el arbustal (SH4) y escapa enseguida (0,454).
  - Es la misma trampa de la plantación del loop 2: el primer día lo decide el combustible de
    los primeros cientos de metros.
- **La hora importa por el ciclo diurno.** En Alerces 2023, prender 2 h antes (20 ART) le da
  al fuego la tarde del día siguiente con más frente, y el sesgo pasa de 1,73 a 2,92.
- **Consecuencia práctica:** para usar el sistema en pronóstico, la ignición tiene que
  ingresarse con la mejor precisión posible (coordenada del parte, no el centroide del
  satélite). Un ensamble sobre la incertidumbre de la ignición daría una banda más honesta que
  una sola corrida.

**Ensamble sobre la incertidumbre de la ignición.** Con las siete corridas de cada incendio
(documentada + seis perturbadas), la probabilidad de quema umbralizada en 0,5 (mayoría, sin
ajuste) da:

| Incendio | Ensamble | Documentada | Media de los miembros | Peor miembro |
|---|---|---|---|---|
| Alerces 2023 | 0,543 | 0,550 | 0,519 | 0,450 |
| Epuyén 2025 | 0,280 | 0,282 | 0,268 | 0,077 |
| Alerces 2016 | 0,400 | 0,400 | 0,407 | 0,273 |

No supera a la mejor estimación, pero elimina el riesgo del peor caso. Es la forma recomendable
de operar con una ignición incierta.

### Loop 6 — ¿qué le falta al día 1?

**H6: viento de valle subestimado, descartada.** Viento ×1,3 y ×1,6 sobre v3:

| Receta | Dice GFS (media) | Dice ERA5 (media) |
|---|---|---|
| base | 0,302 | 0,339 |
| viento ×1,3 | 0,328 | 0,308 |
| viento ×1,6 | 0,353 | 0,298 |
| ADJ 1,3 | 0,364 | 0,365 |

Área a las 24 h (predicho / observado, ha):

| Incendio | base | viento ×1,6 | ADJ 1,3 |
|---|---|---|---|
| Epuyén | 14 / 1.730 | 15 | 25 |
| Alerces 2024 | 49 / 851 | 57 | 76 |
| Patriada | 118 / 2.474 | 122 | 210 |
| Alerces 2016 | 102 / 1.241 | 154 | 228 |

60 % más de viento apenas mueve el día 1. La razón es física: al principio el fuego avanza bajo
dosel (TU/TL), donde ELMFIRE reduce el viento de 20 pies a media llama con un WAF de ~0,1–0,2,
así que más viento arriba casi no llega al combustible. El fuego real del día 1 corre por encima
del dosel (copa, pavesas), y eso no está en el modelo. **El déficit del día 1 no es de viento
medio.**

**H7: humedad del combustible vivo (LW) por debajo del umbral de grandes incendios.**

- `lw_moisture_pct` es un kwarg existente de `write_namelist`; no hay keyword nuevo.
- El valor de base, 110 %, sale de Bianchi y Defossé (2015). Pero en ese trabajo 110 % es el
  **umbral por debajo del cual ocurren los grandes incendios** en la Patagonia andina, no el
  valor de un día de gran incendio.
- Las medias de temporada son 110–220 % para ñire, ciprés, radal y laura, y menos de 100 % para
  la caña colihue.
- Simular grandes incendios con 110 % es tomar el borde húmedo. Un LW algo menor tiene
  criterio, a diferencia del −6 en m1.

| Receta | Dice GFS (media / mediana) | Epuyén | Alerces 2016 (ERA5) | Alarmas |
|---|---|---|---|---|
| LW 110 % (base) | 0,302 / 0,340 | 0,160 / 0,44 | 0,433 / 0,99 | 2 |
| LW 90 % | 0,375 / 0,456 | 0,331 / 1,02 | 0,461 / 2,14 ⚠ | 1 |
| LW 80 % | 0,403 / 0,452 | 0,437 / 1,65 | 0,447 / 2,94 ⚠ | 1 |

- LW actúa donde hay carga viva (SH, TU): Epuyén (54 % SH) responde mucho más que con ADJ.
- **No rescata el día 1** (Epuyén: 18 ha a las 24 h con LW 80 %, contra 14 ha de base). Acelera
  desde el día 2, ya en el arbustal. Es otra perilla de reloj, pero con respaldo en mediciones
  regionales.
- Alerces 2016 la limita: ya llega a tiempo con base, y con LW más seco se pasa.

**Loop 6d: LW + ADJ, la receta final.** LW actúa sobre la carga viva (SH, TU) y ADJ sobre la
velocidad base de todos los combustibles, así que se prueba si suman sin romper la
restricción. Con la receta única para todos, se evalúa sobre los siete incendios juntos:
`objetivo calibracion todas`, `validar todas`.

| Receta | Media / mediana (7) | Alarmas (sin el caso límite) | \|Δt*\| |
|---|---|---|---|
| **LW 100 % + ADJ 1,15** (`lw100-adj115-001`) | **0,372 / 0,411** | **0** (Alerces 2016: 1,95, al límite) | **39,8 h** |
| ADJ 1,3 (`adj-130-001`) | 0,364 / 0,386 | 0 | 69,5 h |
| LW 95 % | 0,359 / 0,443 | 0 | 54,9 h |
| LW 95 % + ADJ 1,1 | 0,382 / 0,436 | 1 (Alerces 2016: 2,27) | 40,8 h |
| LW 90 % | 0,377 / 0,456 | 1 (Alerces 2016: 2,14) | 42,9 h |
| LW 80 % | 0,400 / 0,447 | 1 (Alerces 2016: 2,94) | 32,6 h |

- **Validación cruzada sobre los siete:** se elige `lw100-adj115-001` en 5 de 7 pliegues.
  Fuera de muestra da media 0,364 y mediana 0,366.
- Al sacar Alerces 2016 se elige LW 80 %, que en él desborda (2,94). Como con ADJ solo, un
  incendio lento (Alerces 2016) y uno rápido (Epuyén) acotan la receta desde los dos lados.
- **Receta final: `lw100-adj115-001`.** Gana a ADJ 1,3 en media, mediana y |t* − horizonte|, y
  reparte la aceleración entre dos mecanismos con fundamento:
  - LW justo por debajo del umbral de grandes incendios;
  - un ADJ modesto.
- La ventaja sobre ADJ 1,3 es chica (+0,008 de media), menor que la incertidumbre de la
  ignición (§4, loop 5c).

## 5. Resultados

Dice / sesgo al horizonte contra la cicatriz (truncada al horizonte salvo en Las Golondrinas),
protocolos v2/v3 (pendiente corregida). ⚠ = sesgo fuera de [0,5×, 2×].

**Calibración** (se usaron para elegir):

| Incendio | Clima | `base-001` | `adj-130-001` | **`lw100-adj115-001`** | `humedad-m6-001` (mejor previa) |
|---|---|---|---|---|
| Alerces 2023 | GFS | 0,457 / 0,95 | 0,550 / 1,73 | **0,522 / 1,61** | 0,517 / 1,77 |
| Epuyén 2025 | GFS | 0,160 / 0,44 ⚠ | 0,282 / 0,67 | **0,291 / 0,83** | 0,471 / 2,08 ⚠ |
| Alerces 2024 | GFS | 0,522 / 0,53 | 0,553 / 0,98 | **0,555 / 1,02** | 0,558 / 1,09 |
| Patriada 2026 | GFS | 0,340 / 0,69 | 0,386 / 0,97 | **0,454 / 1,14** | 0,446 / 1,41 |
| Las Golondrinas 2021 (caso límite) | GFS | 0,029 / 0,05 ⚠ | 0,049 / 0,07 ⚠ | 0,047 / 0,06 ⚠ | 0,058 / 0,08 ⚠ |
| Alerces 2016 | ERA5 | 0,433 / 0,99 | 0,400 / 1,72 | **0,411 / 1,95** | 0,410 / 2,98 ⚠ |
| Cholila 2015 | ERA5 | 0,244 / 0,44 ⚠ | 0,329 / 0,71 | **0,324 / 0,66** | 0,393 / 0,74 |
| **Media GFS (5) / ERA5 (2)** | | 0,302 / 0,339 | 0,364 / 0,365 | **0,374 / 0,367** | 0,410 / 0,402 |
| **Media / mediana (los 7)** | | 0,312 / 0,340 | 0,364 / 0,386 | **0,372 / 0,411** | 0,408 / 0,446 |
| **Alarmas (sin el caso límite)** | | 2 | 0 | **0** | 3 |

**Prueba** (no se usaron para elegir):

| Incendio | Clima | `base-001` | `adj-130-001` | **`lw100-adj115-001`** | `humedad-m6-001` |
|---|---|---|---|---|
| Alerces 2015 | ERA5 | 0,195 / 0,40 ⚠ | 0,230 / 1,01 | **0,312 / 1,38** | 0,370 / 2,46 ⚠ |
| Puerto Café 2025 (`v2s`) | GFS | 0,126 / 0,23 ⚠ | 0,179 / 0,34 ⚠ | **0,167 / 0,32 ⚠** | 0,188 / 0,37 ⚠ |
| El Turbio 2025 | GFS | 0,356 / 4,55 ⚠ | 0,241 / 7,25 ⚠ | 0,256 / 6,75 ⚠ | 0,225 / 7,88 ⚠ |
| Epuyén 2019 | ERA5 | 0,129 / 13,7 ⚠ | 0,114 / 16,0 ⚠ | 0,112 / 16,8 ⚠ | 0,103 / 18,5 ⚠ |
| **Media / mediana** | | 0,202 / 0,162 | 0,191 / 0,205 | **0,212 / 0,211** | 0,221 / 0,206 |

**La mejor receta contra `base-001`: `lw100-adj115-001`** (LW 100 % + ADJ 1,15). Sube el Dice medio de calibración de 0,312 a 0,372 (+19 %), sin alarmas, y en prueba de 0,202 a 0,212. La primera candidata, `adj-130-001`, sube el Dice medio de calibración un 20 %
(GFS) y un 8 % (ERA5), y elimina las alarmas de sesgo en los seis incendios alcanzables. Lo
hace sólo con la perilla que PENDING_PARAMETERS reserva para esto, ADJ, y con el valor en el
centro de lo que pide cada incendio.

`humedad-m6-001` tiene más Dice, pero:

- viola la restricción (tres alarmas);
- no tiene soporte físico (m1 ≈ 1 %, cuando estaciones y Fosberg dan 5–7 %);
- en prueba no transfiere mejor: 0,222 contra 0,191, con el mismo patrón de alarmas.

**Qué parámetro movió cuánto, y por qué:**

| Cambio | Efecto sobre el Dice medio (calibración GFS) | Por qué |
|---|---|---|
| Corregir la orientación del terreno | **+0,03 a +0,13 por incendio** (el mayor) | El fuego subía ladera abajo; ahora sube la pendiente |
| ADJ 1,0 → 1,3 | +0,062 | Lleva cada incendio al área observada a tiempo; no cambia la forma |
| LW 110 → 100 % (con ADJ 1,15) | +0,008 sobre ADJ 1,3; mediana +0,025 | Acelera donde hay carga viva (SH/TU): Epuyén y Patriada. 110 % es el umbral de grandes incendios, no el valor del día |
| Viento ×1,3 / ×1,6 | +0,026 / +0,051 (GFS), peor con ERA5 | Bajo dosel, el WAF se come el viento: casi no mueve el día 1 |
| ADJ por grupo (SH, TU) | +0,03 a +0,06, con alarmas | No identificable: la velocidad no sigue a la composición |
| Humedad con criterio (Fosberg, altura) | ±0,01 | El m1 del GFS ya es el de las estaciones |
| Atlas de viento (WindNinja) | −0,011 GFS, +0,020 ERA5 | Ayuda en laderas empinadas (Alerces 2016, +0,07); neutro en valles |
| Rotación empírica del viento | +0,002 | El sesgo de dirección es real, pero su efecto se cancela entre incendios |
| Paso de tiempo a la mitad | +0,003 | Convergido |
| z0 desde el dosel | −0,02 | Doble conteo con el WAF de ELMFIRE |
| CBH × 0,25 | +0,004 | La copa sigue sin iniciarse: el freno es la superficie TL8 |

## 6. Parámetros

Veredictos por entrada de `PENDING_PARAMETERS.md`, para trasladar allá. 

| Entrada | Veredicto | Evidencia |
|---|---|---|
| §1.2 humedad muerta, m1 | **Con criterio: se queda Nelson con el GFS crudo; el delta uniforme no tiene soporte.** | Estaciones (El Bolsón, Esquel, Futaleufú) dan m1 de 5,9–6,6 % en las tardes de fuego; el GFS, 5,5–9,1 %. Las tablas de Fosberg (BehavePlus, llevadas al hemisferio sur) dan lo mismo o más húmedo que Nelson. `fosberg-001` y `altura-001` cambian el Dice en ±0,01. El −6 (m1 ≈ 1 %) es un acelerador que suple el fuego de copas y el viento de valle que faltan (§4, loop 2). |
| §1.2 humedad muerta, m10/m100 (+2/+5) | **Insensible.** | `humedad-m1-m6-001` (−6 sólo en m1) da 2/3 del efecto del −6 completo. El modelo de retardo baja m100 a ~11 % sin cambiar el resultado (`RESULTADOS.md` §8). |
| §1.3 ADJ | **Calibrado contra 6 incendios: 1,3 uniforme (intervalo sin alarmas [1,1; 1,3]).** Por grupo de combustible: **no identificable**. | Cada incendio pide entre 1,00 y 1,53 para llegar a sesgo 1 (media geométrica 1,26). 1,3 es el máximo sin alarmas y da +20 % de Dice (GFS) sobre 1,0. El ADJ por grupo (SH ×1,5–2,5, TU ×1,3) no sigue a la composición de las cicatrices: Alerces 2016 (52 % SH) no pide nada y Epuyén (54 % SH) pide 1,5. |
| §1.4 rugosidad z0 | **Se queda el escalar 0,22 m; el ráster de dosel duplica el WAF.** | z0 = 0,13 × altura del dosel baja el área de Alerces 2023 un 12 % (0,442 contra 0,457), porque reduce el viento bajo el bosque, donde ELMFIRE ya aplica su propio factor de reducción por dosel. En pastizal y matorral sube el viento apenas ~5 %. |
| §3 `dt_s` / `dtmax_s` | **Convergido: 30 s / 300 s quedan justificados.** | Con el paso a la mitad (15 s / 150 s), el Dice cambia +0,004 (Alerces 2023), +0,002 (Epuyén) y +0,003 (Alerces 2016), y el sesgo menos del 3 %. |
| §2 reconstrucción de perímetro | **Fuera de alcance de esta calibración.** | La semilla es puntual; los parámetros de §2 sólo pesan con semilla observada (harness A). |
| §1.6 humedad viva LW (hoy «resuelto» en 110 %) | **Reabrir: 110 % es el umbral de grandes incendios de Bianchi y Defossé (2015), no el valor de un día de gran incendio. Calibrado contra 7 incendios junto con ADJ: LW 100 % + ADJ 1,15.** | Con LW 90–95 %, los incendios dominados por arbustal alcanzan su área (Epuyén: 0,160 → 0,331) y la mediana de calibración sube de 0,340 a 0,45. Alerces 2016, que ya llega con base, limita el valor: con LW 90 % pasa a sesgo 2,14. El intervalo sin alarmas es [95; 110] %. LW no rescata el día 1: acelera desde el día 2, ya en el arbustal. |
| (nuevo) orientación del terreno | **Bug corregido** (`raster_aligner` v3). | Ver §4, loop 2. Con la pendiente bien, `base-001` pasa de 0,425 a 0,457 en Alerces 2023 y de 0,301 a 0,433 en Alerces 2016. |
| (nuevo) viento de superficie | **La dirección del GFS está sesgada ~+43° en la región, sin corrección general con estas herramientas.** | WindNinja (conservación de masa) es neutro en promedio: +7 puntos en Alerces 2016, −2 en Alerces 2023 y Patriada. La canalización por presión y la rotación empírica tampoco mejoran el objetivo (§4, loop 4). |
| (nuevo) dosel CBH | **El CBH no es lo que frena la copa.** | Con el CBH ×0,25, la copa sigue sin iniciarse: la superficie TL8 no da la intensidad (§4, loop 3). |

## 7. Para corregir afuera

### 7.1 Igniciones de mask-dataset-gen

| Incendio | Coordenada de mask-dataset-gen | Problema | Propuesta (con fuentes en el caso) |
|---|---|---|---|
| epuyen-2025 | -42,2921 / -71,4447 | 1.400 m, en la montaña, 490 m fuera de la cicatriz | -42,21516 / -71,4299 (junto al lago, 348 m) |
| los-alerces-2024 | -42,8036 / -71,5939 | 1.015 m, a media ladera, 1 km del Arroyo Centinela documentado y 1,3 km de las 1as detecciones | -42,80381 / -71,61425 (721 m, junto al arroyo y a la 1ª pasada) |
| puerto-patriada-2026 | -42,148083 / -71,534694 | 150 m fuera de la cicatriz | -42,14589 / -71,53471 |
| el-turbio-2025 | -42,2959 / -71,9356 | 60 m fuera de la cicatriz | -42,29621 / -71,93738 |
| las-golondrinas-2021 | -42,084 / -71,371 | centroide MODIS a 1.393 m, 7,9 km de las 1as detecciones; los focos documentados son dos | Las Golondrinas (-42,015 / -71,533) y Cerro Radal (-42,033 / -71,566), 15 h ART del 9-mar |
| cholila-2015 | -42,45 / -71,7333 | sobre el lago (NB8), 350 m fuera, 15 km de las 1as detecciones: es la coordenada del valle, no del foco | -42,48075 / -71,91938 (1ª detección VIIRS SP, nacientes del Río Tigre, 1.234 m) |
| epuyen-2019 | -42,2516 / -71,3243 | 90 m fuera de la cicatriz | -42,25161 / -71,32657 (La Rinconada, 519 m) |
| cerro-plataforma-2015 | -42,294 / -71,869 | centroide MODIS sobre NB, 297 m fuera | pendiente |
| currumahuida-2015 | -42,185 / -71,553 | centroide MODIS, 6,9 km de las 1as detecciones | pendiente |

### 7.2 Crosswalk y dosel (para el director)

- **Forest → TL8 (plantaciones de pino).**
  - En Epuyén 2025 la ignición cae en una plantación, y el modelo queda ~30 h atrapado en
    TL8/TU5 antes de llegar al arbustal. El incendio real cubrió 1.120 ha en 6 h, ardiendo en
    copa.
  - Ni siquiera con el CBH × 0,25 la copa se inicia: la hojarasca TL8 no da la intensidad
    superficial (§4, loops 2 y 3).
  - Para una plantación densa sin podar, un modelo de matorral o de hojarasca con arbustos
    (SH, TU) reproduciría mejor el primer día. Es la asignación a revisar con el director.
- **Rem Dist Rec → GS3 envejece.**
  - Con CCS-BAP 2017, la cicatriz del complejo de 2015 en el valle de El Turbio es "Remanente de
    disturbio reciente" (GS3).
  - El incendio de 2025 re-quemó ese rebrote de 10 años: ardió lento, y el modelo lo corre como
    pastizal-arbustal (sesgo 4,5; el 82 % de la cicatriz es GS3).
  - La asignación es correcta para un disturbio de 2 años y no para uno de 10. Con un mapa de
    2017, conviene decidir con qué modelo pasa el remanente a la clase de su vegetación actual.

### 7.3 Límites que ningún parámetro resuelve

- **Supresión.** Los incendios combatidos con éxito cerca de poblados y rutas (Epuyén 2019,
  El Turbio) sobre-propagan 4–14× sin que ninguna receta lo cambie. Los de calibración, en zonas
  de acceso difícil, sub-propagan.
  - El factor de velocidad que pide un incendio va de ~0,3 a ~1,5 (~5×).
  - ELMFIRE 2025.0212 tiene un módulo de supresión (`&SUPPRESSION`), pero `write_namelist` no
    lo expone y la regla es no agregar keywords. Queda como el trabajo futuro de mayor
    impacto.
- **El día 1 explosivo.** En cinco de siete incendios de calibración, el modelo va 10–50× por
  debajo en las primeras 12–24 h. Faltan las ráfagas de valle (Futaleufú: 3× el viento del
  GFS, con ráfagas de 75 km/h contra 15), la copa en plantaciones y las pavesas.
- **Dirección del viento de superficie.** El frente real corre en promedio ~43° más al sur que
  el empuje del GFS. Ni WindNinja (conservación de masa) ni la canalización por presión lo
  corrigen en general.
- **Ignición.** 500 m o 2 h de error cambian el Dice ±0,1–0,2 (Epuyén: de 0,08 a 0,50). La
  precisión de la ignición es un requisito del producto, no un detalle.

- **Clima de superficie:** el GFS de 0,25° es 4–6 °C más frío que la estación de valle y
  subestima el viento de la tarde (§4 H1).

### 7.4 Documentos que no edito y quedan afectados

- **`RESULTADOS.md` (§4–§8) e `IGN-26-VALIDACION.md` (harness A y B, benchmark):** todas las
  corridas usaron la orientación invertida (§4, loop 2), así que el fuego se empujaba ladera
  abajo.
  - Los órdenes entre mapas de combustible y las conclusiones de §8 hay que re-verificarlos
    con `raster_aligner` v3.
  - En particular, la frase de §8.4 "el modelo además quema ladera arriba hacia el oeste" se
    explica por el viento, no por la pendiente.
