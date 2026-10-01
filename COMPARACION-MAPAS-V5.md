# Comparación de los tres mapas de combustible sobre el benchmark v5

> 2026-09-30, rama `feat/auditoria-fisica`. Reemplaza, como evidencia de la Etapa B, la comparación
> de `RESULTADOS.md` (un incendio, 12 h, con los errores de interfaz de `AUDITORIA-FISICA.md`).
> Reproducir: `uv run python scripts/comparacion_mapas_v5.py [--recetas final|base]`.

## 1. Respuesta corta

Con la receta final (`lw-100-001`: LW 100 %, ADJ 1) y los mismos parámetros para los tres mapas,
sobre los 10 incendios del benchmark v5 que el modelo puede reproducir (sin Las Golondrinas, el
caso límite):

- **Contra WorldCover (baseline): CCS-BAP gana.** En los 6 incendios donde WorldCover es anterior
  al fuego (2021+), gana 5 y empata 1 (El Turbio): Dice medio 0,394 contra 0,090, mediana 0,432
  contra 0,054, diferencia mediana **+0,37** por incendio (test de signos p = 0,06). WorldCover
  pone el bosque en TL3, que casi no propaga: en cinco de los seis sub-predice 12 a 50 veces el
  área (sesgo 0,02–0,08). En los 4 incendios de 2015–2019 sólo hay un WorldCover posterior al
  fuego, que **ve la cicatriz** como pastizal o suelo desnudo (§6): ahí gana 1, pierde 2 y empata
  1. Con los 10: 6 / 2 / 2, Δ mediana +0,20, p = 0,29.
- **Contra MapBiomas: empate.** 4 / 5 / 1, Δ media +0,012, Δ mediana −0,015, p = 1. La
  diferencia cambia de signo con el período: en los 6 incendios 2021+ (GFS) CCS-BAP gana 4,
  pierde 1 y empata 1 (Δ media +0,059: 0,394 contra 0,335); en los 4 de 2015–2019 (ERA5) pierde
  los cuatro (Δ media −0,058). A área igualada (la forma, sin la velocidad) el empate es más
  claro: 4 / 4 / 2, Δ media −0,012.
- **El día 1 sí separa a CCS-BAP de MapBiomas:** gana 8 de 10 (p = 0,04) contra el incremento
  FIRMS, porque propaga más rápido en un día que los dos mapas sub-predicen.
- **Con la base sin calibrar (LW 110 %) el cuadro se sostiene** (§7): contra WorldCover, 6 de 6 en
  los incendios 2021+ (p = 0,03); contra MapBiomas, 5 / 4 / 1 (Δ media +0,008). La ventaja sobre
  MapBiomas en los incendios recientes no la crea la calibración.
- **Separando calibración de prueba:** en calibración (6) CCS-BAP lidera (0,443 contra 0,395 de
  MapBiomas y 0,135 de WorldCover), pero LW 100 % se eligió con CCS-BAP sobre esos mismos
  incendios. En prueba (4) no gana: 0,213 contra 0,254 (MapBiomas) y 0,233 (WorldCover, con
  fuga en dos de los cuatro).

La afirmación que sostienen los datos es **"CCS-BAP predice mucho mejor que WorldCover cuando
la comparación es limpia, y tan bien como MapBiomas"**, no "mejor que los dos". Con 10
incendios, sólo dos contrastes son significativos al 5 %: el día 1 contra MapBiomas (receta final)
y WorldCover en los incendios 2021+ con la base (6 de 6).

## 2. Método

### 2.1 Casos: el paquete v5 más dos mapas

Once protocolos `-v5m` (`calibracion-v5m`, `calibracion-era5-v5m`, `calibracion-v5m-h54` en
Alerces 2023 y `calibracion-v5ms` en Café), uno por caso de `benchmarks/particion.json`. Se
empaquetan con un empaquetador nuevo, `ampliar_mapas` (`scripts/benchmark.py`), que **copia el
paquete v5 por hash** (semilla, ventanas, clima, dosel, atlas, referencias) y sólo agrega los
mapas. Así lo único que cambia entre las iteraciones de un mismo incendio es `fbfm40.tif`:

- cada mapa se recorta a la caja del caso y se exige que quede en la grilla exacta del `dem` del
  paquete (forma, transformación y CRS), o el empaquetado falla;
- el CCS-BAP recortado de nuevo tiene que dar el mismo hash que el del v5 (lo dio en los once);
- `lw-100-001` sobre v5m da **TOA, intensidad y velocidad idénticos por hash** a `lw-100-001`
  sobre v5 en los 11 incendios y todas sus ventanas (difieren sólo `fire_size_stats.csv` y el
  `.dbf` de las isócronas, que llevan tiempos y fechas de la corrida).

### 2.2 Mapas

Los tres con `scripts/build_fuel_maps.py`: el crosswalk de cada producto (`fuels_builder`), la
misma agregación por moda a 30 m y el mismo relleno del hueco fronterizo (lado chileno y, para
CCS-BAP, fuera de Chubut) **con WorldCover 2021**, igual que el CCS-BAP de los paquetes v5.

- **Grilla del AOI** (`benchmark-aoi-asp3-v5`, 4.333 × 2.591): los mapas de `data/static/fuel_maps`
  (WorldCover 2021, MapBiomas 2022 y 2024 ya estaban, con la clave de caché vigente) más MapBiomas
  2023, nuevo.
- **Grilla extendida** (`benchmark-2026-09-28-asp3-v5`, 4.897 × 2.885; Las Golondrinas y los cuatro
  ERA5): `data/static/fuel_maps/benchmark-2026-09-28/`, construida sobre el `dem` de esa
  preparación. WorldCover 2021 y CCS-BAP 2017 reconstruidos ahí salen **byte a byte iguales** a
  los de la preparación, así que el procedimiento es el mismo.
- **MapBiomas 2014, 2015, 2018, 2020 y 2023** se bajaron del COG público de la Colección 2
  (`data/raw/mapbiomas/mapbiomas_<año>_aoi.tif`, ventana de la grilla extendida más 0,02°, que
  cubre también la del AOI). Relleno: 13,7–13,9 % de la grilla extendida y 9,2 % de la del AOI.
- **WorldCover 2020** (v100) se bajó de las teselas públicas de ESA
  (`data/raw/worldcover/esa_worldcover_v100_2020_10m.tif`, misma caja que el v200 local). Misma
  leyenda que v200, mismo crosswalk.
- **Cobertura:** cada mapa se construye sobre la grilla de su preparación, así que la cubre por
  construcción; las ventanas crudas de MapBiomas cubren la grilla con margen. Dentro de las
  cicatrices, ni CCS-BAP ni MapBiomas coinciden celda a celda con WorldCover (0–1 %): el relleno
  no entra en la comparación.

### 2.3 Regla temporal

| Incendio | Año | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|---|
| Alerces 2023 | 2023 | 2017 | 2021 | 2022 |
| Epuyén 2025 | 2025 | 2017 | 2021 | 2024 |
| Alerces 2024 | 2024 | 2017 | 2021 | 2023 |
| Patriada 2026 | 2026 | 2017 | 2021 | 2024 |
| Las Golondrinas (límite) | 2021 | 2017 | 2020 | 2020 |
| Alerces 2016 | 2016 | 2013 | **2020 ‡** | 2015 |
| Cholila 2015 | 2015 | 2013 | **2020 ‡** | 2014 |
| El Turbio 2025 | 2025 | 2017 | 2021 | 2024 |
| Puerto Café 2025 | 2025 | 2017 | 2021 | 2024 |
| Epuyén 2019 | 2019 | 2017 | **2020 ‡** | 2018 |
| Alerces 2015 | 2015 | 2013 | **2020 ‡** | 2014 |

Todos los años los resuelve `"anio": "anterior_al_fuego"` (`definiciones.ANIOS_COMBUSTIBLE`).
WorldCover empieza en 2020: para los cuatro incendios de 2015–2019 no hay mapa anterior.
**Decisión:** correrlo igual, como baseline congelado, con **el primer año publicado (2020)**, el
más cercano al fuego, y reportarlo aparte. Es una excepción declarada en la receta
(`"sin_anterior": "primero_publicado"`), y la iteración queda marcada con `fuga_temporal` en sus
factores (‡). Sin esa declaración, `anterior_al_fuego` sigue rechazando el caso.

Nótese que el CCS-BAP es el mapa **más viejo** en los incendios recientes (2017 contra
2021–2024: 6 a 9 años antes del fuego), y MapBiomas siempre el más nuevo (un año antes).

### 2.4 Recetas: los mismos parámetros para los tres mapas

| | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|
| **Final** (LW 100 %, ADJ 1) | `lw-100-001` | `lw-100-worldcover-001` | `lw-100-mapbiomas-001` |
| **Base** (LW 110 %, ADJ 1) | `base-001` | `fuels-worldcover-002` | `fuels-mapbiomas-001` |

Las recetas nuevas tienen padre (`lw-100-001` y `fuels-worldcover-001`) y motivo. Sólo cambia el
combustible. **LW 100 % se calibró para CCS-BAP** (AUDITORIA-FISICA, loop E), sobre los siete
incendios de calibración: los otros dos mapas corren con un parámetro que no se eligió para
ellos. Por eso la base (LW 110 %, el valor de la literatura, sin calibrar) se reporta como
sensibilidad (§5) y la partición de prueba pesa más que la de calibración.

### 2.5 Métricas

Las del benchmark (IGN-26 §Benchmark), sin cambios: **Dice contra la cicatriz en la última
ventana** (truncada al horizonte), **sesgo de área** (predicho / observado; ⚠ fuera de
[0,5; 2]) y **forma** (Dice a área igualada: en la hora en que lo predicho alcanza el área
observada, o al final si no la alcanza). El **día 1** es la ventana 0 contra el incremento FIRMS.
Diferencias apareadas por incendio (CCS-BAP menos el otro); empate si |Δ| < 0,005; test de signos
exacto, bilateral, sin los empates.

**Las Golondrinas queda fuera de los resúmenes:** es el caso límite de la partición (la ráfaga
nocturna no está en el GFS) y ningún mapa pasa de 0,012.

**Cholila con WorldCover 2020 no arranca:** la semilla (9 celdas) cae entera en NB3 (suelo
desnudo); ELMFIRE no propaga, no deja TOA y `correr` aborta. Se cuenta como lo que predice el
modelo: nada (Dice 0, sesgo 0). WorldCover 2021 pone GR2 en esas mismas celdas, así que es efecto
del producto 2020, cinco años después del incendio (§6).

## 3. Resultados con la receta final

Dice / sesgo / forma. ⚠ sesgo fuera de [0,5; 2]; ‡ WorldCover posterior al fuego.

| Incendio | Conjunto | Clima | CCS-BAP | WorldCover | MapBiomas | Gana |
|---|---|---|---|---|---|---|
| Alerces 2023 | calibración | GFS | **0,496** / 1,83 / 0,427 | 0,100 / 0,08 ⚠ / 0,100 | 0,375 / 0,55 / 0,375 | CCS-BAP |
| Epuyén 2025 | calibración | GFS | **0,500** / 1,75 / 0,429 | 0,059 / 0,06 ⚠ / 0,059 | 0,297 / 0,87 / 0,297 | CCS-BAP |
| Alerces 2024 | calibración | GFS | **0,562** / 1,54 / 0,527 | 0,048 / 0,03 ⚠ / 0,048 | 0,507 / 0,93 / 0,507 | CCS-BAP |
| Patriada 2026 | calibración | GFS | 0,368 / 0,90 / 0,368 | 0,021 / 0,02 ⚠ / 0,021 | **0,371** / 0,41 ⚠ / 0,371 | empate CCS–MB |
| Alerces 2016 | calibración | ERA5 | 0,451 / 1,33 / 0,473 | **0,581** / 2,12 ⚠ / 0,640 ‡ | 0,512 / 1,11 / 0,521 | WorldCover ‡ |
| Cholila 2015 | calibración | ERA5 | 0,280 / 0,55 / 0,280 | 0 (no arranca) ‡ | **0,307** / 0,46 ⚠ / 0,307 | MapBiomas |
| El Turbio 2025 | prueba | GFS | 0,296 / 5,73 ⚠ / 0,154 | 0,292 / 1,87 / 0,154 | **0,337** / 1,99 / 0,275 | MapBiomas |
| Puerto Café 2025 | prueba | GFS | **0,144** / 0,29 ⚠ / 0,144 | 0,021 / 0,08 ⚠ / 0,021 | 0,125 / 0,24 ⚠ / 0,125 | CCS-BAP |
| Epuyén 2019 | prueba | ERA5 | 0,114 / 16,5 ⚠ / 0,236 | 0,114 / 16,5 ⚠ / 0,390 ‡ | **0,207** / 8,63 ⚠ / 0,388 | MapBiomas |
| Alerces 2015 | prueba | ERA5 | 0,298 / 1,49 / 0,281 | **0,504** / 2,68 ⚠ / 0,411 ‡ | 0,347 / 1,62 / 0,276 | WorldCover ‡ |
| *Las Golondrinas (límite)* | calibración | GFS | 0,012 / 0,02 ⚠ | 0,007 / 0,01 ⚠ | 0,009 / 0,01 ⚠ | — |

**Medias y medianas de Dice** (sin el límite):

| Subconjunto | n | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|---|
| Todos | 10 | **0,351** / 0,333 | 0,174 / 0,080 | 0,339 / **0,342** |
| Calibración | 6 | **0,443 / 0,474** | 0,135 / 0,054 | 0,395 / 0,373 |
| Prueba | 4 | 0,213 / 0,220 | 0,233 / 0,203 | **0,254 / 0,272** |
| GFS = 2021+ = sin fuga | 6 | **0,394 / 0,432** | 0,090 / 0,054 | 0,335 / 0,354 |
| ERA5 = 2015–2019 = con fuga | 4 | 0,286 / 0,289 | 0,300 / 0,309 | **0,343 / 0,327** |

**Diferencias apareadas, CCS-BAP menos el otro** (gana / pierde / empata; p del test de signos;
Δ media / Δ mediana):

| Subconjunto | Contra WorldCover, Dice | Contra MapBiomas, Dice | Contra MapBiomas, forma |
|---|---|---|---|
| Todos (10) | 6 / 2 / 2; p 0,29; +0,177 / +0,201 | 4 / 5 / 1; p 1; +0,012 / −0,015 | 4 / 4 / 2; p 1; −0,012 / +0,001 |
| Calibración (6) | 5 / 1 / 0; p 0,22; +0,308 / +0,371 | 3 / 2 / 1; p 1; +0,048 / +0,026 | 3 / 2 / 1; p 1; +0,021 / +0,008 |
| Prueba (4) | 1 / 1 / 2; p 1; −0,020 / +0,002 | 1 / 3 / 0; p 0,63; −0,041 / −0,045 | 1 / 2 / 1; p 1; −0,062 / −0,058 |
| GFS, 2021+ (6) | **5 / 0 / 1; p 0,06; +0,304 / +0,371** | 4 / 1 / 1; p 0,38; +0,059 / +0,037 | 4 / 1 / 1; p 0,38; +0,017 / +0,020 |
| ERA5, 2015–2019 (4) | 1 / 2 / 1; p 1; −0,014 / −0,065 | 0 / 4 / 0; p 0,13; −0,058 / −0,055 | 0 / 3 / 1; p 0,25; −0,056 / −0,038 |

Contra WorldCover, la forma da lo mismo que el Dice en los incendios 2021+ (5 / 0 / 1, +0,274
de media): con WorldCover el fuego casi no crece, así que el área igualada nunca se alcanza.

Lectura por incendio:

- **Los cuatro de calibración GFS:** CCS-BAP gana a WorldCover por 0,35–0,52 y a MapBiomas en tres
  (+0,06 a +0,20). En Patriada empatan en Dice, pero MapBiomas sub-propaga (sesgo 0,41) y
  CCS-BAP no (0,90).
- **CCS-BAP sobre-propaga donde MapBiomas sub-propaga.** En los GFS de calibración, sesgo 0,90–1,83
  contra 0,41–0,93. A área igualada la diferencia con MapBiomas se achica (Δ forma +0,017 contra
  +0,059 en Dice en los 2021+): buena parte de la ventaja de CCS-BAP es **velocidad**, no
  ubicación. Con LW 100 % calibrado para él, eso es esperable.
- **El Turbio (prueba)** es supresión: CCS-BAP sobre-propaga 5,7× por el GS3 del rebrote de la
  cicatriz de 2015 (`Rem Dist Rec`); WorldCover (GR2) y MapBiomas (SH4) quedan en 1,9–2,0×.
  MapBiomas gana también en forma (0,275 contra 0,154 de los otros dos).
- **Café (prueba)**, la explosión que nadie reproduce: los tres sub-predicen; CCS-BAP un poco menos.
- **Los ERA5 (2015–2019)** los gana siempre otro mapa. Contra MapBiomas, por 0,03–0,09. Contra
  WorldCover, por la fuga (§6).

## 4. Dónde se diferencian

Por grupo de combustible **de CCS-BAP** dentro de la cicatriz (última ventana), aciertos /
sobrantes en ha, sumados por grupo de incendios:

**2021+ (GFS, sin fuga; Alerces 2023, Epuyén 2025, Alerces 2024, Patriada, El Turbio, Café)**

| Grupo CCS-BAP | Observado | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|---|
| SH (arbustal) | 6.965 | **3.130** / 5.259 | 117 / 522 | 1.979 / 2.140 |
| TU (bosque con sotobosque) | 9.963 | **2.501** / 3.126 | 216 / 226 | 1.512 / 1.989 |
| TL (hojarasca) | 3.003 | **1.102** / 2.336 | 77 / 175 | 795 / 1.188 |
| GS (pastizal-arbustal) | 1.267 | **1.267** / 3.651 | 394 / 987 | 591 / 867 |
| GR (pastizal) | 361 | 178 / 1.654 | 9 / 189 | 111 / 460 |
| NB | 158 | 0 / 0 | 7 / 220 | 17 / 139 |

**2015–2019 (ERA5, con fuga de WorldCover)**

| Grupo CCS-BAP | Observado | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|---|
| SH | 4.122 | 1.834 / 12.147 | **2.032** / 12.134 | 1.878 / 7.092 |
| TU | 4.749 | **1.512** / 4.525 | 893 / 3.651 | 1.469 / 2.603 |
| TL | 1.655 | 526 / 1.275 | 597 / 1.431 | **679** / 1.159 |
| GR | 210 | 113 / 7.466 | 113 / 7.082 | 117 / 2.948 |

(El sobrante de los ERA5 lo domina Epuyén 2019, que los tres sobre-propagan 9–17×.)

Con el combustible de cada mapa (`benchmark.py analizar`, `analisis.json` de cada iteración):

- **WorldCover** deja sin predecir sobre todo su TL3: 871 de 998 ha en Alerces 2023, 2.439 de
  2.621 en Alerces 2024, 4.574 de 5.664 en Patriada, 8.481 de 8.731 en Café. Es el hallazgo del
  audit original (TL3 casi no propaga) medido en seis incendios.
- **MapBiomas** deja sin predecir sobre todo su TU5 ("bosque cerrado"): 1.247 de 1.375 ha en
  Alerces 2024, 2.723 de 4.224 en Patriada, 7.192 de 8.147 en Café. Su arbustal (SH4/SH9) sí
  propaga.
- **CCS-BAP** acierta más en arbustal (SH: 3.130 contra 1.979 ha de MapBiomas en los 2021+) y en
  bosque con sotobosque (TU: 2.501 contra 1.512), pero sobra el doble. La ganancia está en el
  arbustal y en el bosque que CCS-BAP separa por especie (TU3/TU5/TL6) donde MapBiomas pone un
  solo TU5.

## 5. Día 1

Ventana 0 contra el incremento FIRMS: Dice / sesgo / ha predichas.

| Incendio | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|
| Alerces 2023 | **0,255** / 0,61 / 474 | 0,048 / 0,04 / 30 | 0,128 / 0,20 / 159 |
| Epuyén 2025 | **0,112** / 0,06 / 172 | 0,008 / 0,00 / 12 | 0,029 / 0,01 / 43 |
| Alerces 2024 | **0,183** / 0,10 / 134 | 0,008 / 0,00 / 5 | 0,112 / 0,06 / 77 |
| Patriada 2026 | **0,039** / 0,02 / 114 | 0,003 / 0,00 / 9 | 0,024 / 0,01 / 70 |
| Alerces 2016 ‡ | 0,096 / 0,05 / 105 | **0,413** / 0,26 / 525 | 0,084 / 0,04 / 92 |
| Cholila 2015 ‡ | **0,570** / 1,37 / 377 | 0 / 0 / 0 | 0,545 / 1,39 / 379 |
| El Turbio 2025 | **0,583** / 2,11 / 974 | 0,270 / 0,17 / 77 | 0,526 / 0,36 / 167 |
| Puerto Café 2025 | **0,084** / 0,14 / 481 | 0,014 / 0,06 / 186 | 0,055 / 0,10 / 335 |
| Epuyén 2019 ‡ | 0,211 / 1,16 / 923 | **0,289** / 3,15 / 2.523 | 0,286 / 0,49 / 381 |
| Alerces 2015 ‡ | 0,109 / 0,08 / 121 | **0,348** / 0,57 / 833 | 0,107 / 0,08 / 120 |

- **Contra MapBiomas: gana 8, pierde 1, empata 1 (p = 0,04, Δ media +0,035).** El único contraste
  significativo. El día 1 todos sub-predicen (el límite del día explosivo, AUDITORIA-FISICA §7.3),
  y CCS-BAP sub-predice menos: 1,4 a 5,8 veces más área que MapBiomas en los GFS.
- **Contra WorldCover: 7 / 3 / 0 (p = 0,34)**; las tres derrotas son incendios con fuga, donde
  WorldCover 2020 pone pastizal en la cicatriz. En los seis 2021+, CCS-BAP gana los seis.

## 6. La fuga temporal de WorldCover, medida

¿El mapa "ve" la cicatriz? Porcentaje de pastizal + no combustible (GR + NB) dentro de la
cicatriz y en un anillo de 2 km alrededor. Un mapa anterior al fuego pone menos GR/NB adentro
(el fuego eligió la vegetación); uno que ve la cicatriz quemada, más.

| Incendio | Año | CCS-BAP (año) | WorldCover (año) | MapBiomas (año) |
|---|---|---|---|---|
| Alerces 2023 | 2023 | 3 / 24 (2017) | 13 / 45 (2021) | 3 / 27 (2022) |
| Epuyén 2025 | 2025 | 5 / 27 (2017) | 24 / 42 (2021) | 16 / 36 (2024) |
| Alerces 2024 | 2024 | 0 / 33 (2017) | 7 / 41 (2021) | 1 / 31 (2023) |
| Patriada 2026 | 2026 | 4 / 34 (2017) | 18 / 56 (2021) | 12 / 44 (2024) |
| El Turbio 2025 | 2025 | 0 / 23 (2017) | 66 / 54 (2021) | 20 / 37 (2024) |
| Puerto Café 2025 | 2025 | 1 / 42 (2017) | 3 / 46 (2021) | 3 / 47 (2024) |
| **Alerces 2016** | 2016 | 2 / 25 (2013) | **95 / 50 (2020)** | 13 / 39 (2015) |
| **Cholila 2015** | 2015 | 2 / 41 (2013) | **96 / 66 (2020)** | 14 / 50 (2014) |
| **Epuyén 2019** | 2019 | 7 / 30 (2017) | **86 / 71 (2020)** | 22 / 21 (2018) |
| **Alerces 2015** | 2015 | 1 / 43 (2013) | **80 / 61 (2020)** | 12 / 51 (2014) |

- En los cuatro incendios con fuga, WorldCover 2020 pone **80–96 % de GR/NB dentro de la
  cicatriz** contra 50–71 % alrededor: la ve. Ningún mapa anterior al fuego hace eso (CCS-BAP 0–7 %
  adentro, MapBiomas 1–22 %).
- La fuga **favorece a WorldCover** donde la cicatriz quedó como pastizal: GR2 propaga rápido
  justo donde está lo observado. Es lo que le da Alerces 2016 (0,581, con 1.131 ha sobrantes en
  su GR) y Alerces 2015 (0,504, 1.403 ha en GR). Y lo **perjudica** donde quedó como suelo
  desnudo: Cholila no arranca.
- El Turbio es el caso inverso y sin fuga: WorldCover 2021 ve la cicatriz *anterior* (2015) como
  pastizal (66 % adentro); el incendio de 2025 re-quemó ese rebrote.
- Por eso **las victorias de WorldCover en 2015–2019 no cuentan como evidencia contra CCS-BAP**, y
  la comparación limpia con el baseline son los seis incendios 2021+.

## 7. Sensibilidad: la base sin calibrar (LW 110 %)

`base-001`, `fuels-worldcover-002` y `fuels-mapbiomas-001`: LW 110 %, el valor de la literatura
(Bianchi y Defossé), sin calibrar para ningún mapa. `base-001` sobre v5m también da TOA idéntico a
v5 en los 11 incendios. Dice / sesgo:

| Incendio | CCS-BAP | WorldCover | MapBiomas |
|---|---|---|---|
| Alerces 2023 | **0,461** / 1,55 | 0,100 / 0,08 ⚠ | 0,333 / 0,44 ⚠ |
| Epuyén 2025 | **0,466** / 1,30 | 0,059 / 0,06 ⚠ | 0,262 / 0,69 |
| Alerces 2024 | **0,555** / 1,37 | 0,048 / 0,03 ⚠ | 0,508 / 0,81 |
| Patriada 2026 | 0,321 / 0,74 | 0,021 / 0,02 ⚠ | **0,358** / 0,35 ⚠ |
| Alerces 2016 | 0,444 / 1,05 | **0,581** / 2,12 ⚠ ‡ | 0,506 / 0,97 |
| Cholila 2015 | **0,255** / 0,44 ⚠ | 0 (no arranca) ‡ | 0,252 / 0,38 ⚠ |
| El Turbio 2025 | **0,333** / 4,97 ⚠ | 0,292 / 1,87 | 0,299 / 1,85 |
| Puerto Café 2025 | **0,128** / 0,25 ⚠ | 0,021 / 0,08 ⚠ | 0,118 / 0,23 ⚠ |
| Epuyén 2019 | 0,122 / 15,0 ⚠ | 0,114 / 16,5 ⚠ ‡ | **0,310** / 5,34 ⚠ |
| Alerces 2015 | 0,255 / 0,96 | **0,504** / 2,68 ⚠ ‡ | 0,321 / 1,44 |

| Subconjunto | Contra WorldCover, Dice | Contra MapBiomas, Dice | Contra MapBiomas, forma |
|---|---|---|---|
| Todos (10) | 8 / 2 / 0; p 0,11; +0,160 / +0,181 | 5 / 4 / 1; p 1; +0,008 / +0,007 | 4 / 5 / 1; p 1; −0,015 / −0,002 |
| Calibración (6) | 5 / 1 / 0; p 0,22; +0,282 / +0,330 | 3 / 2 / 1; p 1; +0,048 / +0,026 | 3 / 2 / 1; p 1; +0,029 / +0,015 |
| Prueba (4) | 3 / 1 / 0; p 0,63; −0,023 / +0,024 | 2 / 2 / 0; p 1; −0,052 / −0,028 | 1 / 3 / 0; p 0,63; −0,082 / −0,064 |
| GFS, 2021+ (6) | **6 / 0 / 0; p 0,03; +0,287 / +0,330** | 5 / 1 / 0; p 0,22; +0,065 / +0,041 | 4 / 2 / 0; p 0,69; +0,021 / +0,018 |
| ERA5, 2015–2019 (4) | 2 / 2 / 0; p 1; −0,031 / −0,064 | 0 / 3 / 1; p 0,25; −0,078 / −0,064 | 0 / 3 / 1; p 0,25; −0,069 / −0,036 |

Medias de Dice (todos / calibración / prueba): CCS-BAP 0,334 / 0,417 / 0,210; WorldCover 0,174 /
0,135 / 0,233; MapBiomas 0,327 / 0,370 / 0,262. Día 1: CCS-BAP gana a MapBiomas 7 / 2 / 1 (p
0,18) y a WorldCover 7 / 3 / 0.

- **WorldCover da exactamente lo mismo con LW 110 y 100 %:** su mapa es casi todo TL3 y GR2, sin
  carga leñosa viva (LW sólo cambia la leñosa; LH es igual en las dos), y su 3 % de SH5 no está en
  el camino de ningún fuego. La humedad viva no puede rescatar al baseline.
- **La calibración no fabricó la ventaja sobre MapBiomas:** sin calibrar, CCS-BAP le saca lo mismo
  en calibración (+0,048 de media en las dos recetas) y algo más en los 2021+ (+0,065 contra
  +0,059). LW 100 % acelera a los dos mapas patagónicos (los dos tienen SH y TU), no sólo a
  CCS-BAP.
- **El patrón por período es el mismo:** CCS-BAP adelante en 2021+ (5 / 1), atrás en 2015–2019
  (0 / 3 / 1).

## 8. Salvedades

1. **n = 10, y casi nada es significativo.** Contra WorldCover en los 2021+: 5 / 0 / 1 con la
   receta final (p 0,06) y 6 / 0 / 0 con la base (p 0,03); contra MapBiomas, sólo el día 1 con la
   receta final (p 0,04). Los resultados se leen como
   dirección y magnitud, no como prueba estadística.
2. **Clima, período y fuga están confundidos.** Los seis GFS son exactamente los seis 2021+ sin
   fuga, y los cuatro ERA5, los cuatro 2015–2019 con fuga. Que CCS-BAP pierda contra MapBiomas en
   los ERA5 puede ser el clima (ERA5 propaga ~20 % menos, AUDITORIA-FISICA §7.1), el mapa 2013 de
   CCS-BAP, la cercanía de MapBiomas al fuego (un año) o los incendios: con estos casos no se
   separa.
3. **La receta se calibró con CCS-BAP.** LW 100 % se eligió con CCS-BAP en los siete incendios
   de calibración; los otros mapas corren con un parámetro ajeno. La base sin calibrar (§7) da la
   misma ventaja sobre MapBiomas en calibración (+0,048), así que el sesgo de la calibración es
   chico. Pero en prueba CCS-BAP no gana con ninguna de las dos recetas (0,213 y 0,210 contra
   0,254 y 0,262 de MapBiomas).
4. **Buena parte de la ventaja sobre MapBiomas es velocidad.** CCS-BAP sobre-propaga (sesgo hasta
   1,8 en calibración) y MapBiomas sub-propaga; a área igualada quedan casi iguales (Δ forma
   −0,012 en los 10). Otro LW para MapBiomas podría cerrar la diferencia de Dice.
5. **Los límites del modelo pesan más que el mapa en la mitad de los casos.** Supresión (El Turbio,
   Epuyén 2019: 2–17× de sobre-propagación en los tres mapas), el día explosivo (Café), la ráfaga
   nocturna (Las Golondrinas). Ahí la diferencia entre mapas es ruido sobre un error grande.
6. **El relleno fronterizo es WorldCover 2021 para los tres**, también en los incendios 2015–2019
   (fuga en el relleno). No toca ninguna cicatriz (§2.2).
7. **Trece iteraciones quedaron marcadas `sucio`:** corrieron mientras se commiteaban
   `definiciones.py`, `benchmark.py` (`ampliar_mapas`, la guarda de `analizar`) y
   `comparacion_mapas_v5.py`. Lo que había sin commitear en cada caso es exactamente lo que entró
   en el commit siguiente (`0aede37`, `2529a88`, `35ab1cb`), y sólo `definiciones.py` toca el camino
   de la corrida (resuelve el año del mapa, que cada manifiesto registra en sus factores). Las cuatro de CCS-BAP (tres de `lw-100-001`, una de `base-001`) dan TOA idéntico a v5
   (§2.1, §7). Las nueve de WorldCover y MapBiomas no se re-verificaron (`benchmark.py verificar`
   corre ELMFIRE fuera de la cola).

## 9. Conclusión

- **CCS-BAP con el crosswalk de IGN-20B predice mucho mejor que WorldCover**: en los seis incendios
  donde la comparación es limpia gana cinco y empata uno, con un Dice mediano de 0,43 contra
  0,05. WorldCover no es un baseline débil por casualidad: modela el bosque como TL3 y el fuego no
  avanza (sesgo 0,02–0,08 en cinco de los seis). Es el hallazgo central de la Etapa B, ahora sobre seis incendios y con
  la interfaz corregida.
- **Contra MapBiomas, empate.** CCS-BAP gana en los incendios recientes (4–1–1, +0,06) y en el
  día 1 (8 de 10), pierde los cuatro de 2015–2019, y a área igualada son iguales. Lo que CCS-BAP
  agrega sobre MapBiomas es velocidad en arbustal y bosque mixto (SH, TU), no una mejor ubicación
  del fuego; y su mapa es de 2017, contra uno de un año antes del fuego.
- Para la tesis, la formulación defendible es: **un mapa patagónico (CCS-BAP o MapBiomas) es
  imprescindible; entre los dos, CCS-BAP no es peor y es más rápido el día 1**. "Mejor que
  MapBiomas" no está demostrado con estos once incendios.

## 10. Reproducir

```bash
# Mapas (grilla extendida y del AOI)
uv run python scripts/build_fuel_maps.py --reference data/elmfire/inputs/benchmark-2026-09-28-asp3-v5/dem.tif \
    --out-dir data/static/fuel_maps/benchmark-2026-09-28 --mapbiomas-years 2014 2015 2018 2020 2023 --worldcover-2020
uv run python scripts/build_fuel_maps.py --mapbiomas-years 2022 2023 2024
# Casos (por la cola, nunca en paralelo: data/benchmark/trabajos.txt)
uv run python scripts/benchmark.py empaquetar <incendio>/<protocolo-v5m>
#   <incendio>/<protocolo-v5m> lw-100-001 lw-100-worldcover-001 lw-100-mapbiomas-001
#   <incendio>/<protocolo-v5m> base-001 fuels-worldcover-002 fuels-mapbiomas-001
uv run python scripts/benchmark.py analizar <incendio>/<protocolo-v5m> <recetas …>
uv run python scripts/comparacion_mapas_v5.py --recetas final
uv run python scripts/comparacion_mapas_v5.py --recetas base
```
