# W · Puerta meteorológica: GFS y SMN WRF contra estaciones (frente 4)

Código: `scripts/diagnostico_viento_estaciones.py`, con test sintético en
`tests/test_diagnostico_viento_estaciones.py`. No se corrió ELMFIRE y sólo se usaron incendios de
calibración: los 4 casos `pronostico-v6` de 2023–2026, con bases en `particion.json → calibracion.gfs`.
`uv run python scripts/diagnostico_viento_estaciones.py` tarda ~25 min la primera vez y <1 min con
caché (`data/benchmark/cache/{synop,smn-wrf}/`). Los datos están en `datos/W_*.csv`.

**Veredicto: no pasa.** WRF cumple el criterio en 1 de 3 estaciones (El Bolsón, n = 21). En Esquel
(n = 322) y en Futaleufú (n = 52) empeora la dirección. La Etapa C no se diseña.

## A. Disponibilidad

### A1. SMN WRF 4 km (`W_wrf_disponibilidad.csv`)

- **Bucket.** `s3://smn-ar-wrf`, el mismo del prototipo (`smn_object_url`), de acceso público por
  HTTPS. Las carpetas de `DATA/WRF/DET/` van de 2022 a 2026: **los 4 incendios están cubiertos.**
- **Ciclos.**
  - 2023: sólo 00 y 12 UTC.
  - 2024–2026: 00, 06, 12 y 18 UTC.
  - Huecos en los días de corrida:
    - 2024-01-26 18Z está incompleto: sólo tiene archivos `10M`.
    - 2024-01-28 no tiene 18Z.
    - 2025-01-14 no tiene 00Z.
  - Ninguno deja una hora sin cobertura: se toma el ciclo anterior.
- **Plazos.** f000–f072 horarios, 73 por ciclo.
- **Productos por ciclo.**
  - `01H`: 31–39 MB por hora; un ciclo pesa 2,3–2,7 GB.
  - `10M`: sólo precipitación cada 10 min, ~3,8 MB.
  - `24H`: acumulados diarios.
- **Variables de `01H`.** `magViento10` (m/s, 10 m, **"calibrada con observaciones de superficie"**
  según la documentación del SMN, sin decir con qué estaciones), `dirViento10` (grados, sin
  calibrar), `T2`, `HR2`, `PP`, `PSFC`, radiación, `TSLB`, `SMOIS` y nivel de congelamiento.
  **No hay u10/v10.** La condición inicial es `SAP.SMN-ANA`, sobre GFS 0,25°. La capa límite es MYJ.
- **Cobertura del AOI.** La grilla es Lambert conforme de 999 × 1.249 celdas de 4 km y cubre todo
  el sur de Sudamérica. Las tres estaciones y los 4 dominios caben en un recorte de 19 × 40 celdas.
  La georreferencia se verificó contra el `lat/lon` del archivo: error máximo de 3 m, en 2023 y en
  2026.
- **Descarga.** Las 343 horas de corrida en archivos enteros serían ~12 GB, por encima del tope de
  5 GB. El script lee **sólo `magViento10` y `dirViento10` por rango HTTP** (`/vsicurl/` y driver
  HDF5 de GDAL). Cada variable es un único bloque comprimido de ~3,5 MB, así que una hora cuesta
  7,2 MB medidos. **Total transferido: ~2,5 GB.** En disco quedan 343 recortes `.npy` de ~6 KB.
  El driver HDF5 serializa los hilos, por eso se lee con procesos.
- **Convención.** `dirViento10` es "desde": el desvío contra estaciones es de 20–30°, no de ~180°.
  No pude confirmar si es relativo al norte verdadero o a la grilla. Si fuera a la grilla, el error
  sería la convergencia de meridianos en −71,5°, ≈ 3,7°, menor que el umbral de 10°.
- **Ciclo usado.** Para cada hora, el ciclo más reciente con plazo ≥ 1 h. Es el análogo del GFS
  encadenado f000–f005, porque el f000 de WRF es la condición inicial, sin la dinámica de 4 km.
  Plazo mediano 4 h, máximo 12 h (2023 y el 18Z faltante). Es el mejor caso para WRF: en un P-24
  real, el plazo sería de 1 a 30 h.

### A2. Estaciones (`W_estaciones.csv`)

| Estación | WMO | lat, lon | Altura | Distancia a la ignición (km): A23 / A24 / E25 / P26 |
|---|---|---|---:|---|
| El Bolsón Aero | 87800 | −41,967, −71,517 | 337 m | 102 / 93 / 28,5 / 20,0 |
| Esquel Aero | 87803 | −42,933, −71,150 | 789 m | 35 / 40 / 83 / 93 |
| Futaleufú (Chile) | 85832 | −43,189, −71,849 | 317 m | 41 / 47 / 114 / 119 |

**La verdad de estación es el SYNOP crudo (Ogimet), no el caché de Meteostat.**

- **El Bolsón** reporta `NIL` en la mayoría de las horas: hay SYNOP en 11 de 54, 19 de 115, 14 de
  88 y 18 de 86 horas de corrida, siempre de día. Meteostat da valores en las 343 horas, pero sólo
  coinciden con el SYNOP las horas que existen; el resto es relleno.
  - En Patriada 2026 coincide 1 de 18, porque el inventario horario de Meteostat para 87800 termina
    el 2025-02-20.
  - **Consecuencia lateral:** en Las Golondrinas 2021, 118 de las 145 horas de "viento de la
    estación El Bolsón" (RIESGOS §3, A-inventario fila 33) son relleno de Meteostat. La ráfaga de
    53,6 km/h del 10-03 a las 00Z sí es un SYNOP real.
- **Esquel** reporta un SYNOP por hora en las 343 horas, y coincide con Meteostat en 338.
- **Futaleufú** alterna dos tipos de reporte:
  - en las horas trihorarias, con `iw` = 4 (nudos), coincide con Meteostat;
  - en las intermedias, con `iw` = 1 ("m/s"), el `ff` es 1,5× el de las trihorarias vecinas en
    nudos, así que la unidad es incierta. Leídas como m/s, la media daría ~12 m/s y el sesgo del GFS
    −5 m/s.

  **Sólo se usan los reportes en nudos**, así que Futaleufú queda trihoraria: 15, 38, 29 y 24 horas.
- **Otras fuentes revisadas.**
  - NCEI ISD: bloqueado por un desafío web.
  - METAR de Iowa Mesonet: SCFT sólo desde 2024-04, SAVE parcial y SAVB nada.
  - DMC Chile (`climatologia.meteochile.gob.cl`): las series horarias se piden por formulario con
    registro; no se descargaron.
- **Pares estación–incendio.** Se usan sólo las estaciones que caen dentro de la serie GFS del caso
  (la caja ±0,5°):
  - El Bolsón con Epuyén y Patriada;
  - Esquel con los 4 incendios;
  - Futaleufú con Alerces 2023 y 2024.

  Fuera de esa caja, el repo nunca interpoló el GFS y no hay un "valor recibido". Con el filtro de
  viento observado > 5 km/h quedan **395 estación-horas**: 21 en El Bolsón, 322 en Esquel y 52 en
  Futaleufú.

## B. Comparación (`W_horas.csv`, `W_metricas.csv`, `W_metricas_por_incendio.csv`, `W_criterio.csv`)

### Fuentes comparadas

- **GFS recibido.** La serie GFS cacheada del caso base, con u/v interpolados bilinealmente a la
  estación, convertidos a 20 ft en mph con `wind_height_factor()` y `MS_TO_MPH` (como
  `derive_wind`) y vueltos a 10 m con la misma regla.
  - Equivalencia verificada: la bilineal reproduce el `ws.tif` del paquete al ≤ 0,07 % en 5 celdas
    por incendio.
- **GFS crudo.** La celda de 0,25° más cercana, a 10 m.
- **WRF cercano.** La celda de 4 km más cercana.
- **WRF bilineal.** Bilineal sobre u/v.

Métricas:

- |Δθ| circular: media y mediana. El desvío firmado se informa como mediana y como media circular.
- Rapidez: sesgo como media de (modelo − observado), RMSE y cociente de medias.
- La tarde va de 14 a 20 h ART.

### Total (395 h; tarde 121 h)

| Fuente | \|Δθ\| mediano | Desvío mediano | Sesgo rapidez (m/s) | Cociente | RMSE | \|Δθ\| mediano, tarde / resto |
|---|---:|---:|---:|---:|---:|---|
| GFS recibido | 27,0° | +21° | −1,14 | 0,75 | 2,17 | 16,2° / 31,1° |
| GFS crudo | 24,4° | +16° | −1,28 | 0,72 | 2,24 | 14,2° / 29,1° |
| WRF cercano | 28,5° | +20° | −1,00 | 0,78 | 1,97 | 19,7° / 33,2° |
| WRF bilineal | 29,6° | +24° | −1,02 | 0,78 | 1,99 | 20,7° / 36,6° |

### Por estación, contra el criterio registrado (GFS recibido contra WRF)

| Estación (n) | \|Δθ\| med. GFS | WRF bil. (cerc.) | Reducción | Sesgo GFS | WRF bil. (cerc.) | Reducción del \|sesgo\| | Pasa |
|---|---:|---:|---:|---:|---:|---:|---|
| Esquel (322) | 26,8° | 30,7° (26,5°) | −3,9° (+0,2°) | −0,91 | −0,80 (−0,81) | 12 % (12 %) | no |
| Futaleufú (52) | 19,1° | 39,1° (36,8°) | −20,0° (−17,7°) | −1,96 | −2,21 (−1,97) | −13 % (−1 %) | no |
| El Bolsón (21) | 81,4° | 11,6° (29,1°) | +69,8° (+52,3°) | −2,47 | −1,37 (−1,54) | 45 % (38 %) | **sí** |

**1 de 3 → no pasa**, con WRF bilineal y con WRF cercano.

**Lo que más pesa es la consistencia por incendio** (`W_metricas_por_incendio.csv`):

- WRF bilineal es peor que el GFS recibido en Esquel en los 4 incendios (+2 a +7°) y en Futaleufú
  en los 2 (+9° y +25°).
- Es mejor en El Bolsón en los 2 (Epuyén: 73° → 15°, n = 9; Patriada: 86° → 11°, n = 12).
- La tarde no cambia el orden en ninguna estación. En Esquel, GFS da 14,9° y WRF 20,3°.
- **El veredicto no depende del n chico de El Bolsón:** aunque esa estación fuera sólida, las otras
  dos fallan por márgenes amplios.
- La calibración de `magViento10` con observaciones podría estar dentro de la muestra en las
  estaciones del SMN (Esquel y El Bolsón), lo que favorecería a WRF en la rapidez. Aun así, en
  Esquel reduce el sesgo sólo 12 %.

**Señal que no alcanza el criterio, pero que se registra.** El Bolsón es la estación más cercana a
Epuyén (28 km) y a Patriada (20 km). Ahí el GFS sopla ~80° girado, lo que no aparecía en
AUDITORIA-FISICA:283 porque se midió con el relleno de Meteostat. WRF, en cambio, acierta dentro de
~11–15°.

Esto encaja con un valle N–S (El Bolsón–Lago Puelo) que una celda de 25 km no ve y una de 4 km sí.
Pero son 21 horas diurnas autocorrelacionadas en 2 incendios, y no hay ninguna estación dentro de
los valles de Epuyén ni de Patriada. Como evidencia sirve sólo para pedir las estaciones de INTA y
la Dirección de Bosques (Epuyén, Lago Puelo y El Hoyo; RIESGOS §3), no para una receta.

### Contra AUDITORIA-FISICA:283

Esa medición dio un desvío mediano de −14° a +30° y una rapidez de 0,50–0,87×. Con el SYNOP crudo
y las horas de corrida, el GFS recibido da:

| Estación | Desvío mediano | Cociente de rapidez |
|---|---:|---:|
| Futaleufú | −13° | 0,56 |
| Esquel | +23° | 0,80 |
| El Bolsón | **+81°** | 0,52 |

Futaleufú y Esquel reproducen lo anterior. El Bolsón sale de ese rango.

### Error del GFS contra la dispersión de entrada de GEFS (S5; `W_gefs_contra_error.csv`)

| Incendio | n | \|Δθ\| mediano GFS | σ circular del error | σ GEFS (S5) | RMSE / rapidez obs. | CV GEFS (S5) |
|---|---:|---:|---:|---:|---:|---:|
| Alerces 2023 | 66 | 18,8° | 31° | 3,3° | 0,51 | 0,07 |
| Alerces 2024 | 145 | 29,9° | 38° | 6,0° | 0,52 | 0,10 |
| Epuyén 2025 | 92 | 27,3° | 30° | 5,5° | 0,45 | 0,10 |
| Patriada 2026 | 92 | 25,6° | 41° | 11,4° | 0,44 | 0,15 |

El error del GFS en estaciones es **3–9× la dispersión de dirección** de GEFS y **3–7× la de
rapidez**. Confirma con estaciones de los días de corrida la sub-dispersión de S5 (pendiente (c)/(d)
de R O4). También respalda que un ensamble paramétrico (frente 5) use WD ±25° y no la dispersión de
GEFS.

## C. Diseño de la ingesta

**No corresponde: WRF no pasa.** No se crea `lw-100-obs-wrf-001` y no se gastan las 23 corridas.

Si en el futuro hubiera estaciones dentro de los valles de Epuyén y Patriada y la señal de El Bolsón
se sostuviera, la pieza reutilizable ya existe: la lectura por rango de `leer_wrf`, ~7 MB por hora y
2,5 GB para los 4 incendios. Se agregaría bajo `app/ingestion/`, con un criterio nuevo registrado
antes de mirar.

La advertencia de la revisión sigue en pie: la resolución efectiva de WRF (~25–30 km) es más gruesa
que los valles, y en Esquel y Futaleufú WRF no mejora al GFS.

## Limitaciones

- El SYNOP es el promedio de 10 min a la hora en punto; los modelos son instantáneos.
- El Bolsón sólo tiene horas diurnas.
- Futaleufú queda trihoraria.
- La autocorrelación horaria hace que el n efectivo sea mucho menor que el nominal.
- No se cuantificó el posible sesgo a favor de WRF por la calibración de `magViento10`.
- La dirección de WRF puede tener ±3,7° de rotación de grilla.
