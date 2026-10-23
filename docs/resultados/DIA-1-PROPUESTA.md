# Día 1 explosivo: propuesta

> Corte: 2026-10-11. **Las opciones 1 y 3 ya se implementaron y corrieron: resultados en §7.**
> Las secciones 1–6 son la propuesta original, escrita antes de correr nada. Lo medido en ellas
> sale de paquetes e iteraciones ya congeladas, del fuente de ELMFIRE 2025.0212 y de cálculos
> fuera de línea. Complementa `RIESGOS_Y_SUPOSICIONES.md` §2.
>
> Nada de esto reabre `modelo-v0`. Las opciones que cambian la física quedan condicionadas a
> evidencia externa nueva, como pide la regla de parada. La opción recomendada no cambia la
> física: mide otra cosa.

## Resumen

| # | Opción | Impacto esperado sobre las primeras 24 h | Costo | Toca modelo-v0 |
|---|---|---|---|---|
| 1 | **Protocolo P-24: pronóstico desde el perímetro observado** | Alto en lo operativo: mide lo que la app ya hace. Medio sobre el área del día 1 | Bajo: ~1 h de VM, código acotado | No |
| 2 | Ajuste de velocidad asimilado dentro de P-24 | Alto desde el segundo reinicio; nulo en el primero | Medio | No (otro producto) |
| 3 | Diagnóstico de copa con CFIS, fuera de línea | Explicativo: dice si la copa es el mecanismo | Bajo, sin VM | No |
| 4 | Viento sostenido inferido de la ráfaga (ERA5 `fg10`, GFS `GUST`) | Incierto; sólo en arbustal y estepa | Medio, con un requisito externo | Sí: sería candidato a v1 |
| 5 | Fluctuaciones de viento de ELMFIRE (`WIND_FLUCTUATIONS`) | Bajo | Bajo | Sí |
| 6 | Pavesas con un inventario independiente de focos | Desconocido hasta tener el inventario | Alto | Sí |

**Recomendación:** implementar la opción 1 y correr la 3 en paralelo. La 2 se agrega a P-24 sólo
si el primer resultado muestra que el error persiste después del reinicio. Las opciones 4–6 no
deben correrse antes de tener los datos externos que se describen en cada una (§6).

## 1. Qué se sabe del día 1, medido sin correr nada

### 1.1 La cifra vigente

La cifra de 8–30× que citan `RIESGOS_Y_SUPOSICIONES.md` §2 y `AUDITORIA-FISICA.md` §7.3 salió del
loop B, sobre los protocolos v4. Con modelo-v0 (v6, ventana 0 de `lw-100-001`) y la misma medida
observada a las 24 h del loop B:

| Incendio | Observado 24 h (loop B) | Modelo-v0 (v6) | Déficit |
|---|---:|---:|---:|
| Epuyén 2025 | 1.730 ha | 83 ha | 21× |
| Alerces 2016 | 1.241 ha | 156 ha | 8× |
| Alerces 2024 | 851 ha | 138 ha | 6× |
| Patriada 2026 | 2.474 ha | 410 ha | 6× |
| Alerces 2023 | 485 ha | 482 ha | 1× |
| Cholila 2015 | 255 ha | 480 ha | 0,5× |

El déficit vigente es de **6–21× en cuatro de seis** (Las Golondrinas es el caso límite).
`RIESGOS_Y_SUPOSICIONES.md` §2 ya está actualizado con esta cifra (2026-10-12).

### 1.2 Dónde se abre la brecha

Área FIRMS reconstruida (la misma regla que la semilla, `ignition_builder.build_ignition_layer`)
en cada pasada VIIRS del primer día, contra lo que modelo-v0 había quemado a esa hora (TOA de la
ventana 0):

| Incendio | Pasada 1: horas desde la ignición, observado / modelo | Pasada 2: horas, observado / modelo |
|---|---|---|
| Epuyén 2025 | 4,5 h: 1.964 / 9 ha | 15,9 h: 2.909 / 47 ha |
| Alerces 2016 | 1,8 h: 482 / 2 ha | 13,2 h: 2.077 / 56 ha |
| Patriada 2026 | 2,3 h: 160 / 12 ha | 13,7 h: 5.795 / 159 ha |
| Alerces 2024 | 5,8 h: 70 / 3 ha | 18,9 h: 1.295 / 63 ha |
| Alerces 2023 | 5,1 h: 74 / 28 ha | 19,1 h: 777 / 295 ha |
| Cholila 2015 | 0,1 h: 44 / 0 ha | 23,8 h: 284 / 465 ha |

**Cuidado con la escala.** La reconstrucción infla las áreas chicas: un píxel aislado se dibuja
como un disco de 375 m de radio, unas 44 ha. Por eso las cifras de la primera pasada son cotas
superiores. Aun así, Epuyén tiene **112 detecciones** a las 4,5 h. Con la huella nominal de
14 ha por píxel, eso son ~1.500 ha. Las crónicas dicen 1.120 ha en 6 h
(`docs/crosswalk/DECISIONES-MODELO-V0.md` §5).

**Corrección (2026-10-12).** Con una medida que no infla (la cicatriz dNBR a menos de medio píxel o de un
píxel VIIRS de las detecciones de la primera pasada), lo observado es 640–1.120 ha en Epuyén y
230–410 ha en Alerces 2016. La brecha baja a 70–120×, pero sigue siendo de dos órdenes de
magnitud. La suma nominal de huellas sobreestima en Epuyén porque dos satélites vieron los mismos
píxeles con 23 min de diferencia (`RIESGOS_Y_SUPOSICIONES.md` §2).

Hay dos lecturas:

1. **En Epuyén y Alerces 2016 la brecha está abierta antes de la primera pasada** (2–5 h). Ningún
   pronóstico que arranque en la ignición puede saber eso. Sí puede saberlo uno que arranque en la
   primera detección.
2. **Entre pasadas la brecha sigue creciendo.** Patriada pasa de 160 a 5.795 ha en 11 h, y el
   modelo agrega ~150 ha. Alerces 2024 pasa de 70 a 1.295 ha, y el modelo agrega 60. Si eso se
   repite al arrancar desde el perímetro observado, el déficit es de **velocidad** (un proceso que
   falta) y no de ignición ni de error acumulado. La opción 1 está diseñada para separar esas dos
   causas.

### 1.3 Dos hipótesis descartadas fuera de línea

**El límite de viento de Rothermel.** ELMFIRE 2025.0212 aplica el límite original de Rothermel:
la velocidad del viento a media llama se topa en `0,9 × IR` (pies/min), y el factor de pendiente
se topa en el mismo valor (`elmfire_spread_rate.f90`, ~l. 105–113). La alternativa de Andrews,
Cruz y Rothermel (2013) está en el fuente, comentada. Si ese límite mordiera, podría frenar los
frentes ladera arriba del día 1 (Epuyén 27°, Alerces 2016 29°, loop B).

Para verificarlo se reimplementó Rothermel/Albini fuera de línea con
`app/elmfire/fuel_models.csv`, m1/m10/m100 = 6/8/10 % y LW 100 %. El límite equivale a 17 mph a
media llama en GS2, 23 en SH4, 33 en TL8 y 82 en TU5. La pendiente queda topada recién por
encima de 63–76°. **No muerde** en los combustibles del benchmark. Es una reimplementación
aproximada, pero el margen es de un orden de magnitud.

**Las fluctuaciones de viento como ráfagas.** Se analizan en la opción 5. Su efecto esperado
sobre la velocidad media es de +1–3 %.

### 1.4 Lo que ya sabía el repo y sigue en pie

- Bajo dosel, ELMFIRE reduce el viento de 20 pies con un WAF de ~0,1–0,2. Por eso un viento
  medio 60 % mayor casi no movió el día 1 (RESULTADOS-CSS-BAP loop 6). Ese loop corrió con los
  bugs de v3, pero el razonamiento físico no depende de ellos.
- TL8 bajo dosel no alcanza los ~270 kW/m que pide la copa del pino con un CBH de 1,5 m
  (DECISIONES-MODELO-V0 §5). El cálculo de 1.3 lo confirma: con 20 mph a 20 pies y un WAF de
  0,1, TL8 da ~100 kW/m. Con un WAF de 0,4 (borde o claro), ~500 kW/m.
- La quema experimental A4 de PT-37 es evidencia de fuera del benchmark: 4.800 m/h bajo ráfaga.
  Con ráfaga, SH4 y GS3 llegan al 51–60 % de esa velocidad (DECISIONES-MODELO-V0 §6).

## 2. Opción 1 — Protocolo P-24: pronóstico desde el perímetro observado

### 2.1 Qué es

Se reinicia ELMFIRE en cada pasada VIIRS, desde el perímetro observado hasta ese momento, y se
puntúa el **crecimiento** a 12 y 24 h. No se puntúa la cicatriz final.

Es el modo en que trabaja la app: `ignition_builder.build_ignition_layer` arma la ignición con el
perímetro FIRMS reconstruido. Es también el modo en que trabajan los sistemas operativos. Esa
reconstrucción nunca se validó (`PENDING_PARAMETERS.md` §2, `RIESGOS_Y_SUPOSICIONES.md` §5).

### 2.2 Evidencia externa

- **Práctica operativa.** En WFDSS, Near-Term Fire Behavior (equivalente a FARSITE) corre de forma
  determinista desde el perímetro actual, con horizontes útiles de 1 a 3 días. FSPro corre de
  forma probabilística desde el perímetro o desde el punto, a 7–14 días (WFDSS Help; NIFC,
  *Comparing the Fire Behavior Tools in WFDSS*). Los productos de incidente se publican a
  12 y 24 h; por ejemplo, el NTFB "12hr24hr" del incendio Simmons de 2011.
- **ELMFIRE en operación.** Pyrecast (Pyregence) corre ELMFIRE a 24 h con perímetros WFIGS y
  focos VIIRS de 375 m (cada ~12 h) como entrada. Lo corre en ensamble, perturbando viento,
  humedades y pavesas (Lautenberger 2023, *Automated Wildfire Forecasting in the Continental US*,
  SSFSS). El proveedor también distribuye una plantilla `active_fires-suppressed` para pronósticos
  desde focos activos (`interface-gotchas.md`).
- **Reinicio con focos satelitales.**
  - Cardil, Monedero, Ramírez y Silva (2019, *J. Environ. Manage.* 231:996) reinicializan
    simulaciones con focos MODIS/VIIRS y mejoran la exactitud en todos sus casos.
  - Un estudio con FARSITE y VIIRS de 375 m (*J. Remote Sensing*, doi 10.11834/jrs.20219427) sube
    el Sørensen final de 54 % a 79 %.
  - Coen y Schroeder (2013, *GRL*) inicializan simulaciones acopladas con perímetros VIIRS de
    375 m.
  - En WRF-SFIRE, la inicialización desde la progresión observada con *spin-up* es la que mejor
    funciona (arXiv 2204.00686, 2309.02615).
- **Perímetros VIIRS cada 12 h.** FEDS (Chen et al. 2022, *Sci. Data* 9:249) agrupa los focos
  VIIRS de cada pasada en objetos y cierra el perímetro con *alpha shapes*. Es el mismo esquema
  que `perimeter_reconstruction.py`, que usa *concave hull*. NASA lo marca como experimental, y
  aclara que sus "perímetros" no equivalen a los operativos.
- **Cómo se evalúa.** Se evalúa sólo el área nueva, no la unión con el perímetro inicial. Lo
  proponen Duff, Chong y Tolhurst (2016, *Environ. Model. Softw.* 83:276) y ya es la regla de este
  repo (IGN-26 §12.1). Cardil et al. y el estudio FARSITE-VIIRS usan Sørensen (= Dice).

### 2.3 Qué tiene ya el repo

- **Semilla `observacion`** (`app/validation/cadena.py`). En la ventana n > 0 toma `phi.tif` del
  paquete: lo que FIRMS vio hasta el inicio de la ventana, reconstruido con la misma regla que la
  app (`scripts/benchmark.py::_firms_gfs`). **Los paquetes v6 ya traen esas semillas.**
- **Referencias por ventana** en el paquete: `ref_firms.tif` (detecciones nuevas),
  `ref_firms_horas.tif` (hora de la primera detección por celda), `alcance.tif`, la cicatriz
  truncada al horizonte y `excluido.tif`.
- **Receta `semilla-observacion-001`.** Sólo corrió sobre protocolos anteriores a la auditoría;
  sus números no sirven.

**Hallazgo menor.** La semilla observada de los paquetes v6 no es monótona: con *concave hull*,
más puntos pueden dar menos área. Alerces 2016 pasa de 2.077 ha en la ventana 1 a 1.971 ha en la
ventana 2; Epuyén, de 3.187 a 3.184 ha. **No afecta a modelo-v0**: con semilla `prediccion` sólo
se usa la `phi.tif` de la ventana 0. Sí afectaría a P-24.

### 2.4 Diseño

Todo se fija y se commitea **antes** de correr.

**Casos.** Un protocolo nuevo por incendio, `<incendio>/pronostico-v6`, sobre la misma caja y la
misma preparación que `calibracion-v6`, para que la grilla coincida celda a celda (la
herramienta lo exige con el sha del `dem`):

- Los seis incendios de calibración con reinicios posibles. Las Golondrinas no entra: su única
  ventana es de 24 h y no admite un reinicio con 24 h por delante.
- Los casos de prueba (`benchmarks/particion.json`) no entran.

**Reinicios.**

- Se agrupan las detecciones VIIRS SP del caso en pasadas: detecciones separadas por menos de 2 h.
- Cada pasada cuya hora más 24 h quede dentro del horizonte del caso es un reinicio `T_k`, a la
  hora de su última detección.
- Resultan **34 reinicios**: Alerces 2023 3, Epuyén 6, Alerces 2024 8, Patriada 6, Alerces 2016 4
  y Cholila 7.
- Cada reinicio es una ventana de 24 h, con `t0` en la hora entera y `tstart_s` con los minutos.
  Las ventanas se solapan. Esto es válido con semilla `observacion`: el clima se corta por
  desfase en `_clima`.
- **El primer reinicio de cada incendio es el "día 1 desde la primera detección"**, entre 0,1 y
  5,8 h después de la ignición.

**Semilla.** `S_k = ignición ∪ S_{k−1} ∪ reconstrucción(detecciones ≤ T_k)`: acumulada y por lo
tanto monótona. Los parámetros de la reconstrucción no se tocan (eps 1.500 m, ratio 0,4). Se corre
también una variante diagnóstica, **`S_k` oráculo**: la cicatriz dNBR ∩ píxeles vistos hasta
`T_k`. Usa la cicatriz final, que en tiempo real no existe. Sirve para separar el error de la
reconstrucción del error de propagación.

**Referencia por plazo τ ∈ {12, 24} h.**

- La principal sale de la cicatriz, que es independiente:
  `O_k,τ = cicatriz ∩ vistas(≤ T_k + τ) \ S_k`. `vistas` son las celdas a menos de un píxel
  VIIRS (375 m) de alguna detección; es la misma regla que `hasta_horizonte` en
  `_referencia_cicatriz`.
- Se excluyen las celdas de `excluido.tif`, `S_k` y lo de la cicatriz todavía no visto a
  `T_k + τ`, que ardió después o no se vio.
- Lo predicho fuera de la cicatriz es un falso positivo. Por eso la precisión se interpreta (en
  el harness A no se podía).
- La referencia secundaria es sólo FIRMS: el recall contra las detecciones nuevas, como el harness
  A.
- **Una corrida de 24 h da los dos plazos.** La predicción a τ es
  `{TOA − T_k ≤ τ} \ S_k`.

**Receta.** `lw-100-obs-001`: padre `lw-100-001`, los mismos `parametros` y combustible, y
`"semilla": "observacion"`. Es una receta de evaluación, **no candidata**. No re-elige LW, ADJ,
CBH ni viento: el único campo distinto es la política de semilla, que en este repo vive en la
receta (`definiciones.POLITICAS_SEMILLA`).

**Comparadores.** Se puntúan contra la misma `O_k,τ`:

1. **Cadena de modelo-v0**, la iteración existente `calibracion-v6/lw-100-001`: lo quemado a
   `T_k + τ` según su línea de tiempo cosida, menos `S_k`. La pregunta es cuánto mejora reiniciar.
2. **Persistencia del crecimiento.** `S_k` se dilata isotrópicamente con la distancia equivalente
   que el incendio creció entre `T_{k−1}` y `T_k`, escalada a τ (para k ≥ 1). La pregunta es si
   ELMFIRE le gana a una extrapolación ingenua. Sin este comparador no se puede decir que el
   modelo aporta.

**Métricas por reinicio y plazo.**

- Dice del crecimiento.
- Sesgo del crecimiento (predicho / observado), con la alarma [0,5×, 2×] de IGN-26.
- Recall y precisión.
- Error de llegada contra `ref_firms_horas`; ya existe en `puntuacion.error_llegada`.
- *Skill* frente a la persistencia: `(D − D_pers) / (1 − D_pers)`.

**Resultado principal (fijado de antemano).**

- La **mediana entre incendios del ΔDice a 24 h** (P-24 menos la cadena de modelo-v0). Primero
  se promedia dentro de cada incendio, para que Alerces 2024 (8 reinicios) no pese el doble que
  Alerces 2023 (3).
- Se informan el signo por incendio y un intervalo *bootstrap* por incendio (n = 6).
- Con 6 incendios, 6 de 6 positivos es la única configuración con p < 0,05 en una prueba de
  signos. 5 de 6 da p ≈ 0,11. Hay que decirlo así.

**Resultado del día 1 (descriptivo).** El primer reinicio de cada incendio, a 12 y 24 h: el sesgo
del crecimiento y el Dice, con `S_k` FIRMS y con `S_k` oráculo.

- Si el sesgo sigue por debajo de 0,2× con la semilla oráculo, el déficit del día 1 es de
  velocidad (procesos) y el reinicio no lo resuelve.
- Si sube a [0,5×, 2×], el déficit era sobre todo de la fase previa a la primera detección.

Por §1.2, lo esperable es lo primero en Patriada, Alerces 2024 y Epuyén. Es una hipótesis, no un
resultado.

### 2.5 Cambios de código

Son mínimos; no tocan los builders de ELMFIRE.

| Archivo | Cambio |
|---|---|
| `scripts/benchmark.py` | Un subcomando `pasadas <caso>` que escribe las ventanas de `pronostico-v6` con la regla de 2.4, para que no se escriban a mano |
| `scripts/benchmark.py::_firms_gfs` | La clave opcional del caso `"semilla_acumulada": true` (`observado |= previo`). Es opcional para no cambiar los hashes de los protocolos existentes al re-empaquetar |
| `scripts/benchmark.py::_horas_deteccion` | Un radio como parámetro, para empaquetar `vistas_horas.tif` con 375 m (la referencia por plazo) además del actual de medio píxel |
| `scripts/benchmark.py` | La variante oráculo: la clave `"semilla_oraculo": true`, que construye `S_k` desde la cicatriz |
| `app/validation/cadena.py::puntuar` | Un bloque `por_plazo` cuando el caso declara `"plazos": [12, 24]`: la referencia y las métricas de 2.4 |
| `scripts/benchmark.py` | Un subcomando `pronostico <incendio>` con la tabla pareada contra la cadena de modelo-v0 (exige el mismo sha de `dem`) y contra la persistencia |
| `benchmarks/recetas/lw-100-obs-001.json` | La receta de evaluación |
| `benchmarks/casos/*/pronostico-v6.json` | Seis casos generados por `pasadas` |
| `tests/` | Una prueba de que la semilla acumulada es monótona y de que la referencia por plazo excluye lo no visto todavía |

**Cómputo.** El manifiesto de `lw-100-001` da una mediana de 0,6 min por ventana de 24 h (máximo
1,1). Son 34 reinicios × 2 semillas (FIRMS y oráculo), **~1 h de VM** con un ELMFIRE por vez.

### 2.6 Regla de parada

- No cambia ningún parámetro físico, el crosswalk ni el dosel.
- No mira el conjunto de prueba.
- Su resultado no promueve nada: es otra afirmación ("pronóstico a 24 h desde la última pasada"),
  con su propio protocolo.
- Si más adelante se quiere usar el conjunto de prueba, se corre una vez con el protocolo ya
  congelado, sólo para describir.

### 2.7 Riesgos

- **Referencia ruidosa a 12 h.** Entre pasadas, `vistas(≤ T + 12 h)` puede no tener ninguna
  detección nueva (IGN-26 §12.2). Hay que informar cuántos pares reinicio × plazo son puntuables.
  Eso también es un resultado.
- **n chico.** 34 reinicios repartidos en seis incendios correlacionados. Sirve para describir,
  no para inferir.
- **La reconstrucción infla las semillas chicas** (§1.2). Por eso se corre la variante oráculo.
- **El reinicio corrige dónde, no qué tan rápido.** Si el déficit es de proceso, P-24 lo muestra
  con más limpieza que la cadena, pero no lo cierra.

## 3. Opción 2 — Ajuste de velocidad asimilado, dentro de P-24

### 3.1 Qué es

En cada reinicio k ≥ 1 se usa un ADJ uniforme `ADJ_k`, estimado con el propio incendio. Se compara
el crecimiento observado entre `T_{k−1}` y `T_k` con el que predijo la ventana k−1, que arrancó en
`S_{k−1}` y ya está corrida porque las ventanas se solapan:

```
r = √(A_fin / π) − √(A_inicio / π)        (radio equivalente del crecimiento)
ADJ_k = clamp(r_observado / r_simulado, 1/4, 4)
```

No hace falta ninguna corrida extra. La velocidad superficial es lineal en ADJ:
`VS0 = (ADJ + PERTURB_ADJ) × …` (`elmfire_spread_rate.f90`). El rango [1/4, 4] se fija de
antemano y no se barre.

### 3.2 Evidencia

- Cardil, Monedero, Silva y Ramírez (2019, *Ecol. Model.* 395:39–44) ajustan en tiempo real un
  factor de velocidad por modelo de combustible contra los tiempos de llegada observados. Es el
  método de Wildfire Analyst.
- Lautenberger (2013, *Fire Saf. J.* 62:289–298) presentó ELMFIRE con calibración automática de
  factores de ajuste contra perímetros observados.
- Srivas et al. (2016, *Procedia CS*; 2017) estiman factores de ajuste por combustible con un
  filtro de Kalman por ensambles sobre FARSITE.
- Rochoux et al. (2014, *NHESS* 14:2951) corrigen el viento y el combustible con EnKF a partir
  del frente observado.

### 3.3 Cambio de código

- Un parámetro de receta `adj_asimilado` en `definiciones.PARAMETROS`.
- En `cadena._preparar`, calcular `ADJ_k` desde `previa` (el TOA de la ventana anterior) y la
  `S_k` actual, y reescribir `adj.tif`; es una perilla ya admitida, sin keyword nuevo.
- Registrar `ADJ_k` en el manifiesto.
- Receta `lw-100-obs-adj-001` (padre `lw-100-obs-001`).

### 3.4 Cómo se mide

En P-24, contra `lw-100-obs-001`, con los mismos reinicios k ≥ 1: 28 corridas, ~20 min. Es un
producto distinto (pronóstico asimilado), no un candidato a modelo-v1. No contradice "ADJ = 1"
de modelo-v0, que es una afirmación sobre la receta estática.

### 3.5 Riesgos

- No ayuda al primer reinicio, porque todavía no hay historia.
- Se estima de noche y se aplica de día (o al revés). El ciclo diurno ya está en el clima, así
  que el cociente arrastra el error de la hora.
- Con un crecimiento simulado ~0 el cociente se dispara. El tope lo corta, pero esos reinicios
  quedan marcados.
- El ADJ absorbe errores de dirección del viento y de combustible. Por eso no se usa en la
  comparación de mapas (IGN-26 §12.3).

## 4. Opción 3 — Diagnóstico de copa con CFIS, fuera de línea

### 4.1 Qué es

Se evalúa, sin ELMFIRE, si las celdas de plantación, ciprés y coihue con caña que ardieron el día
1 habrían hecho copa según un modelo de iniciación **independiente de Rothermel**:

- **CFIS** (Cruz, Alexander y Wakimoto 2004, *Forest Science* 50:640): una regresión logística con
  el viento a 10 m en campo abierto, el CBH, la humedad del combustible fino y el consumo
  superficial.
- Se compara con lo que hace ELMFIRE: el criterio de Van Wagner sobre la intensidad superficial
  de Rothermel, con el viento ya reducido por el WAF bajo dosel.

### 4.2 Evidencia

- Cruz y Alexander (2010, *IJWF* 19:377–398) muestran un **sesgo de subpredicción** de la copa en
  los sistemas que acoplan Rothermel con Van Wagner (NEXUS, FlamMap, FARSITE, BehavePlus). Lo
  atribuyen al acople incompatible, a modelos que subpredicen por diseño y a funciones de fracción
  de copa sin sustento.
- ELMFIRE 2025.0212 usa ese mismo acople para la iniciación: `CRITICAL_FLIN = (0,01 × CBH ×
  (460 + 26 × FMC))^1,5` (`elmfire_spread_rate.f90`, l. 164–170). Sólo la velocidad de copa activa
  es de Cruz et al. (2005).
- Valores medidos en Patagonia: CBH 1,5 m y CBD 0,16 kg/m³ en plantaciones de ponderosa sin podar
  (Paritsis et al. 2018, *Forests* 9:117, ya adoptados en v6). Según el resumen, la plantación y
  la invasión multiplican casi por 30 la intensidad potencial, y la poda basal baja la
  probabilidad de copa.
- Para lenga, coihue y ñire **no hay inventario de CBH**: hay valores de literatura de confianza
  media o baja (DECISIONES-MODELO-V0 §2).
- Para ciprés hay sólo descripciones cualitativas: corteza fina y ramas secas persistentes que
  dan acceso a la copa.

### 4.3 Cambio de código

Ninguno en `app/`. Un script de diagnóstico que lea, de los paquetes v6, el mapa, el dosel y el
clima de la ventana 0, y las celdas quemadas a 24 h según la cicatriz y las detecciones.

### 4.4 Cómo se mide

Sobre los seis incendios, sin corridas. CFIS no se ajusta: sus coeficientes son los publicados.

- Si CFIS predice copa en la mayor parte de lo que ardió el primer día y Van Wagner + Rothermel
  no, queda cuantificado el sesgo de acople de la versión fijada. Es evidencia externa en el
  sentido de la regla de parada.
- Si CFIS tampoco predice copa, la copa no explica el día 1 y quedan las pavesas y el viento
  local.

### 4.5 Riesgo

**ELMFIRE 2025.0212 tiene un solo modelo de iniciación** (`CROWN_FIRE_MODEL > 0`) y no se cambia
la versión. Un resultado positivo no se traduce directamente en un cambio del modelo.

La única vía por insumos es un "CBH equivalente" que haga coincidir Van Wagner con CFIS. Eso
mezcla dos modelos, justo lo que critican Cruz y Alexander: su riesgo es alto y no se propone.

Otra perilla posible es `FOLIAR_MOISTURE_CONTENT` (por defecto 90; el repo no la escribe). Es
física pero no ayuda: medir una humedad foliar mayor en coníferas en temporada haría la copa más
difícil.

Por eso el valor de esta opción es explicativo. Decide si vale la pena buscar más datos de dosel.

## 5. Opciones que cambian la física (4–6)

### 5.1 Ráfagas: qué productos hay

| Producto | Variable | Qué es | Cobertura | ¿Está en el repo? |
|---|---|---|---|---|
| HRRR | — | No cubre Argentina | — | — |
| ERA5 | `fg10` (paramId 49) | Ráfaga máxima de 3 s (WMO) desde el post-proceso anterior, a 0,25° | 1940– | No. Open-Meteo la sirve como `wind_gusts_10m`; `_era5_serie` pide sólo el viento medio |
| ERA5 | `i10fg` | Ráfaga instantánea a 10 m | 1940– | No |
| GFS 0,25° | `GUST:surface` | Ráfaga diagnosticada por el post-proceso del GFS (método no verificado acá) | El archivo de AWS que ya usa `GFSClient` | Está en el mismo `pgrb2.0p25` (verificado en el `.idx` del 15-ene-2025 12z); no se descarga |
| Estaciones | ráfaga horaria | Meteostat `wpgt` (Esquel, El Bolsón); DMC Futaleufú desde 1969; SIPAS sin verificar | Puntual | Meteostat ya se usa para el viento medio |

**Dato nuevo.** En Epuyén, el 15-ene-2025 entre las 17 y las 21 UTC, ERA5 da:

- **un viento medio de 12–15 km/h**;
- **una ráfaga de 55–64 km/h**, con un cociente de 4,4–4,7.

El parte del SPMF de esa noche dice "vientos de hasta 70 km/h" que "han favorecido la rápida
propagación de las llamas y generado focos secundarios" (ANBariloche, 16-ene-2025). Los cocientes
típicos de 3 s contra 10 min sobre terreno rugoso rondan 1,5–1,8, así que un cociente de 4–5 no es
un factor de ráfaga. Sugiere que la ráfaga de ERA5 conserva una señal que el viento medio de una
celda de 25 km pierde en el relieve. Es consistente con RIESGOS §3: el reanálisis da 0,40–0,87× lo
que miden las estaciones.

### 5.2 Opción 4 — Viento sostenido inferido de la ráfaga

**Qué es.** Estimar el viento sostenido como `ráfaga / G`, con un factor de ráfaga `G` medido en
estaciones locales, y usarlo en `ws.tif` donde supere al viento medio del reanálisis.

**Evidencia.** Crosby y Chandler (1966, reeditado por el NCFS en 2009):

- Las ráfagas de un minuto cambian la velocidad y la intensidad. En hojarasca de pino, 9 mph
  contra 5 de media duplican la intensidad durante ese minuto.
- Las ráfagas momentáneas casi no cambian la velocidad total, **pero pueden disparar copa o
  pavesas** cuando las condiciones están cerca del umbral.

También están el dato de §5.1 y la quema A4 de PT-37 (§1.4).

**Requisito externo, antes de cualquier corrida.** Comparar `fg10` de ERA5 y `GUST` del GFS
contra la ráfaga y el viento medio de las estaciones, **en días que no sean de los 11 incendios**,
y fijar `G` (o una transferencia ráfaga → sostenido) con esos datos. Ese ajuste sobre datos ajenos
al benchmark es la "evidencia externa nueva" que pide la regla de parada.

**Cambio de código.**

- `app/ingestion/meteorology/gfs/client.py`: agregar `":GUST:surface:"` al diccionario de
  variables.
- `scripts/benchmark.py::_era5_serie`: agregar `wind_gusts_10m`.
- Empaquetar `gust.tif` (protocolos `-v6g`, que con la misma receta reproducen v6 byte a byte).
- Una perilla de receta `viento_desde_rafaga: {"G": …}` en `definiciones.PARAMETROS` y
  `cadena._preparar`.
- Ningún keyword nuevo de ELMFIRE.

**Cómo se mide.**

- Primero en P-24, sólo con el primer reinicio y a 24 h, con `G` fijo.
- Si se quisiera promover, haría falta el gate completo de modelo-v1: calibración, validación
  cruzada, prueba sólo al final y comparación contra modelo-v0.
- Una sola variante: `G` no se barre.

**Riesgos.**

- Rothermel espera un viento medio, no una ráfaga, y el doble conteo es fácil.
- El loop 6 sugiere que bajo dosel no llega al combustible, así que actuaría sobre todo en
  arbustal y estepa.
- Los incendios que ya llegan a su área (Alerces 2016, sesgo 1,69; Alerces 2023, 1,86) se pasarían
  desde el día 2.
- El método del GFS para `GUST` no está documentado acá.

### 5.3 Opción 5 — Fluctuaciones de viento de ELMFIRE

**Qué soporta 2025.0212** (verificado en el fuente, rama `2025.0212`):

- `&SIMULATOR` admite `WIND_FLUCTUATIONS` (por defecto `.FALSE.`), `WIND_SPEED_FLUCTUATION_INTENSITY`
  y `WIND_DIRECTION_FLUCTUATION_INTENSITY` (por defecto 0,0), y `DT_WIND_FLUCTUATIONS` (por
  defecto 15 s) (`elmfire_namelists.f90`, `READ_SIMULATOR`).
- Cada `DT_WIND_FLUCTUATIONS`, `APPLY_WIND_FLUCTUATIONS` (`elmfire_subs.f90`, ~l. 1008) sortea **un
  solo** factor para todo el frente: `ws × (1 + I_v·(r − ½))` y `wd + I_d·(r − ½)·360°`. El
  llamado está en `elmfire_level_set.f90`, ~l. 645.
- **A diferencia de `&SPOTTING`, el valor de `&SIMULATOR` se usa tal cual.** Sólo se sortea si
  `WIND_SPEED_FLUCTUATION_INTENSITY_MIN` y `_MAX` de `&MONTE_CARLO` son > 0
  (`READ_MONTE_CARLO`, `SET_MISC_PARAMETERS`).
- La fluctuación también entra en las pavesas, que usan `WS20_NOW`.

**Por qué el impacto esperado es bajo.**

- El factor es simétrico y de media 1. El aumento de la velocidad media es sólo el de la
  convexidad del factor de viento (`φ_w ∝ U^B`, B ≈ 1,4–1,5): con `I_v` = 1 (±50 %), ≈ +3 %.
- El único efecto grande sería cruzar un umbral (copa) en los intervalos de viento alto. TL8 bajo
  dosel necesita casi el triple de intensidad (§1.4): sería un factor de viento cercano a 2, que
  corresponde a `I_v` ≈ 2 y a viento nulo la mitad del tiempo. No tiene sentido físico.

**Cambio de código.**

- `namelist_writer.write_namelist(wind_fluctuations=…)` escribe los cuatro keywords en
  `&SIMULATOR`.
- La perilla en `definiciones.PARAMETROS`.
- Una entrada en `.claude/skills/elmfire/references/`.
- `I_v = 2(G₁ₘᵢₙ − 1)`, con el factor de ráfaga de 1 minuto de las estaciones (Crosby y Chandler).
- Como el proceso es caótico, varias semillas (`&MONTE_CARLO SEED`).

**Riesgo.** Es estocástico: hacen falta N semillas × 34 reinicios. Puede ser costo sin
efecto. Correrlo sólo si la opción 3 muestra que el primer día está cerca del umbral de copa.

### 5.4 Opción 6 — Pavesas con un inventario independiente

**Qué soporta 2025.0212.** `&SPOTTING`, con distribución lognormal de distancias (Sardoy et al.
2008: `MEAN_SPOTTING_DIST`, `NORMALIZED_SPOTTING_DIST_VARIANCE`, `SPOT_WS_EXP`, `SPOT_FLIN_EXP`),
el modelo UMD (`USE_UMD_SPOTTING_MODEL`), porcentajes de lanzamiento en copa y en superficie,
`PIGN` y `CRITICAL_SPOTTING_FIRELINE_INTENSITY`. El repo ya escribe la plantilla de hindcast sin
sorteo (`namelist_writer.SPOTTING_HINDCAST`).

**Evidencia regional.**

- Sólo cualitativa: el SPMF reporta "focos secundarios" con viento fuerte en Epuyén el 15-ene-2025
  y otra vez en noviembre de 2025, con ráfagas de 80 km/h (NoticiasNQN, 18-nov-2025).
- **No se encontraron mediciones de distancias ni de tasas de pavesas** para *Nothofagus*, ciprés o
  pino en Patagonia norte. La literatura de distancias es de Norteamérica y Australia.
- El loop L ya mostró que cualquier porcentaje sin dato externo es una perilla. Con la plantilla
  no se enciende ningún foco; con 10 %/1 % mejora Cholila y se pasan Alerces 2023 y Epuyén.
- Las pavesas de copa necesitan que la copa se encienda primero, así que dependen de la opción 3.

**Requisito externo.** Un inventario de focos secundarios de incendios **que no estén entre los
11**: otros de la Comarca Andina y del Nahuel Huapi, con partes, Sentinel-2 y focos VIIRS
separados del frente en la pasada siguiente. De ahí salen la distribución de distancias y la
frecuencia por hora de frente activo. Recién con eso se fijan `MEAN_SPOTTING_DIST` y los
porcentajes, sin mirar el benchmark.

**Cambio de código.** Un script de inventario fuera de `app/`. En ELMFIRE, sólo valores nuevos
para claves que `SPOTTING_HINDCAST` ya admite.

**Riesgos.**

- VIIRS (375 m) no ve las pavesas cortas (< 200 m), que son la mayoría.
- El inventario cuesta semanas.
- La salida es caótica: una corrida no basta.

## 6. Recomendación

1. **Implementar P-24 (opción 1) ahora.** Es la única opción que:
   - no depende de datos que no existen;
   - no toca modelo-v0;
   - cuesta ~1 h de VM;
   - mide lo que la app realmente hace.

   Su resultado del día 1 decide qué sigue: si con la semilla oráculo el crecimiento del primer
   reinicio sigue 5× por debajo, el problema es de proceso y el reinicio sólo acota el daño.

2. **Correr la opción 3 en paralelo**, porque no usa la VM. Dice si la copa es el mecanismo del
   salto en plantaciones y caña, con un modelo que no comparte el sesgo de Rothermel + Van Wagner.

3. **Agregar el ajuste asimilado (opción 2) a P-24** sólo si el ΔDice de P-24 queda chico en los
   reinicios k ≥ 1 por subpropagación.

4. **Antes de cualquier opción física (4–6), conseguir el dato externo:**
   - la comparación de ráfagas entre reanálisis y estaciones en días ajenos al benchmark (barata:
     Meteostat y Open-Meteo ya están integrados);
   - y, si la opción 3 da positivo, el inventario de focos secundarios.

   Sin eso, cualquier corrida sería un barrido de perillas sobre los 11 incendios.

**Lo que conviene decir en la tesis:**

- Las primeras 2–6 h, antes de la primera pasada VIIRS, **no son pronosticables** con los procesos
  que tiene ELMFIRE 2025.0212 configurado como modelo-v0.
- El producto defendible es un pronóstico a 24 h desde la última pasada, con su propio protocolo
  y su propia métrica.

## 7. Resultados (2026-10-11)

Se implementaron y corrieron las opciones 1 (P-24) y 3 (copa). Modelo-v0 no cambió: ninguna
receta física nueva, el conjunto de prueba no se corrió y la regla de parada sigue en pie.

### 7.1 Qué se implementó

| Pieza | Dónde |
|---|---|
| Puntuación por plazo, comparador de la cadena, persistencia y resumen | `app/validation/pronostico.py` |
| CFIS, Van Wagner, WAF de ELMFIRE y Rothermel/Albini sin pendiente | `app/validation/copa.py` |
| Empaquetador `pronostico`: deriva del paquete `calibracion-v6` congelado y re-arma el clima por hora desde sus ventanas | `scripts/benchmark.py::_pronostico` |
| Subcomandos `crear-pronostico`, `pronostico` y `copa` | `scripts/benchmark.py` |
| Receta de evaluación (no candidata) | `benchmarks/recetas/lw-100-obs-001.json` |
| 12 casos: 6 incendios × semilla FIRMS acumulada y semilla oráculo | `benchmarks/casos/*/pronostico{,-oraculo}-v6.json` |
| Pruebas | `tests/test_validation_pronostico.py` |
| Carrera en el almacén: dos empaquetados en paralelo guardaban el mismo objeto con el mismo temporal | `app/validation/almacen.py::guardar` |

**Controles.**

- La ventana 0 de P-24 reprodujo el TOA de modelo-v0 **byte a byte** (Alerces 2023).
- El clima re-armado coincide banda por banda con el del caso base.
- Las semillas acumuladas son monótonas.
- Las ventanas con minutos de arranque llevan una banda más (26), para que ELMFIRE no sostenga la
  última.

**Cómputo.** 34 reinicios × 2 semillas: 1 h 28 min de VM, un ELMFIRE por vez.

```bash
uv run python scripts/benchmark.py crear-pronostico epuyen-2025/calibracion-v6 [--semilla oraculo]
uv run python scripts/benchmark.py empaquetar epuyen-2025/pronostico-v6
uv run python scripts/benchmark.py correr epuyen-2025/pronostico-v6 lw-100-obs-001
uv run python scripts/benchmark.py pronostico lw-100-obs-001 <caso> [<caso> …]
uv run python scripts/benchmark.py copa epuyen-2025/calibracion-v6
```

### 7.2 P-24: el reinicio mejora el pronóstico a 12 y 24 h

> **Corrección 2026-10-18** (`DIAGNOSTICO-PRECISION-E2E.md` §4). Las cifras de esta sección y de
> §7.3 y §7.6 se re-puntuaron sin el anillo ya visto al reiniciar. `vistas` usa discos de 375 m y
> la semilla de 187,5 m, y ese anillo, pegado a la semilla, contaba como crecimiento acertado.
> `pronostico.puntuar` ahora lo excluye. Además, la versión anterior tenía invertidas las semillas
> FIRMS y oráculo en el resultado principal. Las tablas viejas quedaron en
> `data/benchmark/p24/tabla-pronostico*-v6-con-anillo.md`. Ninguna corrida cambió.
>
> **Protocolo v7 (2026-10-22).** La semilla FIRMS se filtra a las detecciones conectadas a la
> ignición (`semilla_inicial.filtro_conexo_m`, bug 4 de D; `diagnostico-e2e/notas/T-semilla-v7.md`).
> Sólo cambia Cholila, que sembraba detecciones de otros incendios: pasa de 0,070 / 0,262 a
> 0,078 / 0,327. Los otros 5 paquetes son idénticos a v6. La mediana contra la persistencia a 12 h
> pasa de +0,060 a +0,063, y el resto del resultado principal no cambia. La semilla oráculo sigue en
> v6.

Dice del crecimiento contra la cicatriz ya vista por VIIRS. Es la media por incendio de los
reinicios k ≥ 1, con semilla FIRMS acumulada, que es lo que la app puede hacer:

| Incendio | Reinicios | 12 h: P-24 / cadena v0 | 24 h: P-24 / cadena v0 |
|---|---:|---|---|
| Alerces 2023 | 3 | 0,239 / 0,204 | 0,324 / 0,330 |
| Epuyén 2025 | 6 | 0,122 / 0,017 | 0,189 / 0,049 |
| Alerces 2024 | 8 | 0,342 / 0,152 | 0,443 / 0,253 |
| Patriada 2026 | 6 | 0,149 / 0,018 | 0,208 / 0,043 |
| Alerces 2016 | 4 | 0,087 / 0,000 | 0,122 / 0,000 |
| Cholila 2015 | 7 | 0,078 / 0,056 | 0,327 / 0,205 |

**Resultado principal (fijado en §2.4).**

| Plazo | Mediana ΔDice contra la cadena de modelo-v0 | Mejoran | Mediana ΔDice contra la persistencia | Mejoran |
|---|---:|---:|---:|---:|
| 12 h | **+0,096** | **6 de 6** | +0,063 | 6 de 6 |
| 24 h | **+0,131** | 5 de 6 | +0,142 | 6 de 6 |

Con la semilla oráculo: +0,155 (6 de 6) y +0,185 (6 de 6) contra la cadena.

- Con 6 de 6, la prueba de signos da p = 0,03 a 12 h. A 24 h, 5 de 6 da p ≈ 0,11.
- La única excepción es Alerces 2023 a 24 h. Es el incendio cuyo día 1 la cadena ya reproducía
  (§1.1), y después lo frenó el combate.
- **ELMFIRE le gana a la extrapolación ingenua en los seis incendios.** Sin ese comparador no se
  podía afirmar que el modelo aporte al pronóstico operativo.
- En los reinicios tardíos el crecimiento predicho supera al observado: 25–47× a 24 h en Alerces
  2016 desde las 13 h. En Alerces 2023, a las 30 h, el crecimiento observado a 12 h es casi nulo. Es el límite de supresión
  (RIESGOS §1): el incendio ya estaba contenido. Ahí la persistencia, que no crece si el incendio
  no creció, a veces gana.

Las tablas por reinicio están en `data/benchmark/p24/tabla-pronostico-v7.md` y
`tabla-pronostico-oraculo-v6.md` (v6, antes del filtro: `tabla-pronostico-v6.md`). Las métricas
completas, en `benchmarks/iteraciones/*/pronostico-v7/lw-100-obs-001/pronostico.json` y
`*/pronostico-oraculo-v6/…`.

### 7.3 El día 1: dónde está el déficit

El primer reinicio de cada incendio, a 24 h. Sesgo = crecimiento predicho / observado:

| Incendio | Primera pasada (h desde la ignición) | Semilla FIRMS / oráculo | Crecimiento observado | Sesgo P-24 (FIRMS / oráculo) | Sesgo cadena v0 |
|---|---:|---|---:|---|---:|
| Alerces 2016 | 1,8 | 482 / 408 ha | 865 ha | **1,08 / 0,77** | 0,01 |
| Epuyén 2025 | 4,5 | 1.964 / 1.121 ha | 693 ha | **2,06 / 1,81** | 0,00 |
| Alerces 2023 | 5,1 | 74 / 64 ha | 532 ha | 1,15 / 1,11 | 1,03 |
| Cholila 2015 | 0,1 | 44 / 36 ha | 220 ha | 2,66 / 2,57 | 1,65 |
| Patriada 2026 | 2,3 | 161 / 222 ha | 2.555 ha | **0,45 / 0,50** | 0,22 |
| Alerces 2024 | 5,8 | 70 / 91 ha | 1.070 ha | **0,22 / 0,30** | 0,06 |

Tres lecturas, según el criterio fijado en §2.4:

1. **La semilla FIRMS y la oráculo dan casi lo mismo.** La reconstrucción del perímetro de la
   app (`perimeter_reconstruction.py`) no es la fuente del error. Es la primera evidencia a favor
   de esa reconstrucción, que nunca se había validado (RIESGOS §5).
2. **En Epuyén y Alerces 2016 el "día 1 explosivo" ocurre antes de la primera pasada.** Desde la
   primera detección, el modelo crece lo observado o más. El déficit de 21× y 8× está entero en
   las primeras 2–5 h. La hipótesis de §2.4, que esperaba un déficit de velocidad en Epuyén, no se
   cumplió.
3. **En Patriada y Alerces 2024 queda un déficit de velocidad de 2–4,5×.** Ninguno cae por debajo
   del umbral de 0,2 que se había fijado para declarar "proceso". Es mucho menor que el 6× de la
   cadena, pero existe.

**Consecuencia.** El problema del día 1 deja de ser "el modelo no sirve para las primeras 24 h" y
pasa a ser "las 2–6 h anteriores a la primera detección no son pronosticables". Más un residuo
de 2–3× en dos de seis incendios. Para el uso operativo, el reinicio en cada pasada lo resuelve
casi todo.

### 7.4 Copa: el acople de ELMFIRE casi nunca la enciende donde CFIS sí

Bosque (TU, TL) con dosel que la cicatriz y VIIRS dan por quemado cada día. Se cuenta la fracción
que hace copa en alguna hora anterior a su primera detección (`benchmarks/diagnosticos/copa/`):

| Incendio | Día 1: CFIS (SFC bajo / alto) | Día 1: Van Wagner + Rothermel | Días siguientes: CFIS (SFC bajo) |
|---|---|---:|---|
| Alerces 2023 | 0,99 / 0,99 | 0,005 | 0,14 → 0,00 |
| Alerces 2024 | 0,90 / 1,00 | 0,034 | 0,07 – 0,31 |
| Epuyén 2025 | 1,00 / 1,00 | 0,30 | 0,71 – 0,88 |
| Patriada 2026 | 0,93 / 1,00 | 0,25 | 0,92 – 1,00 |
| Alerces 2016 | 0,68 / 1,00 | 0,23 | 0,26 – 0,41 |
| Cholila 2015 | 0,84 / 0,88 | 0,08 | 0,21 – 0,93 (0,81 en el día 2, el de la explosión) |

Por combustible, el día 1: con el WAF de ELMFIRE bajo dosel (0,07–0,09), Van Wagner **no
enciende copa en ninguna celda** de ñire (TU3), pino (TL8) ni matorral alto (TL2), aunque tengan
CBH de 1–1,5 m. CFIS la enciende en el 99–100 %. Sólo el coihue/ciprés con caña (TU5) llega al
33–83 % en Epuyén, Alerces 2016 y Patriada.

**Lectura.**

- Cruz y Alexander (2010) describen un sesgo de acople. En estos incendios se ve: 68–100 % de copa
  según CFIS contra 0,5–30 % según lo que hace ELMFIRE.
- CFIS además **discrimina el día**. En Alerces 2023 y 2024 la copa es casi total el día 1 y cae
  a 0–30 % después. En Cholila sube el día 2, que es el de la explosión. En Patriada y Epuyén se
  mantiene alta: son los incendios con más arbustal y plantación.
- Combinado con 7.3: en Alerces 2024 y Patriada, que conservan déficit después del reinicio, CFIS
  ve copa el día 1 donde ELMFIRE no.

**Límites.**

- CFIS se ajustó en rodales de coníferas y en terreno llano, con vientos de 3–32 km/h. Aplicarlo
  a ñire y a matorral alto es una extrapolación.
- El SFC es declarado: la cota baja y la alta casi no cambian el resultado.
- El cálculo del lado ELMFIRE es una reimplementación sin pendiente.
- Que la copa se *inicie* no garantiza que la propagación sea la observada.

### 7.5 Qué sigue

- **P-24 queda como el protocolo del pronóstico operativo.** Podría reportarse en la tesis junto
  a modelo-v0, como otra afirmación: "pronóstico a 12–24 h desde la última pasada", +0,10/+0,13
  de Dice contra la cadena y por encima de la persistencia en los seis incendios.
- **No se agrega la opción 2 (ajuste asimilado).** El ΔDice no es chico. Y en los reinicios
  tardíos el error es sobre-propagación por supresión, que un ADJ asimilado absorbería como si
  fuera física.
- **Las primeras 2–6 h quedan como límite declarado**, con los números de 7.3.
- `RIESGOS_Y_SUPOSICIONES.md` §1, §2, §5 y §8, `ESTADO-RESEARCH.md` §6 y `PENDING_PARAMETERS.md`
  quedaron actualizados el 2026-10-12.

### 7.6 Decisión recomendada sobre la copa: no abrir un modelo-v1 por esto

La copa es la explicación con evidencia externa del residuo de Patriada y Alerces 2024: Cruz y
Alexander (2010) más el diagnóstico de 7.4. **Se recomienda declararla como límite cuantificado y
no convertirla en una receta.** Las razones, de la más fuerte a la más débil:

1. **El residuo dura un solo reinicio, y después el modelo ya se pasa.** Sesgo del crecimiento a
   24 h, reinicio por reinicio:
   - Patriada: 0,45 → 0,71 → 0,98 → 110 → 28 → 3,9.
   - Alerces 2024: 0,22 → 1,2 → 2,0 → 2,4 → 1,3 → 1,4 → 2,9 → 4,5.
   - Epuyén, que no tiene residuo: 2,1 → 13 → 49 → 94 → 6,7 → 5,6.

   Cualquier cambio que encienda más copa actúa en todas las horas, no sólo en la primera
   (Rothermel + Van Wagner con WAF bajo dosel apenas cambia de un día a otro), y agrandaría la
   sobre-propagación que ya existe. Es lo mismo que mostró el loop F con CBH bajo: acelera todo el
   incendio, no el salto.
2. **No hay una vía limpia en la versión fijada.** ELMFIRE 2025.0212 tiene un solo criterio de
   iniciación. La única forma de imitar a CFIS sería por insumos: un "CBH equivalente", o una
   humedad foliar por celda y hora (`FMC_FILENAME` existe en `&INPUTS`). Las dos meten valores sin
   sentido físico para forzar un modelo dentro de otro. Es el acople incompatible que critican
   Cruz y Alexander.
3. **Habría que ganarse un modelo-v1 completo** (MODELO-V0 §Contrato): calibración, validación
   cruzada, prueba y comparación contra modelo-v0. Todo para mover el primer reinicio de dos
   incendios, con n = 2 y sin un dato independiente de copa observada.
4. **El uso operativo ya está cubierto.** Con P-24, el residuo afecta sólo a las primeras ~12 h
   desde la primera detección. El reinicio siguiente lo corrige.

**Qué cambiaría esta recomendación:** evidencia de que la copa fue el mecanismo del primer día en
esos incendios. Por ejemplo, Sentinel-2 o imágenes del día 1 con la severidad de copa en las
plantaciones y la caña, o partes que la describan. Con eso, el siguiente paso sería un diagnóstico
de una sola variante, declarada de antemano y sólo sobre el primer reinicio de P-24. Nunca un
barrido.

**Lo que conviene decir en la tesis:**

1. Modelo-v0 no anticipa las primeras 24 h desde la ignición.
2. Casi todo ese déficit está en las 2–6 h previas a la primera detección.
3. Reiniciar en cada pasada da un pronóstico a 12–24 h que le gana a la cadena y a la
   persistencia.
4. El residuo coincide con un sesgo conocido del acople Rothermel + Van Wagner, cuantificado acá
   con CFIS.

## Referencias

Las marcadas con † se leyeron sólo en el resumen o en la ficha bibliográfica, no en el texto
completo.

- Andrews, P. L., Cruz, M. G. y Rothermel, R. C. (2013). Examination of the wind speed limit
  function in the Rothermel surface fire spread model. *IJWF* 22: 959–969. † Citada en el fuente
  de ELMFIRE (`elmfire_spread_rate.f90`, línea comentada).
- Cardil, A., Monedero, S., Ramírez, J. y Silva, C. A. (2019). Assessing and reinitializing
  wildland fire simulations through satellite active fire data. *J. Environ. Manage.* 231:
  996–1003. doi 10.1016/j.jenvman.2018.10.115. †
- Cardil, A., Monedero, S., Silva, C. A. y Ramírez, J. (2019). Adjusting the rate of spread of fire
  simulations in real-time. *Ecol. Model.* 395: 39–44. doi 10.1016/j.ecolmodel.2019.01.017. †
- Chen, Y. et al. (2022). California wildfire spread derived using VIIRS satellite observations and
  an object-based tracking system. *Sci. Data* 9: 249. †
- Coen, J. L. y Schroeder, W. (2013). Use of spatially refined satellite remote sensing fire
  detection data to initialize and evaluate coupled weather-wildfire growth model simulations.
  *GRL* 40. † (Referencia de memoria: la búsqueda sólo encontró la presentación de Giglio, 2016,
  que cita el trabajo de Coen con perímetros VIIRS de 375 m.)
- Crosby, J. S. y Chandler, C. C. (1966). Get the most from your windspeed observation. *Fire
  Control Notes* 27(4). Reimpreso por la NC Forest Service (2009).
- Cruz, M. G. y Alexander, M. E. (2010). Assessing crown fire potential in coniferous forests of
  western North America: a critique of current approaches and recent simulation studies. *IJWF*
  19: 377–398. †
- Cruz, M. G., Alexander, M. E. y Wakimoto, R. H. (2004). Modeling the likelihood of crown fire
  occurrence in conifer forest stands. *Forest Science* 50: 640–658. †
- Cruz, M. G., Alexander, M. E. y Wakimoto, R. H. (2005). Development and testing of models for
  predicting crown fire rate of spread in conifer forest stands. *Can. J. For. Res.* 35:
  1626–1639. (La implementa ELMFIRE, `CROWN_SPREAD_RATE`.)
- Duff, T. J., Chong, D. M. y Tolhurst, K. G. (2016). Indices for the evaluation of wildfire
  spread simulations using contemporaneous predictions and observations of burnt area. *Environ.
  Model. Softw.* 83: 276–285. †
- Lautenberger, C. (2013). Wildland fire modeling with an Eulerian level set method and automated
  calibration. *Fire Saf. J.* 62: 289–298. †
- Lautenberger, C. (2023). *Automated Wildfire Forecasting in the Continental US* (Pyrecast).
  Presentación, SSFSS 2023, Univ. of Maryland.
- Paritsis, J. et al. (2018). Pine plantations and invasion alter fuel structure and potential
  fire behavior in a Patagonian forest-steppe ecotone. *Forests* 9: 117. † (CBH y CBD tomados de
  DECISIONES-MODELO-V0 §2.)
- Rochoux, M. C. et al. (2014). Towards predictive data-driven simulations of wildfire spread –
  Part I. *NHESS* 14: 2951–2973. †
- Sardoy, N. et al. (2008). Numerical study of ground-level distribution of firebrands generated
  by line fires. *Combust. Flame* 154: 478–488. (Distribución que usa `&SPOTTING`.)
- Srivas, T., Artés, T., de Callafon, R. y Altintas, I. (2016). Wildfire spread prediction and
  assimilation for FARSITE using ensemble Kalman filtering. *Procedia Comput. Sci.* 80. †
- *Forest fire spread simulation based on VIIRS active fire data and FARSITE model*. *Journal of
  Remote Sensing* (遥感学报), doi 10.11834/jrs.20219427. †
- arXiv 2204.00686, *Assimilation of Satellite Active Fires Data*; arXiv 2309.02615, *Generative
  Algorithms for Fusion of Physics-Based Wildfire Spread Models with Satellite Data for
  Initializing Wildfire Forecasts*. †
- WFDSS Help: Near-Term Fire Behavior y FARSITE (wfdss.usgs.gov, wfdss.firenet.gov). NIFC RMCC:
  *Comparing the Fire Behavior Tools in WFDSS*.
- ECMWF: ERA5 parameter listing (`fg10`, `i10fg`). NOAA GFS 0,25° en AWS
  (`noaa-gfs-bdp-pds`), inventario `.idx`.
- Partes del SPMF de Chubut citados por ANBariloche (16-ene-2025) y NoticiasNQN (18-nov-2025).
- Fuente de ELMFIRE: `github.com/lautenberger/elmfire`, rama `2025.0212`, `build/source/`
  (`elmfire_namelists.f90`, `elmfire_subs.f90`, `elmfire_level_set.f90`,
  `elmfire_spread_rate.f90`, `elmfire_init.f90`).

## Apéndice: cómo se obtuvieron los números nuevos

No se agregó código al repo. Las cuentas se hicieron con scripts descartables:

- **§1.1 y §1.2.** Las semillas y referencias salen de `benchmarks/casos/*/calibracion*-v6*.paquete.json`
  vía `almacen.abrir`. El TOA de la ventana 0 sale de
  `benchmarks/iteraciones/*/calibracion*-v6*/lw-100-001/manifiesto.json`. Lo observado a cada
  pasada es `benchmark._mascara(detecciones ≤ T)`.
- **§1.3.** Rothermel (1972) con las correcciones de Albini (1976), sobre las filas de
  `app/elmfire/fuel_models.csv` y con la humedad indicada. Es aproximado: sirve para el orden de
  magnitud del límite, no para valores finos.
- **§2.4.** Las pasadas son detecciones de `firms.csv` del paquete separadas por menos de 2 h. Los
  minutos por ventana salen de `corrida.minutos` en los manifiestos de `lw-100-001`.
- **§5.1.** `archive-api.open-meteo.com/v1/archive?models=era5&hourly=wind_speed_10m,wind_gusts_10m`
  en (−42,215, −71,43). El inventario del GFS sale de
  `noaa-gfs-bdp-pds/gfs.20250115/12/atmos/gfs.t12z.pgrb2.0p25.f000.idx`.
