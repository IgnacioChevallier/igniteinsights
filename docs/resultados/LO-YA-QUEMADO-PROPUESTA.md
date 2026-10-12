# Lo ya quemado: propuesta para la app

> Corte: 2026-10-11; resultado de LYQ-1 el 2026-10-12 (§9). Responde a `RIESGOS_Y_SUPOSICIONES.md` §5 (lo ya quemado) y §6 (ingesta
> histórica de FIRMS). Es una propuesta: no cambia código ni `modelo-v0`. Todos los números de
> los §3 y §4 salen de diagnósticos sin ELMFIRE sobre los paquetes `-p` de **calibración** (v6 +
> Hansen `lossyear`). No se abrió ningún resultado del conjunto de prueba.

## Resumen

- **El hueco es más chico de lo que se suponía.** El Hansen que usa la app
  (`Hansen_GFC-2025-v1.13`) ya trae la pérdida de 2025: 3.742 ha en el AOI. El hueco real son
  las quemas de 2026 en adelante. Además, Hansen ve sólo pérdida de **dosel**: no ve las quemas
  de matorral ni de estepa.
- **Lo que hoy falta en la app no es el dosel, es el combustible.** Sobre el bosque del mapa
  CCS-BAP 2017 hay unas **11.600 ha con pérdida de Hansen posterior a 2017** (2018–2025). La app
  ya les quita el dosel, pero les deja el combustible del bosque previo. Las quemas de 2026, como
  Patriada o Los Alerces 2026, no tienen ni eso.
- **Por qué falló el antecedente del loop M.** Reasignó *toda* la pérdida desde 2001 a SH3/SH2,
  sin mirar la edad ni la clase del mapa. En Patriada, el 21 % de la cicatriz es pérdida de 6–15
  años (quemas de 2012 y 2015). El mapa de 2017 ya la veía como matorral SH4/SH3, y esa pérdida
  ardió a 3,7× la tasa del resto del dominio. El loop M frenó justo la etapa más inflamable y
  pisó un mapa que ya la había visto.
- **Regla propuesta.** Sólo se reasignan las quemas **posteriores al año del mapa**:
  - de 0–2 años: GR1;
  - de 3–5 años: el bosque pasa a GS3;
  - de 6–15 años: el bosque pasa a SH3.

  Las clases de matorral y pastizal no se tocan después de los 2 años, y nada se reasigna
  después de los 15. En los casos de calibración cambia como mucho el 0,3 % de una cicatriz
  (Patriada: 16 ha, contra ~1.300 ha del loop M).
- **El benchmark no puede validarla, sólo mostrar que no rompe nada.** En calibración, modelo-v0
  quema como mucho 27 ha sobre esas celdas. Se propone un protocolo de no regresión con una única
  variante congelada de antemano, más una prueba de la premisa con incendios que no están en el
  benchmark.
- **FIRMS de archivo.** Hoy SP cubre hasta el 2026-06-30 y NRT desde el 2026-07-01, sin
  solaparse. Sumar las fuentes SP a la ingesta de la app arregla las fechas viejas con un cambio
  de ~5 líneas.

## 1. Fuentes de cicatrices recientes

| Fuente | Qué ve | Resolución | Cobertura y latencia | Licencia | Cómo se ingiere | Uso propuesto |
|---|---|---|---|---|---|---|
| **Hansen GFC v1.13 `lossyear`** (ya en la app) | Pérdida de dosel que reemplaza al rodal, sea cual sea la causa: también cosecha de plantaciones y volteo | 30 m | 2001–2025. Una versión por año: la pérdida de 2026 recién llegaría con la v1.14 | CC BY 4.0 | Ya está: `download_hansen_lossyear` → `settings.hansen_lossyear_path` | **Paso 1**, sin datos nuevos |
| **dNBR del benchmark** (`../mask-dataset-gen`) | Cicatriz de cada evento, atribuida con VIIRS | 20 m (S2) / 30 m (L8) | Sólo los 14 eventos configurados. Cada uno es un run manual en Earth Engine | Copernicus / USGS, abiertos | Exportar las máscaras `event-filter-*` vigentes con el año del evento a una grilla del AOI | Relleno de alta resolución para esos 14 eventos |
| **MODIS MCD64A1 v061** | Área quemada mensual, con fecha de quema y cualquier vegetación | ~463 m | Desde 2000-11. El 2026-10-11, FIRMS lista `BA_MODIS` hasta 2026-07-01: ~3 meses de latencia | Datos NASA, sin restricción | GEE `MODIS/061/MCD64A1` o LP DAAC; un script offline que escriba el año de quema | **Paso 2**: quemas de 2026 y quemas no forestales |
| **VIIRS VNP64A1** | Ídem, sucesor de MODIS | 500 m | FIRMS lista `BA_VIIRS` desde 2012-03 hasta 2026-07-01 | Datos NASA | Ídem | Reemplazo de MCD64A1 cuando MODIS termine |
| **FIRMS SP / NRT** (ya en la app) | Focos activos (puntos), no área | 375 m | NRT: horas. SP: ~3 meses (hoy hasta 2026-06-30) | Datos NASA | Ya está; reconstruir perímetros como `ignition_builder` | Opcional: quemas de la temporada en curso |
| **Copernicus Burnt Area 300 m** (v3.1/v4) | Área quemada diaria (Sentinel-3 OLCI/SLSTR + focos VIIRS) | 300 m | Al día siguiente de la toma. **No se verificó** desde qué año cubre | Copernicus, abierta | Descarga de CLMS | Alternativa a FIRMS para la temporada en curso |
| **MapBiomas Argentina, Fuego** | Área quemada anual y mensual desde 1998, según el sitio | 30 m (Landsat) | Una colección por año. **No se verificó** si cubre el bosque andino-patagónico ni hasta qué año llega | CC BY 4.0 | Asset de GEE o descarga | Candidata a reemplazar el paso 2 si cubre el AOI |
| **Registros oficiales** (SNMF, APN, CIEFAP, Bosques de Chubut) | El SNMF publica partes con superficie, sin polígonos públicos. Un informe regional cita una cartografía de polígonos de CIEFAP (GPS e imágenes, mínimo 5 ha) | — | — | — | Pedido formal a CIEFAP (Esquel) o a la Dirección de Bosques de Chubut | Validación, si se consigue |

Lectura:

- **Ninguna fuente sola alcanza.** Hansen es fina pero sólo ve bosque, y no distingue quema de
  cosecha. MCD64A1 ve cualquier vegetación pero engorda los bordes y omite fuegos chicos: en
  `mask-dataset-gen` confirma el 81–90 % de las máscaras. El dNBR es el mejor, pero sólo existe
  para 14 eventos.
- **Combinación propuesta:** una capa de año de quema con la misma codificación que `lossyear`
  (0 = sin quema, n = 2000 + n), con la quema más reciente por celda. Se arma con Hansen ∪ dNBR
  de los eventos ∪ MCD64A1. MCD64A1 entra sólo donde no hay dato fino y, en bosque, sólo para
  años que Hansen todavía no publicó (ver §2, severidad).
- **La ventana pre del dNBR no se toca.** Una capa del AOI completo sería un tipo de run nuevo en
  `mask-dataset-gen`, con sus reglas: run nuevo, `--dry-run` primero y cuota de Earth Engine. Las
  ventanas de los runs existentes quedan como están.

## 2. Combustible después del fuego en la Patagonia norte

**Lo que dice la literatura, por edad de la cicatriz**

| Edad | Bosque previo (lenga, coihue, ciprés, alerce, pino) | Matorral y ñire previos | Fuente |
|---|---|---|---|
| 0–2 años | Ceniza, fustes en pie y rebrote incipiente: carga fina muy baja. El fuego se propaga mal | Rebrote de raíz rápido, pero todavía ralo | PT-37 modelo A2: los entreparches amplios (17 m² en promedio) "dificultan la continuidad horizontal del fuego"; loop L (`docs/resultados/AUDITORIA-FISICA.md`) |
| 3–5 años | Pastizal-arbustal de rebrote; la carga fina sube | Los rebrotadores recuperan su estructura: realimentación neutra | PT-37 A2: 0,82 t/ha de fino, ≈ GS3 (crosswalk §5.7); Tiribelli et al. 2018; `DECISIONES-MODELO-V0.md` §4 |
| 6–15 años | Matorral rebrotante continuo de 2–3 m, **más inflamable que el bosque que reemplazó**. Más carga fina cerca del suelo y un microclima más cálido y seco | Matorral maduro: el que ya describe el mapa | Paritsis, Veblen y Holz 2015 (14–29 años después); Landesmann et al. 2021 (18 años); Kitzberger et al. 2016 |
| > 15 años | Matorral estable (un estado alternativo) o bosque en recuperación lenta. El mapa vigente lo ve | — | Paritsis et al. 2015; Blackhall et al. 2017 (16 años) |

**Matices por tipo de vegetación**

- **Lenga.** Muy sensible al fuego y de regeneración lenta. Quemada con severidad, pasa a ñire y
  matorral, que arden más que el bosque original (Paritsis et al. 2015).
- **Coihue y ciprés.** Dependen de la semilla de árboles sobrevivientes. Con fuego de severidad
  moderada o alta pasan a matorral rebrotante (Landesmann et al. 2021).
- **Ñire y matorral.** Son rebrotadores: recuperan su inflamabilidad en pocos años (Tiribelli et
  al. 2018, realimentación neutra). Reasignarlos a un modelo *más lento* después de los 2 años
  contradice la literatura. Ese fue el error del loop M (§3).
- **Severidad.** Con fuego de baja severidad el bosque se recupera y es menos inflamable que el
  matorral (Landesmann et al. 2021). Por eso la regla exige pérdida que reemplace al rodal
  (Hansen, o dNBR alto) para reasignar bosque, y no la reasigna con MCD64A1 solo cuando ya hay
  Hansen publicado para ese año.
- **Pino.** *Pinus contorta* es muy inflamable y aumenta la continuidad vertical del combustible
  (Cóbar-Carranza et al. 2014). Una regeneración densa de pino de 6–15 años podría arder más que
  SH3. No hay modelo medido: queda como incertidumbre declarada.

**¿Cuándo una cicatriz casi no arde, y cuándo arde más que el bosque?**

- **Casi no arde:** en los primeros 1–2 años, sobre todo después de un fuego severo en bosque.
- **Arde más que el bosque:** a partir de los ~5 años, cuando el bosque sensible fue reemplazado
  por matorral rebrotante. Es la realimentación positiva que documentan Paritsis, Tiribelli,
  Landesmann y Kitzberger.

**Antecedente técnico.** LANDFIRE ajusta sus modelos de combustible por disturbio
(`FDist`/`FDistADD`) con tres tramos de edad (1 año, 2–5 y 6–10 años) y tres de severidad. Los
disturbios de más de 10 años no se representan: el mapa de vegetación vuelve a mandar. La regla
de abajo sigue esa misma estructura.

## 3. Por qué falló el antecedente en Patriada

**Qué hizo el loop M** (`lw100-perdsh3-001` / `lw100-perdsh2-001`). Puso
`combustible_perdida_reciente: {"anios": 30}`: toda la pérdida desde 2001 a SH3 (143) o SH2
(142), sin importar la edad ni lo que decía el mapa. Patriada cayó de 0,496 a 0,334 y 0,233, con
alarma.

**Qué había en esa pérdida.** Diagnóstico sobre `puerto-patriada-2026/calibracion-v6-p`:

| Edad de la pérdida | Dentro de la cicatriz | Mapa 2017 en esas celdas | Fracción quemada (dominio: 0,035) |
|---|---|---|---|
| 0–2 años | 5 ha | TU5, SH8, SH4 | 0,002 |
| 3–5 años | 8 ha | TL8, TU5 | 0,001 |
| **6–15 años** (2012: 868 ha; 2015: 313 ha) | **1.202 ha (21 % de la cicatriz)** | **SH4 750, SH3 317**, TU5 91, GR2 24 | **0,129** |
| > 15 años | 98 ha | SH4 59, TU5 30 | 0,099 |

- **La pérdida de 6–15 años ardió a 3,7× la tasa del dominio.** En el anillo de 300 m alrededor
  de la cicatriz, esa pérdida es el 27 % de anillo + cicatriz, contra el 41 % de todo el anillo:
  el fuego entró de más ahí. Es la realimentación positiva del §2.
- **CCS-BAP 2017 ya la veía como matorral** (SH4 y el remanente SH3). El loop M la bajó de SH4 a
  SH3 o SH2. Según Scott y Burgan (2005), SH4 propaga rápido y SH3 lento; SH2 es todavía más
  lento.
- **Conclusión:** el loop M frenó la etapa más inflamable y contradijo a un mapa posterior al
  fuego que la había clasificado bien.

**La regla por edad lo evita de dos maneras:**

1. **Sólo reasigna quemas posteriores al año del mapa.** Las de 2012 y 2015 están en CCS-BAP
   2017, así que no se tocan.
2. **Después de los 2 años, nunca reasigna matorral ni pastizal**, sólo bosque (TL/TU). Un SH4
   sigue siendo SH4.

En la cicatriz de Patriada, la regla cambia **16 ha** (0,3 %); el loop M cambiaba ~1.313 ha.

## 4. Regla de reasignación propuesta

**Dónde se aplica:** en las celdas con año de quema `a` tal que `año del mapa < a < año de la
simulación`. Para Hansen, `a ≤ año de la simulación − 1`, la misma condición que ya usa
`derive_cbh_cbd`. Las fuentes con fecha (dNBR, MCD64A1) pueden incluir quemas de la temporada en
curso si terminaron antes del inicio de la ventana. La edad es `año de la simulación − a`.

| Edad | Bosque (TL 181–189, TU 161–165) | Matorral, pastizal-arbustal y pastizal (SH, GS, GR) | No combustible (NB) | Dosel |
|---|---|---|---|---|
| 0–2 años | **GR1 (101)** | **GR1 (101)** | sin cambio | ninguno (cc = ch = 0) |
| 3–5 años | **GS3 (123)** | mapa | sin cambio | ninguno |
| 6–15 años | **SH3 (143)** | mapa | sin cambio | ninguno |
| > 15 años | mapa | mapa | sin cambio | el de hoy |

Fundamento por fila:

- **0–2 → GR1, pastizal ralo.** La carga fina es mínima (PT-37 A2; Landesmann et al. 2021). Se
  prefiere GR1 a NB9:
  - con fuentes de 500 m, un NB9 metería barreras falsas sobre las islas sin quemar;
  - el loop L midió NB9 a 1 año y GR1 a 2 años sin diferencia en calibración (+0,000).

  En calibración, las cicatrices de 0–2 años quedan en el borde del incendio y no adentro:
  - Alerces 2023: 88 % de esa pérdida en el anillo, contra 42 % de base;
  - Alerces 2016: 100 % contra 42 %;
  - Patriada: 65 % contra 41 %.

  Son pocas hectáreas (10–53 ha) y se leen como indicio, no como prueba.
- **3–5 → GS3, sólo en bosque.** Es el análogo medido de la PT-37 (A2, regeneración de ñire
  post-fuego). `DECISIONES-MODELO-V0.md` §4 ya establece que GS3 describe bien los 2–5 años. El
  matorral rebrotante conserva su clase (Tiribelli et al. 2018).
- **6–15 → SH3, sólo en bosque.** Es la misma decisión que tomó modelo-v0 para el remanente de
  disturbio de CCS-BAP de 6–15 años (`DECISIONES-MODELO-V0.md` §4; Tiribelli et al. 2018;
  Blackhall et al. 2017). Aplicarla a las quemas que el mapa no alcanzó a ver la vuelve
  coherente: no es una perilla nueva.
- **> 15 → el mapa.** Igual que LANDFIRE, y en la app no se da hasta que haya un mapa más nuevo
  que CCS-BAP 2017 que quede viejo.
- **Las quemas que el mapa ya vio no se tocan.** El mapa es la verdad para lo que observó. Si un
  bosque quemado sigue clasificado como bosque, lo más probable es que haya sido un fuego de baja
  severidad (Landesmann et al. 2021).
- **Severidad.** Para reasignar bosque hace falta pérdida de Hansen o dNBR de severidad
  moderada-alta. MCD64A1 alcanza sólo para no bosque, o para bosque en años que Hansen todavía no
  publicó (hoy, 2026).

**Códigos.** 101, 123, 143 y 99 están en `app/elmfire/fuel_models.csv`. La regla sólo cambia
valores de `fbfm40.tif`, `cc` y `ch`: ninguna keyword ni archivo nuevo para ELMFIRE.

**Lo que no se propone:**

- tramos por especie: no hay cargas medidas que los distingan;
- reasignar las quemas que ya están en el mapa;
- cualquier cambio a modelo-v0 o a sus paquetes.

## 5. Cambios de código en la app

Pasos independientes, del más barato al más caro.

### Paso 0 — FIRMS de archivo (chico y separado)

Ver §8.

### Paso 1 — Regla de combustible con Hansen (sin datos nuevos)

1. **`app/elmfire/builder/fuels_builder.py`**
   - Agregar `CCSBAP_ANIO_MAPA = 2017`. Hoy sólo está implícito en `CCSBAP_SOURCE_ID`; MapBiomas
     sería 2024.
   - Agregar una función pura,
     `reasignar_por_edad_de_quema(fbfm40, anio_quema, anio_simulacion, anio_mapa) -> np.ndarray`,
     con la tabla del §4 como dict `COMBUSTIBLE_POR_EDAD_QUEMA`. Al final llama a
     `assert_codes_are_defined`.
   - No va dentro de `ccsbap_to_fbfm40`: el caché es por fuente y la regla depende del año de la
     simulación. Por lo mismo, **no** se sube `DERIVATION_VERSION`.
2. **`app/preparation/service.py`, `run_preparation`**
   - Calcular `anio_simulacion = (gfs_at or fires_until or datetime.now(UTC)).year` una sola vez.
     Hoy esa expresión está inline en la llamada a `derive_cbh_cbd`.
   - Mover la reproyección de `lossyear` (hoy en el bloque de cbh/cbd) antes del paso 2.
   - Después de `shutil.copy2(fbfm_cached, inputs_dir / "fbfm40.tif")`, reescribir
     `inputs_dir/fbfm40.tif` con la regla.
   - Decidir qué muestra el dashboard: hoy copia a `static_dir/fbfm40.tif` el mapa cacheado sin
     la regla. Se propone que muestre el efectivo.
   - Agregar a `warnings` las hectáreas reasignadas por tramo, para que quede auditable en la
     respuesta.
3. **`app/elmfire/builder/canopy_builder.py`, `derive_cbh_cbd`**: sin cambios de lógica. Ya saca
   el dosel en toda la pérdida previa.
4. **`tests/test_fuels_reasignacion.py`** (nuevo, sintético, sin red):
   - TU5 con quema de 1 año pasa a GR1;
   - SH4 con quema de 8 años no cambia;
   - una quema del año del mapa o anterior no cambia;
   - una quema de 20 años no cambia;
   - la salida sólo trae códigos de `fuel_models.csv`.
5. **Benchmark** (para medir; no cambia modelo-v0):
   - en `app/validation/cadena.py`, una perilla `combustible_por_edad_quema` que llame a la
     **misma** función de `fuels_builder`, con `anio_mapa` según el mapa del caso (2013 o 2017);
   - una receta `benchmarks/recetas/lw100-quema-edad-001.json` (padre `lw-100-001`);
   - los paquetes `-p` ya traen `lossyear.tif`: no hay que empaquetar nada.

### Paso 2 — Capa de año de quema combinada (quemas de 2026 y quemas no forestales)

1. **`scripts/preparar_cicatrices.py`** (nuevo, offline, una vez por temporada, en abril). Escribe
   `data/raw/cicatrices/anio_quema_aoi.tif` en la grilla de Hansen, con su codificación, tomando
   la quema más reciente por celda de:
   - Hansen `lossyear`;
   - las máscaras dNBR vigentes de `../mask-dataset-gen` (año = `fire_start_date`);
   - MCD64A1 o VNP64A1 (año de `BurnDate`), exportado de Earth Engine con la cuenta del repo
     hermano, sólo donde no hay dato fino.

   Guarda en un JSON al lado qué fuente aportó cada año.
2. **`app/config.py`**: `cicatrices_path`, opcional como `hansen_lossyear_path`. Si falta, se
   usa Hansen y se avisa en `warnings`.
3. **`app/preparation/service.py`**: preferir `cicatrices_path` sobre `hansen_lossyear_path`
   tanto en la regla como en `derive_cbh_cbd`. Es la misma interfaz (año por celda), así que
   `canopy_builder` no cambia.

### Paso 3 (opcional) — La temporada en curso

Marcar con GR1 los perímetros reconstruidos de detecciones FIRMS de incendios **anteriores** de
la misma temporada (más de 7 días antes de la ventana y fuera del perímetro del incendio que se
simula), o usar Copernicus BA 300 m.

`ponytail:` se deja afuera hasta que haga falta. Con 375 m de buffer engorda los bordes, y un
incendio que se reactiva podría confundirse con otro.

## 6. Plan de medición sin violar la regla de parada

**Qué se puede medir y qué no.** La regla toca muy poco de las cicatrices de calibración:

| Caso de calibración | Quemas no mapeadas en bosque dentro del dominio | En la cicatriz | Que modelo-v0 quema hoy |
|---|---|---|---|
| Alerces 2023 (h54) | 33 ha | 2 ha | 3 ha |
| Epuyén 2025 | 4.222 ha (sobre todo 2021, 3–5 años) | 6 ha | 10 ha |
| Alerces 2024 | 782 ha (la quema de 2023, 1 año) | 0 ha | 0 ha |
| Patriada 2026 | 6.314 ha (sobre todo 2021, 3–5 años) | 16 ha | 18 ha |
| Las Golondrinas (límite) | 96 ha | 15 ha | 0 ha |
| Alerces 2016 (mapa 2013) | 491 ha (la quema de 2015, 1 año) | 0 ha | 27 ha (todo falso positivo) |
| Cholila 2015 (mapa 2013) | 44 ha | 7 ha | 7 ha |

Los incendios reales casi no llegaron a esas quemas, y la simulación tampoco. **El efecto
esperado sobre el Dice de calibración es ≈ 0**, así que el benchmark no puede decir si la regla
es buena. Sólo puede decir que no rompe nada. La justificación es la literatura y la prueba de la
premisa (punto 3).

**Protocolo LYQ-1.** Se fija completo antes de correr y se corre una vez.

1. **Congelar.**
   - La regla es la tabla del §4: sin variantes ni barrido.
   - La fuente es Hansen v1.13 (paso 1).
   - La receta es `lw100-quema-edad-001` sobre `lw-100-001`.
2. **No regresión en calibración**: los 7 casos `-p`, un ELMFIRE por vez y con colas que esperan
   marcadores en los logs. Pasa si se cumplen las tres condiciones, fijadas antes:
   - ninguna alarma nueva (sin contar el caso límite);
   - |Δ media| ≤ 0,01 y |Δ mediana| ≤ 0,01;
   - ningún caso pierde más de 0,02.

   Si pasa, se adopta **en la app**. Si no pasa, no se adopta y se documenta. En ningún caso se
   prueba otra variante con estos datos.
3. **Prueba de la premisa, sin ELMFIRE y fuera del benchmark.**
   - Para cada incendio del AOI de 2016–2026 en MCD64A1 o en el dNBR, medir el contacto con las
     cicatrices previas por tramo de edad: la proporción de quema previa en un anillo de 300 m
     contra la que hay dentro del incendio, frente a la proporción de base.
   - Se excluyen los 4 incendios de prueba.
   - Hipótesis fijadas antes: con 0–2 años, anillo > base (la quema frena); con 6–15 años,
     anillo < base (la quema atrae).
   - Los números de este documento (Alerces 2023, Alerces 2016, Patriada) son exploratorios, con
     pocas hectáreas, y no cuentan como esa prueba.
4. **Humo de la app.** Una preparación con fecha 2026-10-11 (sin correr ELMFIRE), reportando la
   distribución de `fbfm40` sobre las cicatrices de Alerces 2023, Alerces 2024 y Epuyén 2025.
5. **Prueba, al final y sólo descriptiva.** Por construcción, la regla no toca la cicatriz de
   2015 en El Turbio: CCS-BAP 2017 ya la mapea como remanente.

**Por qué no viola la regla de parada:**

- no se re-elige la receta: `lw-100-001` y sus paquetes quedan iguales;
- hay una sola variante, fijada antes;
- el criterio es de no regresión, no de mejora;
- la prueba no participa.

Lo que cambia es la app, en una situación que el benchmark no puede ejercitar: mapa de 2017 y
simulación de 2026.

## 7. Riesgos

1. **Hansen no es fuego.** Su `lossyear` incluye cosecha de plantaciones (TL8) y volteo. Cholila
   2015 tiene 137 ha de pérdida de 2013 *dentro* de la cicatriz, de causa desconocida. Con la
   restricción al año del mapa no entra en el benchmark, pero en la app un raleo de 2019 pasaría
   a SH3.
   - Mitigación: en TL8, exigir confirmación de fuego (MCD64A1 o FIRMS) en el paso 2.
2. **Más rápido que el bosque.** GR1, GS3 y SH3 sin dosel reciben viento abierto (WAF ~0,4),
   mientras el bosque con dosel recibe ~0,08 (`DECISIONES-MODELO-V0.md` §1). Una quema de 3–5
   años en GS3 puede propagar más rápido que el TU5 que reemplaza. Es lo que dice la literatura,
   pero en la app puede generar falsos positivos.
   - Ejemplo: las 4.758 ha de la quema de 2021 en el dominio de Patriada.
3. **La resolución de MCD64A1.** Las celdas de 500 m engordan los bordes y borran las islas sin
   quemar. Por eso entra sólo como relleno, y nunca con NB9.
4. **La severidad es incierta.** Sin dNBR, la pérdida de Hansen es el único indicador de que el
   rodal fue reemplazado. Un fuego de superficie en bosque no se reasigna, y eso es lo correcto
   según Landesmann et al. (2021).
5. **Las fechas.** Hansen es anual: una quema de diciembre puede caer en la versión del año
   siguiente. Las quemas de la misma temporada sólo entran con fuentes fechadas.
6. **El pino.** No hay un modelo medido para la regeneración densa de *P. contorta* después del
   fuego. SH3 podría quedarse corto.
7. **No validable con el benchmark.** El protocolo sólo garantiza que no rompe la calibración. La
   mejora sobre la app no está medida: se apoya en la literatura y en la prueba de la premisa.
8. **Dos mapas a la vista.** Si el dashboard sigue mostrando el mapa cacheado, el usuario no ve el
   combustible con el que corrió la simulación (§5, paso 1.2).

## 8. Arreglo de FIRMS de archivo (paso separado)

**Situación.** `run_firms_ingestion` (`app/ingestion/satellite/firms/service.py`) llama a
`fetch_active_fires` sin `sources`, así que usa `FIRMS_SOURCES`, que son sólo los productos NRT.
`FIRMS_SOURCES_ARCHIVE` existe pero sólo lo usa `scripts/benchmark.py`.

**Disponibilidad hoy** (`/api/data_availability/csv/<MAP_KEY>/ALL`, 2026-10-11):

| Fuente | Desde | Hasta |
|---|---|---|
| VIIRS_SNPP_SP | 2012-01-20 | 2026-06-30 |
| VIIRS_NOAA20_SP | 2018-04-01 | 2026-06-30 |
| VIIRS_SNPP_NRT / VIIRS_NOAA20_NRT | 2026-07-01 | 2026-10-11 |
| VIIRS_NOAA21_NRT (sin SP) | 2024-01-17 | 2026-10-11 |

Lo que muestra la tabla:

- SP y NRT no se solapan: NRT empieza el día después de que termina SP.
- Para una fecha vieja, la app sólo puede recibir NOAA-21, y sólo desde el 2024-01-17. No se
  verificó por qué el loop M recibió 0 detecciones para enero de 2024: NOAA-21 debería cubrir el
  25 de enero.

**Cambio propuesto** (~5 líneas, sin llamar a `data_availability`):

1. En `service.py`, pedir `sources=FIRMS_SOURCES + FIRMS_SOURCES_ARCHIVE`. Las SP devuelven
   vacío para fechas recientes, a un costo de dos requests más.
2. Para la transición, cuando FIRMS publica un mes SP nuevo: en `client.py`, por satélite,
   descartar las filas NRT con `acq_date` ≤ la última fecha SP recibida de ese satélite. No se
   deduplica por coordenadas, porque el reprocesamiento SP mueve los puntos.
3. Renombrar el CSV crudo `viirs_nrt_los_alerces.csv` a `viirs_los_alerces.csv`.
4. Agregar una prueba chica del filtro del punto 2, con DataFrames sintéticos.

El benchmark no cambia: pasa `sources` explícitas. El normalizador acepta la confianza `n`/`h`,
que los productos SP también usan.

## 9. Resultado del protocolo LYQ-1 (2026-10-12)

**Implementado** en `feat/lo-ya-quemado`, commit `547cd10`:

- **la regla** (`fuels_builder.reassign_burns_by_age` / `reassign_burns_in_raster`), con
  `COVER_MAP_YEAR` por fuente;
- **la preparación de la app**: la reasignación va sobre la copia de la preparación y el
  dashboard muestra el mapa efectivo; la respuesta trae `burns_reassigned_ha`;
- **la perilla `combustible_por_edad_quema`** en `cadena.py` y `definiciones.py`, y la receta
  `lw100-quema-edad-001`;
- **FIRMS**: SP + NRT, con `drop_nrt_covered_by_sp`;
- **las pruebas** `tests/test_burn_age_fuels.py` y `tests/test_firms_sources.py`.

`make check` pasa.

**No regresión en calibración.** `lw100-quema-edad-001` sobre los `-p` contra `lw-100-001` sobre
v6, que es el mismo paquete byte a byte sin `lossyear`:

| Incendio | `lw-100-001` (Dice / sesgo) | `lw100-quema-edad-001` (Dice / sesgo) | Δ Dice |
|---|---|---|---|
| Alerces 2023 (h54) | 0,528 / 1,86 | 0,522 / 1,84 | −0,006 |
| Epuyén 2025 | 0,501 / 1,41 | 0,501 / 1,41 | 0,000 |
| Alerces 2024 | 0,635 / 1,35 | 0,635 / 1,35 | 0,000 |
| Patriada 2026 | 0,496 / 0,70 | 0,505 / 0,71 | +0,009 |
| Las Golondrinas (límite) | 0,012 / 0,02 | 0,012 / 0,02 | 0,000 |
| Alerces 2016 | 0,389 / 1,69 | 0,391 / 1,68 | +0,002 |
| Cholila 2015 | 0,513 / 0,87 | 0,514 / 0,87 | +0,001 |
| **Media / mediana** | **0,439 / 0,501** | **0,440 / 0,505** | **+0,001 / +0,004** |

**Criterios fijados en el §6: los tres se cumplen.**

- No aparece ninguna alarma nueva: sólo sigue la del caso límite, y el sesgo máximo es 1,84.
- |Δ media| = 0,001 y |Δ mediana| = 0,004, los dos ≤ 0,01.
- La peor pérdida por caso es Alerces 2023, con −0,006, por debajo de 0,02.

**Decisión: se adopta en la app.** modelo-v0 no cambia. Como se esperaba en el §6, el benchmark
no mide si la regla es buena, sólo que no rompe nada.

**Procedencia.** Las 7 iteraciones tienen sha `547cd10` y `sucio: false`. Se corrieron desde un
worktree limpio, con el runner solo y un ELMFIRE por vez. `verificar` reproduce Alerces 2016 byte
a byte (3 de 3 ventanas).

**Humo de la app** (punto 4 del §6, sin ELMFIRE). Para una simulación de 2026, la regla cambia
15.225 ha del AOI:

| Año de la quema | Edad | Hectáreas | Pasan a |
|---|---|---|---|
| 2025 | 1 | 3.719 | GR1 |
| 2024 | 2 | 5.343 | GR1 |
| 2023 | 3 | 989 | GS3 |
| 2022 | 4 | 209 | GS3 |
| 2021 | 5 | 4.526 | GS3 |
| 2018–2020 | 6–8 | 439 | SH3 |

No se corrió una preparación completa por la API.

**Queda pendiente:**

- el paso 2 (capa de año de quema con MCD64A1 y dNBR, para las quemas de 2026 y las no
  forestales);
- la prueba de la premisa del §6, punto 3;
- la lectura descriptiva del conjunto de prueba.

## Fuentes

**Del repo**

- `docs/resultados/AUDITORIA-FISICA.md` (loops L y M)
- `docs/crosswalk/DECISIONES-MODELO-V0.md` §1–§4
- `docs/crosswalk/IGN-20B-FINAL-CROSSWALK-CCSBAP.md` §5.7
- `docs/referencias/Publ_tec_37_Modelos_combustibles.pdf.md`: Bianchi, Dentoni, Muñoz y
  Defossé (2012), CIEFAP Publ. Téc. 37, modelo A2
- `../mask-dataset-gen/README.md` (validación contra MCD64A1)

**Literatura**

- Paritsis J., Veblen T. T., Holz A. (2015). Positive fire feedbacks contribute to shifts from
  *Nothofagus pumilio* forests to fire-prone shrublands in Patagonia. *J. Veg. Sci.* 26:89–101.
  [CU Experts](https://experts.colorado.edu/display/pubid_95624)
- Tiribelli F., Kitzberger T., Morales J. M. (2018). Changes in vegetation structure and fuel
  characteristics along post-fire succession promote alternative stable states and positive
  fire–vegetation feedbacks. *J. Veg. Sci.* 29:147–156.
  [CONICET](https://ri.conicet.gov.ar/handle/11336/94177)
- Landesmann J. B., Tiribelli F., Paritsis J., Veblen T. T., Kitzberger T. (2021). Increased
  fire severity triggers positive feedbacks of greater vegetation flammability and favors plant
  community-type conversions. *J. Veg. Sci.* 32:e12936.
  [NR Fire Science](https://www.nrfirescience.org/resource/21739)
- Blackhall M. et al. (2017). Effects of biological legacies and herbivory on fuels and
  flammability traits. *J. Ecol.* 105:1309–1322.
  [CONICET](https://ri.conicet.gov.ar/handle/11336/57960)
- Kitzberger T. et al. (2016). Fire–vegetation feedbacks and alternative states. *N. Z. J. Bot.*
  54:247–272 (citado en `DECISIONES-MODELO-V0.md` §2).
- Cóbar-Carranza A. J. et al. (2014). Effect of *Pinus contorta* invasion on forest fuel
  properties. *Biol. Invasions* (`docs/referencias/`).
- Scott J. H., Burgan R. E. (2005). Standard fire behavior fuel models. RMRS-GTR-153.

**Productos y datos**

- LANDFIRE, [FDistADD data dictionary (LF2025)](https://www.landfire.gov/sites/default/files/DataDictionary/LF2025/LF2025_FDistADD.pdf)
- [MODIS MCD64A1 v061 en Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD64A1)
- [Copernicus Burnt Area v3.1 daily 300 m](https://land.copernicus.eu/en/products/vegetation/burnt-area-v3-1-daily-300m);
  [HYGEOS, v4.0 en 24 h](https://hygeos.com/en/unique-global-near-real-time-burnt-area-dataset/)
- [FIRMS data_availability API](https://firms.modaps.eosdis.nasa.gov/api/data_availability/);
  [foro Earthdata: SP con al menos 3 meses de atraso](https://forum.earthdata.nasa.gov/viewtopic.php?p=19364)
- [MapBiomas Argentina](https://argentina.mapbiomas.org/) (colección Fuego: cobertura en el AOI
  sin verificar)
- [CIEFAP, ficha "Incendios en la Patagonia"](http://ciefap.org.ar/documentos/fichas/A2N3_Incendiosenlapatagonia.pdf)
