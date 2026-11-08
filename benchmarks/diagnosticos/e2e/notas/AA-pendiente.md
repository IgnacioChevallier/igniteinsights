# AA · ¿La pendiente le gana de más al llano? Hipótesis y diseño registrado

> 2026-10-31. Nace de una observación en el dashboard (P-24 Patriada, ventana del 05-ene, ciclo
> GFS 05-ene 15:00 ART): con viento de ~6 mph al E, el fuego trepa paredes de 40° o más casi sin
> freno. §1 es exploratorio y ya se miró; §2 a §4 se registran **antes** de calcular nada sobre los
> casos no vistos y antes de correr ELMFIRE.

> **Estado: cerrada el 2026-10-31.** D se confirma; H1 aparece sólo en Patriada y H2 sólo en
> Cholila, sin mecanismo general ni cambios en modelo-v0.

## 0. Objetivo

Determinar si modelo-v0 propaga en terreno empinado demasiado rápido en comparación con el llano,
medido contra lo observado; y, si es así, separar si es porque la pendiente pesa de más (φs) o
porque el viento pesa de menos (φw). Es un diagnóstico: no promueve receta. Un cambio de modelo
exige un modelo-v1 definido de antemano y datos independientes
(`COMPARACION-MAPAS-MODELO-V0-RESULTADOS.md`, cierre; `PENDING_PARAMETERS.md` §4).

## 1. Lo ya visto (exploratorio)

Scripts de exploración: `pendiente_vs_viento.py`, `fp_pendiente.py` y `sesgo_llegada.py` (a mover
al repo si se ejecuta §3).

- **La implementación está bien.** `AUDITORIA-FISICA.md` (tabla de pendiente) verificó unidades y
  orientación de `slp`/`asp` contra Rothermel independiente (0,3 %). ELMFIRE 2025.0212:
  φs = 5,275·β^-0,3·tan²(slp), tope = φw a `0.9·IR` (`elmfire_spread_rate.f90:112-113`); φs y φw se
  suman como vectores (`elmfire_level_set.f90:1695-1726`). `PHIS_ADJ`/`PHIW_ADJ` (`&SIMULATOR`,
  default 1, `elmfire_namelists.f90:605-606`) los multiplican; el repo no los escribe.
- **En el caso del dashboard manda la pendiente, no el viento.** WAF 0,36–0,46 → 2,2 mph a media
  llama. Con SH4 (144): φw = 6,8 contra φs = 10,9 (30°), 23,1 (40°), 46,5 (50°); GR2 (102) igual.
  Celdas ≥ 40° de la ventana v0: `vs` mediano 39 m/min contra 3 m/min en 0–10°.
- **El incendio real también trepó:** 1.567 ha de la cicatriz (27 %) están en ≥ 30°.
- **Sesgo de llegada por pendiente** (cadena `calibracion-v6/lw-100-001`, modelo − 1.ª detección
  VIIRS a ±180 m, mediana en h):

  | caso | 0–10° | 10–20° | 20–30° | 30–40° | ≥ 40° |
  |---|---|---|---|---|---|
  | El Turbio 2025 | 58,7 | 27,3 | 42,4 | 36,6 | 31,6 |
  | Epuyén 2025 | 53,8 | 52,0 | 49,7 | 46,8 | 44,8 |
  | Alerces 2024 | 32,1 | 27,3 | 9,5 | −1,5 | −2,2 |
  | Patriada 2026 | 39,7 | 41,1 | 38,3 | 33,5 | 34,5 |

  En 4 de 4 casos con relieve el atraso baja con la pendiente. Golondrinas no tiene celdas
  empinadas con detección.
- **Exceso fuera de la cicatriz final** (P-24 Patriada `pronostico-gfs-v7`, 7 ventanas, sin
  `excluido`): 47 % (10–20°), 52 % (20–30°), 60 % (30–35°), 67 % (35–40°), 73 % (≥ 40°). Las celdas
  ≥ 30° fuera de la cicatriz miran a todos lados: no es sombra en el dNBR sobre laderas S/SE.

**Fuga ya ocurrida:** El Turbio 2025 es caso de **prueba** y se miró. Queda fuera de §3.

## 2. Hipótesis

- **D (descriptiva).** En modelo-v0, la llegada modelada en celdas ≥ 30° es más temprana, en
  comparación con lo observado, que en celdas de 0–10° del mismo incendio, a igual momento del
  incendio.
- **H1 (pendiente de más).** D se explica porque φs es demasiado grande en paredes.
- **H2 (viento de menos).** D se explica porque el llano va lento: el GFS/ERA5 subestima la rapidez
  (0,52–0,80× contra estaciones, `W-viento-estaciones.md`) y el llano depende más de φw.

H1 y H2 no se excluyen.

## 3. Etapa 1 · ¿D se confirma en casos no vistos? (0 corridas)

**Casos:** los que tienen relieve y no se miraron en §1: Cholila 2015, Alerces 2016, Alerces 2023
(calibración); Epuyén 2019, Alerces 2015, Puerto Café 2025 (prueba). Cada uno con la cadena
modelo-v0 que ya está en `data/benchmark/vistas/` (`calibracion-v6` o `calibracion-era5-v6`,
receta `lw-100-001`). Un caso entra si tiene ≥ 30 celdas con detección en 0–10° y en ≥ 30°.

**Estadístico (único, fijado acá):**
1. Llegada observada por celda: mínima hora de detección VIIRS a ±6 celdas (±180 m, media huella),
   medida desde la ignición del caso. Llegada modelada: `linea_tiempo.tif`.
2. Sesgo = modelada − observada (h). Se excluyen `excluido.tif` y las celdas de la semilla.
3. **Control del momento del incendio:** las celdas se agrupan por la llegada observada en bloques
   de 12 h (≈ dos pasadas VIIRS). Eso evita que D aparezca sólo porque el modelo va tarde el
   día 1 y temprano después de 48 h (`DIAGNOSTICO-PRECISION-E2E.md`, fila área/velocidad) y las
   paredes se queman más tarde.
4. Δ del bloque = mediana del sesgo en 0–10° − mediana en ≥ 30°, sólo en bloques con ≥ 10 celdas
   en las dos bandas. Δ del caso = mediana de los Δ de bloque, ponderada por celdas.

**Criterio:** D se confirma si Δ > 0 en todos los casos que entran, salvo a lo sumo uno, y en al
menos 4. Si no, D queda como exploratorio, §4 no corre y la nota cierra con eso.

**Secundario (sólo se informa):** el mismo Δ sin el control de 12 h, y el exceso fuera de la
cicatriz final en ≥ 30° menos en 10–30°, sobre la misma cadena.

**Amenazas:** la detección VIIRS es cota superior de la llegada y puede depender de la geometría de
visión en laderas; la huella de ±180 m mezcla bandas de pendiente en terreno quebrado.

## 4. Etapa 2 · ¿H1 o H2? (sólo si D se confirma)

**Casos:** sólo calibración con D > 0 en §1 o §3 (Patriada, Alerces 2024, Epuyén 2025 y los de
calibración que confirmen en §3). Prueba no se corre.

**Dos recetas, un solo valor cada una, sin barrido:**

| receta | cambio sobre `lw-100-001` | de dónde sale el valor | código |
|---|---|---|---|
| `lw-100-phis05-001` | `PHIS_ADJ = 0,5` | Ninguna fuente: valor redondo declarado. A 40° en SH4 deja φs ≈ 11,6, aún > φw | parámetro nuevo en `namelist_writer.write_namelist` (sólo se escribe si ≠ 1) y clave de receta |
| `lw-100-v15-001` | `factor_viento = 1,5` | Inversa de ~0,66, centro de la rapidez GFS medida contra estaciones (`W`) | ya existe |

**Lectura (sobre el mismo estadístico de §3, por caso):**
- **H1 a favor** si `phis05` reduce Δ en ≥ 50 % y mueve la mediana de 0–10° en < 3 h.
- **H2 a favor** si `v15` reduce Δ en ≥ 50 %, principalmente porque baja el atraso en 0–10°
  (caída en 0–10° ≥ 2× la de ≥ 30°).
- Las dos o ninguna: se informa tal cual. Se informa también el Dice y el sesgo de área; no deciden.

**Costo:** 2 recetas × 3–6 casos × sus ventanas, una corrida de ELMFIRE por vez. **Fuga:** ninguna
nueva; prueba no se toca.

## 5. Qué no decide esta nota

No adopta `PHIS_ADJ` ni `factor_viento`. Si H1 se sostiene, el resultado alimenta un modelo-v1 a
definir aparte, con la regla escrita antes de verlo sobre datos independientes.

## 6. Etapa 1 · D se confirma (2026-10-31)

Se implementó `benchmark.py pendiente`, sin red ni ELMFIRE. Lee `firms.csv`, `slp.tif`,
`excluido.tif`, `cicatriz.tif` y la semilla desde los hashes del paquete/manifiesto, y la llegada
modelada desde `data/benchmark/vistas/<caso>/<protocolo>/<receta>/linea_tiempo.tif`. La primera
detección se rasteriza en la misma ventana cuadrada de ±6 celdas del exploratorio de §1.

### 6.1 Control de reproducción

Antes de abrir los casos de §3 se corrió la variante secundaria, sin bloques de 12 h, sobre los
cuatro casos ya vistos. Reprodujo a una décima las 20 medianas de §1:

| caso | 0–10° | 10–20° | 20–30° | 30–40° | ≥ 40° |
|---|---:|---:|---:|---:|---:|
| El Turbio 2025 | 58,7 | 27,3 | 42,4 | 36,6 | 31,6 |
| Epuyén 2025 | 53,8 | 52,0 | 49,7 | 46,8 | 44,8 |
| Alerces 2024 | 32,1 | 27,3 | 9,5 | −1,5 | −2,2 |
| Patriada 2026 | 39,7 | 41,1 | 38,3 | 33,5 | 34,5 |

### 6.2 Casos no vistos

Los IDs se tomaron del snapshot `modelo-v0` y se confirmaron en `vistas/`: Cholila y Alerces 2016
usan `calibracion-era5-v6`; Alerces 2023, `calibracion-v6-h54`; Epuyén 2019 y Alerces 2015,
`calibracion-era5-v6`; Puerto Café, `calibracion-v6s`. En todos se usó `lw-100-001`.

| caso | celdas 0–10° | celdas ≥ 30° | bloques válidos | Δ controlado (h) | veredicto del caso | Δ sin control (h) | exceso ≥30° − 10–30° |
|---|---:|---:|---:|---:|---|---:|---:|
| Cholila 2015 | 6.694 | 12.056 | 8 | +21,3 | D a favor | +18,8 | +0,8 pp |
| Alerces 2016 | 2.154 | 1.885 | 1 | −14,1 | excepción, D en contra | −14,0 | −37,9 pp |
| Alerces 2023 | 5.326 | 421 | 4 | +16,8 | D a favor | −3,8 | −16,1 pp |
| Epuyén 2019 | 15.552 | 25 | 0 | — | no entra (< 30 empinadas) | — | +7,8 pp |
| Alerces 2015 | 708 | 955 | 4 | +4,1 | D a favor | +2,2 | +27,1 pp |
| Puerto Café 2025 | 238 | 7.304 | 3 | +7,0 | D a favor | +0,3 | −7,9 pp |

El control temporal es material: Alerces 2023 pasa de Δ = −3,8 h sin control a +16,8 h al comparar
celdas observadas en el mismo bloque de 12 h. Las medianas no controladas de sesgo en 0–10° / ≥30°
fueron 29,8 / 11,0 h (Cholila), 27,6 / 41,6 h (Alerces 2016), −5,8 / −2,0 h
(Alerces 2023), 41,7 / 39,4 h (Alerces 2015) y 56,2 / 55,9 h (Puerto Café). En Epuyén 2019
fueron −0,5 / 48,7 h, pero las 25 celdas empinadas no alcanzan el mínimo registrado.

**Veredicto:** D se confirma. Entran cinco casos; cuatro tienen Δ > 0 y uno tiene Δ < 0. Se cumple
exactamente el criterio de §3: al menos cuatro a favor y, entre los que entran, a lo sumo una
excepción. El exceso fuera de la cicatriz no ordena esos resultados y queda sólo como contexto.

**Desvíos del diseño:** ninguno. La mediana ponderada usa como peso el total de celdas válidas de
0–10° y ≥30° de cada bloque. No se cambiaron casos, bandas, umbrales, pesos ni valores de receta
después de ver los resultados.

### 6.3 Etapa 2 preparada, no corrida

Se agregó `phis_adj` a `write_namelist`: `PHIS_ADJ` se escribe en `&SIMULATOR` sólo si difiere de
1,0. También se cableó como clave de receta y se agregaron las dos recetas congeladas de §4:
`lw-100-phis05-001` y `lw-100-v15-001`. No se ejecutó ELMFIRE.

La etapa 2 queda pendiente sobre cinco casos de calibración con D > 0 en §1 o acá: Patriada 2026,
Alerces 2024, Epuyén 2025, Cholila 2015 y Alerces 2023. Son dos recetas por cinco cadenas, siempre
una corrida de ELMFIRE a la vez. Alerces 2016 queda fuera por Δ < 0; ningún caso de prueba se corre.
H1 y H2 siguen **sin veredicto** hasta completar esas corridas y aplicar §4; Dice y sesgo de área se
informarán sólo como contexto.

## 7. Etapa 2 · H1 en Patriada, H2 en Cholila; ninguna es general (2026-10-31)

Se corrieron las dos recetas de §4 sobre los cinco casos de calibración habilitados. Fueron 10
iteraciones y 42 ventanas de ELMFIRE, siempre una a la vez. Los comparadores de manifiestos no
encontraron ningún cambio de insumo no declarado en las 10 iteraciones.

### 7.1 H1 · reducir la pendiente

`mov. llano` es el cambio de la mediana del sesgo en 0–10° (`phis05` − base). H1 exige reducir Δ
en al menos 50 % y `|mov. llano| < 3 h`.

| caso | Δ base (h) | Δ `phis05` (h) | cambio de Δ | mov. llano (h) | H1 |
|---|---:|---:|---:|---:|---|
| Patriada 2026 | 10,0 | 4,2 | −57,6 % | −0,7 | **sí** |
| Alerces 2024 | 3,5 | −3,0 | −186,0 % | +6,5 | no: mueve el llano ≥ 3 h |
| Epuyén 2025 | −3,2 | 2,7 | aumenta 5,9 h | +1,5 | no: no reduce Δ |
| Cholila 2015 | 21,3 | 33,9 | aumenta 12,6 h | +16,1 | no |
| Alerces 2023 | 16,8 | 15,4 | −7,9 % | −1,0 | no: reducción < 50 % |

H1 queda **a favor sólo en Patriada**. En Alerces 2024 `PHIS_ADJ = 0,5` cruza Δ por cero, pero lo
hace retrasando el llano 6,5 h; falla la salvaguarda registrada. En Cholila, además, reducir φs
agranda el contraste.

### 7.2 H2 · aumentar el viento

`caída` es sesgo base − sesgo `v15`: positiva significa que baja el atraso. H2 exige reducir Δ en
al menos 50 % y que la caída en 0–10° sea al menos dos veces la de ≥30°.

| caso | Δ base (h) | Δ `v15` (h) | cambio de Δ | caída 0–10° / ≥30° (h) | razón | H2 |
|---|---:|---:|---:|---:|---:|---|
| Patriada 2026 | 10,0 | 9,7 | −2,6 % | −0,7 / +15,1 | −0,05 | no |
| Alerces 2024 | 3,5 | 6,1 | aumenta 2,5 h | +14,3 / +6,9 | 2,09 | no: no reduce Δ |
| Epuyén 2025 | −3,2 | −2,3 | aumenta 0,9 h | +8,3 / +2,7 | 3,12 | no: no reduce Δ |
| Cholila 2015 | 21,3 | 1,6 | −92,5 % | +13,9 / +1,2 | 11,83 | **sí** |
| Alerces 2023 | 16,8 | −7,2 | −142,9 % | +4,4 / +4,9 | 0,91 | no: no es principalmente llano |

H2 queda **a favor sólo en Cholila**. Alerces 2023 invierte Δ, pero el cambio es tan grande en la
pared como en el llano y falla la condición de mecanismo. Alerces 2024 y Epuyén sí tienen la razón
esperada, pero Δ no baja.

### 7.3 Contexto de forma y área

Dice / sesgo de área al horizonte; no participan del criterio:

| caso | base | `phis05` | `v15` |
|---|---:|---:|---:|
| Patriada 2026 | 0,496 / 0,70 | 0,444 / 0,54 | 0,560 / 0,93 |
| Alerces 2024 | 0,635 / 1,35 | 0,601 / 1,05 | 0,673 / 1,66 |
| Epuyén 2025 | 0,501 / 1,41 | 0,480 / 1,23 | 0,445 / 2,59 |
| Cholila 2015 | 0,513 / 0,87 | 0,426 / 0,65 | 0,544 / 1,04 |
| Alerces 2023 | 0,528 / 1,86 | 0,490 / 1,49 | 0,551 / 2,49 |

### 7.4 Veredicto

**Aparecen los dos mecanismos, pero como efectos específicos de un caso:** H1 pasa en Patriada y
H2 pasa en Cholila. Tres de cinco casos no apoyan ninguna; ninguno apoya ambas. Por lo tanto no hay
evidencia de que D tenga una explicación regional única por pendiente de más o viento de menos.
El resultado tampoco sostiene adoptar globalmente `PHIS_ADJ = 0,5` ni `factor_viento = 1,5`: eso
no estaba en el alcance de esta nota y, como contexto, ambas recetas empeoran el Dice en algunos
casos o llevan el sesgo de área fuera de la banda sin alarma.

**Desvíos científicos:** ninguno. Se conservaron casos, valores, estadístico y umbrales. Hubo una
incidencia operativa sin corrida: el primer lanzamiento de Alerces 2023 tomó el paquete `app` de
un worktree editable hermano y rechazó `phis_adj` antes de invocar ELMFIRE. Se reintentó fijando
`PYTHONPATH=.` al repo actual. Además cambió el HEAD durante Cholila por un commit paralelo de P-24;
no cambió ninguno de los módulos que preparan o ejecutan estas recetas. Los manifiestos conservan
ambos SHA y marcan el código sucio, porque el soporte de `phis_adj` todavía no está commiteado.

### 7.5 Cierre

La investigación queda cerrada. No se adopta ninguna de las dos recetas, no se modifica
modelo-v0 y no quedan corridas pendientes. Este diagnóstico sólo se reabre ante un bug físico o
evidencia externa nueva; estudiar interacciones entre viento, pendiente, combustibles, copa o
pavesas requiere una hipótesis y un diseño registrados nuevos.
