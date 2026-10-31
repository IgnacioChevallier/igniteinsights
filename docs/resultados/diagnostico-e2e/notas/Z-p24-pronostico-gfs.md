# Z · P-24 con el pronóstico GFS que se tenía en el reinicio

> 2026-10-31. Sigue a [T-semilla-v7](T-semilla-v7.md) y a `DIA-1-PROPUESTA.md` §7. §1 se registró
> antes de bajar ningún pronóstico y antes de correr nada: sólo se conocían las cifras de v7 y la
> disponibilidad del archivo (§2).

## 0. Problema

Los casos `*/pronostico-v7` re-cortan el clima del caso de calibración. En los cuatro incendios GFS
ese clima es `gfs-analisis-encadenado (f000-f005 de ciclos sucesivos)`: cada hora de una ventana
sale del análisis emitido en esa hora, es decir, después del reinicio. En Cholila 2015 y Alerces 2016
es ERA5, que es un reanálisis. Las dos cosas son hindcast meteorológico. El «P-24 gana a la cadena
en 6 de 6 a 12 h» (`DIA-1-PROPUESTA.md` §7.2, ESTADO §6) no incluye el error de pronóstico del GFS,
y no estaba declarado.

## 1. Diseño registrado (antes de calcular)

### 1.1 Qué cambia

Una iteración nueva: casos `<incendio>/pronostico-ciclo-v7` × receta `lw-100-obs-001`, la misma
receta de evaluación de v7. modelo-v0 y la receta `lw-100-001` no se tocan.

El caso es `pronostico-v7` salvo el clima de los reinicios k ≥ 1:

- **Ciclo:** el último ciclo GFS (00, 06, 12, 18 UTC) ya publicado en el instante del reinicio. Se
  toma como publicado si `ciclo + 4 h ≤ reinicio`. Es la misma latencia que usa la app al resolver
  el ciclo vivo (`GFSClient.resolve_cycle`). No sale de estos incendios.
- **Horas:** la banda 0 es la hora entera del reinicio, como en v7. Las bandas son las horas de
  pronóstico de ese ciclo, f005 a f033 según la ventana, una por hora y con la misma cantidad de
  bandas que v7 (25 o 26).
- **Producto y derivación:** el mismo que los análisis de v7: GFS `pgrb2.0p25`, la caja del caso con
  el mismo margen de 0,5°, `derive_wind` y `derive_moisture` (Nelson instantáneo, m10/m100 con los
  offsets +2/+5). `t2m_gfs` y `rh_gfs` son los del ciclo. `orog_gfs` es el terreno del GFS, igual en
  los dos.
- **Las humedades `*_retardo` no se generan.** Necesitan días de historial y `lw-100-obs-001` no las
  usa. Quedan fuera del paquete, en lugar de arrastrar análisis.

Todo lo demás es el paquete v7 byte a byte: estáticos, mapas, dosel, FIRMS, semillas, `phi.tif`,
`vistas_horas`, `ref_firms*`, `alcance` y la ventana 0. La ventana 0 arranca en la ignición, no es un
reinicio y no entra en el resultado (`pronostico.resumir` usa k ≥ 1).

**Control (antes de correr ELMFIRE):** en cada ventana, todos los archivos que no son clima tienen el
mismo SHA-256 que en v7, y el clima tiene la misma cantidad de bandas. Si no, no se corre.

### 1.2 Casos

Los cuatro incendios GFS: Alerces 2023, Epuyén 2025, Alerces 2024 y Patriada 2026. Son 23 reinicios.

**Cholila 2015 y Alerces 2016 quedan fuera del resultado principal** (§2.2). Su v7 usa ERA5. Hay
pronóstico archivado, pero cada 3 h. La variante cambiaría tres cosas a la vez: el producto (ERA5 →
GFS), la resolución temporal (3 h interpoladas) y el plazo. No mediría el error de pronóstico, que
es la pregunta. Sus cifras v7 quedan rotuladas como reanálisis, no como pronóstico.

### 1.3 Métricas

Las de `pronostico.puntuar` y `pronostico.resumir`, sin cambios: Dice del crecimiento contra la
cicatriz ya vista por VIIRS, sin el anillo ya visto al reiniciar. Por incendio, la media de los
reinicios k ≥ 1; entre incendios, la mediana del ΔDice y cuántos incendios mejoran. A 12 y 24 h.

| Comparación | Qué mide |
|---|---|
| ciclo contra la cadena de modelo-v0 | el resultado operativo de P-24. La cadena (`lw-100-001` sobre `calibracion-v6`) sigue con análisis: la comparación favorece a la cadena |
| ciclo contra v7 | cuánto cuesta el error de pronóstico del GFS a 5–33 h. Mismo reinicio, misma semilla, sólo cambia el clima |
| ciclo contra la persistencia | si ELMFIRE sigue aportando sobre la extrapolación ingenua |

Se informa también el sesgo de área por reinicio.

Cifras de v7 en los mismos cuatro incendios, para comparar:

| Plazo | Mediana ΔDice contra la cadena | Mejoran |
|---|---:|---:|
| 12 h | +0,118 | 4 de 4 |
| 24 h | +0,153 | 3 de 4 |

Con n = 4, ni 4 de 4 es significativo por la prueba de signos (p = 0,0625, una cola). El resultado
se informa como descriptivo, igual que el de v7 con 6.

### 1.4 Qué se concluye de cada resultado (fijado antes de calcular)

Contra la cadena, a 12 h, que es el resultado principal de P-24:

| Resultado | Conclusión |
|---|---|
| Mediana > 0 y mejoran 4 de 4 | **P-24 sigue ganando con el pronóstico real.** Las cifras nuevas pasan a ser las del pronóstico operativo en ESTADO §6, `DIA-1-PROPUESTA.md` §7 y RIESGOS §2. Las de v7 se conservan rotuladas como hindcast |
| Mediana > 0 y mejoran 3 de 4 | **Gana, pero no en todos.** Se informa con las cifras nuevas y el incendio que no mejora. Las de v7 quedan rotuladas como hindcast |
| Mediana ≤ 0, o mejoran 2 de 4 o menos | **Con el pronóstico real, P-24 no gana a la cadena.** Las cifras de v7 quedan rotuladas como hindcast en todos lados y la afirmación se restringe a «con meteorología analizada» |

A 24 h se aplica la misma tabla, como resultado secundario.

Contra v7, la mediana del ΔDice (ciclo − v7) a 12 h:

- |Δ| < 0,02: el error de pronóstico a 5–33 h no cambia la conclusión de P-24. El umbral es una
  convención: es del orden de los efectos que el repo ya trató como despreciables (truncado ≤ 0,01,
  reconstrucción de semilla ±0,003). No sale de estos incendios.
- Δ ≤ −0,02: el error de pronóstico se come esa parte de la ventaja. Se informa cuánta de la
  ventaja de v7 sobre la cadena queda.
- Δ ≥ +0,02: el pronóstico funciona mejor que el análisis. No es una mejora del modelo; con n = 4
  se lee como ruido de la meteorología, y se informa por incendio.

Qué no se hace con el resultado, sea cual sea: no se re-calibra nada, no cambia modelo-v0, no se
elige otro ciclo ni otra latencia, y el conjunto de prueba no se abre.

## 2. Disponibilidad del archivo (2026-10-31)

### 2.1 Los cuatro incendios GFS: completo

El bucket AWS `noaa-gfs-bdp-pds` (el que ya usa `GFSClient` vía Herbie) tiene los ciclos y las horas
que pide §1.1. Se verificó el `.idx` de cada hora de cada ciclo: **598 de 598**.

| Incendio | Reinicios | Ciclos | Horas de pronóstico |
|---|---:|---|---|
| Alerces 2023 | 3 | 05-feb 00Z y 12Z, 06-feb 00Z | f006–f033 |
| Epuyén 2025 | 6 | 15-ene 12Z a 18-ene 00Z | f005–f032 |
| Alerces 2024 | 8 | 26-ene 00Z a 29-ene 12Z | f006–f032 |
| Patriada 2026 | 6 | 05-ene 12Z a 08-ene 00Z | f006–f033 |

En los 23 reinicios el ciclo usado es el de las 00Z o las 12Z, de 5 a 8 h antes del reinicio. Las
pasadas VIIRS caen a las 05–07 y 18–20 UTC, antes de que se publique el ciclo de las 06Z o el de las
18Z.

### 2.2 Cholila 2015 y Alerces 2016: hay archivo, pero no es comparable

- AWS empieza en 2021. El catálogo en línea de NCEI (`thredds/catalog/model-gfs-004-files`, 0,5°)
  salta de 2015-08 a 2016-02 y no tiene 2015-02 ni 2016-01. Lo anterior de NCEI está sólo por pedido
  a cinta.
- NCAR RDA d084001 (GFS 0,25°, desde 2015-01) sí tiene los dos meses. Se accede por
  `thredds.rda.ucar.edu` y por OSDF; desde esta máquina `data.rda.ucar.edu`, la URL que usa Herbie,
  falla por el certificado. En 2015 y 2016 el archivo es **cada 3 h** (f000, f003, …), sin `.idx`,
  con 216 MB por hora de pronóstico: unos 20 GB para los 11 reinicios.
- Por §1.2 no entran al resultado principal. Correrlos como resultado secundario (GFS de pronóstico
  interpolado a 1 h contra ERA5) es una decisión del autor; mediría producto y pronóstico juntos.

## 3. Implementación

- `pronostico.ultimo_ciclo(t, latencia_h)`: el ciclo de §1.1. Prueba en
  `tests/test_validation_pronostico.py`.
- `scripts/benchmark.py`: `_clima_ciclo` acepta la hora de pronóstico inicial, la caja y el clima
  crudo. `_pronostico` usa el ciclo en los reinicios cuando el caso trae
  `empaquetado.clima_pronostico.latencia_h`, y guarda los ciclos en `origen.ciclos`.
- Casos: `benchmarks/casos/{los-alerces-2023,epuyen-2025,los-alerces-2024,puerto-patriada-2026}/pronostico-ciclo-v7.json`,
  copias de v7 con el clima y la descripción cambiados.

```bash
uv run python scripts/benchmark.py empaquetar epuyen-2025/pronostico-ciclo-v7
uv run python scripts/benchmark.py correr     epuyen-2025/pronostico-ciclo-v7 lw-100-obs-001
uv run python scripts/benchmark.py pronostico lw-100-obs-001 <caso>/pronostico-ciclo-v7 …
```

## 4. Resultado (2026-10-31)

### 4.1 Corridas y control

Los 4 casos se empaquetaron y corrieron el 2026-10-31, un ELMFIRE por vez: 23 reinicios, 2 h 15 min
de empaquetado (casi todo descarga del GFS) y 45 min de VM. El control de §1.1 pasó en las 27 ventanas: en las 23 de reinicio,
todo lo que no es clima es idéntico a v7 y el clima tiene las mismas bandas; las 4 ventanas 0 son
idénticas. Ciclos y horas en `origen.ciclos` de cada paquete; tablas en
`data/benchmark/p24/tabla-pronostico-ciclo-v7.md` y `comparacion-ciclo-v7.txt`; métricas en
`benchmarks/iteraciones/*/pronostico-ciclo-v7/lw-100-obs-001/pronostico.json`.

### 4.2 Resultado principal

Media por incendio de los reinicios k ≥ 1, Dice del crecimiento:

| Incendio | Reinicios | 12 h: ciclo / v7 / cadena | 24 h: ciclo / v7 / cadena |
|---|---:|---|---|
| Alerces 2023 | 3 | 0,236 / 0,239 / 0,204 | 0,317 / 0,324 / 0,330 |
| Epuyén 2025 | 6 | 0,123 / 0,122 / 0,017 | 0,193 / 0,189 / 0,049 |
| Alerces 2024 | 8 | 0,340 / 0,342 / 0,152 | 0,442 / 0,443 / 0,253 |
| Patriada 2026 | 6 | 0,148 / 0,149 / 0,018 | 0,207 / 0,208 / 0,043 |

| Plazo | Contra la cadena | Contra la persistencia | Contra v7 |
|---|---|---|---|
| 12 h | **+0,118, 4 de 4** | +0,088, 4 de 4 | −0,001 (1 de 4 sube) |
| 24 h | +0,154, 3 de 4 | +0,143, 4 de 4 | −0,001 (1 de 4 sube) |

Por §1.4:

- **12 h, contra la cadena: mediana > 0 y mejoran 4 de 4. P-24 sigue ganando con el pronóstico
  real.** Con n = 4 es descriptivo (signos, p = 0,0625).
- **24 h: gana, pero no en todos (3 de 4).** El que no mejora es Alerces 2023 (−0,014), el mismo
  que en v7 (−0,007): la cadena ya reproducía su día 1 y después lo frenó el combate.
- **Contra v7: |Δ| < 0,02.** El error de pronóstico del GFS a 5–33 h no cambia la conclusión. Ningún
  incendio se mueve más de 0,003 a 12 h ni de 0,007 a 24 h, y ningún reinicio más de 0,031
  (Alerces 2023 k2, 24 h).
- ELMFIRE le sigue ganando a la persistencia en los cuatro, en los dos plazos.

El sesgo de área por reinicio queda casi igual. Con el pronóstico, el crecimiento sale algo mayor en
la mayoría de los reinicios, por ejemplo Alerces 2023 k2 a 24 h: 8,6 contra 7,4. Los reinicios
tardíos, que sobre-propagan decenas o cientos de veces por la supresión (RIESGOS §1), siguen igual.

### 4.3 Por qué casi no cambia

Diferencia entre el clima del ciclo y el de v7, en las 23 ventanas de reinicio (rásters submuestreados
×10):

| Incendio | ws del análisis (mediana) | \|Δws\| mediana / p90 | \|Δwd\| mediana / p90 | \|Δm1\| mediana / p90 |
|---|---:|---|---|---|
| Alerces 2023 | 5,3 mph | 0,1 / 0,5 mph | 1° / 5° | 0,6 / 3,5 pp |
| Epuyén 2025 | 4,9 mph | 0,2 / 0,6 mph | 2° / 10° | 0,5 / 3,4 pp |
| Alerces 2024 | 4,8 mph | 0,2 / 0,6 mph | 3° / 9° | 0,4 / 2,4 pp |
| Patriada 2026 | 4,8 mph | 0,2 / 0,7 mph | 3° / 13° | 0,2 / 1,0 pp |

El pronóstico a 5–33 h y el análisis del mismo GFS difieren en lo que difieren los miembros de GEFS
(3–11°, ESTADO §8). Las dos cosas son el mismo modelo a 0,25°. El error que pesa es
el del GFS contra el viento real del valle (σ 30–41° en estaciones; W, RIESGOS §3), y lo tienen igual
la cadena, v7 y esta variante. Esta nota no lo mide y no lo reduce. Lo que mide es que el «hindcast»
de v7 no le daba a P-24 una ventaja que el pronóstico operativo no tenga.

### 4.4 Consecuencia

- Las cifras de P-24 con pronóstico real (4 incendios GFS: +0,118 en 4 de 4 a 12 h, +0,154 en 3 de 4
  a 24 h) pasan a ESTADO §6.2, `DIA-1-PROPUESTA.md` §7.2 y RIESGOS §2 como las del pronóstico
  operativo.
- Las de v7 (6 incendios: +0,096 en 6 de 6 y +0,131 en 5 de 6) se conservan rotuladas como hindcast:
  análisis GFS posteriores al reinicio en cuatro incendios y ERA5 (reanálisis) en Cholila y Alerces
  2016.
- modelo-v0, `lw-100-001` y `lw-100-obs-001` no cambian. No se eligió otro ciclo ni otra latencia.
- Cholila 2015 y Alerces 2016 siguen sin la variante (§2.2): su P-24 es con reanálisis.

> **Nota (2026-10-31): medición equivalente en `main`.** La rama `main` ya tenía la misma pregunta
> medida en `docs/resultados/P24-PRONOSTICO-GFS.md` (corte 2026-10-23, commit `b2ea414`), con los
> casos `*/pronostico-gfs-v7`. Ahí el hindcast sí estaba declarado, en el ESTADO de `main`; lo que
> dice §0 vale sólo para esta rama. La regla de ciclo es otra: el último ciclo publicado a la hora en
> que la pasada se ve en FIRMS (pasada + 3 h de latencia − 4 h de publicación), en lugar de
> `ciclo + 4 h ≤ reinicio`. Da +0,117 en 4 de 4 a 12 h y +0,153 en 3 de 4 a 24 h, con diferencias por
> incendio de hasta 0,005 contra §4.2 (Alerces 2023 a 24 h: 0,322 contra 0,317). Son dos mediciones independientes que coinciden. Al
> integrar las ramas hay que decidir qué documento queda.
